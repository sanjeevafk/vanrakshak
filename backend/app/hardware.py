"""Hardware MAVLink autopilot driver seam for onboard drone deployment.

Translates high-level mission state decisions and actuator commands into
MAVLink serial telemetry packets (PX4 / ArduPilot flight controllers).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


class AutopilotDriverProtocol(Protocol):
    def connect(self, connection_string: str = "serial:///dev/ttyTHS1:57600") -> bool: ...
    def dispatch_action(self, action: str, *, payload: dict[str, Any] | None = None) -> dict[str, Any]: ...
    def is_connected(self) -> bool: ...


@dataclass
class MAVLinkAutopilotAdapter:
    """MAVLink Autopilot Adapter for PX4 / ArduPilot companion computers."""

    connection_string: str = "serial:///dev/ttyTHS1:57600"
    connected: bool = False
    dispatched_actions: list[dict[str, Any]] = field(default_factory=list)

    def connect(self, connection_string: str | None = None) -> bool:
        if connection_string:
            self.connection_string = connection_string
        # A real transport is intentionally not included in this MVP. Never claim
        # hardware connectivity when only the seam is available.
        self.connected = False
        return False

    def is_connected(self) -> bool:
        return self.connected

    def dispatch_action(self, action: str, *, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        """Dispatches high-level actions to MAVLink serial commands or payload relays."""
        payload_data = payload or {}
        record = {
            "action": action,
            "connection_string": self.connection_string,
            "mavlink_status": "SENT" if self.connected else "SIMULATED",
            "payload": payload_data,
        }

        if action == "RETURN_TO_BASE":
            record["mavlink_cmd"] = "MAV_CMD_NAV_RETURN_TO_LAUNCH"
        elif action == "GIMBAL_LOCK":
            record["mavlink_cmd"] = "MAV_CMD_DO_MOUNT_CONTROL"
        elif action == "SPOTLIGHT_ON":
            record["mavlink_cmd"] = "MAV_CMD_DO_SET_SERVO"
        elif action == "SIREN_ACTIVATE":
            record["mavlink_cmd"] = "MAV_CMD_PAYLOAD_PREPARE_DEPLOY"
        elif action == "DISPATCH_RANGER":
            record["mavlink_cmd"] = "MAV_CMD_NAV_WAYPOINT_SEND_TELEMETRY"
        else:
            record["mavlink_cmd"] = f"MAV_CMD_CUSTOM_{action}"

        self.dispatched_actions.append(record)
        return record
