"""Perception seams used by replay and future live-like input."""
from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
from typing import Protocol
from .schemas import Detection
from .events import InMemoryEventStore, make_event

class DetectorAdapter(Protocol):
    def detect(self, frame: bytes) -> list[Detection]: ...
class TrackerAdapter(Protocol):
    def update(self, detections: list[Detection]) -> list[Detection]: ...
class ArtifactStore(Protocol):
    def put(self, content: bytes, *, media_type: str = "image/jpeg") -> str: ...

class InMemoryArtifactStore:
    def __init__(self) -> None: self._items: dict[str, tuple[bytes, str]] = {}
    def put(self, content: bytes, *, media_type: str = "image/jpeg") -> str:
        artifact_id = f"artifact-{sha256(content).hexdigest()[:16]}"
        self._items.setdefault(artifact_id, (content, media_type)); return artifact_id
    def get(self, artifact_id: str) -> tuple[bytes, str] | None: return self._items.get(artifact_id)

@dataclass(frozen=True)
class CropCandidate:
    track_id: int; timestamp_seconds: float; artifact_ref: str; detector_confidence: float; area: float; sharpness: float = 0.0; occlusion: float = 0.0

class CropSelector:
    def __init__(self, max_per_track: int = 3, min_temporal_spacing: float = 1.0) -> None: self.max_per_track, self.min_temporal_spacing = max_per_track, min_temporal_spacing
    def select(self, candidates: list[CropCandidate]) -> list[CropCandidate]:
        selected: list[CropCandidate] = []
        for candidate in sorted(candidates, key=lambda c: (c.detector_confidence, c.area, c.sharpness, c.timestamp_seconds), reverse=True):
            if candidate.artifact_ref in {item.artifact_ref for item in selected}: continue
            if selected and all(abs(candidate.timestamp_seconds - item.timestamp_seconds) < self.min_temporal_spacing for item in selected): continue
            selected.append(candidate)
            if len(selected) >= self.max_per_track: break
        return selected

def filter_detections(detections: list[Detection], confidence_threshold: float = 0.35) -> list[Detection]:
    return [d for d in detections if d.confidence >= confidence_threshold]

def assign_fallback_track_ids(detections: list[Detection], start: int = 1_000_000) -> list[Detection]:
    used: set[int] = set(); next_id = start; result: list[Detection] = []
    for detection in detections:
        track_id = detection.track_id
        if track_id in used or track_id <= 0:
            while next_id in used: next_id += 1
            track_id, next_id = next_id, next_id + 1
        used.add(track_id); result.append(detection.model_copy(update={"track_id": track_id}))
    return result

class PerceptionPipeline:
    def __init__(self, detector: DetectorAdapter, tracker: TrackerAdapter, artifacts: ArtifactStore, confidence_threshold: float = .35) -> None:
        self.detector, self.tracker, self.artifacts, self.confidence_threshold = detector, tracker, artifacts, confidence_threshold

    def process_frame(self, mission_id: str, frame: bytes, timestamp_seconds: float, store: InMemoryEventStore) -> list[Detection]:
        detections = assign_fallback_track_ids(filter_detections(self.detector.detect(frame), self.confidence_threshold))
        tracked = assign_fallback_track_ids(filter_detections(self.tracker.update(detections), self.confidence_threshold))
        artifact_ref = self.artifacts.put(frame)
        sequence = store.get_last_sequence(mission_id)
        for detection in tracked:
            sequence += 1
            refs = [artifact_ref]
            store.append(make_event(mission_id, sequence, timestamp_seconds, "DETECTION_OBSERVED", "perception", track_id=detection.track_id, evidence_refs=refs, payload=detection.model_dump(by_alias=True)))
            sequence += 1
            store.append(make_event(mission_id, sequence, timestamp_seconds, "TRACK_UPDATED", "perception", track_id=detection.track_id, evidence_refs=refs, payload=detection.model_dump(by_alias=True)))
        return tracked
