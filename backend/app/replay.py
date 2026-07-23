from __future__ import annotations

from dataclasses import dataclass

from .events import InMemoryEventStore, MissionDiagnostics, MissionSummary, make_event, project_summary
from .mission import MissionState, ThreatInput, RULE_ENGINE_CONFIG, threat_score
from .policies import PolicyEngine
from .actuator import ActuatorAdapter
from .state_machines import transition_incident
from .events import IncidentState


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
        incident_states: dict[int, IncidentState] = {}
        policies = PolicyEngine()
        actuator = ActuatorAdapter(mission_id)
        sequence = 0
        track_id = 2 if wildlife else 1

        def emit(event_type: str, source: str, **kwargs):
            nonlocal sequence
            sequence += 1
            return self.store.append(make_event(mission_id, sequence, clock.timestamp_seconds, event_type, source, track_id=kwargs.pop("track_id", None), **kwargs))

        emit("MISSION_STARTED", "mission_control", payload={"state": state.value})
        for _ in range(max(0, ticks)):
            now = clock.tick()
            emit("TELEMETRY_UPDATED", "telemetry_simulator", payload={"battery_pct": round(100 - now * 0.8, 2), "gps": {"lat": 13.083 + now * .0001, "lng": 80.272 + now * .0001}, "wind_mps": 3.2})
            evidence_id = f"obs-{mission_id}-{sequence + 1:05d}"
            emit("DETECTION_OBSERVED", "perception", track_id=track_id, evidence_refs=[evidence_id], payload={"class_name": "elephant" if wildlife else "person", "confidence": 0.92})
            emit("TRACK_UPDATED", "perception", track_id=track_id, evidence_refs=[evidence_id], payload={"class_name": "elephant" if wildlife else "person", "confidence": 0.92, "timestamp_seconds": now})
            score = threat_score(ThreatInput(vlm_confidence=0.9, detector_confidence=0.92, zone_risk=0.8, acoustic_score=0.3))
            emit("THREAT_ASSESSED", "threat_engine", track_id=track_id, evidence_refs=[evidence_id], payload={"score": score, "policy_id": "wildlife_proximity" if wildlife else "human_intrusion"})
            decisions = policies.evaluate({"class_name": "elephant" if wildlife else "person", "confidence": .92, "persistent": True, "vlm_confirmed": not wildlife, "track_id": track_id, "evidence_refs": [evidence_id]})
            for decision in decisions:
                t_id = decision.track_id if decision.track_id is not None else track_id
                emit("POLICY_EVALUATED", "policy_engine", track_id=t_id, evidence_refs=[evidence_id], payload=decision.model_dump())
                current_inc_state = incident_states.get(t_id, IncidentState.OBSERVED)
                incident_transition = transition_incident(current_inc_state, persistent=True, verified=decision.decision == "RECOMMEND_ALERT")
                incident_states[t_id] = IncidentState(incident_transition.next_state)
                emit(
                    "INCIDENT_STATE_CHANGED",
                    "incident_state_machine",
                    track_id=t_id,
                    evidence_refs=[evidence_id],
                    payload={
                        "previous_state": incident_transition.previous_state,
                        "next_state": incident_transition.next_state,
                        "reason_code": incident_transition.reason_code,
                        "explanation": incident_transition.explanation,
                        "policy_id": decision.policy_id,
                        "thresholds": RULE_ENGINE_CONFIG["thresholds"],
                    },
                )
                for command in decision.recommended_actions:
                    command_event = actuator.emit(command, timestamp_seconds=now, incident_id=f"incident-{t_id}", evidence_refs=[evidence_id], policy_id=decision.policy_id)
                    emit("COMMAND_EMITTED", "actuator", track_id=t_id, evidence_refs=[evidence_id], payload=command_event.model_dump())
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
