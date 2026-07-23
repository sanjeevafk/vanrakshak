from app.replay_session import ReplaySessionStore

def test_replay_session_controls_are_bounded():
    store = ReplaySessionStore()
    assert store.state("m1", 3)["cursor"] == 0
    store.step("m1", 3); store.step("m1", 3); assert store.state("m1", 3)["cursor"] == 2
    store.step("m1", 1); assert store.state("m1", 1)["cursor"] == 1
    store.reset("m1"); assert store.state("m1", 3) == {"mission_id": "m1", "cursor": 0, "event_count": 3, "playing": False, "speed": 1.0}
