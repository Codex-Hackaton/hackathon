from datetime import UTC, datetime, timedelta
from random import Random
import unittest

from penalty_app.domain import (
    AIAnalysisDecision,
    DomainError,
    PENALTY_WINDOW_DURATION,
    PenaltyType,
    PenaltyWindowClosedError,
    SessionState,
    StateTransitionError,
    ViewingSession,
    select_random_controller,
)


class ViewingSessionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.session = ViewingSession(
            session_id="session_1",
            owner_user_id="user_a",
        )
        self.now = datetime(2026, 8, 16, 7, 0, tzinfo=UTC)

    def test_fail_keeps_penalty_and_allows_a_new_single_image_submission(self) -> None:
        self.session.schedule()
        self.session.start_viewing_window()
        self.session.end_viewing_window(
            now=self.now,
            default_penalty=PenaltyType.GRAYSCALE,
        )

        self.assertEqual(self.session.state, SessionState.PENALTY_ACTIVE)
        self.assertEqual(self.session.active_penalty, PenaltyType.GRAYSCALE)
        self.assertEqual(
            self.session.penalty_window_closes_at,
            self.now + PENALTY_WINDOW_DURATION,
        )

        self.session.select_penalty(
            now=self.now + timedelta(minutes=5),
            penalty=PenaltyType.BLOCK,
        )
        self.session.submit_proof(
            proof_id="proof_1",
            image_key="proofs/proof_1.jpg",
        )

        with self.assertRaises(StateTransitionError):
            self.session.submit_proof(
                proof_id="proof_2",
                image_key="proofs/proof_2.jpg",
            )

        self.session.record_ai_decision(AIAnalysisDecision.FAIL)
        self.assertEqual(self.session.state, SessionState.PENALTY_ACTIVE)
        self.assertEqual(self.session.active_penalty, PenaltyType.BLOCK)

        self.session.submit_proof(
            proof_id="proof_2",
            image_key="proofs/proof_2.jpg",
        )
        self.session.record_ai_decision(AIAnalysisDecision.PASS)

        self.assertEqual(self.session.state, SessionState.COMPLETED)
        self.assertIsNone(self.session.active_penalty)

    def test_friend_cannot_change_penalty_after_twenty_minutes(self) -> None:
        self.session.schedule()
        self.session.start_viewing_window()
        self.session.end_viewing_window(
            now=self.now,
            default_penalty=PenaltyType.MUTED,
        )

        with self.assertRaises(PenaltyWindowClosedError):
            self.session.select_penalty(
                now=self.now + timedelta(minutes=20),
                penalty=PenaltyType.OBSTRUCTION,
            )

        self.assertEqual(self.session.active_penalty, PenaltyType.MUTED)

    def test_only_human_review_decisions_can_be_resolved_by_a_friend(self) -> None:
        self.session.schedule()
        self.session.start_viewing_window()
        self.session.end_viewing_window(
            now=self.now,
            default_penalty=PenaltyType.BLOCK,
        )
        self.session.submit_proof(
            proof_id="proof_1",
            image_key="proofs/proof_1.jpg",
        )
        self.session.record_ai_decision(AIAnalysisDecision.FAIL)

        with self.assertRaises(StateTransitionError):
            self.session.resolve_human_review(passed=True)

        self.assertEqual(self.session.active_penalty, PenaltyType.BLOCK)

    def test_human_review_can_complete_or_return_to_penalty(self) -> None:
        self.session.schedule()
        self.session.start_viewing_window()
        self.session.end_viewing_window(
            now=self.now,
            default_penalty=PenaltyType.BLOCK,
        )
        self.session.submit_proof(
            proof_id="proof_1",
            image_key="proofs/proof_1.jpg",
        )
        self.session.record_ai_decision(AIAnalysisDecision.HUMAN_REVIEW)
        self.session.resolve_human_review(passed=False)

        self.assertEqual(self.session.state, SessionState.PENALTY_ACTIVE)
        self.assertEqual(self.session.active_penalty, PenaltyType.BLOCK)


class ControllerSelectionTests(unittest.TestCase):
    def test_selects_one_active_member_and_deduplicates_candidates(self) -> None:
        controller = select_random_controller(
            ["user_b", "user_c", "user_b"],
            random_source=Random(7),
        )
        self.assertIn(controller, {"user_b", "user_c"})

    def test_requires_an_active_member(self) -> None:
        with self.assertRaises(DomainError):
            select_random_controller([])


if __name__ == "__main__":
    unittest.main()
