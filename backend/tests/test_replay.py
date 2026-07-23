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
