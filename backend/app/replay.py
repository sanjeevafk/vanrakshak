from __future__ import annotations

from dataclasses import dataclass

from .events import InMemoryEventStore, MissionDiagnostics, MissionSummary, make_event, project_summary
from .mission import MissionState, ThreatInput, threat_score


@dataclass
class ReplayClock:
    timestamp_seconds: float = 0.0
    step_seconds: float = 1.0

    def tick(self) -> float:
        current = self.timestamp_seconds
        self.timestamp_seconds += self.step_seconds
        return current


class MissionRunner:
    """Thin deterministic orchestrator; domain decisions remain in services/policies."""
    def __init__(self, store: InMemoryEventStore) -> None:
        self.store = store

    def run(self, mission_id: str, ticks: int = 3, *, wildlife: bool = False) -> tuple[MissionSummary, MissionDiagnostics]:
        self.store.clear(mission_id)
        clock = ReplayClock()
        state = MissionState.PATROL
        sequence = 0
        track_id = 2 if wildlife else 1

        def emit(event_type: str, source: str, **kwargs):
            nonlocal sequence
            sequence += 1
            return self.store.append(make_event(mission_id, sequence, clock.timestamp_seconds, event_type, source, track_id=kwargs.pop("track_id", None), **kwargs))

        emit("MISSION_STARTED", "mission_control", payload={"state": state.value})
        for _ in range(max(0, ticks)):
            now = clock.tick()
            evidence_id = f"obs-{mission_id}-{sequence + 1:05d}"
            emit("DETECTION_OBSERVED", "perception", track_id=track_id, evidence_refs=[evidence_id], payload={"class_name": "elephant" if wildlife else "person", "confidence": 0.92})
            emit("TRACK_UPDATED", "perception", track_id=track_id, evidence_refs=[evidence_id], payload={"class_name": "elephant" if wildlife else "person", "confidence": 0.92, "timestamp_seconds": now})
            score = threat_score(ThreatInput(vlm_confidence=0.9, detector_confidence=0.92, zone_risk=0.8, acoustic_score=0.3))
            emit("THREAT_ASSESSED", "threat_engine", track_id=track_id, evidence_refs=[evidence_id], payload={"score": score, "policy_id": "wildlife_proximity" if wildlife else "human_intrusion"})
            if state == MissionState.PATROL:
                next_state = MissionState.INVESTIGATE
            elif state == MissionState.INVESTIGATE:
                next_state = MissionState.TRACK
            elif state == MissionState.TRACK:
                next_state = MissionState.VERIFY
            else:
                next_state = MissionState.ALERT if not wildlife else state
            if next_state != state:
                previous = state
                state = next_state
                emit("MISSION_STATE_CHANGED", "mission_state_machine", evidence_refs=[evidence_id], payload={"previous_state": previous.value, "next_state": state.value, "reason_code": "PERSISTENT_EVIDENCE"})
            clock.timestamp_seconds = now + clock.step_seconds
        return project_summary(mission_id, self.store.list_events(mission_id)), MissionDiagnostics(sampled_ticks=max(0, ticks))
