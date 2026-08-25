import { useEffect, useMemo, useState } from "react";
import { VisionService, type VideoDetection } from "../services/VisionService";
import { SceneUnderstandingService } from "../services/SceneUnderstandingService";
import { MissionService, type MissionEvent, type MissionSummary } from "../services/MissionService";

const backend = import.meta.env.VITE_BACKEND_URL ?? "http://127.0.0.1:8000";
const vision = new VisionService(backend);
const scene = new SceneUnderstandingService(backend);
const missions = new MissionService(backend);

/** One-click demo presets: clips served by the backend from demo_videos/. */
const PRESET_CLIPS = [
  { label: "ANALYZE GEMINI CLIP (DEMO)", file: "Photorealistic_autonomous_dron.mp4", note: "SYNTHETIC TEST FOOTAGE" },
  { label: "ANALYZE POACHING CLIP (DEMO)", file: "05_poaching_suspect_synthetic.mp4", note: "SYNTHETIC TEST FOOTAGE" },
];

type Command = { command: string; status: string };

/** Derive live hardware effects from the acknowledged command log. */
function activeEffects(commands: Command[]) {
  const relevant = commands.filter((c) =>
    ["SIREN_ACTIVATE", "SIREN_DEACTIVATE", "SPOTLIGHT_ON", "SPOTLIGHT_OFF", "DISPATCH_RANGER", "WILDLIFE_ALERT"].includes(c.command)
  );
  const last = (name: string) => {
    for (let i = relevant.length - 1; i >= 0; i--) if (relevant[i].command === name) return relevant[i];
    return undefined;
  };
  const acked = (c?: Command) => !!c && c.status === "ACKNOWLEDGED";
  const sirenOn = last("SIREN_ACTIVATE");
  const sirenOff = last("SIREN_DEACTIVATE");
  const spotOn = last("SPOTLIGHT_ON");
  const spotOff = last("SPOTLIGHT_OFF");
  const dispatch = last("DISPATCH_RANGER");
  return {
    siren:
      acked(sirenOn) &&
      (!sirenOff || (sirenOn !== undefined && sirenOff !== undefined && relevant.indexOf(sirenOn) > relevant.indexOf(sirenOff))),
    spotlight:
      acked(spotOn) &&
      (!spotOff || (spotOn !== undefined && spotOff !== undefined && relevant.indexOf(spotOn) > relevant.indexOf(spotOff))),
    dispatch: dispatch ? dispatch.status : null,
  };
}

function statusClass(status: string) {
  if (status.includes("UNAVAILABLE")) return "cmd-unavail";
  if (status === "ACKNOWLEDGED") return "cmd-ack";
  if (status === "SENT") return "cmd-sent";
  return "";
}

/** Collapse the raw actuator log into one row per unique command with an emission count. */
function summarizeCommands(commands: Command[]) {
  const rows = new Map<string, { command: string; status: string; count: number }>();
  for (const c of commands) {
    const command = String(c.command);
    const status = String(c.status);
    const row = rows.get(command);
    if (row) {
      row.count += 1;
      row.status = status; // latest status wins (SENT → ACKNOWLEDGED lifecycle)
    } else {
      rows.set(command, { command, status, count: 1 });
    }
  }
  return Array.from(rows.values());
}

