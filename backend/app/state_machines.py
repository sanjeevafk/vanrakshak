from __future__ import annotations

from dataclasses import dataclass

from .events import IncidentState
from .mission import MissionState


@dataclass(frozen=True)
class Transition:
    previous_state: str
    next_state: str
    reason_code: str
    explanation: str
    evidence_refs: tuple[str, ...] = ()


def transition_mission(current: MissionState, *, threat_score: float = 0, battery_pct: float = 100, geofence_breached: bool = False, target_verified: bool = False, target_lost: bool = False, ranger_dispatched: bool = False) -> Transition:
    if geofence_breached:
        return Transition(current, MissionState.RETURN_HOME, "GEOFENCE_BREACH", "Return home because the geofence was breached.")
    if battery_pct < 25 or (current == MissionState.ALERT and battery_pct < 20):
        return Transition(current, MissionState.RETURN_HOME, "LOW_BATTERY", "Return home because battery is below the configured threshold.")
    next_state = current
    reason = "NO_CHANGE"
    explanation = "No mission transition conditions were met."
    if current == MissionState.PATROL and threat_score > 45:
        next_state, reason, explanation = MissionState.INVESTIGATE, "THREAT_DETECTED", "Investigate persistent threat evidence."
    elif current == MissionState.INVESTIGATE and target_verified:
        next_state, reason, explanation = MissionState.TRACK, "TARGET_VERIFIED", "Track the verified target."
    elif current == MissionState.TRACK and target_verified:
        next_state, reason, explanation = MissionState.VERIFY, "VERIFICATION_REQUIRED", "Capture verification evidence."
    elif current == MissionState.VERIFY and threat_score > 85:
        next_state, reason, explanation = MissionState.ALERT, "HIGH_CONFIRMED_THREAT", "Escalate the confirmed high-severity threat."
    elif current == MissionState.TRACK and target_lost:
        next_state, reason, explanation = MissionState.PATROL, "TARGET_LOST", "Resume patrol after target loss."
    elif current == MissionState.ALERT and ranger_dispatched:
        next_state, reason, explanation = MissionState.TRACK, "RANGER_DISPATCH_ACK", "Continue observation after ranger acknowledgement."
    return Transition(current, next_state, reason, explanation)


def transition_incident(current: IncidentState, *, persistent: bool = False, under_review: bool = False, verified: bool = False, dispatched: bool = False, resolved: bool = False, expired: bool = False) -> Transition:
    if expired:
        return Transition(current, IncidentState.EXPIRED, "TARGET_LOST_TIMEOUT", "Expire the incident after the configured target-loss timeout.")
    if resolved:
        return Transition(current, IncidentState.RESOLVED, "INCIDENT_RESOLVED", "Incident resolution was acknowledged.")
    if dispatched:
        return Transition(current, IncidentState.DISPATCHED, "RANGER_DISPATCHED", "Ranger dispatch was acknowledged.")
    if verified:
        return Transition(current, IncidentState.VERIFIED, "EVIDENCE_VERIFIED", "Evidence met the verification requirement.")
    if under_review:
        return Transition(current, IncidentState.UNDER_REVIEW, "POLICY_REVIEW", "Policy requested additional review.")
    if persistent:
        return Transition(current, IncidentState.PERSISTING, "PERSISTENT_TRACK", "Track persisted across replay ticks.")
    return Transition(current, IncidentState.OBSERVED, "OBSERVATION_RECORDED", "Observation was recorded.")
