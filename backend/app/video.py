from pathlib import Path
import tempfile
from typing import Callable

from .schemas import Detection, VideoDetectionResponse, VideoFrameResponse


def process_video(payload: bytes, sample_every_n_frames: int = 2, model_name: str = "yolov8n.pt", tracker_name: str = "bytetrack.yaml", confidence_threshold: float = 0.35, on_sample: Callable[[bytes, int, float, list[Detection]], None] | None = None) -> VideoDetectionResponse:
    """Process an MP4 using YOLO tracking when available.

    Model weights are loaded at runtime by ultralytics. If OpenCV/model loading is
    unavailable, the response remains valid and explicitly reports FALLBACK.
    """
    if not payload:
        return VideoDetectionResponse(frame_count=0, fps=0, source="FALLBACK", frames=[])
    try:
        import cv2
        from ultralytics import YOLO, RTDETR

        with tempfile.NamedTemporaryFile(suffix=Path(".mp4").name, delete=True) as temp:
            temp.write(payload)
            temp.flush()
            capture = cv2.VideoCapture(temp.name)
            fps = float(capture.get(cv2.CAP_PROP_FPS) or 0)
            total = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
            model = RTDETR(model_name) if model_name.lower().startswith("rtdetr") else YOLO(model_name)
            frames: list[VideoFrameResponse] = []
            representative_frame: str | None = None
            index = 0
            next_fallback_id = 1_000_000
            while True:
                ok, frame = capture.read()
                if not ok:
                    break
                if index % max(1, sample_every_n_frames) == 0:
                    if representative_frame is None:
                        import base64
                        encoded_ok, encoded = cv2.imencode(".jpg", frame)
                        if encoded_ok:
                            representative_frame = base64.b64encode(encoded.tobytes()).decode("ascii")
                    result = model.track(frame, persist=True, tracker=tracker_name, conf=confidence_threshold, verbose=False)[0]
                    detections: list[Detection] = []
                    seen_track_ids: set[int] = set()
                    if result.boxes is not None:
                        for box in result.boxes:  # type: ignore[attr-defined]
                            xyxy = box.xyxy[0].tolist()
                            raw_id = int(box.id[0].item()) if box.id is not None else None
                            # A tracker ID must be unique within a frame. Some tracker/model
                            # failures expose 0 or duplicate IDs; do not silently publish them.
                            if raw_id is None or raw_id in seen_track_ids:
                                track_id = next_fallback_id
                                next_fallback_id += 1
                            else:
                                track_id = raw_id
                            seen_track_ids.add(track_id)
                            class_id = int(box.cls[0].item())
                            confidence = float(box.conf[0].item())
                            if confidence < confidence_threshold:
                                continue
                            detections.append(Detection(track_id=track_id, **{"class": model.names[class_id]}, confidence=confidence, bbox=xyxy))
                    timestamp = index / fps if fps else 0
                    if on_sample:
                        on_sample(frame, index, timestamp, detections)
                    frames.append(VideoFrameResponse(frame_index=index, timestamp_seconds=timestamp, detections=detections))
                index += 1
            capture.release()
            return VideoDetectionResponse(frame_count=total or index, fps=fps, source="YOLO", frames=frames, representative_frame=representative_frame)
    except Exception:
        return VideoDetectionResponse(frame_count=0, fps=0, source="FALLBACK", frames=[])
