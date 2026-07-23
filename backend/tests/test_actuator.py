from app.actuator import ActuatorAdapter, MISSION_COMMANDS

def test_every_mission_state_has_mapping():
    assert set(MISSION_COMMANDS) == {"PATROL", "INVESTIGATE", "TRACK", "VERIFY", "RETURN_HOME"}

def test_human_and_wildlife_actions_are_distinct():
    adapter = ActuatorAdapter("m1")
    human = adapter.for_policy("human_intrusion", incident_id="i1")
    wildlife = adapter.for_policy("wildlife_proximity", incident_id="i2")
    assert any(c.command == "SIREN_ACTIVATE" for c in human)
    assert all(c.command != "SIREN_ACTIVATE" for c in wildlife)
    assert all(c.status == "ACKNOWLEDGED" for c in human + wildlife)

def test_duplicate_commands_and_suppressant():
    adapter = ActuatorAdapter("m1")
    first = adapter.emit("PATROL_SCAN"); second = adapter.emit("PATROL_SCAN")
    assert first.command_id == second.command_id and len(adapter.emitted) == 1
    assert adapter.emit("FIRE_SUPPRESSANT_DEPLOY").status == "UNAVAILABLE"
