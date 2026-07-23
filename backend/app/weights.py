"""On-demand model weights loader and remote fetcher."""
from __future__ import annotations

import os
import hashlib
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


def ensure_model_weights(filename: str = "rtdetr-l.pt", custom_url: str | None = None, expected_sha256: str | None = None, max_bytes: int = 2_000_000_000) -> Path:
    """Ensures model weights exist locally in the weights cache directory.
    
    If missing, fetches the weights dynamically from remote storage.
    """
    weights_dir = get_weights_dir()
    requested = Path(filename)
    if requested.name != filename or requested.is_absolute():
        raise ValueError("model filename must be a plain filename")
    file_path = (weights_dir / filename).resolve()
    if weights_dir.resolve() not in file_path.parents:
        raise ValueError("model path escapes cache directory")

    if file_path.exists() and file_path.stat().st_size > 0:
        return file_path

    url = custom_url or DEFAULT_WEIGHTS_URLS.get(filename)
    if not url or not (url.startswith("https://github.com/") or url.startswith("https://huggingface.co/")):
        raise ValueError("model URL must use an approved HTTPS host")

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "VanRakshak/1.0"})
        digest = hashlib.sha256(); total = 0
        with urllib.request.urlopen(req, timeout=60) as response, open(file_path, "wb") as out_file:
            while chunk := response.read(1024 * 1024):
                total += len(chunk)
                if total > max_bytes:
                    raise ValueError("model download exceeds maximum size")
                digest.update(chunk); out_file.write(chunk)
        if expected_sha256 and digest.hexdigest().lower() != expected_sha256.lower():
            raise ValueError("model checksum does not match expected SHA-256")
    except Exception as err:
        if file_path.exists():
            file_path.unlink()
        raise RuntimeError(f"Failed to download model weights '{filename}' from {url}: {err}") from err

    return file_path
