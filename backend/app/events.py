"""Replay-first mission contracts, append-only storage, and read projections."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Protocol

from pydantic import BaseModel, Field


class IncidentState(StrEnum):
    OBSERVED = "OBSERVED"
    PERSISTING = "PERSISTING"
    UNDER_REVIEW = "UNDER_REVIEW"
    VERIFIED = "VERIFIED"
    DISPATCHED = "DISPATCHED"
    RESOLVED = "RESOLVED"
    EXPIRED = "EXPIRED"


class MissionEvent(BaseModel):
    event_id: str
    mission_id: str
    sequence: int = Field(ge=1)
    timestamp_seconds: float = Field(ge=0)
    type: str
    source: str
    vehicle_id: str = "drone-1"
    track_id: int | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    evidence_refs: list[str] = Field(default_factory=list)
    schema_version: int = 1


class Evidence(BaseModel):
    evidence_id: str
    mission_id: str
    kind: str
    timestamp_seconds: float = Field(ge=0)
    artifact_ref: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    schema_version: int = 1


class TrackObservation(BaseModel):
    observation_id: str
    track_id: int
    class_name: str
    confidence: float = Field(ge=0, le=1)
    timestamp_seconds: float = Field(ge=0)
    evidence_refs: list[str] = Field(default_factory=list)


class ThreatAssessment(BaseModel):
    assessment_id: str
    track_id: int
    score: float = Field(ge=0, le=100)
    contributions: dict[str, dict[str, float]]
    evidence_refs: list[str]
    schema_version: int = 1


class PolicyDecision(BaseModel):
    policy_id: str
    decision: str
    severity: str
    track_id: int | None = None
    confidence: float = Field(ge=0, le=1)
    evidence_refs: list[str] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)


class CommandEvent(BaseModel):
    command_id: str
    command: str
    status: str
    mission_id: str
    incident_id: str | None = None
    evidence_refs: list[str] = Field(default_factory=list)
    policy_id: str | None = None


class MissionSummary(BaseModel):
    mission_id: str
    mission_state: str
    incidents: dict[str, str] = Field(default_factory=dict)
    latest_tracks: dict[str, dict[str, Any]] = Field(default_factory=dict)
    latest_threats: dict[str, dict[str, Any]] = Field(default_factory=dict)
    commands: list[dict[str, Any]] = Field(default_factory=list)
    event_count: int = 0


class MissionDiagnostics(BaseModel):
    sampled_ticks: int = 0
    fallback_warnings: list[str] = Field(default_factory=list)


class EventStoreProtocol(Protocol):
    def append(self, event: MissionEvent) -> MissionEvent: ...


class InMemoryEventStore:
    def __init__(self) -> None:
        self._events: dict[str, list[MissionEvent]] = {}

    def append(self, event: MissionEvent) -> MissionEvent:
        events = self._events.setdefault(event.mission_id, [])
        expected = len(events) + 1
        if event.sequence != expected:
            event = event.model_copy(update={"sequence": expected})
        events.append(event)
        return event

    def append_many(self, events: list[MissionEvent]) -> list[MissionEvent]:
        return [self.append(event) for event in events]

    def list_events(self, mission_id: str, after_sequence: int | None = None, limit: int | None = None) -> list[MissionEvent]:
        result = self._events.get(mission_id, [])
        if after_sequence is not None:
            result = [event for event in result if event.sequence > after_sequence]
        return result[:limit] if limit is not None else list(result)

    def clear(self, mission_id: str) -> None:
        self._events.pop(mission_id, None)

    def get_last_sequence(self, mission_id: str) -> int:
        return len(self._events.get(mission_id, []))


def project_summary(mission_id: str, events: list[MissionEvent]) -> MissionSummary:
    state = "PATROL"
    incidents: dict[str, str] = {}
    tracks: dict[str, dict[str, Any]] = {}
    threats: dict[str, dict[str, Any]] = {}
    commands: list[dict[str, Any]] = []
    for event in events:
        if event.type == "MISSION_STATE_CHANGED":
            state = event.payload["next_state"]
        elif event.type == "INCIDENT_STATE_CHANGED" and event.track_id is not None:
            incidents[str(event.track_id)] = event.payload["next_state"]
        elif event.type == "TRACK_UPDATED" and event.track_id is not None:
            tracks[str(event.track_id)] = event.payload
        elif event.type == "THREAT_ASSESSED" and event.track_id is not None:
            threats[str(event.track_id)] = event.payload
        elif event.type == "COMMAND_EMITTED":
            commands.append(event.payload)
    return MissionSummary(mission_id=mission_id, mission_state=state, incidents=incidents, latest_tracks=tracks, latest_threats=threats, commands=commands, event_count=len(events))


def make_event(mission_id: str, sequence: int, timestamp: float, event_type: str, source: str, **kwargs: Any) -> MissionEvent:
    return MissionEvent(event_id=f"evt-{mission_id}-{sequence:05d}", mission_id=mission_id, sequence=sequence, timestamp_seconds=timestamp, type=event_type, source=source, **kwargs)
