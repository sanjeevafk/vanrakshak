# VanRakshak
### Autonomous AI Drone Patrolling & Forest Defense System

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Hugging Face Model](https://img.shields.io/badge/%F0%9F%A4%97%20Hugging%20Face-Model%20(YOLOv8n)-yellow)](https://huggingface.co/sanjeevafk/vanrakshak-forest-yolov8n)
[![Hugging Face Dataset](https://img.shields.io/badge/%F0%9F%A4%97%20Hugging%20Face-Dataset%20(7.9k%20Images)-blue)](https://huggingface.co/datasets/sanjeevafk/vanrakshak-forest-aerial-thermal)
[![Python](https://img.shields.io/badge/Python-3.11%2B-blue?logo=python)](backend/)
[![React](https://img.shields.io/badge/Frontend-React_18_%2B_Vite-61DAFB?logo=react)](frontend/)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?logo=fastapi)](backend/)
[![Status](https://img.shields.io/badge/Build-Passing-brightgreen)]()

**VanRakshak** is an open-source, edge-native autonomous drone surveillance and command-and-control (C2) platform engineered for **wildfire detection**, **anti-poaching defense**, **illegal logging interdiction**, and **wildlife conservation**.

---

## Pre-trained Models & Datasets

- **Hugging Face Model Hub**: [sanjeevafk/vanrakshak-forest-yolov8n](https://huggingface.co/sanjeevafk/vanrakshak-forest-yolov8n) (PyTorch + Edge ONNX weights)
- **Hugging Face Dataset Hub**: [sanjeevafk/vanrakshak-forest-aerial-thermal](https://huggingface.co/datasets/sanjeevafk/vanrakshak-forest-aerial-thermal) (7,946 aerial and LWIR thermal frames)
- **1-Click Google Colab Training**: [vanrakshak_yolov8_training.ipynb](https://colab.research.google.com/github/sanjeevafk/vanrakshak/blob/main/vanrakshak_yolov8_training.ipynb)

### Empirical Model Benchmarks (Tesla T4 GPU)

| Metric | Measured Score | Hardware / Note |
|---|---|---|
| **mAP@50** | **80.76%** | High-altitude bounding box detection quality |
| **Precision** | **83.76%** | Ultra-low false alarm rate for autonomous ranger alerting |
| **Recall** | **72.45%** | Robust target recall across canopy occlusion & night thermal |
| **mAP@50-95** | **42.71%** | Strict multi-IoU geometric precision |
| **Inference Latency** | **2.7 ms** | **~190+ FPS throughput** on GPU (5.2 ms end-to-end frame turnaround) |
| **Model Size** | **3.0M params** | **6.0 MB** PyTorch (`best.pt`) / **11.7 MB** ONNX (`best.onnx`) |

---

## Key Capabilities

- **Edge AI Computer Vision**: Real-time object detection and multi-object tracking (YOLOv8 + ByteTrack) optimized for edge companion computers (NVIDIA Jetson / Raspberry Pi).
- **Multimodal VLM Verification**: Bounded crop extraction and zero-shot Vision-Language Model (VLM) scene enrichment to verify threats and suppress false positives before escalation.
- **Deterministic Safety Policy Engine**: Rule engine enforcing wildlife-safe protocols (human deterrent sirens are strictly suppressed for elephants and endangered fauna) while triggering emergency ranger dispatch and automated fire suppressant deployment for confirmed hazards.
- **Tactical Mission C2 Console**: React + Vite operator cockpit featuring live telemetry, event replay streams, evidence inspection drawers, and actuator controls.
- **Hardware & MAVLink / SITL Integration**: Native autopilot seam translating mission decisions into MAVLink commands (`RETURN_TO_BASE`, `PATROL_SCAN`, status alerts) compatible with ArduPilot / PX4.

---

## System Architecture

```
                               ┌────────────────────────────────────────┐
                               │           Video / Drone Feed           │
                               └──────────────────┬─────────────────────┘
                                                  │
                                                  ▼
                        ┌───────────────────────────────────────────────────┐
                        │      Edge Perception (YOLOv8 + ByteTrack)         │
                        └─────────────────────────┬─────────────────────────┘
                                                  │ (Detections & Bboxes)
                                                  ▼
                        ┌───────────────────────────────────────────────────┐
                        │  Evidence Store (Quality Bounded Crop Extractor)  │
                        └─────────────────────────┬─────────────────────────┘
                                                  │
                       ┌──────────────────────────┴──────────────────────────┐
                       ▼                                                     ▼
    ┌──────────────────────────────────────┐             ┌──────────────────────────────────────┐
    │     VLM Multimodal Verification      │             │      Acoustic & Sensor Telemetry     │
    └──────────────────┬───────────────────┘             └──────────────────┬───────────────────┘
                       │                                                    │
                       └──────────────────────────┬─────────────────────────┘
                                                  │
                                                  ▼
                        ┌───────────────────────────────────────────────────┐
                        │     Deterministic Domain Safety Policy Engine     │
                        │   (Anti-Poaching · Wildlife Safe · Fire Alert)    │
                        └─────────────────────────┬─────────────────────────┘
                                                  │
                                                  ▼
                        ┌───────────────────────────────────────────────────┐
                        │     Mission Control & Actuator Dispatch Seam      │
                        │  (MAVLink RTL · Acoustic Siren · Ranger Dispatch) │
                        └─────────────────────────┬─────────────────────────┘
                                                  │
                                                  ▼
                        ┌───────────────────────────────────────────────────┐
                        │       Tactical Operator C2 Web Console            │
                        └───────────────────────────────────────────────────┘
```

---

## Quick Start

### 1. Clone & Install

```bash
# Clone repository
git clone https://github.com/sanjeevafk/vanrakshak.git
cd vanrakshak

# Install backend and frontend dependencies
make install
```

### 2. Configure Environment

```bash
cp .env.example .env
```

*(Optional: configure `NVIDIA_API_KEY` for live VLM multimodal verification. Synthetic and local fallback modes work out-of-the-box without keys.)*

### 3. Launch Demo Application

```bash
make start
```

- **Frontend Console**: [http://127.0.0.1:5173](http://127.0.0.1:5173)
- **FastAPI Backend Docs**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

## Testing & Benchmarks

```bash
# Run full backend and frontend test suite
make test

# Typecheck and build frontend for production
make build

# Run the complete evaluation benchmark
make eval
```

---

## Repository Structure

```
vanrakshak/
├── backend/                  # FastAPI Edge Backend
│   ├── app/                  # Perception, Policies, Replay, Actuator, VLM
│   ├── tests/                # Unit and integration test suite (63+ tests)
│   ├── pyproject.toml        # Backend configuration
│   └── requirements.txt      # Python dependencies
├── frontend/                 # Tactical C2 Console (React + TypeScript + Vite)
│   ├── src/                  # Components, Pages, State & Services
│   ├── tests/                # Vitest test suite
│   └── vite.config.ts        # Vite build configuration
├── docs/                     # Technical specifications and guides
│   └── ARCHITECTURE.md                     # System architecture specification
├── scripts/                  # Automation & Benchmark Runners
│   ├── start_app.sh          # One-command dual server launcher
│   ├── run_evals.sh          # Automated evaluation and test runner
│   ├── benchmark_video.py    # YOLOv8 + ByteTrack benchmark
│   └── export_tensorrt.py    # TensorRT engine export helper
├── Makefile                  # Standard developer commands
├── LICENSE                   # Apache 2.0 Open Source License
└── README.md
```

---

## Technical Documentation

- [System Architecture & Design Specification](docs/ARCHITECTURE.md)

---

## Contributing

We welcome community contributions. Please read our [CONTRIBUTING.md](CONTRIBUTING.md) guide before submitting pull requests.

---

## License

This project is licensed under the **Apache License 2.0** — see the [LICENSE](LICENSE) file for details.
