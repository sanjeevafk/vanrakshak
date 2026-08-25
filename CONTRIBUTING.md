# Contributing to VanRakshak

Thank you for your interest in contributing to **VanRakshak**, an open-source autonomous drone patrolling and forest conservation platform.

## Development Setup

### 1. Prerequisites
- **Python 3.11+**
- **Node.js 18+** and **npm**
- (Optional) **ArduPilot SITL** for simulated drone MAVLink telemetry

### 2. Quick Setup

```bash
# Clone the repository
git clone https://github.com/sanjeevafk/vanrakshak.git
cd vanrakshak

# Install dependencies
make install

# Configure environment
cp .env.example .env

# Run the complete application
make start
```

## Running Tests & Benchmarks

Before submitting a pull request, ensure all tests pass:

```bash
# Run all backend and frontend tests
make test

# Run frontend typecheck and production build
make build

# Run the full automated evaluation pipeline
make eval
```

## Architectural Guidelines

- **Event-Driven Immutability**: All mission state is derived from an append-only `MissionEvent` trace.
- **Strict Separation of Concerns**: Keep perception, evidence capture, domain safety policies, mission state machines, and hardware actuation cleanly separated.
- **Safety First**: Non-lethal, conservative interventions only. Wildlife encounters must not trigger acoustic intruder sirens.

## Submitting Pull Requests

1. Fork the repository and create your branch from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```
2. Commit your changes with clear, descriptive commit messages:
   ```bash
   git commit -m "feat: add thermal wildfire hotspot tracking"
   ```
3. Push to your branch and open a Pull Request.

## License

By contributing to VanRakshak, you agree that your contributions will be licensed under the Apache 2.0 License.
