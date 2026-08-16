from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from random import Random
from typing import Sequence


PENALTY_WINDOW_DURATION = timedelta(minutes=20)


class DomainError(ValueError):
    pass


class StateTransitionError(DomainError):
    pass


class PenaltyWindowClosedError(DomainError):
    pass


class PenaltyType(StrEnum):
    BLOCK = "BLOCK"
    GRAYSCALE = "GRAYSCALE"
    OBSTRUCTION = "OBSTRUCTION"
    MUTED = "MUTED"


class SessionState(StrEnum):
    DRAFT = "DRAFT"
    SCHEDULED = "SCHEDULED"
    VIEWING_WINDOW_ACTIVE = "VIEWING_WINDOW_ACTIVE"
    PENALTY_ACTIVE = "PENALTY_ACTIVE"
    AI_ANALYZING = "AI_ANALYZING"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    COMPLETED = "COMPLETED"


class AIAnalysisDecision(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    HUMAN_REVIEW = "HUMAN_REVIEW"


@dataclass(frozen=True, slots=True)
class ProofSubmission:
    proof_id: str
    image_key: str

    def __post_init__(self) -> None:
        if not self.proof_id:
            raise DomainError("proof_id is required")
        if not self.image_key:
            raise DomainError("one image_key is required")


@dataclass(slots=True)
class ViewingSession:
    session_id: str
    owner_user_id: str
    state: SessionState = SessionState.DRAFT
    active_penalty: PenaltyType | None = None
    penalty_window_opened_at: datetime | None = None
    penalty_window_closes_at: datetime | None = None
    active_proof: ProofSubmission | None = None

    def schedule(self) -> None:
        self._require_state(SessionState.DRAFT)
        self.state = SessionState.SCHEDULED

    def start_viewing_window(self) -> None:
        self._require_state(SessionState.SCHEDULED)
        self.state = SessionState.VIEWING_WINDOW_ACTIVE

    def end_viewing_window(
        self,
        *,
        now: datetime,
        default_penalty: PenaltyType,
    ) -> None:
        self._require_state(SessionState.VIEWING_WINDOW_ACTIVE)
        self.penalty_window_opened_at = now
        self.penalty_window_closes_at = now + PENALTY_WINDOW_DURATION
        self.active_penalty = default_penalty
        self.state = SessionState.PENALTY_ACTIVE

    def select_penalty(
        self,
        *,
        now: datetime,
        penalty: PenaltyType,
    ) -> None:
        self._require_state(SessionState.PENALTY_ACTIVE)
        if (
            self.penalty_window_opened_at is None
            or self.penalty_window_closes_at is None
            or now < self.penalty_window_opened_at
            or now >= self.penalty_window_closes_at
        ):
            raise PenaltyWindowClosedError("friend penalty selection is closed")
        self.active_penalty = penalty

    def submit_proof(self, *, proof_id: str, image_key: str) -> None:
        self._require_state(SessionState.PENALTY_ACTIVE)
        self.active_proof = ProofSubmission(proof_id=proof_id, image_key=image_key)
        self.state = SessionState.AI_ANALYZING

    def record_ai_decision(self, decision: AIAnalysisDecision) -> None:
        self._require_state(SessionState.AI_ANALYZING)
        if self.active_proof is None:
            raise DomainError("an active proof is required")

        if decision is AIAnalysisDecision.PASS:
            self.active_penalty = None
            self.active_proof = None
            self.state = SessionState.COMPLETED
        elif decision is AIAnalysisDecision.FAIL:
            self.active_proof = None
            self.state = SessionState.PENALTY_ACTIVE
        else:
            self.state = SessionState.HUMAN_REVIEW

    def resolve_human_review(self, *, passed: bool) -> None:
        self._require_state(SessionState.HUMAN_REVIEW)
        if passed:
            self.active_penalty = None
            self.active_proof = None
            self.state = SessionState.COMPLETED
        else:
            self.active_proof = None
            self.state = SessionState.PENALTY_ACTIVE

    def _require_state(self, expected: SessionState) -> None:
        if self.state is not expected:
            raise StateTransitionError(
                f"expected state {expected}, got {self.state}"
            )


def select_random_controller(
    active_member_ids: Sequence[str],
    *,
    random_source: Random | None = None,
) -> str:
    candidates = tuple(dict.fromkeys(member_id for member_id in active_member_ids if member_id))
    if not candidates:
        raise DomainError("at least one active group member is required")
    return (random_source or Random()).choice(candidates)
