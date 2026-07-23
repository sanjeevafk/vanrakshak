from app.events import IncidentState
from app.policies import PolicyEngine, ThermalFirePolicy, HumanIntrusionPolicy, WildlifeProximityPolicy
from app.state_machines import transition_incident, transition_mission
from app.mission import MissionState


def test_human_requires_confirmation_for_siren():
    base = {"class_name": "person", "persistent": True, "confidence": .9, "track_id": 1}
    assert "SIREN_ACTIVATE" not in HumanIntrusionPolicy().evaluate(base)[0].recommended_actions
    assert "SIREN_ACTIVATE" in HumanIntrusionPolicy().evaluate({**base, "vlm_confirmed": True})[0].recommended_actions


def test_wildlife_never_recommends_human_siren():
    decision = WildlifeProximityPolicy().evaluate({"class_name": "elephant", "confidence": .9, "track_id": 2})[0]
    assert "SIREN_ACTIVATE" not in decision.recommended_actions


def test_thermal_is_explicitly_unsupported():
    assert ThermalFirePolicy().evaluate({"input_type": "thermal"})[0].decision == "UNSUPPORTED_INPUT"


def test_transitions_are_deterministic_and_explainable():
    result = transition_mission(MissionState.PATROL, threat_score=50)
    assert result.next_state == MissionState.INVESTIGATE
    assert result.reason_code == "THREAT_DETECTED"
    incident = transition_incident(IncidentState.OBSERVED, persistent=True)
    assert incident.next_state == IncidentState.PERSISTING
    assert PolicyEngine().evaluate({"class_name": "elephant", "confidence": .8})[0].policy_id == "wildlife_proximity"
