export type MissionEvent = { sequence: number; timestamp_seconds: number; type: string; track_id?: number; evidence_refs: string[]; payload: Record<string, unknown> };
export type MissionSummary = { mission_id: string; mission_state: string; incidents: Record<string, string>; latest_tracks: Record<string, Record<string, unknown>>; latest_threats: Record<string, Record<string, unknown>>; commands: Array<Record<string, unknown>>; event_count: number };
export class MissionService {
  constructor(private readonly baseUrl = "http://127.0.0.1:8000") {}
  async run(ticks = 3): Promise<{ summary: MissionSummary; events: MissionEvent[] }> {
    const created = await fetch(`${this.baseUrl}/missions`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({}) });
    if (!created.ok) throw new Error(`Mission creation failed: ${created.status}`);
    const { mission_id } = await created.json();
    const run = await fetch(`${this.baseUrl}/missions/${mission_id}/run`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ ticks }) });
    if (!run.ok) throw new Error(`Mission run failed: ${run.status}`);
    const body = await run.json();
    const eventsResponse = await fetch(`${this.baseUrl}${body.events_url}`);
    if (!eventsResponse.ok) throw new Error(`Mission events failed: ${eventsResponse.status}`);
    return { summary: body.summary, events: (await eventsResponse.json()).events };
  }
}
