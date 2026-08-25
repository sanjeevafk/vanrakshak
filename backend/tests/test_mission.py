from app.mission import ActuatorSimulation, MissionState, ThreatInput, next_state, threat_score


def test_threat_formula_includes_acoustic_and_is_bounded_inputs():
    assert threat_score(ThreatInput(vlm_confidence=1, detector_confidence=1, zone_risk=1, acoustic_score=1)) == 100
    assert threat_score(ThreatInput(vlm_confidence=0, detector_confidence=0, zone_risk=0, acoustic_score=1)) == 15


def test_fsm_uses_configured_transitions():
    assert next_state(MissionState.PATROL, 46, 100) == MissionState.INVESTIGATE
    assert next_state(MissionState.INVESTIGATE, 20, 100, target_verified=True) == MissionState.TRACK
    assert next_state(MissionState.VERIFY, 86, 100) == MissionState.ALERT
    assert next_state(MissionState.PATROL, 90, 24) == MissionState.RETURN_HOME


def test_actuator_ack_lifecycle():
    actuator = ActuatorSimulation()
    assert actuator.emit("SPOTLIGHT_ON")["status"] == "ACKNOWLEDGED"
    assert actuator.emit("FIRE_SUPPRESSANT_DEPLOY")["status"] == "ACKNOWLEDGED"
