"""Independent, side-effect-free policy evaluation."""
from __future__ import annotations

from typing import Any

from .events import PolicyDecision


class Policy:
    policy_id = "base"

    def evaluate(self, data: dict[str, Any]) -> list[PolicyDecision]:
        raise NotImplementedError


class HumanIntrusionPolicy(Policy):
    policy_id = "human_intrusion"

    def evaluate(self, data: dict[str, Any]) -> list[PolicyDecision]:
        if data.get("class_name") != "person" or not data.get("persistent", False):
            return []
        confidence = float(data.get("confidence", 0))
        confirmed = bool(data.get("vlm_confirmed", False))
        if confidence < 0.7 or not confirmed:
            return [PolicyDecision(policy_id=self.policy_id, decision="RECOMMEND_REVIEW", severity="MEDIUM", track_id=data.get("track_id"), confidence=confidence, evidence_refs=data.get("evidence_refs", []))]
        return [PolicyDecision(policy_id=self.policy_id, decision="RECOMMEND_ALERT", severity="HIGH", track_id=data.get("track_id"), confidence=confidence, evidence_refs=data.get("evidence_refs", []), recommended_actions=["SIREN_ACTIVATE", "DISPATCH_RANGER"])]


class WildlifeProximityPolicy(Policy):
    policy_id = "wildlife_proximity"

    def evaluate(self, data: dict[str, Any]) -> list[PolicyDecision]:
        if data.get("class_name") not in {"elephant", "wildlife", "animal"}:
            return []
        return [PolicyDecision(policy_id=self.policy_id, decision="WILDLIFE_ALERT", severity="HIGH", track_id=data.get("track_id"), confidence=float(data.get("confidence", 0)), evidence_refs=data.get("evidence_refs", []), recommended_actions=["WILDLIFE_ALERT", "DISPATCH_RANGER"])]


class VehicleIntrusionPolicy(Policy):
    policy_id = "vehicle_intrusion"

    def evaluate(self, data: dict[str, Any]) -> list[PolicyDecision]:
        if data.get("class_name") not in {"car", "truck", "bus", "vehicle"}:
            return []
        return [PolicyDecision(policy_id=self.policy_id, decision="RECOMMEND_ALERT", severity="HIGH", track_id=data.get("track_id"), confidence=float(data.get("confidence", 0)), evidence_refs=data.get("evidence_refs", []), recommended_actions=["DISPATCH_RANGER"])]


class RailwayConflictPolicy(Policy):
    policy_id = "railway_conflict"

    def evaluate(self, data: dict[str, Any]) -> list[PolicyDecision]:
        if data.get("class_name") not in {"elephant", "wildlife", "animal"} or not data.get("railway_intersection", False):
            return []
        return [PolicyDecision(policy_id=self.policy_id, decision="RAILWAY_ALERT", severity="CRITICAL", track_id=data.get("track_id"), confidence=float(data.get("confidence", 0)), evidence_refs=data.get("evidence_refs", []), recommended_actions=["WILDLIFE_ALERT", "DISPATCH_RANGER"])]


class ThermalFirePolicy(Policy):
    policy_id = "thermal_fire"

    def evaluate(self, data: dict[str, Any]) -> list[PolicyDecision]:
        if data.get("input_type") != "thermal" and data.get("class_name") not in {"fire", "smoke", "fire_hazard"} and data.get("activity_type") not in {"FIRE_HAZARD", "FOREST_FIRE", "FIRE"}:
            return []
        confidence = float(data.get("confidence", 0.9))
        return [PolicyDecision(policy_id=self.policy_id, decision="RECOMMEND_ALERT", severity="CRITICAL", track_id=data.get("track_id"), confidence=confidence, evidence_refs=data.get("evidence_refs", []), recommended_actions=["FIRE_SUPPRESSANT_DEPLOY", "DISPATCH_RANGER"])]


class PolicyEngine:
    def __init__(self, policies: list[Policy] | None = None) -> None:
        self.policies = policies or [HumanIntrusionPolicy(), VehicleIntrusionPolicy(), WildlifeProximityPolicy(), RailwayConflictPolicy(), ThermalFirePolicy()]

    def evaluate(self, data: dict[str, Any]) -> list[PolicyDecision]:
        return [decision for policy in self.policies for decision in policy.evaluate(data)]
