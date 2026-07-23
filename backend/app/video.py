from io import BytesIO
from pathlib import Path
import tempfile

from .schemas import Detection, VideoDetectionResponse, VideoFrameResponse


def process_video(payload: bytes, sample_every_n_frames: int = 5) -> VideoDetectionResponse:
    """Process an MP4 using YOLO tracking when available.

    Model weights are loaded at runtime by ultralytics. If OpenCV/model loading is
    unavailable, the response remains valid and explicitly reports FALLBACK.
    """
    if not payload:
        return VideoDetectionResponse(frame_count=0, fps=0, source="FALLBACK", frames=[])
    try:
        import cv2
        from ultralytics import YOLO

        with tempfile.NamedTemporaryFile(suffix=Path(".mp4").name, delete=True) as temp:
            temp.write(payload)
            temp.flush()
            capture = cv2.VideoCapture(temp.name)
            fps = float(capture.get(cv2.CAP_PROP_FPS) or 0)
            total = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
            model = YOLO("yolov8n.pt")
            frames: list[VideoFrameResponse] = []
            index = 0
            while True:
                ok, frame = capture.read()
                if not ok:
                    break
                if index % max(1, sample_every_n_frames) == 0:
                    result = model.track(frame, persist=True, verbose=False)[0]
                    detections: list[Detection] = []
                    if result.boxes is not None:
                        for box in result.boxes:
                            xyxy = box.xyxy[0].tolist()
                            track_id = int(box.id[0]) if box.id is not None else index
                            detections.append(Detection(track_id=track_id, **{"class": model.names[int(box.cls[0])]}, confidence=float(box.conf[0]), bbox=xyxy))
                    frames.append(VideoFrameResponse(frame_index=index, timestamp_seconds=index / fps if fps else 0, detections=detections))
                index += 1
            capture.release()
            return VideoDetectionResponse(frame_count=total or index, fps=fps, source="YOLO", frames=frames)
    except Exception:
        return VideoDetectionResponse(frame_count=0, fps=0, source="FALLBACK", frames=[])
