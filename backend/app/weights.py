"""On-demand model weights loader and remote fetcher."""
from __future__ import annotations

import os
import urllib.request
from pathlib import Path

DEFAULT_WEIGHTS_URLS: dict[str, str] = {
    "rtdetr-l.pt": "https://github.com/ultralytics/assets/releases/download/v8.2.0/rtdetr-l.pt",
    "yolov8n.pt": "https://github.com/ultralytics/assets/releases/download/v8.2.0/yolov8n.pt",
}


def get_weights_dir() -> Path:
    target_dir = Path(os.getenv("MODEL_CACHE_DIR", "./weights")).resolve()
    target_dir.mkdir(parents=True, exist_ok=True)
    return target_dir


def ensure_model_weights(filename: str = "rtdetr-l.pt", custom_url: str | None = None) -> Path:
    """Ensures model weights exist locally in the weights cache directory.
    
    If missing, fetches the weights dynamically from remote storage.
    """
    weights_dir = get_weights_dir()
    file_path = weights_dir / filename

    if file_path.exists() and file_path.stat().st_size > 0:
        return file_path

    url = custom_url or DEFAULT_WEIGHTS_URLS.get(filename) or f"https://huggingface.co/models/{filename}"
    print(f"[VanRakshak Weights] Model file '{filename}' not found locally at {file_path}. Fetching from {url}...")

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "VanRakshak/1.0"})
        with urllib.request.urlopen(req) as response, open(file_path, "wb") as out_file:
            data = response.read()
            out_file.write(data)
        print(f"[VanRakshak Weights] Successfully downloaded '{filename}' ({file_path.stat().st_size} bytes).")
    except Exception as err:
        if file_path.exists():
            file_path.unlink()
        raise RuntimeError(f"Failed to download model weights '{filename}' from {url}: {err}") from err

    return file_path
