# Senior Architecture Review: VanRakshak Replay-First MVP

## Executive assessment

The existing plan has the correct replay-first direction, but it currently places too much responsibility in the proposed `MissionRunner`, treats mission state and incident state as one concern, and returns overly large snapshot responses.

Refine the design around four boundaries:

```text
Perception → Evidence → Policy/Reasoning → Mission Control → Actuation
```

Use immutable mission events as the replay source of truth. Derived state, summaries, and UI views should be projections of those events.

## 1. Architecture refinements

Keep `MissionRunner` thin. It should only:

1. Read the next replay tick.
2. Invoke perception.
3. append evidence events.
4. invoke reasoning/policies.
5. append decision events.
6. invoke the actuator adapter.
7. append command events.

It must not own detection logic, threat formulas, policy rules, memory mutation, or UI-specific state.

Use these components:

```text
ReplayClock
  → PerceptionPipeline
  → EvidenceStore
  → PolicyEngine
  → MissionStateMachine
  → ActuatorAdapter
  → EventLog
  → State/Event Projections
```

Recommended module responsibilities:

- `ReplayClock`: deterministic frame/timestamp progression.
- `PerceptionPipeline`: detector, tracker, crop selection, VLM, acoustic and telemetry inputs.
- `EvidenceStore`: immutable observations and bounded track evidence.
- `PolicyEngine`: evaluates independent domain policies.
- `MissionStateMachine`: controls drone mission state only.
- `IncidentStateMachine`: controls individual event/track lifecycle.
- `ActuatorAdapter`: converts decisions into simulated commands.
- `EventLog`: append-only mission event stream.
- `ProjectionService`: derives current state, summaries, and UI views.

## 2. Mission trace architecture

Make `MissionEvent` the canonical replay format.

Example:

```json
{
  "event_id": "evt-00042",
  "mission_id": "mission-1",
  "sequence": 42,
  "timestamp_seconds": 14.2,
  "type": "THREAT_ASSESSED",
  "source": "threat_engine",
  "track_id": 12,
  "payload": {},
  "evidence_refs": ["obs-18", "vlm-04"],
  "schema_version": 1
}
```

Use event types such as:

- `MISSION_STARTED`
- `FRAME_PROCESSED`
- `DETECTION_OBSERVED`
- `TRACK_UPDATED`
- `SCENE_ANALYZED`
- `THREAT_ASSESSED`
- `POLICY_EVALUATED`
- `MISSION_STATE_CHANGED`
- `INCIDENT_STATE_CHANGED`
- `COMMAND_EMITTED`
- `COMMAND_ACKNOWLEDGED`
- `MISSION_COMPLETED`
- `MISSION_FAILED`

Do not place every full detection history and all images inside every response. Store large artifacts separately and reference them by ID.

Expose separate endpoints:

```text
POST /missions
POST /missions/{mission_id}/run
GET  /missions/{mission_id}
GET  /missions/{mission_id}/events
GET  /missions/{mission_id}/summary
GET  /missions/{mission_id}/artifacts/{artifact_id}
```

For the MVP, these can be implemented over in-memory storage, but the contracts should already be event-oriented.

## 3. Mission memory split

Do not implement one mutable `MissionMemoryService`.

Split it into:

- `MissionContext`
  - mission ID
  - replay clock
  - current mission state
  - telemetry snapshot
  - configuration version
- `TrackStore`
  - immutable observations
  - current track projections
  - first/last seen
  - confidence evolution
- `ThreatStore`
  - threat assessments
  - evidence references
  - policy results
- `CommandStore`
  - emitted commands
  - ACK lifecycle
  - active effects

Stores should append records and expose derived read models. Only the mission state machine and command adapter should mutate their own state.

This reduces hidden coupling and makes replay/reset straightforward.

## 4. Policy engine

Do not encode human, wildlife, railway, and thermal rules directly into FSM transitions.

Use independent policies:

```text
HumanIntrusionPolicy
VehicleIntrusionPolicy
WildlifeProximityPolicy
RailwayConflictPolicy
ThermalFirePolicy
```

Each policy receives a read-only `PolicyInput`:

```json
{
  "tracks": [],
  "scene_results": [],
  "telemetry": {},
  "zone_context": {},
  "mission_context": {}
}
```

