import { RULE_ENGINE_CONFIG } from "../config/ruleEngineConfig";

export function threatScore(vlmConfidence: number, detectorConfidence: number, zoneRisk: number, acousticScore: number): number {
  const w = RULE_ENGINE_CONFIG.weights;
  const clamp = (v: number) => Math.min(1, Math.max(0, v));
  return clamp(w.w1_vlmConfidence * clamp(vlmConfidence) + w.w2_detectorConfidence * clamp(detectorConfidence) + w.w3_zoneRisk * clamp(zoneRisk) + w.w4_acousticScore * clamp(acousticScore)) * 100;
}

export function nextMissionState(state: "PATROL" | "INVESTIGATE" | "TRACK" | "VERIFY" | "ALERT" | "RETURN_HOME", threatScoreValue: number, batteryPct: number, geofenceBreached = false): string {
  const t = RULE_ENGINE_CONFIG.fsmThresholds;
  if (geofenceBreached || batteryPct < t.returnHomeBatteryPct) return "RETURN_HOME";
  if (state === "PATROL" && threatScoreValue > t.investigateThreatScore) return "INVESTIGATE";
  if (state === "VERIFY" && threatScoreValue > t.alertThreatScore) return "ALERT";
  return state;
}

