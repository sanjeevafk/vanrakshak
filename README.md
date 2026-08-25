# 🌲 VanRakshak (वनरक्षक)
### Autonomous AI Drone Patrolling & Forest Defense System

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11%2B-blue?logo=python)](backend/)
[![React](https://img.shields.io/badge/Frontend-React_18_%2B_Vite-61DAFB?logo=react)](frontend/)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?logo=fastapi)](backend/)
[![Status](https://img.shields.io/badge/Build-Passing-brightgreen)]()

**VanRakshak** is an open-source, edge-native autonomous drone surveillance and command-and-control (C2) platform engineered for **wildfire detection**, **anti-poaching defense**, **illegal logging interdiction**, and **wildlife conservation**.

---

## 🌟 Key Capabilities

- 🛰️ **Edge AI Computer Vision**: Real-time object detection and multi-object tracking (YOLOv8 + ByteTrack) optimized for edge companion computers (NVIDIA Jetson / Raspberry Pi).
- 🧠 **Multimodal VLM Verification**: Bounded crop extraction and zero-shot Vision-Language Model (VLM) scene enrichment to verify threats and suppress false positives before escalation.
- 🛡️ **Deterministic Safety Policy Engine**: Rule engine enforcing wildlife-safe protocols (human deterrent sirens are strictly suppressed for elephants and endangered fauna) while triggering emergency ranger dispatch and automated fire suppressant deployment for confirmed hazards.
- 🎮 **Tactical Mission C2 Console**: React + Vite operator cockpit featuring live telemetry, event replay streams, evidence inspection drawers, and actuator controls.
- 🚁 **Hardware & MAVLink / SITL Integration**: Native autopilot seam translating mission decisions into MAVLink commands (`RETURN_TO_BASE`, `PATROL_SCAN`, status alerts) compatible with ArduPilot / PX4.

---

## 🏗️ System Architecture

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

## 🚀 Quick Start

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

## 🧪 Testing & Benchmarks

```bash
# Run full backend and frontend test suite
make test

# Typecheck and build frontend for production
make build

# Run the complete evaluation benchmark
make eval
```

---

## 📂 Repository Structure

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
├── docs/                     # Architecture blueprints, pitch decks, and presentations
│   ├── MAVLINK_SITL_IMPLEMENTATION.md      # ArduPilot SITL Integration Guide
│   ├── YOLO_FINETUNING_IMPLEMENTATION.md   # Domain Model Fine-Tuning Blueprint
│   ├── vanrakshak_architecture_and_pitch_guide.md
│   └── vanrakshak_msme_presentation.html  # Interactive Pitch Deck
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

## 📚 Technical Documentation & Deep Dives

- 📖 [MAVLink & SITL Integration Blueprint](docs/MAVLINK_SITL_IMPLEMENTATION.md)
- 🎯 [Forest YOLO Fine-Tuning Guide](docs/YOLO_FINETUNING_IMPLEMENTATION.md)
- 📊 [Architecture & Strategy Guide](docs/vanrakshak_architecture_and_pitch_guide.md)
- 🖥️ [Interactive MSME Pitch Presentation](docs/vanrakshak_msme_presentation.html)

---

## 🤝 Contributing

We welcome community contributions! Please read our [CONTRIBUTING.md](CONTRIBUTING.md) guide before submitting pull requests.

---

## 📄 License

This project is licensed under the **Apache License 2.0** — see the [LICENSE](LICENSE) file for details.
