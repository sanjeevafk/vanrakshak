#!/usr/bin/env python3
"""TensorRT Export & Edge Inference Optimization CLI for RT-DETR.

Exports PyTorch (.pt) weights to TensorRT (.engine) or ONNX format for low-latency
high-FPS execution on edge companion hardware (e.g., NVIDIA Jetson Orin Nano/NX).
"""
import argparse
import sys
from pathlib import Path

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.weights import ensure_model_weights


def export_model(model_name: str = "rtdetr-l.pt", export_format: str = "engine", half: bool = True, device: int = 0) -> Path:
    """Exports PyTorch RT-DETR model to compiled TensorRT or ONNX engine."""
    weights_path = ensure_model_weights(model_name)
    print(f"[TensorRT Exporter] Loading model weights from {weights_path}...")

    try:
        from ultralytics import RTDETR
    except ImportError:
        print("[TensorRT Exporter] Error: 'ultralytics' package is required for TensorRT export.")
        print("Install it with: pip install ultralytics")
        sys.exit(1)

    model = RTDETR(str(weights_path))

    print(f"[TensorRT Exporter] Exporting model to format='{export_format}', half={half}, device={device}...")
    output_file = model.export(format=export_format, half=half, device=device)
    print(f"[TensorRT Exporter] Model successfully exported to: {output_file}")
    return Path(output_file)


def main():
    parser = argparse.ArgumentParser(description="Export RT-DETR model to TensorRT engine for edge hardware.")
    parser.add_argument("--model", type=str, default="rtdetr-l.pt", help="Model filename (default: rtdetr-l.pt)")
    parser.add_argument("--format", type=str, default="engine", choices=["engine", "onnx", "torchscript"], help="Export format (default: engine)")
    parser.add_argument("--half", dest="half", action="store_true", help="Enable FP16 precision")
    parser.add_argument("--no-half", dest="half", action="store_false", help="Disable FP16 precision")
    parser.set_defaults(half=True)
    parser.add_argument("--device", type=int, default=0, help="CUDA device index (default: 0)")

    args = parser.parse_args()
    export_model(model_name=args.model, export_format=args.format, half=args.half, device=args.device)


if __name__ == "__main__":
    main()
