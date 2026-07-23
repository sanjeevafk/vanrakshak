from enum import StrEnum
from pydantic import BaseModel, Field


class MissionState(StrEnum):
    PATROL = "PATROL"
    INVESTIGATE = "INVESTIGATE"
    TRACK = "TRACK"
    VERIFY = "VERIFY"
    ALERT = "ALERT"
    RETURN_HOME = "RETURN_HOME"


RULE_ENGINE_CONFIG = {
    "weights": {"vlm": 0.35, "detector": 0.25, "zone": 0.25, "acoustic": 0.15},
    "thresholds": {"investigate": 45.0, "alert": 85.0, "battery_return": 25.0, "critical_battery": 20.0, "high_confidence": 0.70},
}


class ThreatInput(BaseModel):
    vlm_confidence: float = Field(ge=0, le=1)
    detector_confidence: float = Field(ge=0, le=1)
    zone_risk: float = Field(ge=0, le=1)
    acoustic_score: float = Field(ge=0, le=1)


def threat_score(value: ThreatInput) -> float:
    w = RULE_ENGINE_CONFIG["weights"]
    return round((w["vlm"] * value.vlm_confidence + w["detector"] * value.detector_confidence + w["zone"] * value.zone_risk + w["acoustic"] * value.acoustic_score) * 100, 3)


def next_state(current: MissionState, score: float, battery_pct: float, *, geofence_breached=False, target_verified=False, target_lost=False, ranger_dispatched=False) -> MissionState:
    t = RULE_ENGINE_CONFIG["thresholds"]
    if geofence_breached or battery_pct < t["battery_return"] or (current == MissionState.ALERT and battery_pct < t["critical_battery"]):
        return MissionState.RETURN_HOME
    if current == MissionState.PATROL and score > t["investigate"]:
        return MissionState.INVESTIGATE
    if current == MissionState.INVESTIGATE and target_verified:
        return MissionState.TRACK
    if current == MissionState.TRACK and target_verified:
        return MissionState.VERIFY
    if current == MissionState.VERIFY and score > t["alert"]:
        return MissionState.ALERT
    if current == MissionState.ALERT and ranger_dispatched:
        return MissionState.TRACK
    if current == MissionState.TRACK and target_lost:
        return MissionState.PATROL
    return current


class ActuatorSimulation:
    def __init__(self): self.commands: list[dict] = []
    def emit(self, command: str) -> dict:
        item = {"command": command, "status": "SENT"}
        self.commands.append(item)
        item["status"] = "ACKNOWLEDGED" if command != "FIRE_SUPPRESSANT_DEPLOY" else "UNAVAILABLE"
        return item
