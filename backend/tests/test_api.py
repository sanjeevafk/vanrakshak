from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_detect_contract():
    response = client.post("/detect", files={"file": ("frame.jpg", b"frame", "image/jpeg")})
    body = response.json()
    assert response.status_code == 200
    assert {"track_id", "class", "confidence", "bbox"} <= body["detections"][0].keys()


def test_scene_fallback():
    body = client.post("/scene-understanding", json={"image": "aW1hZ2U="}).json()
    assert body["reason"] == "VLM_UNREACHABLE"


def test_video_detection_contract_for_empty_upload():
    response = client.post("/detect/video", files={"file": ("clip.mp4", b"", "video/mp4")})
    assert response.status_code == 200
    assert response.json() == {"frame_count": 0, "fps": 0.0, "source": "FALLBACK", "frames": [], "representative_frame": None}

def test_mission_run_summary_and_event_pagination():
    created = client.post("/missions", json={"mission_id": "api-mission"})
    assert created.status_code == 200
    run = client.post("/missions/api-mission/run", json={"ticks": 3})
    body = run.json()
    assert body["summary"]["mission_state"] == "VERIFY"
    assert body["event_count"] == body["summary"]["event_count"]
    page = client.get("/missions/api-mission/events?after_sequence=2&limit=2").json()
    assert [event["sequence"] for event in page["events"]] == [3, 4]

def test_wildlife_replay_has_no_human_siren():
    client.post("/missions", json={"mission_id": "wildlife-mission"})
    summary = client.post("/missions/wildlife-mission/run", json={"ticks": 1, "wildlife": True}).json()["summary"]
    assert all(command["command"] != "SIREN_ACTIVATE" for command in summary["commands"])

def test_same_replay_shape_is_deterministic():
    first = client.post("/missions/deterministic/run", json={"ticks": 2}).json()["summary"]
    second = client.post("/missions/deterministic/run", json={"ticks": 2}).json()["summary"]
    assert first == second

def test_video_mission_empty_upload_uses_event_contract():
    response = client.post("/missions/video-mission/run/video", files={"file": ("empty.mp4", b"", "video/mp4")})
    assert response.status_code == 200
    body = response.json()
    assert body["event_count"] == 0
    assert body["summary"]["mission_id"] == "video-mission"

def test_missing_artifact_returns_404():
    assert client.get("/missions/m1/artifacts/artifact-missing").status_code == 404
