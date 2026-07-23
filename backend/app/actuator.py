"""Simulated actuator adapter; no physical or MAVLink side effects."""
from __future__ import annotations
from dataclasses import dataclass
from .events import CommandEvent

MISSION_COMMANDS = {"PATROL": "PATROL_SCAN", "INVESTIGATE": "SPOTLIGHT_ON", "TRACK": "GIMBAL_LOCK", "VERIFY": "CAPTURE_VERIFICATION_FRAMES", "RETURN_HOME": "RETURN_TO_BASE"}

@dataclass
class ActuatorAdapter:
    mission_id: str
    emitted: list[CommandEvent] | None = None

    def __post_init__(self) -> None:
        if self.emitted is None: self.emitted = []

    def emit(self, command: str, *, timestamp_seconds: float = 0.0, incident_id: str | None = None, evidence_refs: list[str] | None = None, policy_id: str | None = None) -> CommandEvent:
        command_id = f"cmd-{self.mission_id}-{len(self.emitted or []) + 1:05d}"
        if command == "FIRE_SUPPRESSANT_DEPLOY": status = "UNAVAILABLE"
        else: status = "SENT"
        event = CommandEvent(command_id=command_id, command=command, status=status, mission_id=self.mission_id, incident_id=incident_id, evidence_refs=evidence_refs or [])
        if not any(item.command == command and item.incident_id == incident_id for item in self.emitted or []):
            self.emitted.append(event)
        else:
            return next(item for item in self.emitted or [] if item.command == command and item.incident_id == incident_id)
        if status == "SENT": event.status = "ACKNOWLEDGED"
        return event

    def for_mission_state(self, state: str, *, timestamp_seconds: float = 0.0, evidence_refs: list[str] | None = None) -> CommandEvent:
        return self.emit(MISSION_COMMANDS[state], timestamp_seconds=timestamp_seconds, evidence_refs=evidence_refs)

    def for_policy(self, policy_id: str, *, incident_id: str | None = None, timestamp_seconds: float = 0.0, evidence_refs: list[str] | None = None) -> list[CommandEvent]:
        commands = {"human_intrusion": ["SIREN_ACTIVATE", "DISPATCH_RANGER"], "wildlife_proximity": ["WILDLIFE_ALERT", "DISPATCH_RANGER"], "railway_conflict": ["WILDLIFE_ALERT", "DISPATCH_RANGER"], "thermal_fire": ["UNSUPPORTED_INPUT"]}.get(policy_id, [])
        return [self.emit(command, timestamp_seconds=timestamp_seconds, incident_id=incident_id, evidence_refs=evidence_refs, policy_id=policy_id) for command in commands]
