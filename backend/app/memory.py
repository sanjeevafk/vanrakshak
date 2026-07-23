"""Small append-oriented mission read models for deterministic replay."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
from .events import CommandEvent, PolicyDecision, ThreatAssessment, TrackObservation
from .mission import MissionState

@dataclass
class MissionContext:
    mission_id: str
    vehicle_id: str = "drone-1"
    current_state: MissionState = MissionState.PATROL
    replay_timestamp_seconds: float = 0.0
    configuration_version: int = 1
    telemetry: dict[str, Any] = field(default_factory=dict)

class TrackStore:
    def __init__(self) -> None: self.observations: list[TrackObservation] = []
    def append(self, observation: TrackObservation) -> None: self.observations.append(observation)
    def latest(self) -> dict[int, TrackObservation]:
        result: dict[int, TrackObservation] = {}
        for observation in self.observations: result[observation.track_id] = observation
        return result
    def reset(self) -> None: self.observations.clear()

class ThreatStore:
    def __init__(self) -> None:
        self.assessments: list[ThreatAssessment] = []
        self.decisions: list[PolicyDecision] = []
    def append_assessment(self, assessment: ThreatAssessment) -> None: self.assessments.append(assessment)
    def append_decisions(self, decisions: list[PolicyDecision]) -> None: self.decisions.extend(decisions)
    def reset(self) -> None: self.assessments.clear(); self.decisions.clear()

class CommandStore:
    def __init__(self) -> None: self.commands: list[CommandEvent] = []
    def append(self, command: CommandEvent) -> bool:
        if any(existing.command_id == command.command_id for existing in self.commands): return False
        self.commands.append(command); return True
    def acknowledge(self, command_id: str) -> None:
        for command in self.commands:
            if command.command_id == command_id: command.status = "ACKNOWLEDGED"
    def reset(self) -> None: self.commands.clear()

def explain_threat(*, vlm: float, detector: float, zone: float, acoustic: float, evidence_refs: list[str], track_id: int, assessment_id: str) -> ThreatAssessment:
    values = {"vlm": vlm, "detector": detector, "zone": zone, "acoustic": acoustic}
    weights = {"vlm": .35, "detector": .25, "zone": .25, "acoustic": .15}
    contributions = {key: {"value": max(0, min(1, value)), "weight": weights[key], "contribution": round(max(0, min(1, value)) * weights[key] * 100, 3)} for key, value in values.items()}
    total = round(sum(item["contribution"] for item in contributions.values()), 3)
    contributions["total"] = {"value": total, "weight": 1.0, "contribution": total}
    return ThreatAssessment(assessment_id=assessment_id, track_id=track_id, score=total, contributions=contributions, evidence_refs=evidence_refs)
