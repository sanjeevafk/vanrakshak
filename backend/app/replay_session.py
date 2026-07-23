from __future__ import annotations
from dataclasses import dataclass
from .events import InMemoryEventStore, MissionEvent

@dataclass
class ReplaySession:
    mission_id: str
    cursor: int = 0
    playing: bool = False
    speed: float = 1.0

class ReplaySessionStore:
    def __init__(self) -> None: self.sessions: dict[str, ReplaySession] = {}
    def get(self, mission_id: str) -> ReplaySession: return self.sessions.setdefault(mission_id, ReplaySession(mission_id))
    def reset(self, mission_id: str) -> ReplaySession:
        session = self.get(mission_id); session.cursor = 0; session.playing = False; return session
    def step(self, mission_id: str, event_count: int) -> ReplaySession:
        session = self.get(mission_id); session.cursor = min(event_count, session.cursor + 1); return session
    def state(self, mission_id: str, event_count: int) -> dict:
        session = self.get(mission_id)
        return {"mission_id": mission_id, "cursor": min(session.cursor, event_count), "event_count": event_count, "playing": session.playing, "speed": session.speed}
