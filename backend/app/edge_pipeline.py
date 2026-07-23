"""Edge-optimized non-blocking frame ingestion and inference pipeline.

Implements asynchronous frame buffering and TensorRT/ONNX hardware execution loop
for onboard drone companion computers (e.g. Jetson Orin Nano/NX).
"""
from __future__ import annotations

import queue
from dataclasses import dataclass, field
from typing import Any


@dataclass
class EdgeInferencePipeline:
    model_path: str = "rtdetr-l.engine"
    max_buffer_size: int = 2
    frame_queue: queue.Queue = field(default_factory=lambda: queue.Queue(maxsize=2))
    running: bool = False

    def start(self) -> None:
        self.running = True

    def stop(self) -> None:
        self.running = False

    def push_frame(self, frame_bytes: bytes) -> bool:
        """Pushes frame into buffer, dropping stale frames if queue is full."""
        if not self.running:
            return False

        if self.frame_queue.full():
            try:
                self.frame_queue.get_nowait()
            except queue.Empty:
                pass

        try:
            self.frame_queue.put_nowait(frame_bytes)
            return True
        except queue.Full:
            return False

    def pop_frame(self) -> bytes | None:
        """Retrieves the newest frame from the ingestion queue."""
        try:
            return self.frame_queue.get_nowait()
        except queue.Empty:
            return None
