import { describe, expect, it } from "vitest";
import { MissionService } from "../src/services/MissionService";

describe("mission projections", () => {
  it("loads backend summary and events", async () => {
    const fetcher = globalThis.fetch;
    globalThis.fetch = (async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/missions")) return new Response(JSON.stringify({ mission_id: "m1" }), { status: 200 });
      if (url.endsWith("/run")) return new Response(JSON.stringify({ events_url: "/missions/m1/events", summary: { mission_id: "m1", mission_state: "VERIFY", incidents: {}, latest_tracks: {}, latest_threats: {}, commands: [], telemetry: {}, event_count: 1 } }), { status: 200 });
      return new Response(JSON.stringify({ events: [] }), { status: 200 });
    }) as typeof fetch;
    const result = await new MissionService("http://test").run();
    expect(result.summary.mission_state).toBe("VERIFY");
    globalThis.fetch = fetcher;
  });
});
