import base64
from .schemas import Detection, DetectionResponse, SceneResponse


def detect_bytes(payload: bytes) -> DetectionResponse:
    # Adapter seam for ultralytics/ByteTrack. Deterministic fallback keeps the API usable
    # in development and CI without downloading model weights.
    if not payload:
        return DetectionResponse(detections=[], source="FALLBACK")
    return DetectionResponse(
        detections=[Detection(track_id=1, **{"class": "person"}, confidence=0.5, bbox=[0, 0, 1, 1])],
        source="FALLBACK",
    )


async def scene_understanding(image: str, provider_url: str | None, api_key: str | None) -> SceneResponse:
    if not provider_url or not api_key:
        return SceneResponse(scene_summary="Person detected (Fallback Mode - VLM Unreachable)", activity_type="SAFE_WILDLIFE", behavior_rating="LOW", vlm_confidence=0.5, reason="VLM_UNREACHABLE")
    # Provider integration is intentionally isolated server-side; a deployment can replace
    # this adapter without exposing credentials to the frontend.
    try:
        base64.b64decode(image, validate=True)
    except Exception:
        return SceneResponse(scene_summary="Invalid image; fallback analysis used", activity_type="SAFE_WILDLIFE", behavior_rating="LOW", vlm_confidence=0.5, reason="VLM_UNREACHABLE")
    return SceneResponse(scene_summary="Provider adapter not configured", activity_type="SAFE_WILDLIFE", behavior_rating="LOW", vlm_confidence=0.5, reason="VLM_UNREACHABLE")
