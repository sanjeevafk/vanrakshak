# MAVLink SITL Integration — Agent Execution Plan

**Project:** VanRakshak
**Goal:** Replace the stubbed `MAVLinkAutopilotAdapter` in `backend/app/hardware.py` with a real `pymavlink` transport connected to ArduPilot SITL, wire the adapter into **both** mission paths (synthetic runner + video missions), add a low-battery `RETURN_TO_BASE` dispatch so the demo can show the drone flying home, and surface connection state in the frontend.
**Execution model:** Each agent task is self-contained, has explicit file targets, acceptance criteria, and a rollback note. Tasks must be executed **in order**. If any acceptance criterion fails, stop and report — do not skip ahead.

---

## Architecture after this implementation

```
FastAPI backend (main.py)
  └─ ActuatorAdapter (actuator.py)                 ← unchanged (still the simulated command log)
       └─ MAVLinkAutopilotAdapter (hardware.py)    ← real pymavlink transport
            └─ pymavlink UDP transport
                 └─ ArduPilot SITL (udp:127.0.0.1:14550)
                      └─ MAVProxy map GUI          ← live drone on map

Command fan-out (both mission paths):
  MissionRunner (replay.py)  ─┐
  run_video_mission (main.py) ─┴─> COMMAND_EMITTED events ──> _autopilot.dispatch_action()
```

Policy engine, state machines, mission runner logic, and the frontend mission console are **not** redesigned. Only `hardware.py`, wiring in `main.py`/`config.py`/`replay.py`, one new setting, and a frontend badge change.

---

## Prerequisites (human setup, not agent tasks)

Install these before running any agent task:

```bash
# 1. ArduPilot SITL
pip install MAVProxy
git clone https://github.com/ArduPilot/ardupilot.git --depth=1
cd ardupilot && git submodule update --init --recursive
./Tools/environment_install/install-prereqs-ubuntu.sh -y
./waf configure --board sitl && ./waf copter

# 2. pymavlink (backend dependency is added in Task 1)
pip install pymavlink

# 3. Verify SITL works (run in a separate terminal, keep it running)
cd ardupilot
sim_vehicle.py -v ArduCopter --console --map
# You should see a map window with a drone at a home position.
# MAVProxy by default outputs telemetry to 127.0.0.1:14550 (UDP).
# If you start SITL with --no-mavproxy, add:  --out 127.0.0.1:14550
```

**SITL default UDP port:** `14550` on `127.0.0.1`
**Do not close the SITL terminal** during agent tasks that need a live connection.

---

## Agent Task 1 — Add pymavlink dependency

**Scope:** `backend/requirements.txt`
**Estimated time:** < 1 minute
**Dependencies:** none

### Instructions

Append to `backend/requirements.txt`:

```
pymavlink>=2.4,<3
```

### Acceptance criteria

- `cd backend && .venv/bin/pip install -r requirements.txt` completes without error
- `cd backend && .venv/bin/python -c "import pymavlink; print('ok')"` prints `ok`

### Rollback

Remove the added line. No other files touched.

---

## Agent Task 2 — Implement real MAVLink transport in `hardware.py`

**Scope:** `backend/app/hardware.py` only
**Estimated time:** 15–20 minutes
**Dependencies:** Task 1

### Context

Current `MAVLinkAutopilotAdapter.connect()` always returns `False` (stub). The `AutopilotDriverProtocol` defines the interface that **must be preserved exactly** — `connect`, `dispatch_action`, `is_connected` — because existing tests (`backend/tests/test_hardware.py`) and the backend wiring depend on it.

### Instructions

Replace the entire content of `backend/app/hardware.py` with:

