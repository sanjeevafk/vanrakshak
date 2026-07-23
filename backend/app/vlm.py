"""Bounded backend-only vision-language adapter with deterministic fallbacks."""
from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import re
import time
from typing import Any, Awaitable, Callable

from pydantic import BaseModel, Field


class VLMResult(BaseModel):
    provider: str
    model: str
    prompt_version: str
    latency_ms: float = Field(ge=0)
    confidence: float = Field(ge=0, le=1)
    artifact_ref: str
    evidence_id: str
    scene_summary: str = ""
    fallback_reason: str | None = None


class VLMAdapter:
    def __init__(self, *, provider: str = "nvidia", model: str = "meta/llama-3.2-11b-vision-instruct", prompt_version: str = "forest-v1", timeout_seconds: float = 10.0, max_calls_per_track: int = 3, request: Callable[[dict[str, Any]], Awaitable[str]] | None = None) -> None:
        self.provider, self.model, self.prompt_version = provider, model, prompt_version
        self.timeout_seconds, self.max_calls_per_track, self.request = timeout_seconds, max_calls_per_track, request
        self._cache: dict[str, VLMResult] = {}
        self._calls: dict[int, int] = {}
        self._lock = asyncio.Lock()

    @staticmethod
    def _parse(content: str) -> dict[str, Any]:
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if not match:
            raise ValueError("response did not contain JSON")
        parsed = json.loads(match.group(0))
        if not isinstance(parsed, dict):
            raise ValueError("response JSON must be an object")
        return parsed

    def _fallback(self, artifact_ref: str, evidence_id: str, reason: str, started: float) -> VLMResult:
        return VLMResult(provider=self.provider, model=self.model, prompt_version=self.prompt_version, latency_ms=round((time.monotonic() - started) * 1000, 3), confidence=0, artifact_ref=artifact_ref, evidence_id=evidence_id, fallback_reason=reason)

    async def analyze(self, *, track_id: int, crop: bytes, artifact_ref: str, evidence_id: str) -> VLMResult:
        started = time.monotonic()
        digest = hashlib.sha256(crop).hexdigest()
        cache_key = f"{digest}:{self.model}:{self.prompt_version}"
        async with self._lock:
            if cache_key in self._cache:
                return self._cache[cache_key]
            if self._calls.get(track_id, 0) >= self.max_calls_per_track:
                return self._fallback(artifact_ref, evidence_id, "CALL_LIMIT", started)
            self._calls[track_id] = self._calls.get(track_id, 0) + 1
        if not self.request:
            return self._fallback(artifact_ref, evidence_id, "PROVIDER_NOT_CONFIGURED", started)
        try:
            payload = {"model": self.model, "prompt_version": self.prompt_version, "image_base64": base64.b64encode(crop).decode("ascii")}
            raw = await asyncio.wait_for(self.request(payload), timeout=self.timeout_seconds)
            parsed = self._parse(raw)
            result = VLMResult(provider=self.provider, model=self.model, prompt_version=self.prompt_version, latency_ms=round((time.monotonic() - started) * 1000, 3), confidence=float(parsed["vlm_confidence"]), artifact_ref=artifact_ref, evidence_id=evidence_id, scene_summary=str(parsed.get("scene_summary", "")))
            self._cache[cache_key] = result
            return result
        except asyncio.TimeoutError:
            return self._fallback(artifact_ref, evidence_id, "TIMEOUT", started)
        except Exception:
            return self._fallback(artifact_ref, evidence_id, "INVALID_PROVIDER_RESPONSE", started)
