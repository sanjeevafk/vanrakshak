"""Simulated actuator adapter; no physical or MAVLink side effects."""
from __future__ import annotations
from dataclasses import dataclass, field
from .events import CommandEvent

MISSION_COMMANDS = {"PATROL": "PATROL_SCAN", "INVESTIGATE": "SPOTLIGHT_ON", "TRACK": "GIMBAL_LOCK", "VERIFY": "CAPTURE_VERIFICATION_FRAMES", "ALERT": "ALERT_BEACON_ON", "RETURN_HOME": "RETURN_TO_BASE"}

@dataclass
class ActuatorAdapter:
    mission_id: str
    emitted: list[CommandEvent] = field(default_factory=list)

    def emit(self, command: str, *, timestamp_seconds: float = 0.0, incident_id: str | None = None, evidence_refs: list[str] | None = None, policy_id: str | None = None) -> CommandEvent:
        command_id = f"cmd-{self.mission_id}-{len(self.emitted) + 1:05d}"
        if command in {"FIRE_SUPPRESSANT_DEPLOY", "UNSUPPORTED_INPUT"}: status = "UNAVAILABLE"
        else: status = "SENT"
        event = CommandEvent(command_id=command_id, command=command, status=status, mission_id=self.mission_id, incident_id=incident_id, evidence_refs=evidence_refs or [], policy_id=policy_id)
        if not any(item.command == command and item.incident_id == incident_id for item in self.emitted):
            self.emitted.append(event)
        else:
            return next(item for item in self.emitted if item.command == command and item.incident_id == incident_id)
        return event

    def acknowledge(self, command_id: str) -> CommandEvent | None:
        for command in self.emitted:
            if command.command_id == command_id and command.status == "SENT":
                command.status = "ACKNOWLEDGED"
                return command
        return None

    def for_mission_state(self, state: str, *, timestamp_seconds: float = 0.0, evidence_refs: list[str] | None = None) -> CommandEvent:
        return self.emit(MISSION_COMMANDS[state], timestamp_seconds=timestamp_seconds, evidence_refs=evidence_refs)

    def for_policy(self, policy_id: str, *, incident_id: str | None = None, timestamp_seconds: float = 0.0, evidence_refs: list[str] | None = None) -> list[CommandEvent]:
        supported_commands = {
            "human_intrusion": ["SIREN_ACTIVATE", "DISPATCH_RANGER"],
            "wildlife_proximity": ["WILDLIFE_ALERT", "DISPATCH_RANGER"],
            "vehicle_intrusion": ["DISPATCH_RANGER"],
        }
        if policy_id in supported_commands:
            return [self.emit(command, timestamp_seconds=timestamp_seconds, incident_id=incident_id, evidence_refs=evidence_refs, policy_id=policy_id) for command in supported_commands[policy_id]]
        return [self.emit("UNSUPPORTED_INPUT", timestamp_seconds=timestamp_seconds, incident_id=incident_id, evidence_refs=evidence_refs, policy_id=policy_id)]
