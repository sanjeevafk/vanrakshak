import { RULE_ENGINE_CONFIG } from "../config/ruleEngineConfig";
export class AcousticSignalService {
  next(raw?: number) { const c = RULE_ENGINE_CONFIG.acoustic; const value = raw ?? c.fallbackScore; return { acoustic_score: Math.min(c.maxScore, Math.max(c.minScore, value)), source_mode: c.sourceMode }; }
}

