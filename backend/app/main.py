from fastapi import FastAPI, File, UploadFile
from .config import get_settings
from .schemas import DetectionResponse, SceneResponse, VideoDetectionResponse
from .services import detect_bytes, scene_understanding
from .video import process_video

app = FastAPI(title="VanRakshak Inference API", version="0.1.0")


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
