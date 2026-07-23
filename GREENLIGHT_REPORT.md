# VanRakshak MVP Greenlight Report

Date: 2026-07-23

## Validated behavior

- Append-only mission events have monotonic sequence numbers and deterministic event IDs.
- Mission summaries and current incident/track/threat/command views are projections of the event stream.
- Replay uses simulated timestamps and can be reset and rerun deterministically.
- Human, wildlife, vehicle, railway, and thermal policies are independent and side-effect free.
- Human siren recommendations require persistent, confirmed human evidence.
- Wildlife and railway decisions do not recommend the human-intruder siren.
- Thermal input returns `UNSUPPORTED_INPUT` and cannot trigger suppressant actions.
- VLM responses are validated, cached, bounded to three calls per track, and safely fall back on timeout or invalid output.
- Simulated commands are idempotent and expose ACK/unavailable statuses.
- Frontend projections consume backend mission state and events.

## Verification results

- Backend: 31 tests passing.
- Frontend: 4 tests passing.
- Frontend TypeScript typecheck: passing.
- Frontend production build: passing.

## Simulated behavior

- Telemetry, replay clock, actuator commands, command ACKs, and ranger dispatch are simulated.
- The synthetic mission runner uses deterministic replay observations; it is not a live flight controller.
- NVIDIA provider calls are adapter-ready but require backend credentials and network access.

## Unsupported behavior

- Thermal/fire perception is represented as an unsupported plugin input.
- Physical drone control, MAVLink, physical siren, payload deployment, and fire suppression are unavailable.
- No external database or durable event store is included in this milestone.

## Risks and limitations

- YOLOv8n is a general COCO model and is not validated for thermal imagery, wildfire smoke, or forest-specific activity.
- The current replay runner demonstrates orchestration contracts; production video-to-mission wiring still needs richer frame-level evidence integration.
- In-memory state is lost when the backend process stops.
- VLM confidence is provider output and should not be treated as ground truth.
- False positives and false negatives remain possible, especially under occlusion, low light, and unusual camera angles.

## Decision

**Greenlight for a replay-first software demonstration only.** Do not use this milestone for physical actuation or operational safety decisions.