export default function MissionConsole({ onBack }: { onBack: () => void }) {
  const [file, setFile] = useState<File>();
  const [preview, setPreview] = useState<string>();
  const [result, setResult] = useState<VideoDetection>();
  const [sceneResult, setSceneResult] = useState<any>();
  const [busy, setBusy] = useState(false);
  const [busyScenario, setBusyScenario] = useState(false);
  const [error, setError] = useState<string>();
  const [mission, setMission] = useState<MissionSummary>();
  const [events, setEvents] = useState<MissionEvent[]>([]);
  const [eventCursor, setEventCursor] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(1);
  const [selectedEvent, setSelectedEvent] = useState<MissionEvent>();
  const [demoCommands, setDemoCommands] = useState<Command[]>([]);

  const detections = useMemo(() => result?.frames.flatMap((frame) => frame.detections) ?? [], [result]);
  const effects = useMemo(() => activeEffects((mission?.commands ?? []) as Command[]), [mission?.commands]);
  const commands = useMemo(() => [...((mission?.commands ?? []) as Command[]), ...demoCommands], [mission?.commands, demoCommands]);
  const commandSummary = useMemo(() => summarizeCommands(commands), [commands]);

  useEffect(() => {
    if (!playing || eventCursor >= events.length) return;
    const timer = window.setTimeout(() => setEventCursor((cursor) => cursor + 1), 1000 / speed);
    return () => window.clearTimeout(timer);
  }, [playing, eventCursor, events.length, speed]);

  function loadMission(summary: MissionSummary, nextEvents: MissionEvent[]) {
    setMission(summary);
    setEvents(nextEvents);
    setEventCursor(0);
    setPlaying(false);
    setSelectedEvent(undefined);
  }

  async function replayAction(action: "start" | "pause" | "reset" | "step") {
    if (!mission) return;
    try {
      const state = await missions.replay(mission.mission_id, action, speed);
      setEventCursor(state.cursor);
      setPlaying(state.playing);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Replay control failed");
    }
  }

  async function analyze(fileOverride?: File) {
    const target = fileOverride ?? file;
    if (!target) return;
    setBusy(true);
    setError(undefined);
    setDemoCommands([]);
    try {
      const next = await vision.detectVideo(target);
      setResult(next);
      if (next.representative_frame) {
        try {
          setSceneResult(await scene.understand(next.representative_frame));
        } catch {
          // VLM is best-effort: detection + mission still land even if it drops.
        }
      }
      const replay = await missions.runVideo(target);
      loadMission(replay.summary, replay.events);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Analysis failed");
    } finally {
      setBusy(false);
    }
  }

  /** One-click preset: fetch a demo clip from the backend and run the full analysis. */
  async function analyzePreset(preset: (typeof PRESET_CLIPS)[number]) {
    setBusy(true);
    setError(undefined);
    setDemoCommands([]);
    try {
      const response = await fetch(`${backend}/demo_videos/${preset.file}`);
      if (!response.ok) throw new Error(`Clip fetch failed: ${response.status}`);
      const bytes = await response.arrayBuffer();
      const clipFile = new File([bytes], preset.file, { type: "video/mp4" });
      setFile(clipFile);
      setPreview(URL.createObjectURL(clipFile));
      setResult(undefined);
      setSceneResult(undefined);
      await analyze(clipFile);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Preset analysis failed");
      setBusy(false);
    }
  }

  /** Deterministic synthetic scenario — persistent person + optional VLM activity label → siren + dispatch. */
  async function runSyntheticScenario(activity?: string) {
    setBusyScenario(true);
    setError(undefined);
    // Synthetic scenario replaces the live-footage analysis: clear stale video state
    // so DETECTIONS / SCENE UNDERSTANDING reflect the new mission, not the old clip.
    setResult(undefined);
    setSceneResult(undefined);
    setDemoCommands([]);
    try {
      const replay = await missions.run({ ticks: 24, activity });
      loadMission(replay.summary, replay.events);
      // The synthetic path has no real VLM call; surface the scenario's semantic label
      // in the SCENE UNDERSTANDING panel, clearly marked as a synthetic demo.
      if (activity) {
        setSceneResult({
          scene_summary: `Persistent human track in a protected forest zone — ${activity.replace(/_/g, " ")} (synthetic demo scenario).`,
          activity_type: activity,
          behavior_rating: "HIGH",
          vlm_confidence: 0.9,
          reason: "SYNTHETIC DEMO — not a real VLM call",
        });
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Scenario failed");
    } finally {
      setBusyScenario(false);
    }
  }

  function fireSuppression() {
    setDemoCommands((list) => [
      ...list,
      { command: "FIRE_SUPPRESSANT_DEPLOY", status: "UNAVAILABLE — HARDWARE NOT INSTALLED (Phase 2)" },
    ]);
  }

  const wildlifeAlert = events.some(
    (event) => event.payload.policy_id === "wildlife_proximity" || event.payload.policy_id === "railway_conflict"
  );
  const poachingSuspect = events.some((event) => event.type === "SCENE_ANALYZED" && event.payload.activity_type === "POACHING_SUSPECT");
  const thermalUnsupported =
    sceneResult?.activity_type === "FIRE_HAZARD" || events.some((event) => event.payload.decision === "UNSUPPORTED_INPUT");

  return (
    <div className="console-wrap">
      <div className="console-topbar">
        <div className="console-topbar-left">
          <button className="back-home" onClick={onBack}>← VANRAKSHAK</button>
          <span className="console-topbar-title">MISSION CONSOLE</span>
        </div>
        <span className="console-topbar-status">SYSTEM ONLINE</span>
      </div>
      <main className="app">
      <header>
        <div className="header-left">
          <div>
            <p className="eyebrow">VANRAKSHAK // C2 CONTROL</p>
            <h1>Forest mission console</h1>
          </div>
        </div>
        <span className="status">● SYSTEM ONLINE</span>
      </header>

      {effects.siren && (
        <div className="siren-banner" role="alert">🚨 SIREN ACTIVE — ALERT STATE · commanding ranger dispatch</div>
      )}

      <section className="grid">
        <div className="panel">
          <div className="panel-title">
            <span>LIVE FOOTAGE</span>
            <span>{result?.source ?? "STANDBY"}</span>
          </div>
          <div className="video-wrap">
            {preview ? <video className="video" src={preview} controls /> : <div className="drop">Upload drone footage to begin analysis</div>}
            {effects.spotlight && <div className="spotlight" aria-hidden="true" />}
          </div>
          <input
            aria-label="Drone footage"
            type="file"
            accept="video/*"
            onChange={(event) => {
              const next = event.target.files?.[0];
              if (next) {
                setFile(next);
                setPreview(URL.createObjectURL(next));
                setResult(undefined);
                setSceneResult(undefined);
              }
            }}
          />
          <div className="buttons">
            <button disabled={!file || busy} onClick={() => analyze()}>{busy ? "ANALYZING…" : "ANALYZE FOOTAGE"}</button>
            <button className="btn-ghost" disabled={busyScenario} onClick={() => runSyntheticScenario()}>
              {busyScenario ? "RUNNING…" : "CONFIRMED HUMAN (DEMO)"}
            </button>
            <button className="btn-ghost" disabled={busyScenario} onClick={() => runSyntheticScenario("POACHING_SUSPECT")}>
              {busyScenario ? "RUNNING…" : "POACHING SUSPECT (DEMO)"}
            </button>
          </div>
          <div className="buttons" style={{ marginTop: 8 }}>
            {PRESET_CLIPS.map((preset) => (
              <button key={preset.file} className="btn-preset" disabled={busy} onClick={() => analyzePreset(preset)}>
                {busy ? "ANALYZING…" : preset.label}
              </button>
            ))}
          </div>
          <p className="muted" style={{ fontSize: 11 }}>Presets run live on {PRESET_CLIPS[0]?.note} — never presented as real drone footage.</p>
          {error && <p className="error">{error}</p>}
        </div>

        <aside className="panel">
          <div className="panel-title"><span>MISSION STATUS</span><span className="badge">REPLAY DEMO</span></div>
          <div className="metric"><span>STATE</span><strong>{mission?.mission_state ?? "PATROL"}</strong></div>
          <div className="metric"><span>DETECTIONS</span><strong>{detections.length}</strong></div>
          <div className="metric"><span>INCIDENTS</span><strong>{Object.keys(mission?.incidents ?? {}).length}</strong></div>
        </aside>
      </section>

      <section className="panel">
        <div className="panel-title">TELEMETRY</div>
        <div className="metric"><span>BATTERY</span><strong>{mission?.telemetry.battery_pct ?? "—"}%</strong></div>
        <div className="metric"><span>WIND</span><strong>{mission?.telemetry.wind_mps ?? "—"} m/s</strong></div>
        <div className="metric"><span>GPS</span><strong>{mission?.telemetry.gps ? `${Number(mission.telemetry.gps.lat).toFixed(4)}, ${Number(mission.telemetry.gps.lng).toFixed(4)}` : "—"}</strong></div>
      </section>

      <section className="panel">
        <div className="panel-title"><span>MISSION EVENT STREAM</span><span className="badge">{eventCursor}/{events.length}</span></div>
        <div className="replay-controls">
          <button disabled={!events.length} onClick={() => replayAction(playing ? "pause" : "start")}>{playing ? "PAUSE" : "START"}</button>
          <button disabled={!events.length} onClick={() => replayAction("reset")}>RESET</button>
          <button disabled={eventCursor >= events.length} onClick={() => replayAction("step")}>STEP</button>
          <label>SPEED{" "}
            <select value={speed} onChange={(event) => setSpeed(Number(event.target.value))}>
              <option value={0.5}>0.5×</option>
              <option value={1}>1×</option>
              <option value={2}>2×</option>
            </select>
          </label>
        </div>
        {events.length ? (
          <div className="stream">
            {events.slice(0, eventCursor).map((event) => (
              <button className="event" key={event.sequence} onClick={() => setSelectedEvent(event)}>
                <span>{event.timestamp_seconds.toFixed(2)}s</span>
                <span>{event.type}{event.track_id ? ` // TRACK ${event.track_id}` : ""}</span>
              </button>
            ))}
          </div>
        ) : (
          <p className="muted">No mission events yet.</p>
        )}
        {selectedEvent && (
          <div className="evidence">
            <div className="panel-title"><span>EVIDENCE DRAWER</span><button onClick={() => setSelectedEvent(undefined)}>CLOSE</button></div>
            <p>{selectedEvent.type} // sequence {selectedEvent.sequence}</p>
            <p className="muted">Evidence: {selectedEvent.evidence_refs.join(", ") || "none"}</p>
            <pre>{JSON.stringify(selectedEvent.payload, null, 2)}</pre>
          </div>
        )}
      </section>

      {wildlifeAlert && (
        <section className="panel alert-panel">WILDLIFE / RAILWAY ALERT — human-intruder siren is not recommended.</section>
      )}
      {poachingSuspect && (
        <section className="panel warning-panel">POACHING SUSPECT — persistent human in a protected zone · VLM label POACHING_SUSPECT · siren + ranger dispatch (synthetic demo).</section>
      )}
      {thermalUnsupported && (
        <section className="panel warning-panel">THERMAL / FIRE INPUT UNSUPPORTED — no suppression action is available.</section>
      )}

      <section className="grid">
        <div className="panel">
          <div className="panel-title">SCENE UNDERSTANDING</div>
          <p>{sceneResult?.scene_summary ?? "Awaiting semantic analysis…"}</p>
          {sceneResult?.reason && <span className="badge">{sceneResult.reason}</span>}
        </div>

        <div className="panel">
          <div className="panel-title"><span>AUTONOMOUS RESPONSE</span><span className="badge">SIMULATED ACTUATORS</span></div>
          <div className="effects">
            <span className={`chip ${effects.siren ? "chip-on pulse" : "chip-off"}`}>SIREN {effects.siren ? "ON" : "OFF"}</span>
            <span className={`chip ${effects.spotlight ? "chip-on" : "chip-off"}`}>SPOTLIGHT {effects.spotlight ? "ON" : "OFF"}</span>
            <span className={`chip ${effects.dispatch ? "chip-ack" : "chip-off"}`}>DISPATCH {effects.dispatch ?? "—"}</span>
          </div>
          {commandSummary.length > 0 && (
            <p className="muted cmd-summary-hint">{commands.length} logged commands → {commandSummary.length} distinct actions</p>
          )}
          {commandSummary.length ? (
            commandSummary.map((row) => (
              <p className={`command ${statusClass(row.status)}`} key={row.command}>
                <span className="cmd-name">{row.command}</span>
                {row.count > 1 && <span className="cmd-count">× {row.count}</span>}
                <span className="cmd-status">{row.status}</span>
              </p>
            ))
          ) : (
            <p className="muted">No commands emitted yet.</p>
          )}
          <div className="buttons" style={{ marginTop: 14 }}>
            <button className="btn-warn" onClick={fireSuppression}>FIRE SUPPRESSION (PHASE 2)</button>
          </div>
        </div>
      </section>
    </main>
    </div>
  );
}
