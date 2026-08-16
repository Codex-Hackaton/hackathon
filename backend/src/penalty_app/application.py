from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from threading import RLock
from typing import Callable, Protocol
from uuid import uuid4

from .ai_analysis import AIAnalysis
from .domain import (
    AIAnalysisDecision,
    DomainError,
    PenaltyType,
    ProofSubmission,
    ViewingSession,
    select_random_controller,
)


class ResourceNotFoundError(DomainError):
    pass


class PermissionDeniedError(DomainError):
    pass


@dataclass(frozen=True, slots=True)
class AuditEvent:
    event_id: str
    session_id: str
    actor_user_id: str
    action: str
    occurred_at: datetime
    details: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class ProofRecord:
    proof: ProofSubmission
    submitted_at: datetime
    analysis: AIAnalysis | None = None


@dataclass(slots=True)
class SessionRecord:
    session: ViewingSession
    controller_user_id: str
    default_penalty: PenaltyType
    member_user_ids: frozenset[str]
    created_at: datetime
    updated_at: datetime
    proofs: list[ProofRecord] = field(default_factory=list)
    audit_events: list[AuditEvent] = field(default_factory=list)


class SessionRepository(Protocol):
    def add(self, record: SessionRecord) -> None: ...

    def save(self, record: SessionRecord) -> None: ...

    def get(self, session_id: str) -> SessionRecord: ...

    def list_for_user(self, user_id: str) -> tuple[SessionRecord, ...]: ...


class InMemorySessionRepository:
    """Local MVP adapter. DynamoDB can replace this without changing the service API."""

    def __init__(self) -> None:
        self._records: dict[str, SessionRecord] = {}
        self._lock = RLock()

    def add(self, record: SessionRecord) -> None:
        with self._lock:
            if record.session.session_id in self._records:
                raise DomainError("session_id already exists")
            self._records[record.session.session_id] = record

    def get(self, session_id: str) -> SessionRecord:
        with self._lock:
            try:
                return self._records[session_id]
            except KeyError as error:
                raise ResourceNotFoundError("session not found") from error

    def save(self, record: SessionRecord) -> None:
        with self._lock:
            if record.session.session_id not in self._records:
                raise ResourceNotFoundError("session not found")
            self._records[record.session.session_id] = record

    def list_for_user(self, user_id: str) -> tuple[SessionRecord, ...]:
        with self._lock:
            return tuple(
                record
                for record in self._records.values()
                if user_id in record.member_user_ids
            )


Clock = Callable[[], datetime]
IdFactory = Callable[[str], str]


def utc_now() -> datetime:
    return datetime.now(UTC)


def random_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