```python
"""Hardware MAVLink autopilot driver seam for onboard drone deployment.

Translates high-level mission state decisions and actuator commands into
MAVLink packets (ArduPilot SITL over UDP, or a real flight controller over
serial). Falls back to SIMULATED mode when pymavlink or the connection is
unavailable — the adapter never crashes the mission pipeline.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any, Protocol


class AutopilotDriverProtocol(Protocol):
    def connect(self, connection_string: str = "serial:///dev/ttyTHS1:57600") -> bool: ...
    def dispatch_action(self, action: str, *, payload: dict[str, Any] | None = None) -> dict[str, Any]: ...
    def is_connected(self) -> bool: ...


# Only flight commands are sent as command_long packets. Everything else is
# surfaced as a STATUSTEXT notification in the MAVProxy/GCS console (SITL does
# not simulate a siren, spotlight, gimbal, or ranger dispatch).
_FLIGHT_COMMANDS = {"RETURN_TO_BASE", "PATROL_SCAN"}

_MAVLINK_CMD_NAME = {
    "RETURN_TO_BASE":  "MAV_CMD_NAV_RETURN_TO_LAUNCH",   # 20 — real flight command
    "PATROL_SCAN":     "MAV_CMD_NAV_LOITER_UNLIM",       # 17 — real flight command
    "GIMBAL_LOCK":     "MAV_CMD_DO_MOUNT_CONTROL",       # 205 — real enum (not sent)
    "SPOTLIGHT_ON":    "MAV_CMD_DO_SET_SERVO",           # 183 — real enum (not sent)
    "SIREN_ACTIVATE":  "MAV_CMD_PAYLOAD_PREPARE_DEPLOY", # 30001 — real enum (not sent)
    "DISPATCH_RANGER": "MAV_CMD_PAYLOAD_CONTROL_DEPLOY",  # 30002 — real enum (not sent)
}


@dataclass
class MAVLinkAutopilotAdapter:
    """MAVLink Autopilot Adapter for PX4 / ArduPilot companion computers.

    Connects via pymavlink over UDP (SITL) or serial (real hardware).
    Falls back to SIMULATED mode if pymavlink is unavailable or connection fails.
    """

    connection_string: str = "serial:///dev/ttyTHS1:57600"
    connected: bool = False
    dispatched_actions: list[dict[str, Any]] = field(default_factory=list)
    _mav: Any = field(default=None, init=False, repr=False)
    _heartbeat_thread: Any = field(default=None, init=False, repr=False)
    _stop_heartbeat: bool = field(default=False, init=False, repr=False)

    def connect(self, connection_string: str | None = None) -> bool:
        """Establish a pymavlink connection to SITL or a real autopilot.

        Connection string formats:
          UDP (SITL):    "udp:127.0.0.1:14550"
          Serial (real): "serial:///dev/ttyTHS1:57600"  (colon-baud form)
          TCP:           "tcp:127.0.0.1:5760"
        """
        if connection_string:
            self.connection_string = connection_string
        try:
            from pymavlink import mavutil  # type: ignore[import]
        except ImportError:
            self.connected = False
            return False
        try:
            cs = self.connection_string
            if cs.startswith("serial://"):
                # "serial:///dev/ttyTHS1:57600" -> device "/dev/ttyTHS1", baud 57600
                device, _, baud = cs[len("serial://"):].partition(":")
                self._mav = mavutil.mavlink_connection(device, baud=int(baud or 57600))
            else:
                self._mav = mavutil.mavlink_connection(cs, baud=57600)
            hb = self._mav.wait_heartbeat(timeout=10)
            if hb is None:
                self.connected = False
                return False
            self._mav.set_mode_auto()
            self.connected = True
            self._start_heartbeat_sender()
            return True
        except Exception:
            self.connected = False
            return False

    def is_connected(self) -> bool:
        return self.connected

    def dispatch_action(self, action: str, *, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        """Dispatch a high-level action to MAVLink or record it as SIMULATED."""
        payload_data = payload or {}
        mavlink_status = "SIMULATED"
        if self.connected and self._mav is not None:
            sent = self._send_mavlink_command(action, payload_data)
            mavlink_status = "SENT" if sent else "SEND_FAILED"
        record = {
            "action": action,
            "connection_string": self.connection_string,
            "mavlink_status": mavlink_status,
            "payload": payload_data,
            "mavlink_cmd": _MAVLINK_CMD_NAME.get(action, f"MAV_CMD_CUSTOM_{action}"),
        }
        self.dispatched_actions.append(record)
        return record

    def _send_mavlink_command(self, action: str, payload: dict[str, Any]) -> bool:
        """Translate a high-level action into a MAVLink packet."""
        try:
            mav = self._mav
            if action == "RETURN_TO_BASE":
                # MAV_CMD_NAV_RETURN_TO_LAUNCH (20)
                mav.mav.command_long_send(
                    mav.target_system, mav.target_component,
                    20, 0, 0, 0, 0, 0, 0, 0, 0,
                )
            elif action == "PATROL_SCAN":
                # MAV_CMD_NAV_LOITER_UNLIM (17) — holds position in a patrol loiter
                mav.mav.command_long_send(
                    mav.target_system, mav.target_component,
                    17, 0, 0, 0, 0, 0, 0, 0, 0,
                )
            else:
                # GCS/payload-side actions (siren, spotlight, dispatch, gimbal):
                # appear in the MAVProxy console; SITL does not model them.
                text = f"VanRakshak: {action}".encode("utf-8")[:50].ljust(50)
                mav.mav.statustext_send(6, text)  # MAV_SEVERITY_INFO
            return True
        except Exception:
            return False

    def _start_heartbeat_sender(self) -> None:
        """Send a GCS heartbeat to SITL every second (required to keep GUIDED/AUTO alive)."""
        self._stop_heartbeat = False

        def _loop() -> None:
            try:
                from pymavlink.dialects.v20 import ardupilotmega as mavdialect  # type: ignore[import]
            except ImportError:
                return
            while not self._stop_heartbeat:
                try:
                    self._mav.mav.heartbeat_send(
                        mavdialect.MAV_TYPE_GCS,
                        mavdialect.MAV_AUTOPILOT_INVALID,
                        0, 0, 0,
                    )
                except Exception:
                    pass
                time.sleep(1.0)

        self._heartbeat_thread = threading.Thread(target=_loop, daemon=True)
        self._heartbeat_thread.start()

    def disconnect(self) -> None:
        """Cleanly close the MAVLink connection."""
        self._stop_heartbeat = True
        if self._mav is not None:
            try:
                self._mav.close()
            except Exception:
                pass
        self.connected = False
```

