from fastapi import FastAPI, File, UploadFile, Query, HTTPException, Response
import base64
from .config import get_settings
from .schemas import DetectionResponse, SceneResponse, VideoDetectionResponse
from .services import detect_bytes, scene_understanding
from .video import process_video
from .events import InMemoryEventStore, project_summary, make_event
from .replay import MissionRunner
from .perception import InMemoryArtifactStore
from pydantic import BaseModel, Field

app = FastAPI(title="VanRakshak Inference API", version="0.1.0")
event_store = InMemoryEventStore()
runner = MissionRunner(event_store)
artifact_store = InMemoryArtifactStore()

class MissionCreate(BaseModel):
    mission_id: str | None = None
    wildlife: bool = False

class MissionRun(BaseModel):
    ticks: int = Field(default=3, ge=0, le=300)
    wildlife: bool = False


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/detect", response_model=DetectionResponse)
async def detect(file: UploadFile = File(...)) -> DetectionResponse:
    return detect_bytes(await file.read())


@app.post("/detect/video", response_model=VideoDetectionResponse)
async def detect_video(file: UploadFile = File(...)) -> VideoDetectionResponse:
    return process_video(await file.read())


@app.post("/scene-understanding", response_model=SceneResponse)
async def understand(image: str) -> SceneResponse:
    settings = get_settings()
    return await scene_understanding(
        image,
        settings.vlm_provider_url or settings.nvidia_api_url,
        settings.vlm_provider_api_key or settings.nvidia_api_key,
        settings.nvidia_model,
        settings.vlm_provider_timeout_seconds,
    )

@app.post("/missions")
def create_mission(request: MissionCreate) -> dict:
    import uuid
    mission_id = request.mission_id or f"mission-{uuid.uuid4().hex[:8]}"
    event_store.clear(mission_id)
    return {"mission_id": mission_id, "status": "CREATED", "wildlife": request.wildlife}

@app.post("/missions/{mission_id}/run")
def run_mission(mission_id: str, request: MissionRun | None = None) -> dict:
    request = request or MissionRun()
    summary, diagnostics = runner.run(mission_id, request.ticks, wildlife=request.wildlife)
    return {"mission_id": mission_id, "summary": summary.model_dump(), "event_count": summary.event_count, "events_url": f"/missions/{mission_id}/events", "diagnostics": diagnostics.model_dump()}

@app.post("/missions/{mission_id}/run/video")
async def run_video_mission(mission_id: str, file: UploadFile = File(...)) -> dict:
    """Convert sampled video output into the same replay event contract."""
    result = process_video(await file.read())
    event_store.clear(mission_id)
    sequence = 0
    for frame in result.frames:
        sequence += 1
        event_store.append(make_event(mission_id, sequence, frame.timestamp_seconds, "FRAME_PROCESSED", "perception", payload={"frame_index": frame.frame_index, "detector_source": result.source}))
        for detection in frame.detections:
            sequence += 1
            event_store.append(make_event(mission_id, sequence, frame.timestamp_seconds, "DETECTION_OBSERVED", "perception", track_id=detection.track_id, payload=detection.model_dump(by_alias=True)))
    artifact_refs: list[str] = []
    if result.representative_frame:
        artifact_refs.append(artifact_store.put(base64.b64decode(result.representative_frame)))
    summary = project_summary(mission_id, event_store.list_events(mission_id))
    return {"mission_id": mission_id, "summary": summary.model_dump(), "event_count": summary.event_count, "events_url": f"/missions/{mission_id}/events", "artifacts": artifact_refs, "video": result.model_dump()}

@app.get("/missions/{mission_id}/artifacts/{artifact_id}")
def mission_artifact(mission_id: str, artifact_id: str) -> Response:
    # Artifact IDs are content-addressed; mission_id is retained in the route
    # for stable client contracts and future mission ownership checks.
    del mission_id
    artifact = artifact_store.get(artifact_id)
    if artifact is None:
        raise HTTPException(status_code=404, detail="artifact not found")
    content, media_type = artifact
    return Response(content=content, media_type=media_type)

@app.get("/missions/{mission_id}/events")
def mission_events(mission_id: str, after_sequence: int | None = Query(default=None, ge=0), limit: int = Query(default=100, ge=1, le=1000)) -> dict:
    events = event_store.list_events(mission_id, after_sequence, limit)
    return {"mission_id": mission_id, "events": [event.model_dump() for event in events], "next_sequence": events[-1].sequence if events else after_sequence or 0}

@app.get("/missions/{mission_id}/summary")
def mission_summary(mission_id: str) -> dict:
    return project_summary(mission_id, event_store.list_events(mission_id)).model_dump()

@app.get("/missions/{mission_id}")
def mission(mission_id: str) -> dict:
    return mission_summary(mission_id)

@app.get("/config/runtime")
def runtime_config() -> dict:
    from .mission import RULE_ENGINE_CONFIG
    return {"schema_version": 1, "config": RULE_ENGINE_CONFIG}
