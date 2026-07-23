from app.events import InMemoryEventStore
from app.perception import InMemoryArtifactStore, PerceptionPipeline
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
