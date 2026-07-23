from fastapi import FastAPI, File, UploadFile
from .config import get_settings
from .schemas import DetectionResponse, SceneResponse
from .services import detect_bytes, scene_understanding

app = FastAPI(title="VanRakshak Inference API", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/detect", response_model=DetectionResponse)
async def detect(file: UploadFile = File(...)) -> DetectionResponse:
    return detect_bytes(await file.read())


@app.post("/scene-understanding", response_model=SceneResponse)
async def understand(image: str) -> SceneResponse:
    settings = get_settings()
    return await scene_understanding(image, settings.vlm_provider_url, settings.vlm_provider_api_key)

