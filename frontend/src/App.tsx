import { useMemo, useState } from "react";
import { VisionService, type VideoDetection } from "./services/VisionService";
import { SceneUnderstandingService } from "./services/SceneUnderstandingService";
import { threatScore } from "./services/ThreatAssessmentService";

const backend = import.meta.env.VITE_BACKEND_URL ?? "http://127.0.0.1:8000";
const vision = new VisionService(backend);
const scene = new SceneUnderstandingService(backend);

export default function App() {
  const [file, setFile] = useState<File>(); const [preview, setPreview] = useState<string>();
  const [result, setResult] = useState<VideoDetection>(); const [sceneResult, setSceneResult] = useState<any>();
  const [busy, setBusy] = useState(false); const [error, setError] = useState<string>();
  const detections = useMemo(() => result?.frames.flatMap((frame) => frame.detections) ?? [], [result]);
  const threat = threatScore(sceneResult?.vlm_confidence ?? 0, detections.length ? 0.5 : 0, 0.6, 0.3);
  async function analyze() { if (!file) return; setBusy(true); setError(undefined); try { const next = await vision.detectVideo(file); setResult(next); setSceneResult(await scene.understand("aW1hZ2U=")); } catch (e) { setError(e instanceof Error ? e.message : "Analysis failed"); } finally { setBusy(false); } }
  return <main className="app"><header><div><p className="eyebrow">VANRAKSHAK // C2 CONTROL</p><h1>Forest mission console</h1></div><span className="status">● SYSTEM ONLINE</span></header>
    <section className="grid"><div className="panel"><div className="panel-title"><span>LIVE FOOTAGE</span><span>{result?.source ?? "STANDBY"}</span></div>{preview ? <video className="video" src={preview} controls /> : <div className="drop">Upload drone footage to begin analysis</div>}<input aria-label="Drone footage" type="file" accept="video/*" onChange={(event) => { const next = event.target.files?.[0]; if (next) { setFile(next); setPreview(URL.createObjectURL(next)); setResult(undefined); setSceneResult(undefined); } }} /><button disabled={!file || busy} onClick={analyze}>{busy ? "ANALYZING…" : "ANALYZE FOOTAGE"}</button>{error && <p className="error">{error}</p>}</div>
      <aside className="panel"><div className="panel-title">MISSION STATUS</div><div className="metric"><span>STATE</span><strong>{threat > 45 ? "INVESTIGATE" : "PATROL"}</strong></div><div className="metric"><span>THREAT SCORE</span><strong className={threat > 45 ? "danger" : "safe"}>{threat.toFixed(1)}/100</strong></div><div className="metric"><span>DETECTIONS</span><strong>{detections.length}</strong></div><div className="metric"><span>SCENE</span><strong>{sceneResult?.behavior_rating ?? "—"}</strong></div></aside></section>
    <section className="panel"><div className="panel-title">DETECTION STREAM</div>{detections.length ? <div className="stream">{result?.frames.map((frame) => <div className="event" key={frame.frame_index}><span>{frame.timestamp_seconds.toFixed(2)}s</span><span>{frame.detections.map((d) => `${d.class} #${d.track_id}`).join(", ") || "No objects"}</span></div>)}</div> : <p className="muted">No detections yet. Results will appear here after analysis.</p>}</section>
    <section className="grid"><div className="panel"><div className="panel-title">SCENE UNDERSTANDING</div><p>{sceneResult?.scene_summary ?? "Awaiting semantic analysis…"}</p>{sceneResult?.reason && <span className="badge">{sceneResult.reason}</span>}</div><div className="panel"><div className="panel-title">COMMAND LOG</div><p className={detections.length ? "command" : "muted"}>{detections.length ? "DISPATCH_RANGER // SIMULATED ACKNOWLEDGED" : "No commands emitted."}</p></div></section>
  </main>;
}
