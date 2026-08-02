# VanRakshak — Project Brief & MSME Demo Presentation Strategy

**Prepared for:** MSME Idea Hackathon 6.0 — live demo + pitch
**Team:** Sanjeev Kumar S (lead) · Prajan SS · Kamlesh Y — 3rd Year CSE, Robotics & Automation, Saveetha Engineering College
**Mentor:** Dr. Rajendra Thilahar C, Department of AI & DS
**IP:** Patent application No. 202341070952 A (published 03/11/2023)
**Companion artifacts:** `docs/vanrakshak_msme_presentation.html` (presentation site) · `docs/index.html` (narrative one-pager) · `docs/VanRakshak_Refined_PitchDeck_v5.pptx` · `docs/VanRakshak_Pitch_Deck.pptx`

> This brief is the reference for how we demo VanRakshak. It is honest about what is real, what is simulated, and what is still only documented. Read it before any dry run.

---

## 1. Reality check — what is real, simulated, or only documented

This matters more than anything else. Presenting anything as live that isn't will surface in Q&A and sink credibility.

| Layer | Status | Where |
| --- | --- | --- |
| Synthetic test footage (poaching) | **Synthetic, clearly labeled** | `scripts/generate_synthetic_clips.py` (offline, zero-cost) → `demo_videos/05_…` + `.meta.json` `SYNTHETIC TEST FOOTAGE`; only clips that pass the real detection pipeline are kept |
| Video ingestion + YOLOv8n detection | **Real** | `backend/app/video.py`, ultralytics, real model weights, benchmarked on 4 clips |
| ByteTrack multi-object tracking | **Real** | Stable track IDs across frames (11 unique IDs on the elephant clip) |
| VLM scene understanding (NVIDIA llama-3.2-11b-vision) | **Real** (needs API key + network) | `backend/app/services.py`, `vlm.py`; rule-based fallback when unreachable |
| Threat scoring + 5 independent policies | **Real** | `mission.py`, `policies.py`, config-driven weights |
| Mission FSM + incident FSM | **Real** | `state_machines.py`, tested transitions |
| Actuator commands + ACK lifecycle | **Real logic, simulated hardware** | `actuator.py`; `SENT → ACKNOWLEDGED`, suppressant → `UNAVAILABLE` |
| Deterministic event log + replay | **Real** | Backend-owned replay controls (cursor / step / speed) |
| Telemetry (battery/GPS/wind) | **Simulated** | Physics-informed generator, no flight controller |
| Ranger dispatch workflow | **Simulated** | Event/command-level only |
| Drone, MAVLink, siren, payload, fire suppression | **Not present** | Explicitly Phase 2 / out of scope |
| "Defense-grade C2" UI (Leaflet map, FSM visualizer, siren audio, dispatch modal, Recharts, Zustand) | **Partially built** | Spec in `docs/vanrakshak_demo_plan.md`; `App.tsx` is a functional console with an autonomous-response panel, siren banner, and CONFIRMED HUMAN demo — no map/HUD/dispatch modal yet |

### The single most important finding

**The strongest asset is the decision discipline, not the detection.** The elephant clip demonstrates something most AI-drone demos cannot: the system deliberately **does not** trigger the human-intruder siren for wildlife. The vehicle clip shows *dispatch without siren* ("detection is not confirmation"). The confirmed-human replay shows the full escalation. This "conservative by design / know when not to escalate" story is **provably demonstrated in working, tested code**.

The **frontend console** was refactored to make the autonomous response visible (siren banner, spotlight vignette, CONFIRMED HUMAN demo, FIRE SUPPRESSION → UNAVAILABLE) but is still a lean console, not the "defense-grade C2" imagery (map, HUD, dispatch modal) in the docs and pitch deck. The biggest landmine is the **thermal/fire gap**: the stock COCO model returns *zero* detections on thermal footage and can misclassify smoke. Both are handled head-on in the demo narrative.

---

## 2. Verification status (defensible numbers)

