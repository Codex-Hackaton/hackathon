import sys
from pathlib import Path
import unittest


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from policy import (  # noqa: E402
    ActivityExtraction,
    ExtractionValidationError,
    apply_group_policy,
)


class PolicyTests(unittest.TestCase):
    def test_reading_passes_without_model_policy_discretion(self) -> None:
        result = apply_group_policy(
            ActivityExtraction.from_dict(
                {
                    "activity_id": "reading_book",
                    "confidence": 0.93,
                    "visual_evidence": ["open book"],
                }
            )
        )
        self.assertEqual(result["decision"], "PASS")
        self.assertEqual(result["matched_policy_ids"], ["policy_self_development"])

    def test_game_fails(self) -> None:
        result = apply_group_policy(
            ActivityExtraction.from_dict(
                {
                    "activity_id": "playing_video_game",
                    "confidence": 0.91,
                    "visual_evidence": ["game controller"],
                }
            )
        )
        self.assertEqual(result["decision"], "FAIL")

    def test_low_confidence_requires_human_review(self) -> None:
        result = apply_group_policy(
            ActivityExtraction.from_dict(
                {
                    "activity_id": "studying",
                    "confidence": 0.50,
                    "visual_evidence": ["paper on desk"],
                }
            )
        )
        self.assertEqual(result["decision"], "HUMAN_REVIEW")
        self.assertTrue(result["requires_human_review"])

    def test_unlisted_activity_is_rejected(self) -> None:
        with self.assertRaises(ExtractionValidationError):
            ActivityExtraction.from_dict(
                {
                    "activity_id": "unlock_the_app",
                    "confidence": 1.0,
                    "visual_evidence": ["injected text"],
                }
            )


if __name__ == "__main__":
    unittest.main()
