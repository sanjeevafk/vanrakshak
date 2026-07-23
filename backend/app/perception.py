"""Perception seams used by replay and future live-like input."""
from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
from typing import Protocol
from .schemas import Detection
from .events import InMemoryEventStore, make_event
from .events import Evidence

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

class EvidenceStore:
    def __init__(self, max_per_track: int = 32) -> None:
        self.max_per_track = max_per_track
        self._items: dict[str, list[Evidence]] = {}

    def append(self, evidence: Evidence, track_id: int | None = None) -> None:
        key = str(track_id) if track_id is not None else "mission"
        bucket = self._items.setdefault(key, [])
        bucket.append(evidence)
        del bucket[:-self.max_per_track]

    def list_for_track(self, track_id: int) -> list[Evidence]:
        return list(self._items.get(str(track_id), []))

    def reset(self) -> None:
        self._items.clear()

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

def extract_crop(frame_bytes: bytes, bbox: list[float], *, image_format: str = ".jpg") -> bytes:
    """Extract a clamped encoded crop; keeps raw frame data out of event payloads."""
    try:
        import cv2
        import numpy as np
        image = cv2.imdecode(np.frombuffer(frame_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError("invalid image bytes")
        height, width = image.shape[:2]
        x1, y1, x2, y2 = [int(round(value)) for value in bbox]
        x1, x2 = max(0, min(x1, width - 1)), max(0, min(x2, width))
        y1, y2 = max(0, min(y1, height - 1)), max(0, min(y2, height))
        if x2 <= x1 or y2 <= y1:
            raise ValueError("empty crop bounds")
        ok, encoded = cv2.imencode(image_format, image[y1:y2, x1:x2])
        if not ok:
            raise ValueError("crop encoding failed")
        return encoded.tobytes()
    except ImportError as error:
        raise RuntimeError("opencv is required for crop extraction") from error

class TrackEvidenceBuilder:
    def __init__(self, artifacts: InMemoryArtifactStore, selector: CropSelector | None = None) -> None:
        self.artifacts = artifacts
        self.selector = selector or CropSelector(max_per_track=3)
        self._candidates: dict[int, list[CropCandidate]] = {}

    def add(self, *, track_id: int, frame_bytes: bytes, bbox: list[float], timestamp_seconds: float, detector_confidence: float, area: float = 0.0, sharpness: float = 0.0) -> CropCandidate:
        crop = extract_crop(frame_bytes, bbox)
        candidate = CropCandidate(track_id, timestamp_seconds, self.artifacts.put(crop), detector_confidence, area, sharpness)
        self._candidates.setdefault(track_id, []).append(candidate)
        return candidate

    def selected(self, track_id: int) -> list[CropCandidate]:
        return self.selector.select(self._candidates.get(track_id, []))

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
