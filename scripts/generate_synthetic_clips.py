#!/usr/bin/env python3
"""Generate SYNTHETIC TEST FOOTAGE for the VanRakshak demo — free, offline, deterministic.

Why synthetic clips?
  We cannot legally film poaching. Compositing a REAL detected person (segmented out
  of demo_videos/02_intruder_vehicle_surveillance.mp4 by YOLOv8n-seg) onto forest
  canopy footage gives us realistic drone-aerial test footage that is GUARANTEED to
  pass the real detection pipeline — no API key, no network, no cost, deterministic.

HONESTY RULE (matches docs/vanrakshak_msme_demo_brief.md):
  Every generated clip is clearly labeled "SYNTHETIC TEST FOOTAGE" in the demo.
  These clips are NEVER presented as real drone footage. If a clip fails the
  pipeline check (no credible person detections), it is NOT kept — it is deleted.

Usage:
  python3 scripts/generate_synthetic_clips.py [--output-dir demo_videos] [--seconds 8]

Pipeline per clip:
  1. Segment the largest confident person out of the vehicle clip (YOLOv8n-seg) → RGBA sprite.
  2. Composite the sprite walking across a blurred forest-canopy background (aerial look).
  3. Encode with OpenCV (mp4v, 30 fps).
  4. Run it through backend/app/video.py (YOLOv8n + ByteTrack, every 2nd frame).
  5. Keep the clip ONLY if person detections >= MIN_PERSON_DETECTIONS and
     frames_with_person >= MIN_FRAMES_WITH_PERSON; otherwise delete it.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "demo_videos"
VEHICLE_CLIP = ROOT / "demo_videos" / "02_intruder_vehicle_surveillance.mp4"
FOREST_CLIP = ROOT / "demo_videos" / "04_wildlife_elephants_monitoring.mp4"
SEG_MODEL = ROOT / "backend" / "yolov8n-seg.pt"
FOREST_BG_FRAME = 200        # elephant-clip frame to blur into canopy

MIN_PERSON_DETECTIONS = 20   # credible person footprint across sampled frames
MIN_FRAMES_WITH_PERSON = 10  # persist across frames so ByteTrack forms a track

sys.path.insert(0, str(ROOT / "backend"))
from app.video import process_video  # noqa: E402  (after path setup)
from ultralytics import YOLO  # noqa: E402


def extract_person_sprite() -> np.ndarray:
    """Segment the largest confident person from the vehicle clip; return RGBA sprite."""
    seg = YOLO(str(SEG_MODEL))
    cap = cv2.VideoCapture(str(VEHICLE_CLIP))
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open {VEHICLE_CLIP}")
    best: tuple[float, int, int, int, int, np.ndarray, np.ndarray] | None = None
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    for n in range(0, frame_count, 5):
        cap.set(cv2.CAP_PROP_POS_FRAMES, n)
        ok, frame = cap.read()
        if not ok:
            continue
        res = seg(frame, verbose=False)[0]
        for box, mask in zip(res.boxes, res.masks or []):
            if res.names[int(box.cls[0])] != "person" or float(box.conf[0]) < 0.6:
                continue
            x1, y1, x2, y2 = [int(v) for v in box.xyxy[0]]
            area = (x2 - x1) * (y2 - y1)
            if best is None or area > best[0]:
                best = (area, x1, y1, x2, y2, mask.data[0].cpu().numpy(), frame)
    cap.release()
    if best is None:
        raise RuntimeError("No person found in the vehicle clip — cannot build a synthetic poacher clip.")
    _, x1, y1, x2, y2, mask, frame = best
    person_bgr = frame[y1:y2, x1:x2]
    fh, fw = frame.shape[:2]
    mask_full = cv2.resize(mask, (fw, fh), interpolation=cv2.INTER_LINEAR)
    mask_crop = cv2.resize(mask_full[y1:y2, x1:x2], (x2 - x1, y2 - y1), interpolation=cv2.INTER_LINEAR)
    return np.dstack([person_bgr, (mask_crop * 255).astype(np.uint8)])


def build_background() -> tuple[np.ndarray, int, int]:
    """Blur a forest frame into aerial canopy; return (bg, width, height)."""
    cap = cv2.VideoCapture(str(FOREST_CLIP))
    cap.set(cv2.CAP_PROP_POS_FRAMES, FOREST_BG_FRAME)
    ok, bg = cap.read()
    cap.release()
    if not ok:
        raise RuntimeError(f"Cannot read {FOREST_CLIP} frame {FOREST_BG_FRAME}")
    h, w = bg.shape[:2]
    bg = cv2.GaussianBlur(bg, (0, 0), sigmaX=30)  # heavy blur removes elephants -> clean canopy
    return bg, w, h


def composite_clip(sprite: np.ndarray, bg: np.ndarray, w: int, h: int, out: Path, seconds: int = 8, fps: int = 30) -> None:
    """Animate the person walking across the canopy and encode an mp4."""
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(out), fourcc, fps, (w, h))
    if not writer.isOpened():
        raise RuntimeError("OpenCV VideoWriter could not open (mp4v codec missing).")
    n = int(fps * seconds)
    sprite_h = int(h * 0.22)  # person ~22% of frame height — realistic aerial scale
    for i in range(n):
        t = i / max(1, n - 1)
        scale = 0.85 + 0.3 * t  # gentle approach: "drone descends"
        sh = int(sprite_h * scale)
        sw = max(1, int(sh * sprite.shape[1] / sprite.shape[0]))
        sp = cv2.resize(sprite, (sw, sh), interpolation=cv2.INTER_AREA)
        x = int(w * (0.05 + 0.8 * t))
        y = int(h * (0.60 - 0.08 * t + 0.01 * np.sin(i / 6)))
        frame_i = bg.copy()
        alpha = sp[:, :, 3:4].astype(np.float32) / 255.0
        roi = frame_i[y:y + sh, x:x + sw]
        if roi.shape[:2] == (sh, sw):
            blended = sp[:, :, :3].astype(np.float32) * alpha + roi.astype(np.float32) * (1.0 - alpha)
            frame_i[y:y + sh, x:x + sw] = blended.astype(np.uint8)
        writer.write(frame_i)
    writer.release()


def verify_clip(path: Path) -> dict:
    """Run the real detection pipeline; return detection stats."""
    started = time.perf_counter()
    response = process_video(path.read_bytes(), sample_every_n_frames=2, model_name="yolov8n.pt", tracker_name="bytetrack.yaml")
    elapsed = time.perf_counter() - started
    frames_with_person = 0
    total_person_detections = 0
    track_ids: set[int] = set()
    class_counts: dict[str, int] = {}
    for frame in response.frames:
        for det in frame.detections:
            class_counts[det.class_name] = class_counts.get(det.class_name, 0) + 1
            if det.class_name == "person":
                total_person_detections += 1
                if det.track_id is not None:
                    track_ids.add(det.track_id)
        if any(d.class_name == "person" for d in frame.detections):
            frames_with_person += 1
    return {
        "clip": path.name,
        "runtime_s": round(elapsed, 2),
        "frames_sampled": len(response.frames),
        "total_detections": sum(class_counts.values()),
        "person_detections": total_person_detections,
        "frames_with_person": frames_with_person,
        "unique_person_tracks": len(track_ids),
        "classes": class_counts,
        "passes": total_person_detections >= MIN_PERSON_DETECTIONS and frames_with_person >= MIN_FRAMES_WITH_PERSON,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic poaching test footage (free, offline, deterministic).")
    parser.add_argument("--output-dir", default=str(OUT_DIR), help="Where to write clips and metadata (default: demo_videos/)")
    parser.add_argument("--seconds", type=int, default=8, help="Clip length in seconds (default: 8)")
    args = parser.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(exist_ok=True)
    for required in (VEHICLE_CLIP, FOREST_CLIP):
        if not required.exists():
            sys.exit(f"Missing required clip: {required}")

    print("== 1/4 Extracting person sprite (YOLOv8n-seg, offline) ==")
    sprite = extract_person_sprite()
    print(f"   sprite: {sprite.shape[1]}x{sprite.shape[0]} RGBA (real person pixels)")

    print("== 2/4 Building blurred forest-canopy background ==")
    bg, w, h = build_background()
    print(f"   background: {w}x{h}")

    name = "05_poaching_suspect_synthetic"
    path = out_dir / f"{name}.mp4"
    print(f"== 3/4 Compositing + encoding -> {path.name} ({args.seconds}s @ 30fps) ==")
    composite_clip(sprite, bg, w, h, path, seconds=args.seconds)

    print("== 4/4 Verifying through the real pipeline (YOLOv8n + ByteTrack) ==")
    stats = verify_clip(path)
    print(json.dumps(stats, indent=2))

    meta = {
        "label": "SYNTHETIC TEST FOOTAGE",
        "generation": "procedural composite (offline, deterministic, zero-cost)",
        "person_source": str(VEHICLE_CLIP),
        "background_source": str(FOREST_CLIP),
        "notes": "Real person segmented by YOLOv8n-seg composited onto blurred forest canopy. Never present as real drone footage.",
        **stats,
    }
    if stats["passes"]:
        (out_dir / f"{name}.meta.json").write_text(json.dumps(meta, indent=2))
        print(f"   KEPT -> {out_dir / (name + '.mp4')} (credible person detections, {stats['unique_person_tracks']} stable track(s))")
        (out_dir / "synthetic_generation_report.json").write_text(json.dumps({"kept": [name], "rejected": [], "report": meta}, indent=2))
        print(f"\nDone. Metadata: {out_dir / (name + '.meta.json')}")
    else:
        # Never leave a failing clip (or a stale meta claiming it passed) in the demo dir.
        path.unlink(missing_ok=True)
        (out_dir / f"{name}.meta.json").unlink(missing_ok=True)
        (out_dir / "synthetic_generation_report.json").write_text(
            json.dumps({"kept": [], "rejected": [name], "reason": "did not meet person-detection thresholds", "report": meta}, indent=2)
        )
        print(f"   REJECTED + deleted -> {name}.mp4 (not enough person detections; do NOT use in the demo)")
        sys.exit(1)


if __name__ == "__main__":
    main()
