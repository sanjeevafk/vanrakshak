from app.events import CommandEvent, TrackObservation
from app.memory import CommandStore, MissionContext, TrackStore, explain_threat
from app.mission import MissionState

def test_explainable_threat_formula_and_bounds():
    assessment = explain_threat(vlm=2, detector=-1, zone=.9, acoustic=.3, evidence_refs=["e1"], track_id=1, assessment_id="a1")
    assert assessment.score == 62.0
    assert assessment.contributions["vlm"]["contribution"] == 35
    assert assessment.evidence_refs == ["e1"]

def test_track_store_latest_and_reset():
    store = TrackStore(); store.append(TrackObservation(observation_id="o1", track_id=1, class_name="person", confidence=.5, timestamp_seconds=0)); store.append(TrackObservation(observation_id="o2", track_id=1, class_name="person", confidence=.8, timestamp_seconds=1))
    assert store.latest()[1].observation_id == "o2"; store.reset(); assert store.latest() == {}

def test_command_store_is_idempotent_and_acknowledgeable():
    store = CommandStore(); command = CommandEvent(command_id="c1", command="PATROL_SCAN", status="SENT", mission_id="m1")
    assert store.append(command) is True; assert store.append(command) is False; store.acknowledge("c1"); assert command.status == "ACKNOWLEDGED"

def test_context_has_replay_authority():
    context = MissionContext("m1"); assert context.current_state == MissionState.PATROL and context.configuration_version == 1
