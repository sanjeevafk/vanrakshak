import { useEffect, useMemo, useState } from "react";
import { VisionService, type VideoDetection } from "./services/VisionService";
import { SceneUnderstandingService } from "./services/SceneUnderstandingService";
import { MissionService, type MissionEvent, type MissionSummary } from "./services/MissionService";

const backend = import.meta.env.VITE_BACKEND_URL ?? "http://127.0.0.1:8000";
const vision = new VisionService(backend);
const scene = new SceneUnderstandingService(backend);
const missions = new MissionService(backend);

export default function App() {
  const [file, setFile] = useState<File>(); const [preview, setPreview] = useState<string>();
  const [result, setResult] = useState<VideoDetection>(); const [sceneResult, setSceneResult] = useState<any>();
  const [busy, setBusy] = useState(false); const [error, setError] = useState<string>();
  const [mission, setMission] = useState<MissionSummary>(); const [events, setEvents] = useState<MissionEvent[]>([]);
  const [eventCursor, setEventCursor] = useState(0); const [playing, setPlaying] = useState(false); const [speed, setSpeed] = useState(1);
  const [selectedEvent, setSelectedEvent] = useState<MissionEvent>();
  const detections = useMemo(() => result?.frames.flatMap((frame) => frame.detections) ?? [], [result]);
  useEffect(() => { if (!playing || eventCursor >= events.length) return; const timer = window.setTimeout(() => setEventCursor((cursor) => cursor + 1), 1000 / speed); return () => window.clearTimeout(timer); }, [playing, eventCursor, events.length, speed]);
  async function analyze() {
    if (!file) return;
    setBusy(true);
    setError(undefined);
    try {
      const next = await vision.detectVideo(file);
      setResult(next);
      if (next.representative_frame) setSceneResult(await scene.understand(next.representative_frame));
      const hasWildlife = next.frames.some((frame) =>
        frame.detections.some((det) => ["elephant", "animal", "wildlife"].includes(det.class.toLowerCase()))
      );
      const replay = await missions.run({
        ticks: Math.max(3, next.frames.length),
        wildlife: hasWildlife,
      });
      setMission(replay.summary);
      setEvents(replay.events);
      setEventCursor(0);
      setPlaying(false);
      setSelectedEvent(undefined);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Analysis failed");
    } finally {
      setBusy(false);
    }
  }
  return <main className="app"><header><div><p className="eyebrow">VANRAKSHAK // C2 CONTROL</p><h1>Forest mission console</h1></div><span className="status">● SYSTEM ONLINE</span></header>
    <section className="grid"><div className="panel"><div className="panel-title"><span>LIVE FOOTAGE</span><span>{result?.source ?? "STANDBY"}</span></div>{preview ? <video className="video" src={preview} controls /> : <div className="drop">Upload drone footage to begin analysis</div>}<input aria-label="Drone footage" type="file" accept="video/*" onChange={(event) => { const next = event.target.files?.[0]; if (next) { setFile(next); setPreview(URL.createObjectURL(next)); setResult(undefined); setSceneResult(undefined); } }} /><button disabled={!file || busy} onClick={analyze}>{busy ? "ANALYZING…" : "ANALYZE FOOTAGE"}</button>{error && <p className="error">{error}</p>}</div>
      <aside className="panel"><div className="panel-title"><span>MISSION STATUS</span><span className="badge">REPLAY DEMO</span></div><div className="metric"><span>STATE</span><strong>{mission?.mission_state ?? "PATROL"}</strong></div><div className="metric"><span>EVENTS</span><strong>{mission?.event_count ?? 0}</strong></div><div className="metric"><span>DETECTIONS</span><strong>{detections.length}</strong></div><div className="metric"><span>INCIDENTS</span><strong>{Object.keys(mission?.incidents ?? {}).length}</strong></div></aside></section>
    <section className="panel"><div className="panel-title"><span>MISSION EVENT STREAM</span><span className="badge">{eventCursor}/{events.length}</span></div><div className="replay-controls"><button disabled={!events.length} onClick={() => setPlaying((value) => !value)}>{playing ? "PAUSE" : "START"}</button><button disabled={!events.length} onClick={() => { setPlaying(false); setEventCursor(0); }}>RESET</button><button disabled={eventCursor >= events.length} onClick={() => setEventCursor((cursor) => Math.min(events.length, cursor + 1))}>STEP</button><label>SPEED <select value={speed} onChange={(event) => setSpeed(Number(event.target.value))}><option value={0.5}>0.5×</option><option value={1}>1×</option><option value={2}>2×</option></select></label></div>{events.length ? <div className="stream">{events.slice(0, eventCursor).map((event) => <button className="event" key={event.sequence} onClick={() => setSelectedEvent(event)}><span>{event.timestamp_seconds.toFixed(2)}s</span><span>{event.type}{event.track_id ? ` // TRACK ${event.track_id}` : ""}</span></button>)}</div> : <p className="muted">No mission events yet.</p>}{selectedEvent && <div className="evidence"><div className="panel-title"><span>EVIDENCE DRAWER</span><button onClick={() => setSelectedEvent(undefined)}>CLOSE</button></div><p>{selectedEvent.type} // sequence {selectedEvent.sequence}</p><p className="muted">Evidence: {selectedEvent.evidence_refs.join(", ") || "none"}</p><pre>{JSON.stringify(selectedEvent.payload, null, 2)}</pre></div>}</section>
    {events.some((event) => event.payload.policy_id === "wildlife_proximity" || event.payload.policy_id === "railway_conflict") && <section className="panel alert-panel">WILDLIFE / RAILWAY ALERT — human-intruder siren is not recommended.</section>}
    {(sceneResult?.activity_type === "FIRE_HAZARD" || events.some((event) => event.payload.decision === "UNSUPPORTED_INPUT")) && <section className="panel warning-panel">THERMAL / FIRE INPUT UNSUPPORTED — no suppression action is available.</section>}
    <section className="grid"><div className="panel"><div className="panel-title">SCENE UNDERSTANDING</div><p>{sceneResult?.scene_summary ?? "Awaiting semantic analysis…"}</p>{sceneResult?.reason && <span className="badge">{sceneResult.reason}</span>}</div><div className="panel"><div className="panel-title"><span>COMMAND LOG</span><span className="badge">REPLAY DEMO</span></div>{mission?.commands.length ? mission.commands.map((command, index) => <p className="command" key={index}>{String(command.command)} // {String(command.status)}</p>) : <p className="muted">No commands emitted.</p>}</div></section>
  </main>;
}