Each returns zero or more `PolicyDecision` objects:

```json
{
  "policy_id": "human_intrusion",
  "decision": "RECOMMEND_ALERT",
  "severity": "HIGH",
  "track_id": 12,
  "confidence": 0.88,
  "evidence_refs": ["obs-18", "vlm-04"],
  "recommended_actions": ["SIREN_ACTIVATE", "DISPATCH_RANGER"]
}
```

The FSM consumes normalized decisions, not domain-specific conditions.

Thermal/fire and railway policies should initially be disabled or return `UNSUPPORTED_INPUT`, not be partially implemented inside the FSM.

## 5. Separate mission and incident state

Use two state machines.

### Mission state

Describes the drone’s operational mode:

```text
PATROL
INVESTIGATE
TRACK
VERIFY
ALERT
RETURN_HOME
```

### Incident state

Describes an individual track/event:

```text
OBSERVED
PERSISTING
UNDER_REVIEW
VERIFIED
DISPATCHED
RESOLVED
EXPIRED
```

A single mission can have multiple incidents. For example, the drone can remain in `TRACK` while one human incident is `DISPATCHED` and another vehicle incident is `UNDER_REVIEW`.

Every transition must be a pure function of:

```text
previous state
ordered event history
configuration version
```

Every transition must emit:

- previous state
- next state
- reason code
- human-readable explanation
- evidence references
- threshold values used
- policy ID, if applicable

Avoid using wall-clock time in replay decisions. Use replay timestamps only.

## 6. Vision pipeline refinements

Replace simple First / Highest / Last crop selection with quality-aware selection.

For each track, score candidate observations using:

- detector confidence
- bounding-box area within safe bounds
- crop sharpness
- crop completeness
- occlusion estimate
- temporal spacing
- scene diversity

Select at most three crops using diversity-aware ranking:

1. Best-quality crop.
2. Best crop from a materially different timestamp/view.
3. Latest valid crop before the decision deadline.

Do not send crops smaller than a configured minimum resolution. Do not send duplicate or near-identical crops.

VLM strategy:

- Cache by `sha256(image_bytes + prompt_version + model_id)`.
- Cache per track and per mission.
- Limit to three VLM requests per track.
- Use a bounded concurrency pool.
- Record latency, provider model, prompt version, and fallback reason.
- Never let VLM latency block telemetry or basic tracking indefinitely.

The VLM is evidence enrichment, not the sole source of safety-critical action.

## 7. Backend contract refinements

Replace one large `/mission/analyze` response with:

```text
MissionCreateResponse
MissionRunResponse
MissionSummary
MissionEventPage
MissionDiagnostics
```

`MissionSummary` should contain only:

- mission metadata
- final mission state
- incident summaries
- command summary
- aggregate metrics
- warnings
- event counts

`MissionEventPage` should support:

- `after_sequence`
- `limit`
- event type filtering

Large crops, raw frames, and model artifacts should be referenced, not embedded repeatedly.

For a simple hackathon implementation, `/mission/analyze` may remain as a convenience endpoint, but it should return:

```json
{
  "mission_id": "mission-1",
  "summary": {},
  "event_count": 42,
  "events_url": "/missions/mission-1/events",
  "diagnostics": {}
}
```

Do not return every frame image and every repeated state snapshot by default.

## 8. Configuration

Make backend configuration authoritative.

The frontend should not duplicate:

- FSM thresholds
- threat weights
- action policies
- model thresholds
- zone risk values

Expose read-only runtime configuration metadata:

```text
GET /config/runtime
```

The response should include:

- configuration version
- detector/tracker selection
- enabled policies
- threshold names and values
- VLM model identifier
- replay sampling settings

Frontend configuration should contain only display preferences and backend URL.

Every event should record the configuration version used to produce it.

## 9. Explainability

Represent evidence explicitly:

```json
{
  "evidence_id": "ev-18",
  "kind": "DETECTION | TRACK | VLM | TELEMETRY | ZONE | ACOUSTIC",
  "track_id": 12,
  "timestamp_seconds": 14.2,
  "summary": "Person track persisted for 4.0 seconds",
  "values": {
    "detector_confidence": 0.84,
    "vlm_confidence": 0.81,
    "zone_risk": 0.9,
    "acoustic_score": 0.32
  },
  "artifact_ref": "artifact-18"
}
```

