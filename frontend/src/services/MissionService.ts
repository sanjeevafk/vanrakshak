export type MissionEvent = { sequence: number; timestamp_seconds: number; type: string; track_id?: number; evidence_refs: string[]; payload: Record<string, unknown> };
export type MissionSummary = { mission_id: string; mission_state: string; incidents: Record<string, string>; latest_tracks: Record<string, Record<string, unknown>>; latest_threats: Record<string, Record<string, unknown>>; commands: Array<Record<string, unknown>>; telemetry: Record<string, any>; telemetry_history: Array<Record<string, any>>; event_count: number };
export type MissionRunOptions = { ticks?: number; wildlife?: boolean };

export class MissionService {
  constructor(private readonly baseUrl = "http://127.0.0.1:8000") {}
  async run(options: MissionRunOptions | number = {}): Promise<{ summary: MissionSummary; events: MissionEvent[] }> {
    const opts: MissionRunOptions = typeof options === "number" ? { ticks: options } : options;
    const ticks = opts.ticks ?? 3;
    const wildlife = opts.wildlife ?? false;
    const created = await fetch(`${this.baseUrl}/missions`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ wildlife }) });
    if (!created.ok) throw new Error(`Mission creation failed: ${created.status}`);
    const { mission_id } = await created.json();
    const run = await fetch(`${this.baseUrl}/missions/${mission_id}/run`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ ticks, wildlife }) });
    if (!run.ok) throw new Error(`Mission run failed: ${run.status}`);
    const body = await run.json();
    const eventsResponse = await fetch(`${this.baseUrl}${body.events_url}`);
    if (!eventsResponse.ok) throw new Error(`Mission events failed: ${eventsResponse.status}`);
    return { summary: body.summary, events: (await eventsResponse.json()).events };
  }
  async replay(missionId: string, action: "start" | "pause" | "reset" | "step", speed = 1): Promise<{ cursor: number; event_count: number; playing: boolean; speed: number }> {
    const query = action === "start" ? `?speed=${speed}` : "";
    const response = await fetch(`${this.baseUrl}/missions/${missionId}/replay/${action}${query}`, { method: "POST" });
    if (!response.ok) throw new Error(`Replay ${action} failed: ${response.status}`);
    return response.json();
  }
}
