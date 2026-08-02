# VanRakshak — Day-of Presentation Checklist (MSME Idea Hackathon 6.0)

**Deck:** `docs/vanrakshak_msme_presentation.html` (11 slides) · **Console:** `http://127.0.0.1:5173`
**Timing:** 10:00 pitch + 5:00 Q&A · **Keys:** `←`/`→` slides · `S` speaker notes · `F11` fullscreen
**Pushed commit:** `54dafdf` on `main` (github.com/sanjeevafk/vanrakshak)

---

## ☑️ Night before (30 min)

- [ ] **Dry-run the full 10:00 + 5:00 once, out loud**, with a timer. This is the single highest-value item.
- [ ] Verify `make start` boots cleanly (backend :8000 + frontend :5173) from the project root.
- [ ] Confirm all clips present in `demo_videos/` (4 real + `05_poaching_suspect_synthetic` + 3 Gemini).
- [ ] Confirm internet is available for the VLM (`.env` → `NVIDIA_API_KEY`); if the venue has no internet, see Fallbacks below — the demo still works without it.
- [ ] Charge laptop fully; bring charger + backup laptop if available.
- [ ] Confirm the deck works **over HTTP** (see T-30) — never open it as a raw `file://` during the pitch.

## ☑️ T-30 min (before judges arrive)

- [ ] **`make start`** in its own terminal tab. Leave it running. (Ctrl+C shuts both servers down cleanly.)
- [ ] Open the **deck over HTTP**: `http://127.0.0.1:8000/presentation/vanrakshak_msme_presentation.html`
  — this guarantees video/slides load with zero path issues.
- [ ] **Pre-open the console tab** (the one genuinely essential step):
  open `http://127.0.0.1:5173` in a second tab and **leave it open**.
- [ ] *(Optional, ~1 min)* In the console tab, run **`ANALYZE FOOTAGE`** on the elephant clip once —
  warms the VLM connection so live analysis during Q&A is fast. Skip if time is tight.
- [ ] **Pre-load the elephant clip** in the console file picker (chosen, NOT yet analyzed) →
  a Q&A "show us live" becomes one click (~12 s narration).
- [ ] Fullscreen the deck (`F11`), test `←`/`→` and `S` (notes drawer). Walk to the back of the room —
  confirm text is legible at projector distance.
- [ ] Silence notifications; disable sleep/auto-lock on the laptop.

## 🎤 During the pitch (10:00)

| Time | Slide | Beat |
|---|---|---|
| 0:00–0:45 | Hero | Framing line + honesty pledge + patent (202341070952A) |
| 0:45–2:15 | Problem | 6 pain points → punch line: "current drones don't decide anything" |
| 2:15–3:00 | Vision | The autonomous forest response agent |
| 3:00–3:40 | Metrics | **0 sirens for wildlife** — say it twice. 735 · 5,607 · 98% (derived) |
| 3:40–5:10 | Architecture | 5-stage pipeline + dual-tier edge/cloud |
| 5:10–6:30 | Innovations | Not an LLM wrapper; formula card; conservative-by-design |
| 6:30–7:45 | FSM + calculator | Run confirmed-human path; invite judges to pull sliders |
| 7:45–8:30 | Roadmap | Hardware swap-in story |
| 8:30–9:30 | Commercial | ₹15 L ask; competitive table |
| 9:30–10:00 | Closing | Ask → **Alt-Tab to the pre-opened console tab** → `CONFIRMED HUMAN (DEMO)` or `POACHING SUSPECT (DEMO)` → siren banner + ACK chips |

**Autonomous response to show (console):**
- `CONFIRMED HUMAN (DEMO)` — siren banner, spotlight, dispatch ACK
- `POACHING SUSPECT (DEMO)` — same path + `POACHING_SUSPECT` VLM label banner
- `FIRE SUPPRESSION (PHASE 2)` — honest UNAVAILABLE path
- `ANALYZE GEMINI CLIP (DEMO)` / `ANALYZE POACHING CLIP (DEMO)` — one-click synthetic footage (labeled SYNTHETIC TEST FOOTAGE)

## ❓ Q&A (5:00) — highest-probability landmines

| Question | One-liner |
|---|---|
| "No drone — isn't this a simulation?" | Perception + reasoning real on real footage; telemetry/actuation simulated by design. |
| "LLM wrapper?" | VLM is one of four fused signals in a **deterministic** formula; LLM never touches a motor. |
| "Can't detect fire?" | Correct — COCO isn't fire-trained; unsupported input is routed explicitly, never hallucinated. |
| "What's real vs simulated?" | Detection, tracking, VLM, scoring, FSM = real. Battery, ACKs, dispatch = simulated. |
| "Is the poaching footage real?" | No — **synthetic test footage**, labeled as such (`.meta.json`); generated to exercise the escalation path. |

## 🛟 Fallbacks (if something breaks)

- **VLM down / no internet:** scene panel shows "Awaiting semantic analysis…" — detection + mission still run. Or use `CONFIRMED HUMAN (DEMO)` (no VLM needed).
- **Video analysis hangs:** fall back to `CONFIRMED HUMAN (DEMO)` or the synthetic mission API — instant, deterministic.
- **Projector resolution weird:** deck is responsive; `F11` and scroll. Worst case, present from the narrative one-pager `docs/index.html`.
- **Both servers die mid-pitch:** `Ctrl+C` → re-run `make start` (~5 s). Keep the two URLs in a sticky note.

## ✅ After the pitch

- [ ] Copy the pitch deck + brief to a USB/cloud (leave-behind for judges if offered).
- [ ] Commit + push any last-minute fixes (`git add -A && git commit && git push`).