### Acceptance criteria

- `cd backend && .venv/bin/python -c "from app.hardware import MAVLinkAutopilotAdapter; print(MAVLinkAutopilotAdapter().is_connected())"` prints `False`
- With SITL running: `.connect("udp:127.0.0.1:14550")` returns `True`, `.is_connected()` returns `True`
- `.dispatch_action("RETURN_TO_BASE")` returns `{"mavlink_status": "SENT", ...}`
- With SITL **not** running: `.dispatch_action("SIREN_ACTIVATE")` returns `{"mavlink_status": "SIMULATED", ...}`
- MAVProxy map shows the drone returning home on `RETURN_TO_BASE`
- All existing backend tests pass: `cd backend && .venv/bin/pytest -q`

> **Note:** once pymavlink is installed, the existing `test_mavlink_connect_and_dispatch` (which calls `connect("udp://:14540")` with no SITL running) will take up to ~10 seconds — that is the `wait_heartbeat(timeout=10)` returning `None`. Expected; do not "fix" it by shortening the timeout.

### Rollback

```bash
git checkout backend/app/hardware.py
```

---

## Agent Task 3 — Config field + startup wiring in `main.py`/`config.py`/`.env`

**Scope:** `backend/app/config.py`, `backend/app/main.py`, `backend/.env`
**Estimated time:** 10 minutes
**Dependencies:** Task 2

### Step 1 — Add config fields to `config.py`

In the `Settings` class (after `nvidia_model`), add:

```python
mavlink_connection_string: str | None = None  # e.g. "udp:127.0.0.1:14550"
battery_drain_per_second: float = 0.8         # demo can raise this to reach low battery faster
```

### Step 2 — Add to `backend/.env`

```
MAVLINK_CONNECTION_STRING=udp:127.0.0.1:14550
```

(`config.py` already reads `backend/.env` via `SettingsConfigDict(env_file=(".env", "../.env"))`.)

### Step 3 — Module-level adapter + lifespan in `main.py`

Replace the `app = FastAPI(title="VanRakshak Inference API", version="0.1.0")` line with:

