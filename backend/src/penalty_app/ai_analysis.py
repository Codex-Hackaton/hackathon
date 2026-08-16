from __future__ import annotations

from dataclasses import dataclass
import json
import re
from typing import Any

from .domain import AIAnalysisDecision


ALLOWED_ACTIVITY_IDS = frozenset(
    {
        "reading_book",
        "studying",
        "playing_video_game",
        "watching_short_form",
        "unknown",
    }
)
ANALYSIS_ID_PATTERN = re.compile(r"^analysis_[A-Za-z0-9_-]+$")
POLICY_ID_PATTERN = re.compile(r"^policy_[a-z0-9_]+$")


class AIAnalysisValidationError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class DetectedActivity:
    activity_id: str
    confidence: float
    visual_evidence: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class AIAnalysis:
    analysis_id: str
    detected_activities: tuple[DetectedActivity, ...]
    decision: AIAnalysisDecision
    decision_confidence: float
    matched_policy_ids: tuple[str, ...]
    reason: str
    requires_human_review: bool

    @classmethod
    def from_json(cls, payload: str) -> AIAnalysis:
        try:
            value = json.loads(payload)
        except json.JSONDecodeError as error:
            raise AIAnalysisValidationError("response is not valid JSON") from error
        return cls.from_dict(value)

    @classmethod
    def from_dict(cls, value: Any) -> AIAnalysis:
        if not isinstance(value, dict):
            raise AIAnalysisValidationError("analysis must be an object")

        expected_keys = {
            "analysis_id",
            "detected_activities",
            "decision",
            "decision_confidence",
            "matched_policy_ids",
            "reason",
            "requires_human_review",
        }
        _require_exact_keys(value, expected_keys, "analysis")

        analysis_id = _require_string(value["analysis_id"], "analysis_id")
        if ANALYSIS_ID_PATTERN.fullmatch(analysis_id) is None:
            raise AIAnalysisValidationError("analysis_id has an invalid format")

        raw_activities = value["detected_activities"]
        if not isinstance(raw_activities, list) or not raw_activities:
            raise AIAnalysisValidationError("detected_activities must be a non-empty list")
        activities = tuple(_parse_activity(item) for item in raw_activities)

        try:
            decision = AIAnalysisDecision(value["decision"])
        except (TypeError, ValueError) as error:
            raise AIAnalysisValidationError("decision is invalid") from error

        decision_confidence = _require_confidence(
            value["decision_confidence"], "decision_confidence"
        )

        raw_policy_ids = value["matched_policy_ids"]
        if not isinstance(raw_policy_ids, list):
            raise AIAnalysisValidationError("matched_policy_ids must be a list")
        policy_ids = tuple(
            _require_string(policy_id, "matched_policy_ids item")
            for policy_id in raw_policy_ids
        )
        if len(set(policy_ids)) != len(policy_ids):
            raise AIAnalysisValidationError("matched_policy_ids must be unique")
        if any(POLICY_ID_PATTERN.fullmatch(policy_id) is None for policy_id in policy_ids):
            raise AIAnalysisValidationError("matched_policy_ids contains an invalid id")

        reason = _require_string(value["reason"], "reason")
        requires_human_review = value["requires_human_review"]
        if not isinstance(requires_human_review, bool):
            raise AIAnalysisValidationError("requires_human_review must be a boolean")

        expects_review = decision is AIAnalysisDecision.HUMAN_REVIEW
        if requires_human_review is not expects_review:
            raise AIAnalysisValidationError(
                "requires_human_review must agree with decision"
            )

        return cls(
            analysis_id=analysis_id,
            detected_activities=activities,
            decision=decision,
            decision_confidence=decision_confidence,
            matched_policy_ids=policy_ids,
            reason=reason,
            requires_human_review=requires_human_review,
        )


def _parse_activity(value: Any) -> DetectedActivity:
    if not isinstance(value, dict):
        raise AIAnalysisValidationError("activity must be an object")
    _require_exact_keys(
        value,
        {"activity_id", "confidence", "visual_evidence"},
        "activity",
    )

    activity_id = _require_string(value["activity_id"], "activity_id")
    if activity_id not in ALLOWED_ACTIVITY_IDS:
        raise AIAnalysisValidationError(f"unknown activity_id: {activity_id}")

    raw_evidence = value["visual_evidence"]
    if not isinstance(raw_evidence, list):
        raise AIAnalysisValidationError("visual_evidence must be a list")
    evidence = tuple(
        _require_string(item, "visual_evidence item") for item in raw_evidence
    )
    if len(set(evidence)) != len(evidence):
        raise AIAnalysisValidationError("visual_evidence must be unique")

    return DetectedActivity(
        activity_id=activity_id,
        confidence=_require_confidence(value["confidence"], "confidence"),
        visual_evidence=evidence,
    )


def _require_exact_keys(value: dict[str, Any], expected: set[str], name: str) -> None:
    actual = set(value)
    if actual != expected:
        unexpected = sorted(actual - expected)
        missing = sorted(expected - actual)
        raise AIAnalysisValidationError(
            f"{name} keys do not match contract; missing={missing}, unexpected={unexpected}"
        )


def _require_string(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise AIAnalysisValidationError(f"{name} must be a non-empty string")
    return value


def _require_confidence(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise AIAnalysisValidationError(f"{name} must be a number")
    confidence = float(value)
    if not 0 <= confidence <= 1:
        raise AIAnalysisValidationError(f"{name} must be between 0 and 1")
    return confidence