Every threat assessment must include:

- component scores
- weights
- weighted contributions
- final score
- threshold comparison
- evidence IDs

Every transition must include:

- transition reason code
- explanation
- evidence IDs
- relevant configuration values

This makes the demo inspectable and supports future incident review.

## 10. Extensibility

Use adapters and normalized event schemas:

```text
DetectorAdapter
TrackerAdapter
VLMAdapter
AcousticAdapter
TelemetryAdapter
ActuatorAdapter
Policy
```

Multi-drone support should be represented by:

```json
{
  "mission_id": "m1",
  "vehicle_id": "drone-2",
  "source_id": "camera-front"
}
```

Do not create a separate mission runner per sensor or drone. The same event model should support multiple `vehicle_id` values.

Live streaming should replace `ReplayClock` with a `LiveClock`; it should not change policy, FSM, memory, or actuator interfaces.

Thermal and acoustic plugins should emit normalized evidence events. The core reasoning stack should not know how the sensor produced the evidence.

## 11. Scope reduction for the MVP

Postpone these to Phase 2:

- Full RT-DETR production selection.
- Custom thermal/fire model training.
- Real railway map integration.
- Multi-drone coordination.
- Persistent external event database.
- Re-identification across separate missions.
- Physical MAVLink or hardware integration.
- Complex map editing.
- Audio waveform processing.
- Automated model benchmarking with labeled datasets.

Keep in the MVP:

- Deterministic replay.
- YOLOv8n + ByteTrack.
- Optional BoT-SORT benchmark mode.
- Visible RGB supported classes.
- NVIDIA VLM evidence enrichment.
- Separate mission and incident state.
- Human-threat siren policy.
- Wildlife alert policy without human siren.
- Simulated telemetry, zones, commands, and ACKs.
- Event log and replay timeline.

## Agent execution sequence

### Agent 1 — Contracts and event core

Implement:

- MissionEvent schemas.
- Evidence schemas.
- Mission/incident states.
- Event log.
- Read-only projections.
- Configuration versioning.

Acceptance: deterministic synthetic event stream replays to identical projections.

### Agent 2 — Perception and evidence

Implement:

- Detector/tracker adapter interface.
- Quality-aware crop selector.
- TrackStore.
- NVIDIA VLM adapter.
- Cache and bounded concurrency.
- Artifact references.

Acceptance: one track produces at most three VLM calls and stable evidence IDs.

### Agent 3 — Policies and reasoning

Implement:

- ThreatStore.
- Threat score with explainable contributions.
- Human, vehicle, wildlife, railway, and thermal policy interfaces.
- Enabled RGB policies.
- Unsupported thermal policy.

Acceptance: policy results are independent of the FSM and fully testable in isolation.

### Agent 4 — Mission and actuation

Implement:

- Mission state machine.
- Incident state machine.
- CommandStore.
- Actuator adapter.
- Deterministic mission runner.

Acceptance: human threat, wildlife proximity, target loss, battery, and geofence scenarios produce deterministic event traces.

### Agent 5 — Frontend projections and replay

Implement:

- Mission summary view.
- Event timeline.
- Threat evidence drawer.
- Track view.
- Command/ACK view.
- Replay controls.
- Wildlife and unsupported-input states.

Acceptance: frontend renders backend events without calculating authoritative decisions locally.

### Agent 6 — Verification

Implement:

- Unit tests for each policy and state machine.
- API integration tests.
- Deterministic replay golden traces.
- UI integration tests.
- Demo-video report.
- `GREENLIGHT_REPORT.md`.

## Definition of done

The MVP is greenlit when:

- Replaying the same video with the same configuration produces byte-equivalent event traces.
- MissionRunner contains orchestration only.
- Mission and incident state are separate.
- All decisions reference immutable evidence.
- All thresholds come from backend configuration.
- Human threats can produce simulated siren and dispatch events.
- Elephants produce wildlife alerts without human sirens.
- Thermal/fire input produces an explicit unsupported result.
- VLM failures produce safe, explainable fallback events.
- Large artifacts are not embedded in normal mission summaries.
- Backend tests, frontend tests, type checks, and replay golden tests pass.
- Known limitations are recorded in `GREENLIGHT_REPORT.md`.
