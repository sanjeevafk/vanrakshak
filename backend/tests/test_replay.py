from app.events import InMemoryEventStore, make_event, project_summary
from app.replay import MissionRunner


def test_event_store_sequences_and_reset():
    store = InMemoryEventStore()
    store.append(make_event("m1", 99, 0, "MISSION_STARTED", "test"))
    store.append(make_event("m1", 99, 1, "FRAME_PROCESSED", "test"))
    assert [e.sequence for e in store.list_events("m1")] == [1, 2]
    store.clear("m1")
    assert store.get_last_sequence("m1") == 0


def test_projection_is_replay_deterministic():
    store = InMemoryEventStore()
    runner = MissionRunner(store)
    first, _ = runner.run("m1", ticks=3)
    events = store.list_events("m1")
    assert first == project_summary("m1", events)
    assert first.mission_state == "VERIFY"
    assert first.event_count == len(events)


def test_event_pagination():
    store = InMemoryEventStore()
    MissionRunner(store).run("m1", ticks=2)
    page = store.list_events("m1", after_sequence=2, limit=2)
    assert [event.sequence for event in page] == [3, 4]


def test_incident_state_changed_payload_provenance():
    store = InMemoryEventStore()
    MissionRunner(store).run("m1", ticks=1)
    events = store.list_events("m1")
    incident_events = [e for e in events if e.type == "INCIDENT_STATE_CHANGED"]
    assert len(incident_events) > 0
    for evt in incident_events:
        assert "policy_id" in evt.payload
        assert evt.payload["policy_id"] == "human_intrusion"
        assert "thresholds" in evt.payload
        assert "investigate" in evt.payload["thresholds"]
        assert "previous_state" in evt.payload
        assert "next_state" in evt.payload
        assert "reason_code" in evt.payload
        assert "explanation" in evt.payload


def test_incident_state_isolated_per_track():
    store = InMemoryEventStore()
    runner = MissionRunner(store)
    summary_human, _ = runner.run("m_human", ticks=2, wildlife=False)
    summary_wildlife, _ = runner.run("m_wildlife", ticks=2, wildlife=True)
    assert summary_human.incidents.get("1") == "VERIFIED"
    assert summary_wildlife.incidents.get("2") == "PERSISTING"

def test_acknowledgements_are_explicit_events():
    store = InMemoryEventStore()
    MissionRunner(store).run("m1", ticks=1)
    assert any(event.type == "COMMAND_ACKNOWLEDGED" for event in store.list_events("m1"))


def test_vlm_confirmed_passed_directly_to_policy_evaluation():
    store = InMemoryEventStore()
    runner = MissionRunner(store)
    # When vlm_confirmed is False, human intrusion policy decision is RECOMMEND_REVIEW instead of RECOMMEND_ALERT
    summary_unconfirmed, _ = runner.run("m_unconfirmed", ticks=1, wildlife=False, vlm_confirmed=False)
    events = store.list_events("m_unconfirmed")
    policy_events = [e for e in events if e.type == "POLICY_EVALUATED"]
    assert len(policy_events) > 0
    assert policy_events[0].payload["decision"] == "RECOMMEND_REVIEW"


def test_poaching_suspect_activity_emits_scene_label_and_full_escalation():
    store = InMemoryEventStore()
    runner = MissionRunner(store)
    summary, _ = runner.run("m_poach", ticks=2, wildlife=False, activity="POACHING_SUSPECT")
    events = store.list_events("m_poach")
    scene_events = [e for e in events if e.type == "SCENE_ANALYZED"]
    assert len(scene_events) > 0
    for scene in scene_events:
        assert scene.payload["activity_type"] == "POACHING_SUSPECT"
        assert scene.payload["source"] == "synthetic_demo"
    # Poaching is a person — the genuine human-intrusion escalation path fires.
    command_events = [e for e in events if e.type == "COMMAND_EMITTED"]
    commands = {e.payload["command"] for e in command_events}
    assert "SIREN_ACTIVATE" in commands
    assert "DISPATCH_RANGER" in commands
    assert summary.incidents.get("1") in {"VERIFIED", "ALERT"}


def test_poaching_activity_absent_by_default():
    store = InMemoryEventStore()
    MissionRunner(store).run("m_plain", ticks=1)
    events = store.list_events("m_plain")
    assert not any(e.type == "SCENE_ANALYZED" for e in events)


