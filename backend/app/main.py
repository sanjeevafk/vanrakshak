from fastapi import FastAPI, File, UploadFile, Query, HTTPException, Response
import base64
from .config import get_settings
from .schemas import DetectionResponse, SceneResponse, VideoDetectionResponse
from .services import detect_bytes, scene_understanding
from .video import process_video
from .events import InMemoryEventStore, project_summary, make_event
from .replay import MissionRunner
from .perception import InMemoryArtifactStore
from .policies import PolicyEngine
from .actuator import ActuatorAdapter
from .mission import MissionState, ThreatInput, threat_score
from .state_machines import transition_incident
from .events import IncidentState
from .replay_session import ReplaySessionStore
from pydantic import BaseModel, Field

app = FastAPI(title="VanRakshak Inference API", version="0.1.0")
event_store = InMemoryEventStore()
runner = MissionRunner(event_store)
artifact_store = InMemoryArtifactStore()
replay_sessions = ReplaySessionStore()

class MissionCreate(BaseModel):
    mission_id: str | None = None
    wildlife: bool = False

class MissionRun(BaseModel):
    ticks: int = Field(default=3, ge=0, le=300)
    wildlife: bool = False
    vlm_confirmed: bool = True


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
    summary, diagnostics = runner.run(mission_id, request.ticks, wildlife=request.wildlife, vlm_confirmed=request.vlm_confirmed)
    return {"mission_id": mission_id, "summary": summary.model_dump(), "event_count": summary.event_count, "events_url": f"/missions/{mission_id}/events", "diagnostics": diagnostics.model_dump()}

@app.post("/missions/{mission_id}/run/video")
async def run_video_mission(mission_id: str, file: UploadFile = File(...)) -> dict:
    """Convert sampled video output into the same replay event contract."""
    result = process_video(await file.read())
    event_store.clear(mission_id)
    sequence = 0
    track_counts: dict[int, int] = {}
    policies = PolicyEngine()
    actuator = ActuatorAdapter(mission_id)
    evidence_refs: dict[int, list[str]] = {}
    incident_states: dict[int, IncidentState] = {}
    mission_state = MissionState.PATROL
    state_transition_emitted = False
    def emit(event_type: str, timestamp: float, *, track_id: int | None = None, refs: list[str] | None = None, payload: dict | None = None) -> None:
        nonlocal sequence
        sequence += 1
        event_store.append(make_event(mission_id, sequence, timestamp, event_type, "perception" if event_type in {"FRAME_PROCESSED", "DETECTION_OBSERVED", "TRACK_UPDATED"} else "mission_control", track_id=track_id, evidence_refs=refs or [], payload=payload or {}))
    for frame in result.frames:
        emit("FRAME_PROCESSED", frame.timestamp_seconds, payload={"frame_index": frame.frame_index, "detector_source": result.source})
        for detection in frame.detections:
            if not state_transition_emitted:
                mission_state = MissionState.INVESTIGATE
                emit("MISSION_STATE_CHANGED", frame.timestamp_seconds, refs=[], payload={"previous_state": MissionState.PATROL.value, "next_state": mission_state.value, "reason_code": "VIDEO_EVIDENCE_DETECTED", "explanation": "Video perception produced a qualifying detection."})
                state_transition_emitted = True
            track_counts[detection.track_id] = track_counts.get(detection.track_id, 0) + 1
            ref = f"video-{mission_id}-track-{detection.track_id}-frame-{frame.frame_index}"
            evidence_refs.setdefault(detection.track_id, []).append(ref)
            refs = [ref]
            emit("DETECTION_OBSERVED", frame.timestamp_seconds, track_id=detection.track_id, refs=refs, payload=detection.model_dump(by_alias=True))
            emit("TRACK_UPDATED", frame.timestamp_seconds, track_id=detection.track_id, refs=refs, payload={**detection.model_dump(by_alias=True), "observation_count": track_counts[detection.track_id]})
            score = threat_score(ThreatInput(vlm_confidence=0, detector_confidence=detection.confidence, zone_risk=.6, acoustic_score=.3))
            emit("THREAT_ASSESSED", frame.timestamp_seconds, track_id=detection.track_id, refs=refs, payload={"score": score, "policy_id": "video_detection"})
            decisions = policies.evaluate({"class_name": detection.class_name, "confidence": detection.confidence, "persistent": track_counts[detection.track_id] >= 2, "vlm_confirmed": False, "track_id": detection.track_id, "evidence_refs": refs})
            for decision in decisions:
                emit("POLICY_EVALUATED", frame.timestamp_seconds, track_id=detection.track_id, refs=refs, payload=decision.model_dump())
                previous_incident = incident_states.get(detection.track_id, IncidentState.OBSERVED)
                transition = transition_incident(previous_incident, persistent=track_counts[detection.track_id] >= 2, verified=decision.decision == "RECOMMEND_ALERT")
                incident_states[detection.track_id] = IncidentState(transition.next_state)
                emit("INCIDENT_STATE_CHANGED", frame.timestamp_seconds, track_id=detection.track_id, refs=refs, payload={"previous_state": transition.previous_state, "next_state": transition.next_state, "reason_code": transition.reason_code, "explanation": transition.explanation, "policy_id": decision.policy_id})
                for command_name in decision.recommended_actions:
                    command = actuator.emit(command_name, timestamp_seconds=frame.timestamp_seconds, incident_id=f"incident-{detection.track_id}", evidence_refs=refs, policy_id=decision.policy_id)
                    emit("COMMAND_EMITTED", frame.timestamp_seconds, track_id=detection.track_id, refs=refs, payload=command.model_dump())
                    acknowledged = actuator.acknowledge(command.command_id)
                    if acknowledged:
                        emit("COMMAND_ACKNOWLEDGED", frame.timestamp_seconds, track_id=detection.track_id, refs=refs, payload={"command_id": acknowledged.command_id, "command": acknowledged.command, "status": acknowledged.status})
    if result.representative_frame:
        settings = get_settings()
        scene_result = await scene_understanding(result.representative_frame, settings.vlm_provider_url or settings.nvidia_api_url, settings.vlm_provider_api_key or settings.nvidia_api_key, settings.nvidia_model, settings.vlm_provider_timeout_seconds)
        emit("SCENE_ANALYZED", 0.0, refs=[], payload={"provider": "nvidia" if settings.nvidia_api_key or settings.vlm_provider_api_key else "fallback", "model": settings.nvidia_model, "activity_type": scene_result.activity_type, "behavior_rating": scene_result.behavior_rating, "vlm_confidence": scene_result.vlm_confidence, "reason": scene_result.reason})
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

