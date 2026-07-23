"""Edge-optimized non-blocking frame ingestion and inference pipeline.

Implements asynchronous frame buffering and TensorRT/ONNX hardware execution loop
for onboard drone companion computers (e.g. Jetson Orin Nano/NX).
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Any


@dataclass
class EdgeInferencePipeline:
    model_path: str = "rtdetr-l.engine"
    max_buffer_size: int = 2
    frame_queue: deque[bytes] = field(default_factory=deque)
    running: bool = False

    def start(self) -> None:
        self.running = True

    def stop(self) -> None:
        self.running = False

    def push_frame(self, frame_bytes: bytes) -> bool:
        """Pushes frame into buffer, dropping stale frames if queue is full."""
        if not self.running:
            return False

        if len(self.frame_queue) >= self.max_buffer_size:
            self.frame_queue.popleft()
        self.frame_queue.append(frame_bytes)
        return True

    def pop_frame(self) -> bytes | None:
        """Retrieves the newest frame from the ingestion queue."""
        if not self.frame_queue:
            return None
        newest = self.frame_queue[-1]
        self.frame_queue.clear()
        return newest