```python
from contextlib import asynccontextmanager

from .hardware import MAVLinkAutopilotAdapter

_autopilot = MAVLinkAutopilotAdapter()


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    conn = settings.mavlink_connection_string
    if conn:
        connected = _autopilot.connect(conn)
        print(f"[MAVLink] {'Connected' if connected else 'SITL unavailable - simulated mode'}: {conn}")
    yield


app = FastAPI(title="VanRakshak Inference API", version="0.1.0", lifespan=lifespan)
```

> Do **not** use `@app.on_event("startup")` — it is deprecated in current FastAPI versions.

### Step 4 — Hardware status endpoint

Add near the other GET endpoints in `main.py`:

```python
@app.get("/hardware/status")
def hardware_status() -> dict:
    return {
        "connected": _autopilot.is_connected(),
        "connection_string": _autopilot.connection_string,
        "mode": "LIVE" if _autopilot.is_connected() else "SIMULATED",
        "dispatched_count": len(_autopilot.dispatched_actions),
    }
```

### Acceptance criteria

- Server starts with no `MAVLINK_CONNECTION_STRING` set → no crash, no MAVLink log line
- Server starts with SITL running → log prints `[MAVLink] Connected ...: udp:127.0.0.1:14550`
- `GET /hardware/status` returns `{"mode": "LIVE", ...}` when SITL is up, `{"mode": "SIMULATED", ...}` when down
- All tests pass: `cd backend && .venv/bin/pytest -q`

### Rollback

```bash
git checkout backend/app/main.py backend/app/config.py
```

---

## Agent Task 4 — Command fan-out to MAVLink + low-battery `RETURN_TO_BASE`

**Scope:** `backend/app/main.py`, `backend/app/replay.py`
**Estimated time:** 20 minutes
**Dependencies:** Task 3

This is what makes the demo truthful: every `COMMAND_EMITTED` event — from **both** the synthetic runner (`POST /missions/{id}/run`, used by the frontend "CONFIRMED HUMAN (DEMO)" / "POACHING SUSPECT (DEMO)" buttons) and video missions (`POST /missions/{id}/run/video`) — is forwarded to the autopilot. And a new low-battery check generates `RETURN_TO_BASE` when the simulated battery crosses the configured threshold, so the demo can visibly land/return the drone.

### Step 1 — Configurable battery drain in the synthetic runner (`backend/app/replay.py`)

In `MissionRunner.run`, locate the `TELEMETRY_UPDATED` emission (currently around line 47):

```python
emit("TELEMETRY_UPDATED", "telemetry_simulator", payload={"battery_pct": round(max(0, min(100, 100 - now * 0.8)), 2), ...})
```

Replace the inline battery formula with a settings-driven value and add the low-battery check immediately after it. At the top of `run` (near `track_id = ...`), add `battery_return_dispatched = False`. Then:

```python
battery_pct = round(max(0, min(100, 100 - now * get_settings().battery_drain_per_second)), 2)
emit("TELEMETRY_UPDATED", "telemetry_simulator", payload={"battery_pct": battery_pct, "gps": {"lat": 13.083 + now * .0001, "lng": 80.272 + now * .0001}, "wind_mps": 3.2})
if battery_pct < RULE_ENGINE_CONFIG["thresholds"]["battery_return"] and not battery_return_dispatched:
    # Note: TELEMETRY_UPDATED is emitted before evidence_id exists in this loop,
    # so the battery command events intentionally carry no evidence refs.
    battery_return_dispatched = True
    command_event = actuator.emit("RETURN_TO_BASE", timestamp_seconds=now)
    emit("COMMAND_EMITTED", "actuator", evidence_refs=[], payload=command_event.model_dump())
    acknowledged = actuator.acknowledge(command_event.command_id)
    if acknowledged:
        emit("COMMAND_ACKNOWLEDGED", "actuator", evidence_refs=[],
             payload={"command_id": acknowledged.command_id, "command": acknowledged.command, "status": acknowledged.status})
```

Imports needed in `replay.py`: `from .config import get_settings` (add). `RULE_ENGINE_CONFIG` and `actuator` are already in scope.

### Step 2 — Same battery drain + check in the video handler (`backend/app/main.py`)

