from app.actuator import ActuatorAdapter, MISSION_COMMANDS
from app.mission import MissionState

def test_every_mission_state_has_mapping():
    assert set(MISSION_COMMANDS) == {state.value for state in MissionState}

def test_for_mission_state_alert():
    adapter = ActuatorAdapter("m1")
    event = adapter.for_mission_state("ALERT")
    assert event.command == "ALERT_BEACON_ON"
    assert event.status == "SENT"


def test_human_and_wildlife_actions_are_distinct():
    adapter = ActuatorAdapter("m1")
    human = adapter.for_policy("human_intrusion", incident_id="i1")
    wildlife = adapter.for_policy("wildlife_proximity", incident_id="i2")
    assert any(c.command == "SIREN_ACTIVATE" for c in human)
    assert all(c.command != "SIREN_ACTIVATE" for c in wildlife)
    assert all(c.status == "SENT" for c in human + wildlife)
    assert all(c.policy_id == "human_intrusion" for c in human)
    assert all(c.policy_id == "wildlife_proximity" for c in wildlife)

def test_duplicate_commands_and_suppressant():
    adapter = ActuatorAdapter("m1")
    first = adapter.emit("PATROL_SCAN"); second = adapter.emit("PATROL_SCAN")
    assert first.command_id == second.command_id and len(adapter.emitted) == 1
    assert adapter.emit("FIRE_SUPPRESSANT_DEPLOY").status == "SENT"


def test_thermal_policy_produces_suppressant_and_dispatch():
    adapter = ActuatorAdapter("m1")
    thermal = adapter.for_policy("thermal_fire", incident_id="i2")
    assert any(c.command == "FIRE_SUPPRESSANT_DEPLOY" for c in thermal)
    assert any(c.command == "DISPATCH_RANGER" for c in thermal)
    assert all(c.status == "SENT" for c in thermal)

