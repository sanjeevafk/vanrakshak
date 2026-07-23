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


async def scene_understanding(image: str, provider_url: str | None, api_key: str | None, model: str = "meta/llama-3.2-11b-vision-instruct", timeout_seconds: float = 10.0) -> SceneResponse:
    if not provider_url or not api_key:
        return SceneResponse(scene_summary="Person detected (Fallback Mode - VLM Unreachable)", activity_type="SAFE_WILDLIFE", behavior_rating="LOW", vlm_confidence=0.5, reason="VLM_UNREACHABLE")
    try:
        base64.b64decode(image, validate=True)
        import httpx
        image_url = f"data:image/jpeg;base64,{image}"
        response = await httpx.AsyncClient(timeout=timeout_seconds).post(
            provider_url,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": model, "temperature": 0, "max_tokens": 300, "response_format": {"type": "json_object"}, "messages": [{"role": "user", "content": [{"type": "text", "text": "Analyze this forest surveillance image. Return ONLY one JSON object with exactly these keys: scene_summary (string), activity_type (one of ILLEGAL_LOGGING, POACHING_SUSPECT, UNAUTHORIZED_VEHICLE, FIRE_HAZARD, SAFE_WILDLIFE), behavior_rating (one of LOW, MEDIUM, HIGH, CRITICAL), vlm_confidence (number 0.0 to 1.0). Do not include markdown or explanations."}, {"type": "image_url", "image_url": {"url": image_url}}]}]},
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        import re
        candidate = re.search(r"\{.*\}", content, re.DOTALL)
        if not candidate:
            raise ValueError("provider did not return JSON")
        parsed = __import__("json").loads(candidate.group(0))
        return SceneResponse(**parsed)
    except Exception:
        return SceneResponse(scene_summary="Fallback analysis used", activity_type="SAFE_WILDLIFE", behavior_rating="LOW", vlm_confidence=0.5, reason="VLM_UNREACHABLE")
