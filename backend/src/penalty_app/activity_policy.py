from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Any
from uuid import uuid4

from .ai_analysis import AIAnalysis


ALLOWED_ACTIVITY_IDS = frozenset(
    {
        "reading_book",
        "studying",
        "playing_video_game",
        "watching_short_form",
        "unknown",
    }
)
PASS_ACTIVITIES = frozenset({"reading_book", "studying"})
FAIL_ACTIVITIES = frozenset({"playing_video_game", "watching_short_form"})
HUMAN_REVIEW_THRESHOLD = 0.75


class ExtractionValidationError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class ActivityExtraction:
    activity_id: str
    confidence: float
    visual_evidence: tuple[str, ...]

    @classmethod
    def from_dict(cls, value: Any) -> ActivityExtraction:
        if not isinstance(value, dict):
            raise ExtractionValidationError("VLM extraction must be an object")
        if set(value) != {"activity_id", "confidence", "visual_evidence"}:
            raise ExtractionValidationError("VLM extraction keys are invalid")

        activity_id = value["activity_id"]
        if activity_id not in ALLOWED_ACTIVITY_IDS:
            raise ExtractionValidationError("VLM returned an unknown activity_id")

        raw_confidence = value["confidence"]
        if isinstance(raw_confidence, bool) or not isinstance(
            raw_confidence, (int, float)
        ):
            raise ExtractionValidationError("confidence must be numeric")
        confidence = float(raw_confidence)
        if not isfinite(confidence) or not 0 <= confidence <= 1:
            raise ExtractionValidationError("confidence must be between 0 and 1")

        raw_evidence = value["visual_evidence"]
        if not isinstance(raw_evidence, list) or not 1 <= len(raw_evidence) <= 5:
            raise ExtractionValidationError(
                "visual_evidence must contain between 1 and 5 items"
            )
        if any(
            not isinstance(item, str) or not item.strip() for item in raw_evidence
        ):
            raise ExtractionValidationError("visual_evidence contains an invalid item")

        return cls(
            activity_id=activity_id,
            confidence=confidence,
            visual_evidence=tuple(dict.fromkeys(raw_evidence)),
        )


def apply_group_policy(extraction: ActivityExtraction) -> AIAnalysis:
    if (
        extraction.activity_id == "unknown"
        or extraction.confidence < HUMAN_REVIEW_THRESHOLD
    ):
        decision = "HUMAN_REVIEW"
        policy_ids: list[str] = []
        reason = "The activity could not be identified with sufficient confidence."
    elif extraction.activity_id in PASS_ACTIVITIES:
        decision = "PASS"
        policy_ids = ["policy_self_development"]
        reason = "The detected activity is permitted by the self-development policy."
    elif extraction.activity_id in FAIL_ACTIVITIES:
        decision = "FAIL"
        policy_ids = ["policy_focus_goal"]
        reason = "The detected activity conflicts with the focus policy."
    else:
        decision = "HUMAN_REVIEW"
        policy_ids = []
        reason = "No deterministic policy mapping exists for the detected activity."

    return AIAnalysis.from_dict(
        {
            "analysis_id": f"analysis_{uuid4().hex}",
            "detected_activities": [
                {
                    "activity_id": extraction.activity_id,
                    "confidence": extraction.confidence,
                    "visual_evidence": list(extraction.visual_evidence),
                }
            ],
            "decision": decision,
            "decision_confidence": extraction.confidence,
            "matched_policy_ids": policy_ids,
            "reason": reason,
            "requires_human_review": decision == "HUMAN_REVIEW",
        }
    )
