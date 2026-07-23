export const RULE_ENGINE_CONFIG = {
  weights: { w1_vlmConfidence: 0.35, w2_detectorConfidence: 0.25, w3_zoneRisk: 0.25, w4_acousticScore: 0.15 },
  confidenceEvolution: { alpha_gain: 0.15, beta_decay: 0.05, max_confidence: 0.99, min_confidence: 0 },
  fsmThresholds: { investigateThreatScore: 45, alertThreatScore: 85, highConfidenceDetection: 0.7, verifyVlmConfidence: 0.75, returnHomeBatteryPct: 25, criticalBatteryPct: 20, investigateTimeoutSec: 30, trackLossTimeoutSec: 15, ambiguousEvidenceFallbackSec: 20 },
  acoustic: { sourceMode: "SIMULATED" as const, fallbackScore: 0.3, smoothingAlpha: 0.2, maxScore: 1, minScore: 0 },
} as const;

