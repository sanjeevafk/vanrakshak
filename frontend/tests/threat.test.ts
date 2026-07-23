import { describe, expect, it } from "vitest";
import { nextMissionState, threatScore } from "../src/services/ThreatAssessmentService";

describe("threat assessment", () => {
  it("stays bounded for out-of-range inputs", () => expect(threatScore(4, -2, 3, 9)).toBe(75));
  it("includes acoustic signal", () => expect(threatScore(0, 0, 0, 1)).toBe(15));
  it("uses configured FSM thresholds", () => {
    expect(nextMissionState("PATROL", 46, 100)).toBe("INVESTIGATE");
    expect(nextMissionState("PATROL", 20, 24)).toBe("RETURN_HOME");
    expect(nextMissionState("VERIFY", 86, 100)).toBe("ALERT");
  });
});
