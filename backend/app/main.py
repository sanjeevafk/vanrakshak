from fastapi import FastAPI, File, UploadFile, Query
from .config import get_settings
from .schemas import DetectionResponse, SceneResponse, VideoDetectionResponse
from .services import detect_bytes, scene_understanding
from .video import process_video
from .events import InMemoryEventStore, project_summary
from .replay import MissionRunner
from pydantic import BaseModel, Field

app = FastAPI(title="VanRakshak Inference API", version="0.1.0")
event_store = InMemoryEventStore()
runner = MissionRunner(event_store)

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