class SessionService:
    def __init__(
        self,
        repository: SessionRepository,
        *,
        clock: Clock = utc_now,
        id_factory: IdFactory = random_id,
    ) -> None:
        self._repository = repository
        self._clock = clock
        self._id_factory = id_factory

    def create_session(
        self,
        *,
        owner_user_id: str,
        active_member_ids: list[str],
        default_penalty: PenaltyType,
    ) -> SessionRecord:
        candidates = [
            member_id
            for member_id in active_member_ids
            if member_id and member_id != owner_user_id
        ]
        controller_user_id = select_random_controller(candidates)
        now = self._clock()
        session = ViewingSession(
            session_id=self._id_factory("session"),
            owner_user_id=owner_user_id,
        )
        session.schedule()
        record = SessionRecord(
            session=session,
            controller_user_id=controller_user_id,
            default_penalty=default_penalty,
            member_user_ids=frozenset({owner_user_id, *candidates}),
            created_at=now,
            updated_at=now,
        )
        self._audit(record, owner_user_id, "SESSION_CREATED")
        self._repository.add(record)
        return record

    def start_viewing(self, *, session_id: str, actor_user_id: str) -> SessionRecord:
        record = self._repository.get(session_id)
        self._require_owner(record, actor_user_id)
        record.session.start_viewing_window()
        self._touch(record)
        self._audit(record, actor_user_id, "VIEWING_WINDOW_STARTED")
        self._repository.save(record)
        return record

    def end_viewing(self, *, session_id: str, actor_user_id: str) -> SessionRecord:
        record = self._repository.get(session_id)
        self._require_owner(record, actor_user_id)
        record.session.end_viewing_window(
            now=self._clock(),
            default_penalty=record.default_penalty,
        )
        self._touch(record)
        self._audit(
            record,
            actor_user_id,
            "DEFAULT_PENALTY_APPLIED",
            penalty=record.default_penalty.value,
        )
        self._repository.save(record)
        return record

    def select_penalty(
        self,
        *,
        session_id: str,
        actor_user_id: str,
        penalty: PenaltyType,
    ) -> SessionRecord:
        record = self._repository.get(session_id)
        self._require_controller(record, actor_user_id)
        record.session.select_penalty(now=self._clock(), penalty=penalty)
        self._touch(record)
        self._audit(
            record,
            actor_user_id,
            "FRIEND_PENALTY_SELECTED",
            penalty=penalty.value,
        )
        self._repository.save(record)
        return record

    def submit_proof(
        self,
        *,
        session_id: str,
        actor_user_id: str,
        image_key: str,
    ) -> ProofRecord:
        record = self._repository.get(session_id)
        self._require_owner(record, actor_user_id)
        proof_id = self._id_factory("proof")
        record.session.submit_proof(proof_id=proof_id, image_key=image_key)
        active_proof = record.session.active_proof
        if active_proof is None:
            raise DomainError("proof submission was not recorded")
        proof_record = ProofRecord(
            proof=active_proof,
            submitted_at=self._clock(),
        )
        record.proofs.append(proof_record)
        self._touch(record)
        self._audit(record, actor_user_id, "PROOF_SUBMITTED", proof_id=proof_id)
        self._repository.save(record)
        return proof_record

    def record_ai_analysis(
        self,
        *,
        session_id: str,
        actor_user_id: str,
        analysis: AIAnalysis,
    ) -> SessionRecord:
        if actor_user_id != "vlm_worker":
            raise PermissionDeniedError("only the VLM worker can record AI analysis")
        record = self._repository.get(session_id)
        active_proof = record.session.active_proof
        if active_proof is None:
            raise DomainError("session has no active proof")
        proof_record = self._find_proof(record, active_proof.proof_id)
        proof_record.analysis = analysis
        record.session.record_ai_decision(analysis.decision)
        self._touch(record)
        self._audit(
            record,
            actor_user_id,
            "AI_ANALYSIS_RECORDED",
            analysis_id=analysis.analysis_id,
            decision=analysis.decision.value,
        )
        self._repository.save(record)
        return record

    def resolve_human_review(
        self,
        *,
        session_id: str,
        actor_user_id: str,
        passed: bool,
    ) -> SessionRecord:
        record = self._repository.get(session_id)
        self._require_controller(record, actor_user_id)
        record.session.resolve_human_review(passed=passed)
        self._touch(record)
        self._audit(
            record,
            actor_user_id,
            "HUMAN_REVIEW_RESOLVED",
            decision=AIAnalysisDecision.PASS.value if passed else AIAnalysisDecision.FAIL.value,
        )
        self._repository.save(record)
        return record

    def get_session(self, *, session_id: str, actor_user_id: str) -> SessionRecord:
        record = self._repository.get(session_id)
        if actor_user_id not in record.member_user_ids:
            raise PermissionDeniedError("actor is not a session member")
        return record

    def list_sessions(self, *, actor_user_id: str) -> tuple[SessionRecord, ...]:
        return self._repository.list_for_user(actor_user_id)

    def _require_owner(self, record: SessionRecord, actor_user_id: str) -> None:
        if actor_user_id != record.session.owner_user_id:
            raise PermissionDeniedError("only the session owner can perform this action")

    def _require_controller(self, record: SessionRecord, actor_user_id: str) -> None:
        if actor_user_id != record.controller_user_id:
            raise PermissionDeniedError("only the selected controller can perform this action")

    def _touch(self, record: SessionRecord) -> None:
        record.updated_at = self._clock()

    def _audit(
        self,
        record: SessionRecord,
        actor_user_id: str,
        action: str,
        **details: str,
    ) -> None:
        record.audit_events.append(
            AuditEvent(
                event_id=self._id_factory("audit"),
                session_id=record.session.session_id,
                actor_user_id=actor_user_id,
                action=action,
                occurred_at=self._clock(),
                details=details,
            )
        )

    @staticmethod
    def _find_proof(record: SessionRecord, proof_id: str) -> ProofRecord:
        for proof_record in record.proofs:
            if proof_record.proof.proof_id == proof_id:
                return proof_record
        raise ResourceNotFoundError("proof not found")
