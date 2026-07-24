#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"
VIDEO_DIR="$ROOT_DIR/demo_videos"

echo "== Backend tests =="
(cd "$BACKEND_DIR" && .venv/bin/pytest -q)

echo "== Frontend tests =="
(cd "$FRONTEND_DIR" && npm test)

echo "== Frontend typecheck =="
(cd "$FRONTEND_DIR" && npm run typecheck)

echo "== Frontend production build =="
(cd "$FRONTEND_DIR" && npm run build)

echo "== YOLOv8n + ByteTrack benchmarks =="
for video in \
  "$VIDEO_DIR/01_thermal_intruder_drone.mp4" \
  "$VIDEO_DIR/02_intruder_vehicle_surveillance.mp4" \
  "$VIDEO_DIR/03_thermal_wildfire_smoke_recon.mp4" \
  "$VIDEO_DIR/04_wildlife_elephants_monitoring.mp4"; do
  [[ -f "$video" ]] || { echo "Missing benchmark video: $video" >&2; exit 1; }
  echo "-- $(basename "$video")"
  (cd "$BACKEND_DIR" && .venv/bin/python scripts/benchmark_video.py "$video" --bytetrack-only)
done

echo "All tests, builds, and benchmarks completed successfully."