Locate the `TELEMETRY_UPDATED` emission in `run_video_mission` (currently around line 125). Before the frame loop, add `battery_return_dispatched = False`. Add `RULE_ENGINE_CONFIG` to the existing `from .mission import MissionState, ThreatInput, threat_score` line in `main.py` (it is not imported there yet).

> **Important:** the video handler's local `emit` helper has a *different signature* than `replay.py`'s: `emit(event_type, timestamp, *, track_id=None, refs=None, payload=None)` — there is no `source` argument and no `evidence_refs` kwarg. Do **not** copy Step 1 verbatim. Replace the battery formula in the `TELEMETRY_UPDATED` payload with `battery_pct` (computed from `get_settings().battery_drain_per_second`), then add this handler-specific block after the emit (mirroring the handler's existing command-emission code around line 149):

```python
if battery_pct < RULE_ENGINE_CONFIG["thresholds"]["battery_return"] and not battery_return_dispatched:
    battery_return_dispatched = True
    command = actuator.emit("RETURN_TO_BASE", timestamp_seconds=frame.timestamp_seconds)
    emit("COMMAND_EMITTED", frame.timestamp_seconds, refs=[], payload=command.model_dump())
    acknowledged = actuator.acknowledge(command.command_id)
    if acknowledged:
        emit("COMMAND_ACKNOWLEDGED", frame.timestamp_seconds, refs=[],
             payload={"command_id": acknowledged.command_id, "command": acknowledged.command, "status": acknowledged.status})
```

### Step 3 — Forward `COMMAND_EMITTED` events to the autopilot (both handlers in `main.py`)

In `run_mission` (after `runner.run(...)`) and in `run_video_mission` (after the frame loop, before building `summary`), add:

```python
for event in event_store.list_events(mission_id):
    if event.type == "COMMAND_EMITTED":
        _autopilot.dispatch_action(event.payload.get("command", ""), payload={"mission_id": mission_id, "event_id": event.event_id})
```

This covers siren, ranger dispatch, wildlife alerts, and the new `RETURN_TO_BASE` from both paths.

### Acceptance criteria

- Synthetic mission with fast drain reaches `RETURN_TO_BASE`:
  ```bash
  cd backend && .venv/bin/python - <<'PY'
  import os
  os.environ["MAVLINK_BATTERY_DRAIN_PER_SECOND"] = "5.0"
  from app.config import get_settings; get_settings.cache_clear()
  from fastapi.testclient import TestClient
  from app.main import app
  c = TestClient(app)
  c.post("/missions", json={"mission_id": "batt"})
  body = c.post("/missions/batt/run", json={"ticks": 25}).json()
  cmds = [e["payload"]["command"] for e in body["summary"]["commands"]]
  assert "RETURN_TO_BASE" in cmds, cmds
  print("RETURN_TO_BASE emitted:", "RETURN_TO_BASE" in cmds)
  PY
  ```
- `_autopilot.dispatched_actions` contains `RETURN_TO_BASE` after a qualifying run (with SITL up: `mavlink_status == "SENT"`; without: `"SIMULATED"`).
- With SITL running, run a 24-tick synthetic mission from the frontend ("CONFIRMED HUMAN (DEMO)") → MAVProxy console shows `VanRakshak: SIREN_ACTIVATE` and `VanRakshak: DISPATCH_RANGER`.
- Full suite passes: `cd backend && .venv/bin/pytest -q`

### Rollback

```bash
git checkout backend/app/main.py backend/app/replay.py
```

---

## Agent Task 5 — Integration tests

**Scope:** `backend/tests/test_hardware_live.py` (new file)
**Estimated time:** 10 minutes
**Dependencies:** Task 2

Create `backend/tests/test_hardware_live.py`:

```python
"""Integration tests for the MAVLink hardware adapter.

Live tests are skipped automatically when SITL is not running on port 14550.
Run with SITL active: pytest tests/test_hardware_live.py -v -s
"""
import pytest
from app.hardware import MAVLinkAutopilotAdapter    def _sitl_available() -> bool:
        # MAVProxy listens on TCP 5760 (14550 is UDP output, so a TCP probe
        # there never succeeds even when SITL is up). Probe 5760 instead.
        import socket
        try:
            s = socket.create_connection(("127.0.0.1", 5760), timeout=1)
            s.close()
            return True
        except OSError:
            return False


@pytest.mark.skipif(not _sitl_available(), reason="SITL not running on port 14550")
class TestMAVLinkLive:
    def test_connect_returns_true(self):
        adapter = MAVLinkAutopilotAdapter()
        assert adapter.connect("udp:127.0.0.1:14550") is True
        assert adapter.is_connected() is True

    def test_dispatch_return_to_base(self):
        adapter = MAVLinkAutopilotAdapter()
        adapter.connect("udp:127.0.0.1:14550")
        result = adapter.dispatch_action("RETURN_TO_BASE")
        assert result["mavlink_status"] == "SENT"
        assert result["mavlink_cmd"] == "MAV_CMD_NAV_RETURN_TO_LAUNCH"

    def test_dispatch_siren(self):
        adapter = MAVLinkAutopilotAdapter()
        adapter.connect("udp:127.0.0.1:14550")
        result = adapter.dispatch_action("SIREN_ACTIVATE")
        assert result["mavlink_status"] == "SENT"


class TestMAVLinkSimulated:
    """Always runs — no SITL required."""

    def test_connect_fails_gracefully(self):
        adapter = MAVLinkAutopilotAdapter(connection_string="udp:127.0.0.1:19999")
        assert adapter.connect() is False
        assert adapter.is_connected() is False

    def test_dispatch_produces_simulated_status(self):
        adapter = MAVLinkAutopilotAdapter()
        result = adapter.dispatch_action("SIREN_ACTIVATE")
        assert result["mavlink_status"] == "SIMULATED"
        assert "mavlink_cmd" in result

    def test_dispatch_appends_to_log(self):
        adapter = MAVLinkAutopilotAdapter()
        adapter.dispatch_action("PATROL_SCAN")
        adapter.dispatch_action("GIMBAL_LOCK")
        assert len(adapter.dispatched_actions) == 2

    def test_serial_string_parses_device_and_baud(self, monkeypatch):
        # Exercise the serial:// parsing without hardware by faking pymavlink.
        import pymavlink.mavutil as mavutil

        captured: dict[str, object] = {}

        class FakeMav:
            def wait_heartbeat(self, timeout):
                return True

            def set_mode_auto(self):
                pass

            def close(self):
                pass

        def fake_connection(cs, baud=115200):
            captured["cs"] = cs
            captured["baud"] = baud
            return FakeMav()

        monkeypatch.setattr(mavutil, "mavlink_connection", fake_connection)
        adapter = MAVLinkAutopilotAdapter(connection_string="serial:///dev/ttyTHS1:57600")
        assert adapter.connect() is True
        assert captured["cs"] == "/dev/ttyTHS1"
        assert captured["baud"] == 57600
        adapter.disconnect()
```

### Acceptance criteria

- `pytest tests/test_hardware_live.py::TestMAVLinkSimulated -v` passes with no SITL
- `pytest tests/test_hardware_live.py -v` passes fully with SITL running
- `pytest -q` (full suite) still passes

---

## Agent Task 6 — Frontend connection status badge

**Scope:** `frontend/src/App.tsx`
**Estimated time:** 15 minutes
**Dependencies:** Task 3 (endpoint must exist)

### Instructions

**Step 1 — Poll the endpoint.** In `App.tsx`, the backend base URL is the existing `backend` constant (line 6: `const backend = import.meta.env.VITE_BACKEND_URL ?? "http://127.0.0.1:8000";`). Inside the `App` component, after the existing state declarations, add:

```tsx
const [hwMode, setHwMode] = useState<"LIVE" | "SIMULATED">("SIMULATED");

useEffect(() => {
  const poll = () =>
    fetch(`${backend}/hardware/status`)
      .then((r) => r.json())
      .then((d) => setHwMode(d.mode))
      .catch(() => setHwMode("SIMULATED"));
  poll();
  const id = window.setInterval(poll, 5000);
  return () => window.clearInterval(id);
}, []);
```

**Step 2 — Badge in the header.** The header currently ends with `<span className="status">● SYSTEM ONLINE</span>` (line ~212). Add the badge immediately after that span:

```tsx
<span
  style={{
    display: "inline-flex",
    alignItems: "center",
    gap: 4,
    background: hwMode === "LIVE" ? "#16a34a" : "#92400e",
    color: "white",
    borderRadius: 999,
    padding: "3px 12px",
    fontSize: 12,
    fontWeight: 600,
    letterSpacing: "0.02em",
  }}
>
  {hwMode === "LIVE" ? "🟢 SITL Connected" : "🟡 Simulated"}
</span>
```

### Acceptance criteria

- Badge shows `🟡 Simulated` when SITL is off
- Badge shows `🟢 SITL Connected` within 5 seconds of SITL starting
- `cd frontend && npm run typecheck` and `npm run build` pass

---

## Agent Task 7 — End-to-end demo verification (final gate)

**Scope:** manual/scripted verification; no code changes unless a fix is required
**Estimated time:** 15 minutes
**Dependencies:** Tasks 1–6

### Setup

```bash
# Terminal 1 — SITL (keep running)
cd ardupilot && sim_vehicle.py -v ArduCopter --console --map

# Terminal 2 — backend with demo battery drain (drain 3.5%/s so a 24-tick
# synthetic mission crosses the 25% return threshold)
cd vanrakshak/backend
MAVLINK_CONNECTION_STRING=udp:127.0.0.1:14550 MAVLINK_BATTERY_DRAIN_PER_SECOND=3.5 \
  .venv/bin/python -m uvicorn app.main:app --port 8000

# Terminal 3 — frontend
cd vanrakshak/frontend && npm run dev
```

### Checklist (run each and record the result)

1. `GET http://127.0.0.1:8000/health` → `{"status":"ok"}`; backend log shows `[MAVLink] Connected ...: udp:127.0.0.1:14550`
2. `GET http://127.0.0.1:8000/hardware/status` → `{"mode":"LIVE","connected":true,...}`
3. Frontend header shows `🟢 SITL Connected`
4. Click **CONFIRMED HUMAN (DEMO)** → MAVProxy console prints `VanRakshak: SIREN_ACTIVATE` and `VanRakshak: DISPATCH_RANGER`; frontend shows siren banner + `DISPATCH_RANGER ACKNOWLEDGED`
5. Battery crosses 25% during that 24-tick mission (drain 3.5) → MAVProxy map shows the drone returning home; event stream contains `COMMAND_EMITTED` `RETURN_TO_BASE`
6. Upload `demo_videos/02_intruder_vehicle_surveillance.mp4` → `DISPATCH_RANGER` appears in MAVProxy console (vehicle policy). **Note:** `SIREN_ACTIVATE` will *not* fire for video missions — the human siren requires VLM-confirmed evidence, which the video path does not provide. Use the synthetic "CONFIRMED HUMAN (DEMO)" button for the siren demo.
7. Full suites pass: `cd backend && .venv/bin/pytest -q`; `cd frontend && npm test && npm run typecheck && npm run build`

### Definition of Done (greenlight)

All seven checklist items pass with the evidence recorded. If any fails, fix forward in the owning task and re-run this gate.

---

## Known limitations

- SITL does not simulate a physical gimbal, siren, spotlight, or ranger dispatch — those appear as `STATUSTEXT` in the MAVProxy console (`VanRakshak: <ACTION>`)
- `RETURN_TO_BASE` (RTL) and `PATROL_SCAN` (loiter) cause visible drone movement; all other actions are console-only
- Human siren for **video** missions still requires VLM-confirmed evidence (`vlm_confirmed=True`); the synthetic runner and frontend demo buttons provide the deterministic siren path
- Real hardware serial: `MAVLINK_CONNECTION_STRING=serial:///dev/ttyUSB0:57600` (verified parsing in Task 2, but still needs hardware to test end-to-end)
- `dispatched_actions` list is not thread-locked — safe for demo; add `threading.Lock` for production
- Backend in-memory mission state is lost on restart; MAVLink connectivity is re-established on each startup via the lifespan hook