@app.get("/missions/{mission_id}/replay")
def replay_state(mission_id: str) -> dict:
    return replay_sessions.state(mission_id, event_store.get_last_sequence(mission_id))

@app.post("/missions/{mission_id}/replay/start")
def replay_start(mission_id: str, speed: float = Query(default=1.0, gt=0, le=8)) -> dict:
    session = replay_sessions.get(mission_id); session.playing = True; session.speed = speed
    return replay_sessions.state(mission_id, event_store.get_last_sequence(mission_id))

@app.post("/missions/{mission_id}/replay/pause")
def replay_pause(mission_id: str) -> dict:
    replay_sessions.get(mission_id).playing = False
    return replay_sessions.state(mission_id, event_store.get_last_sequence(mission_id))

@app.post("/missions/{mission_id}/replay/reset")
def replay_reset(mission_id: str) -> dict:
    replay_sessions.reset(mission_id)
    return replay_sessions.state(mission_id, event_store.get_last_sequence(mission_id))

@app.post("/missions/{mission_id}/replay/step")
def replay_step(mission_id: str) -> dict:
    replay_sessions.step(mission_id, event_store.get_last_sequence(mission_id))
    return replay_sessions.state(mission_id, event_store.get_last_sequence(mission_id))

@app.get("/missions/{mission_id}")
def mission(mission_id: str) -> dict:
    return mission_summary(mission_id)

@app.get("/config/runtime")
def runtime_config() -> dict:
    from .mission import RULE_ENGINE_CONFIG
    return {"schema_version": 1, "config": RULE_ENGINE_CONFIG}
