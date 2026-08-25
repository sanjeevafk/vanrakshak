import asyncio
import pytest
from app.actuator import ActuatorAdapter
from app.mission import MissionState
from app.policies import PolicyEngine
from app.state_machines import transition_mission
from app.vlm import VLMAdapter

@pytest.mark.parametrize("name,data,expected", [
    ("no-threat", {"class_name": "bird"}, 0),
    ("persistent-person", {"class_name": "person", "persistent": True, "confidence": .9, "vlm_confirmed": True, "track_id": 1}, 1),
    ("vehicle", {"class_name": "car", "confidence": .8, "track_id": 2}, 1),
    ("elephant", {"class_name": "elephant", "confidence": .9, "track_id": 3}, 1),
    ("thermal", {"input_type": "thermal"}, 1),
])
def test_policy_scenarios(name, data, expected):
    assert len(PolicyEngine().evaluate(data)) == expected, name

def test_battery_and_geofence_overrides():
    assert transition_mission(MissionState.PATROL, battery_pct=24).next_state == MissionState.RETURN_HOME
    assert transition_mission(MissionState.TRACK, geofence_breached=True).next_state == MissionState.RETURN_HOME
    assert transition_mission(MissionState.TRACK, target_lost=True).next_state == MissionState.PATROL

def test_wildlife_railway_and_suppressant_commands():
    adapter = ActuatorAdapter("scenario")
    wildlife = adapter.for_policy("wildlife_proximity", incident_id="wildlife-1")
    assert {command.command for command in wildlife} == {"WILDLIFE_ALERT", "DISPATCH_RANGER"}
    railway = adapter.for_policy("railway_conflict", incident_id="railway-1")
    assert {command.command for command in railway} == {"WILDLIFE_ALERT", "DISPATCH_RANGER"}
    assert all(c.status == "SENT" for c in railway)
    assert adapter.emit("FIRE_SUPPRESSANT_DEPLOY").status == "SENT"

def test_vlm_timeout_fallback_scenario():
    async def timeout(_):
        await asyncio.sleep(.02)
        return '{"vlm_confidence": 1}'
    result = asyncio.run(VLMAdapter(request=timeout, timeout_seconds=.001).analyze(track_id=9, crop=b"scenario", artifact_ref="a", evidence_id="e"))
    assert result.fallback_reason == "TIMEOUT" and result.confidence == 0