- Backend: **61 tests passing** · Frontend: **4 tests + typecheck + production build passing**
- Elephant clip: 735 detections, 11 unique tracks, 225 sampled frames, ~12 s runtime
- Vehicle clip: 157 detections, 27 tracks · Thermal intruder: 0 detections · Wildfire: 1 (misclassified "donut")
- Synthetic poaching clip (`05_poaching_suspect_synthetic.mp4`): **120/120 sampled frames detect a person, 1 stable track** — procedural composite, `SYNTHETIC TEST FOOTAGE`
- Gemini-generated clips (all 1280×720, 10 s, labeled synthetic; stock YOLOv8n + ByteTrack):
  - `Photorealistic_autonomous_dron.mp4` → **122 person detections**, 5 tracks · VLM: `ILLEGAL_LOGGING` · HIGH · conf 0.80
  - `Thermal_infrared_drone_surveil.mp4` → **127 person detections**, 8 tracks · VLM: `ILLEGAL_LOGGING` · HIGH · conf 0.80
  - `Ultra_realistic_FPV_drone_reco.mp4` → **65 person detections**, 9 tracks · VLM: `ILLEGAL_LOGGING` · HIGH · conf 0.80
- Gemini clips read as **illegal logging** (not `POACHING_SUSPECT`) — use them for the illegal-activity beat; the composite clip + `POACHING SUSPECT (DEMO)` button carry the poaching story
- Deterministic replay: same video + same config → byte-equivalent event traces
- Demo environment is **ready to run**: `backend/.venv`, `frontend/node_modules`, all clips in `demo_videos/`

---

## 3. Positioning strategy — "Demo the brain, not the drone"

> "A drone is a camera with propellers. Every vendor can fly one. The value — and the moat — is what happens **between the pixels and the decision**. VanRakshak is the autonomy brain: real perception, real semantic reasoning, deterministic policy, closed-loop command semantics. Today we demo the brain live. The drone is a swap-in payload; the interface boundary where it plugs in is already defined."

This reframe (a) acknowledges the no-drone reality before anyone can raise it, (b) turns it into an architectural strength, (c) sets expectations that the demo is software, live, right now.

### Narrative arc

1. **Act I — See (proof in numbers):** problem → metrics — 735 real detections, 0 sirens for wildlife: the *non-alarm* decision, measured.
2. **Act II — Decide (interactive):** the FSM run-path animation + threat calculator (6:30–7:45) — the confirmed-human escalation lives **in the deck**. Contrast beat (spoken): the vehicle run dispatched without a siren — "detection is not confirmation."
3. **Act III — Prove:** architecture + innovations (conservative-by-design, edge/offline) + roadmap.
4. **Closer — Ask + live console:** commercial ask → closing, then the live C2 console (CONFIRMED HUMAN) in the 9:30–10:00 slot; the elephant clip stays pre-loaded for a one-click ANALYZE in Q&A.

---

## 4. The 10-minute demo script (+ 5-minute Q&A)

