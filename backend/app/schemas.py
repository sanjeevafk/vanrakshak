from typing import Literal
from pydantic import BaseModel, Field

ActivityType = Literal["ILLEGAL_LOGGING", "POACHING_SUSPECT", "UNAUTHORIZED_VEHICLE", "FIRE_HAZARD", "SAFE_WILDLIFE"]
BehaviorRating = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]


class Detection(BaseModel):
    track_id: int = Field(ge=0)
    class_name: str = Field(min_length=1, alias="class")
    confidence: float = Field(ge=0, le=1)
    bbox: list[float] = Field(min_length=4, max_length=4)

    model_config = {"populate_by_name": True}


class DetectionResponse(BaseModel):
    detections: list[Detection]
    source: Literal["YOLO", "FALLBACK"]


class SceneResponse(BaseModel):
    scene_summary: str
    activity_type: ActivityType
    behavior_rating: BehaviorRating
    vlm_confidence: float = Field(ge=0, le=1)
    reason: str | None = None

