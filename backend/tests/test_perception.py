from app.perception import CropCandidate, CropSelector, InMemoryArtifactStore, assign_fallback_track_ids, filter_detections
from app.schemas import Detection

def test_filters_low_confidence_and_assigns_unique_fallback_ids():
    detections = [Detection(track_id=0, **{"class": "person"}, confidence=.2, bbox=[0, 0, 1, 1]), Detection(track_id=0, **{"class": "person"}, confidence=.8, bbox=[0, 0, 1, 1])]
    result = assign_fallback_track_ids(filter_detections(detections))
    assert len(result) == 1 and result[0].track_id == 1_000_000

def test_artifact_references_are_deterministic():
    store = InMemoryArtifactStore(); assert store.put(b"crop") == store.put(b"crop")

def test_crop_selection_is_bounded_diverse_and_deduplicated():
    candidates = [CropCandidate(1, t, f"a{t}", .9 - t / 100, .2) for t in range(5)] + [CropCandidate(1, 0, "a0", .9, .2)]
    selected = CropSelector().select(candidates)
    assert len(selected) <= 3 and len({c.artifact_ref for c in selected}) == len(selected)
    assert all(abs(selected[i].timestamp_seconds - selected[j].timestamp_seconds) >= 1 for i in range(len(selected)) for j in range(i))