Pacing: every deck section maps to a timed slot (also encoded in the deck's speaker notes — press `S`). Total **10:00**, then **5:00 Q&A**.

| Time | Deck section | Focus |
| --- | --- | --- |
| 0:00–0:45 | Hero | Framing line + honesty pledge + patent |
| 0:45–2:15 | Problem | 6 pain points → the punch line |
| 2:15–3:00 | Vision | The autonomous forest response agent |
| 3:00–3:40 | Metrics | 735 · 0 · 5,607 · 98% |
| 3:40–5:10 | Architecture | 5-stage pipeline + dual-tier edge/cloud |
| 5:10–6:30 | Innovations | 6 differentiators + threat formula |
| 6:30–7:45 | FSM + calculator | Run escalation path; judge pulls sliders |
| 7:45–8:30 | Roadmap | Phases, hardware swap-in story |
| 8:30–9:30 | Commercial | ₹15 L ask, competitive table |
| 9:30–10:00 | Closing + live console | Ask; then CONFIRMED HUMAN in the console |

### 0:00–0:45 — Hook & framing (Hero)
- Framing line: *"A drone is a camera with propellers. Every vendor can fly one. The value — and the moat — is what happens **between the pixels and the decision**. Today we demo the brain live. The drone is a swap-in payload; the interface boundary is already defined."*
- Honesty pledge: *"Perception and reasoning are real, running live on real footage. Telemetry and actuators are simulated."* Mention the patent (202341070952A) early.

### 0:45–2:15 — The problem (6 cards)
- "Forests are vast. Surveillance isn't." Walk 6 pain points, ~8 seconds each.
- Punch line: "Current drones only record footage — they don't decide anything. Alert fatigue is the killer."
- Close on the three stats: <3 s alert latency vs. hours today · >15 km² per sortie · >60% patrol cost reduction.

### 2:15–3:00 — Vision (5 pillars)
- One sentence: *"An autonomous forest response agent that patrols, understands, assesses, acts, and coordinates with rangers."*
- Anchor each pillar to a tested module. Chips: Jetson Orin Nano · RGB/Thermal/LiDAR/GPS/IMU · patent.

### 3:00–3:40 — Proof, not slides (metrics)
- "Measured numbers from real runs, not estimates."
- **Money metric: 0 human-intruder sirens fired for wildlife.** Say it twice.
- 735 real detections · 5,607 events replayed deterministically · 98% bandwidth reduction.

### 3:40–5:10 — Architecture (pipeline + dual-tier)
- Walk Perceive → Prove → Reason → Control → Act.
- "Every decision carries evidence references, thresholds, and reason codes — an audit trail, not a black box."
- Dual-tier card answers the offline question preemptively: tracking onboard at 30+ FPS, quantized VLM on the Jetson, events + 20–40 KB keyframes instead of video streams.

### 5:10–6:30 — Innovations (6 cards + formula)
- "Not an LLM wrapper" — the VLM is one of four fused signals in a deterministic formula (show the formula card).
- Lead with conservative-by-design: 735 detections, 0 sirens for wildlife.
- The >98% bandwidth card is the swarm argument.

### 6:30–7:45 — Mission FSM + threat calculator (interactive)
- Press **Run confirmed-human path**; watch PATROL → INVESTIGATE → TRACK → VERIFY → ALERT highlight.
- "Deterministic: same inputs, same transitions, same reason codes. An LLM has never touched a motor."
- Calculator: "Judge, pull these sliders." Thresholds 45 / 85. An elephant profile stays under the siren.

### 7:45–8:30 — Roadmap
- Roadmap: prototype (this demo) → pilot → trials → commercial → multi-state → national. Phase 1 domain models close the thermal gap; Phase 2 MAVLink + payloads.
- "The hardware is a swap-in payload — the interface contract already exists."

### 8:30–9:30 — Commercial
- Business: hardware + DaaS + recurring analytics + govt contracts. The ₹15 L ask allocation bars animate in.
- Close the competitive table: full autonomy + edge AI + real-time alerts is the gap.

### 9:30–10:00 — Closing + live console demo
- "From surveillance to intelligence. The brain is ready — the next step is putting it in the air with a partner forest department."
- Team + mentor + contact. Ask: partner a pilot.
- **The C2 console is the prototype.** The stack is already running (`make start`). Open `http://127.0.0.1:5173` and click **CONFIRMED HUMAN (DEMO)** or **POACHING SUSPECT (DEMO)** — siren banner + ACK chips show the end-to-end autonomous response; **FIRE SUPPRESSION (PHASE 2)** shows the UNAVAILABLE path. Keep the elephant clip pre-loaded (not yet analyzed) so a Q&A **ANALYZE** is one click (~12 s).

### The 5-minute Q&A allocation
- Budget ~60 s per question, 4 questions, ~20 s closing line. Highest-probability four: (1) "Where's the drone / isn't this a simulation?", (2) "Isn't this an LLM wrapper?", (3) "It can't detect fire?", (4) "What's real vs. simulated?"
- Answer with the one-liner from the Q&A table, then offer the live demo as the proof — the elephant clip is pre-loaded in the console, so "want to see it live?" is a one-click ANALYZE.

---

## 5. Pre-demo checklist & runbook

```bash
make start          # starts backend :8000 + frontend :5173 (scripts/start_app.sh)
curl localhost:8000/health && curl localhost:8000/config/runtime
```

1. **Open the deck over HTTP:** `http://127.0.0.1:8000/presentation/vanrakshak_msme_presentation.html` after `make start` — one-origin load, guaranteed clean. The prototype story now lives in the **C2 console** at `http://127.0.0.1:5173` (the deck's former video-clip section was removed — the console *is* the prototype).
2. **Pre-warm the model** — run the elephant clip once before the audience arrives (first run downloads YOLOv8n weights, warms the VLM connection).
3. **Verify the VLM key** in `.env`; confirm one `scene-understanding` call succeeds. If network is flaky, lower `vlm_provider_timeout_seconds` so the fallback path shows gracefully.
4. **C2 console demo buttons are now built-in:** `CONFIRMED HUMAN (DEMO)` runs the synthetic escalation (siren + dispatch, ACK lifecycle); `POACHING SUSPECT (DEMO)` runs the same person path with the VLM activity labeled `POACHING_SUSPECT` (siren + dispatch + warning banner) — the poaching story, honestly labeled as synthetic; and `FIRE SUPPRESSION (PHASE 2)` shows the UNAVAILABLE path. No extra prep needed.
5. **Clips pre-selected** in `demo_videos/` — elephant first. **Pre-load the elephant clip in the C2 console** (file chosen, not yet analyzed) so a Q&A ANALYZE is one click (~12 s narration). **Pre-open the console tab in the browser** (`http://127.0.0.1:5173`) and keep it warm in the background — the 9:30 close then switches to an already-loaded tab instead of typing a URL and waiting for the dev server. Vehicle and thermal clips stay available for contrast runs.
6. **Screen:** fullscreen the browser; the dark theme projects well. The siren is a visual pulse — there is no audio asset, so don't promise sound.
7. **Backup:** if a video analysis hangs, fall back to `CONFIRMED HUMAN (DEMO)` or the synthetic mission API (`/missions/{id}/run` with `ticks`) — instant and deterministic.
8. **Venv note:** console scripts were repaired (stale shebangs from the old repo path) — `make start` and `make eval` now work; if the venv is ever recreated, re-check `.venv/bin/uvicorn`.
9. **Dry-run the full 10:00 + 5:00 once**, with the Q&A out loud.

---

## 6. The 5-minute Q&A — landmines & answers

Budget ~60 s per answer. Priority order: (1) no-drone/simulation, (2) LLM wrapper, (3) fire/thermal gap, (4) real-vs-simulated. One-liners below; expand with the live demo as proof.

| Question | Answer |
| --- | --- |
| **"There's no drone. Isn't this just a simulation?"** | "Perception and reasoning are real and running live on real footage. Telemetry and actuation are simulated by design — the drone is a hardware adapter, and the interface boundary is defined. You're seeing the part that's actually hard." |
| **"Isn't this an LLM wrapper?"** | "An LLM wrapper outputs text. Here the VLM is one of four fused signals feeding a **deterministic** threat formula and state machines. An LLM has never been allowed to touch an actuator in this codebase." |
| **"It can't detect fire or thermal footage."** | "Correct, and we show it in the demo. The COCO model wasn't trained for it. The platform routes unsupported input explicitly instead of hallucinating, and domain detector training is the defined next milestone." |
| **"How does it work with no internet in a forest?"** | "Dual-tier: tracking runs onboard at 30+ FPS; a quantized small VLM (Moondream2 / Florence-2 class) runs locally on the Jetson; if the VLM dies, we fall back to spatial-persistence threat scoring — flight and safety never depend on the cloud." |
| **"What's the accuracy?"** | "These clips have no ground truth, so we quote capability, not accuracy. Precision/recall, ID-switch and fragmentation benchmarking against labeled forest data is a defined next step." |
| **"How do you stop hallucinations from crashing a drone?"** | "VLM output is sanitized into bounded numeric metrics. Geofence breach and low-battery return-to-home are enforced by deterministic safety code outside the model." |
| **"Why pay for this vs. a basic YOLO drone?"** | "A basic YOLO drone alarms on everything. We solve alert fatigue, give an evidence trail for every decision, and cut telemetry bandwidth >98% — that's what makes multi-drone ops viable." |
| **"What's real vs. simulated in what we just saw?"** | "Video detection, tracking, VLM understanding, threat scoring and the state machines are real. Battery, GPS drift, actuator ACKs and ranger dispatch are simulated. Nothing here would fly a physical drone today." |
| **"Is that poaching footage real?"** | "No — it's **synthetic test footage**, generated and labeled as such (see the `.meta.json`). We can't legally film poaching, so we generate it to exercise the escalation path — standard practice in defense/aerospace. Every clip only ships if it passes the real detection pipeline, and the console labels it SYNTHETIC TEST FOOTAGE." |

---

## 7. Audience variants

- **Hackathon judges (MSME):** lead with the working E2E pipeline + societal impact (poaching, wildfires, human-wildlife conflict). Emphasize that it *runs*, tests are green, and the architecture plan is senior-grade. Show the honest-limitations beat.
- **Defense evaluators:** lead with determinism and explainability — evidence-linked events, reason codes, config-driven thresholds, server-only API keys, geofence/battery safety overrides. Replay/inspectability is the strongest card.
- **Investors:** lead with market and moat — false-alarm fatigue, >98% bandwidth, multi-drone scalability, low-cost Jetson stack, hardware-agnostic brain (TCO argument).

---

## 8. Asset inventory

| Asset | Use |
| --- | --- |
| `docs/vanrakshak_msme_presentation.html` | **Primary** — interactive presentation site for the live pitch |
| `docs/index.html` | Narrative one-pager ("knows when *not* to escalate") — backdrop / printed leave-behind / QR code |
| `docs/VanRakshak_Refined_PitchDeck_v5.pptx` | Formal deck (team, vision, hardware, pipeline, multi-drone, innovation) |
| `docs/VanRakshak_Pitch_Deck.pptx` | MSME deck (problem, market gap, business model, ₹15 L funding ask, metrics, roadmap) |
| `docs/HACKATHON.pdf` · `docs/msme-pitchdeck.pdf` · `docs/VanRakshak.pdf` | Submission documents |
| `docs/vanrakshak-ai-pipeline.png` · `docs/mission-loop.png` · `docs/multidrone-collab.png` · `docs/vanrakshak-drone.png` | Architecture diagrams |
| `demo_videos/` | 4 benchmark clips + mangrove benchmark clip (used by `scripts/run_evals.sh`) |

---

## 9. Key deck facts to reuse (from MSME deck)

- **Vision:** "Building India's Indigenous Wildlife Intelligence Platform."
- **Product targets:** >95% detection accuracy · <3 s alert latency · >15 km² coverage per sortie · >45 min flight time · <5% false alarm rate · >60% patrol cost reduction
- **Funding ask:** ₹15,00,000 (₹15 Lakhs) — Drone hardware & prototype 35% · AI model development 25% · Edge computing hardware 15% · Dashboard development 10% · Field testing & validation 10% · Documentation & certification 5%
- **Business model:** Primary — drone hardware sales, Drone-as-a-Service; Recurring — maintenance contracts, AI analytics subscription, training programs, government contracts
- **Customers:** State Forest Departments, Wildlife Protection Authorities, National Parks → NGOs, eco-tourism, mining, railways, disaster management
- **Roadmap:** Prototype → Pilot → Forest Trials → Commercial Product → Multi-State Deployment → National Expansion
- **IP:** Patent application 202341070952 A, published 03/11/2023
- **Prototype compute:** NVIDIA Jetson Orin Nano · Sensors: RGB · Thermal · LiDAR · GPS · IMU
