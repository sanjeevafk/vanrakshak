from app.events import InMemoryEventStore
from app.perception import EvidenceStore, InMemoryArtifactStore, PerceptionPipeline, TrackEvidenceBuilder, extract_crop
from app.events import Evidence
from app.schemas import Detection

class Detector:
    def detect(self, frame): return [Detection(track_id=0, **{"class": "person"}, confidence=.8, bbox=[0, 0, 1, 1])]
class Tracker:
    def update(self, detections): return detections

def test_pipeline_emits_evidence_linked_detection_and_track_events():
    store = InMemoryEventStore()
    result = PerceptionPipeline(Detector(), Tracker(), InMemoryArtifactStore()).process_frame("m1", b"frame", 1, store)
    events = store.list_events("m1")
    assert result[0].track_id == 1_000_000
    assert [event.type for event in events] == ["DETECTION_OBSERVED", "TRACK_UPDATED"]
    assert events[0].evidence_refs == events[1].evidence_refs

def test_evidence_store_is_bounded_per_track():
    store = EvidenceStore(max_per_track=2)
    for index in range(3):
        store.append(Evidence(evidence_id=f"e{index}", mission_id="m1", kind="crop", timestamp_seconds=index), track_id=1)
    assert [item.evidence_id for item in store.list_for_track(1)] == ["e1", "e2"]

def test_extract_crop_clamps_bounds():
    import cv2
    import numpy as np
    ok, encoded = cv2.imencode(".jpg", np.zeros((20, 20, 3), dtype=np.uint8))
    crop = extract_crop(encoded.tobytes(), [-5, -5, 10, 10])
    assert crop and crop != encoded.tobytes()

def test_extract_crop_accepts_raw_decoded_frame():
    # Regression: the video mission on_sample callback hands over raw decoded BGR
    # frames (numpy arrays), not encoded bytes. Crops must still be extractable so
    # per-track VLM enrichment is not silently dropped on video missions.
    import cv2
    import numpy as np
    frame = np.zeros((40, 40, 3), dtype=np.uint8)
    frame[10:30, 10:30] = (0, 255, 0)
    crop = extract_crop(frame, [10, 10, 30, 30])
    assert crop
    decoded = cv2.imdecode(np.frombuffer(crop, dtype=np.uint8), cv2.IMREAD_COLOR)
    assert decoded.shape[:2] == (20, 20)

def test_track_evidence_builder_accepts_raw_decoded_frames():
    import cv2
    import numpy as np
    frame = np.zeros((40, 40, 3), dtype=np.uint8)
    frame[10:30, 10:30] = (0, 255, 0)
    builder = TrackEvidenceBuilder(InMemoryArtifactStore())
    builder.add(track_id=9, frame_bytes=frame, bbox=[10, 10, 30, 30], timestamp_seconds=0, detector_confidence=.9)
    selected = builder.selected(9)
    assert len(selected) == 1
    assert selected[0].artifact_ref.startswith("artifact-")

def test_track_evidence_builder_stores_bounded_crop_artifacts():
    import cv2
    import numpy as np
    ok, encoded = cv2.imencode(".jpg", np.zeros((20, 20, 3), dtype=np.uint8))
    builder = TrackEvidenceBuilder(InMemoryArtifactStore())
    for timestamp in range(5):
        builder.add(track_id=4, frame_bytes=encoded.tobytes(), bbox=[0, 0, 10, 10], timestamp_seconds=timestamp, detector_confidence=.8)
    assert len(builder.selected(4)) <= 3
