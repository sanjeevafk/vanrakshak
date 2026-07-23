import json
import sys
import time
from pathlib import Path

from app.video import process_video


def main() -> None:
    video = Path(sys.argv[1])
    payload = video.read_bytes()
    cases = [
        ("YOLOv8n + BoT-SORT", "yolov8n.pt", "botsort.yaml"),
        ("YOLOv8n + ByteTrack", "yolov8n.pt", "bytetrack.yaml"),
        ("RT-DETR-l + BoT-SORT", "rtdetr-l.pt", "botsort.yaml"),
    ]
    if "--yolo-only" in sys.argv:
        cases = cases[:2]
    results = []
    for label, model, tracker in cases:
        started = time.perf_counter()
        response = process_video(payload, sample_every_n_frames=5, model_name=model, tracker_name=tracker)
        elapsed = time.perf_counter() - started
        ids = [d.track_id for frame in response.frames for d in frame.detections]
        results.append({
            "configuration": label,
            "model": model,
            "tracker": tracker,
            "source": response.source,
            "elapsed_seconds": round(elapsed, 2),
            "frame_count": response.frame_count,
            "sampled_frames": len(response.frames),
            "detections": len(ids),
            "unique_track_ids": len(set(ids)),
            "duplicate_ids_within_frame": sum(len([d.track_id for d in f.detections]) - len(set(d.track_id for d in f.detections)) for f in response.frames),
            "classes": sorted({d.class_name for f in response.frames for d in f.detections}),
        })
    print(json.dumps({"video": str(video), "results": results}, indent=2))


if __name__ == "__main__":
    main()
