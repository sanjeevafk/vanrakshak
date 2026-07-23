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


