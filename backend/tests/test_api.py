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
    body = client.post("/scene-understanding", params={"image": "aW1hZ2U="}).json()
    assert body["reason"] == "VLM_UNREACHABLE"


def test_video_detection_contract_for_empty_upload():
    response = client.post("/detect/video", files={"file": ("clip.mp4", b"", "video/mp4")})
    assert response.status_code == 200
    assert response.json() == {"frame_count": 0, "fps": 0.0, "source": "FALLBACK", "frames": []}
