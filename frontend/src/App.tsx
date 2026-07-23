import { useMemo, useState } from "react";
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
  const detections = useMemo(() => result?.frames.flatMap((frame) => frame.detections) ?? [], [result]);
  async function analyze() { if (!file) return; setBusy(true); setError(undefined); try { const next = await vision.detectVideo(file); setResult(next); if (next.representative_frame) setSceneResult(await scene.understand(next.representative_frame)); const replay = await missions.run(); setMission(replay.summary); setEvents(replay.events); } catch (e) { setError(e instanceof Error ? e.message : "Analysis failed"); } finally { setBusy(false); } }
  return <main className="app"><header><div><p className="eyebrow">VANRAKSHAK // C2 CONTROL</p><h1>Forest mission console</h1></div><span className="status">● SYSTEM ONLINE</span></header>
    <section className="grid"><div className="panel"><div className="panel-title"><span>LIVE FOOTAGE</span><span>{result?.source ?? "STANDBY"}</span></div>{preview ? <video className="video" src={preview} controls /> : <div className="drop">Upload drone footage to begin analysis</div>}<input aria-label="Drone footage" type="file" accept="video/*" onChange={(event) => { const next = event.target.files?.[0]; if (next) { setFile(next); setPreview(URL.createObjectURL(next)); setResult(undefined); setSceneResult(undefined); } }} /><button disabled={!file || busy} onClick={analyze}>{busy ? "ANALYZING…" : "ANALYZE FOOTAGE"}</button>{error && <p className="error">{error}</p>}</div>
      <aside className="panel"><div className="panel-title">MISSION STATUS</div><div className="metric"><span>STATE</span><strong>{mission?.mission_state ?? "PATROL"}</strong></div><div className="metric"><span>EVENTS</span><strong>{mission?.event_count ?? 0}</strong></div><div className="metric"><span>DETECTIONS</span><strong>{detections.length}</strong></div><div className="metric"><span>INCIDENTS</span><strong>{Object.keys(mission?.incidents ?? {}).length}</strong></div></aside></section>
    <section className="panel"><div className="panel-title">MISSION EVENT STREAM</div>{events.length ? <div className="stream">{events.map((event) => <div className="event" key={event.sequence}><span>{event.timestamp_seconds.toFixed(2)}s</span><span>{event.type}{event.track_id ? ` // TRACK ${event.track_id}` : ""}</span></div>)}</div> : <p className="muted">No mission events yet.</p>}</section>
    <section className="grid"><div className="panel"><div className="panel-title">SCENE UNDERSTANDING</div><p>{sceneResult?.scene_summary ?? "Awaiting semantic analysis…"}</p>{sceneResult?.reason && <span className="badge">{sceneResult.reason}</span>}</div><div className="panel"><div className="panel-title">COMMAND LOG</div>{mission?.commands.length ? mission.commands.map((command, index) => <p className="command" key={index}>{String(command.command)} // {String(command.status)}</p>) : <p className="muted">No commands emitted.</p>}</div></section>
  </main>;
}
