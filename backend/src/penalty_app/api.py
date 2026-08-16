from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime
import os
from pathlib import Path
from threading import RLock
from typing import Annotated, Any, Callable, TypeVar

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from .ai_analysis import AIAnalysis
from .application import (
    InMemorySessionRepository,
    PermissionDeniedError,
    ProofRecord,
    ResourceNotFoundError,
    SessionRecord,
    SessionRepository,
    SessionService,
)
from .domain import DomainError, PenaltyType
from .persistence import DynamoDBSessionRepository, SQLiteSessionRepository
from .storage import LocalProofStorage, ProofStorage, S3ProofStorage, UploadSlotError
from .vlm import DeterministicDemoVLM, RunPodVLMClient, VLMClient, VLMUnavailableError
from .workflow import AnalysisJob, StepFunctionsAnalysisWorkflow


class IdempotencyConflictError(DomainError):
    pass


T = TypeVar("T")


class InMemoryIdempotencyStore:
    def __init__(self) -> None:
        self._values: dict[str, tuple[str, Any]] = {}
        self._lock = RLock()

    def execute(
        self,
        *,
        scope: str,
        key: str,
        fingerprint: str,
        operation: Callable[[], T],
    ) -> T:
        cache_key = f"{scope}:{key}"
        with self._lock:
            cached = self._values.get(cache_key)
            if cached is not None:
                cached_fingerprint, cached_value = cached
                if cached_fingerprint != fingerprint:
                    raise IdempotencyConflictError(
                        "idempotency key was already used with a different request"
                    )
                return cached_value
            value = operation()
            self._values[cache_key] = (fingerprint, value)
            return value


class CreateSessionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    active_member_ids: list[str] = Field(min_length=1)
    default_penalty: PenaltyType


class SelectPenaltyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    penalty: PenaltyType


class UploadSlotRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content_type: str


class SubmitProofRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    image_key: str = Field(min_length=1)


class ResolveReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    passed: bool


class UploadSlotResponse(BaseModel):
    upload_url: str
    image_key: str
    expires_at: datetime
    required_content_type: str


class ProofResponse(BaseModel):
    proof_id: str
    image_key: str
    submitted_at: datetime

    @classmethod
    def from_record(cls, record: ProofRecord) -> ProofResponse:
        return cls(
            proof_id=record.proof.proof_id,
            image_key=record.proof.image_key,
            submitted_at=record.submitted_at,
        )


class SessionResponse(BaseModel):
    session_id: str
    owner_user_id: str
    controller_user_id: str
    state: str
    default_penalty: PenaltyType
    active_penalty: PenaltyType | None
    penalty_window_closes_at: datetime | None
    active_proof_id: str | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_record(cls, record: SessionRecord) -> SessionResponse:
        active_proof = record.session.active_proof
        return cls(
            session_id=record.session.session_id,
            owner_user_id=record.session.owner_user_id,
            controller_user_id=record.controller_user_id,
            state=record.session.state.value,
            default_penalty=record.default_penalty,
            active_penalty=record.session.active_penalty,
            penalty_window_closes_at=record.session.penalty_window_closes_at,
            active_proof_id=active_proof.proof_id if active_proof else None,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )


class AnalysisResponse(BaseModel):
    session: SessionResponse
    analysis: dict[str, Any]


class HealthResponse(BaseModel):
    status: str
    vlm_mode: str


class AnalysisJobResponse(BaseModel):
    analysis_job_id: str
    session_id: str
    status: str
    session: SessionResponse | None = None
    analysis: dict[str, Any] | None = None
    error: str | None = None


UserID = Annotated[str, Header(alias="X-User-ID", min_length=1)]
IdempotencyKey = Annotated[str, Header(alias="Idempotency-Key", min_length=8)]


def create_app(
    *,
    service: SessionService | None = None,
    repository: SessionRepository | None = None,
    database_path: Path | None = None,
    storage: ProofStorage | None = None,
    vlm_client: VLMClient | None = None,
    analysis_workflow: StepFunctionsAnalysisWorkflow | None = None,
) -> FastAPI:
    active_repository: SessionRepository | None = repository
    if service is None:
        if active_repository is None:
            active_repository = (
                SQLiteSessionRepository(database_path)
                if database_path is not None
                else InMemorySessionRepository()
            )
        session_service = SessionService(active_repository)
    else:
        session_service = service
    proof_storage = storage or LocalProofStorage()
    analyzer = vlm_client or _vlm_from_environment()
    workflow = analysis_workflow or _workflow_from_environment()
    idempotency = InMemoryIdempotencyStore()

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        yield
        if isinstance(active_repository, SQLiteSessionRepository):
            active_repository.close()

    app = FastAPI(
        title="OFFMate API",
        version="0.1.0",
        description="Friend-controlled short-form penalty session API",
        lifespan=lifespan,
    )
    app.state.session_repository = active_repository
    app.state.session_service = session_service
    app.state.proof_storage = proof_storage
    app.state.vlm_client = analyzer
    app.state.idempotency = idempotency
    app.state.analysis_workflow = workflow

    @app.middleware("http")
    async def use_cognito_subject(request: Request, call_next):
        if (
            os.getenv("OFFMATE_TRUST_API_GATEWAY_AUTH") == "true"
            and request.url.path != "/health"
        ):
            event = request.scope.get("aws.event", {})
            authorizer = event.get("requestContext", {}).get("authorizer", {})
            claims = authorizer.get("claims") or authorizer.get("jwt", {}).get(
                "claims", {}
            )
            subject = claims.get("sub")
            if not subject:
                return JSONResponse(status_code=401, content={"detail": "unauthorized"})
            headers = [
                (key, value)
                for key, value in request.scope["headers"]
                if key.lower() != b"x-user-id"
            ]
            headers.append((b"x-user-id", subject.encode("utf-8")))
            request.scope["headers"] = headers
        return await call_next(request)

    @app.exception_handler(ResourceNotFoundError)
    async def handle_not_found(_: Request, error: ResourceNotFoundError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(error)})

    @app.exception_handler(PermissionDeniedError)
    async def handle_forbidden(_: Request, error: PermissionDeniedError) -> JSONResponse:
        return JSONResponse(status_code=403, content={"detail": str(error)})

    @app.exception_handler(DomainError)
    async def handle_domain_error(_: Request, error: Exception) -> JSONResponse:
        return JSONResponse(status_code=409, content={"detail": str(error)})

    @app.exception_handler(VLMUnavailableError)
    async def handle_vlm_error(_: Request, error: VLMUnavailableError) -> JSONResponse:
        return JSONResponse(status_code=503, content={"detail": str(error)})

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(
            status="ok",
            vlm_mode="runpod" if isinstance(analyzer, RunPodVLMClient) else "demo",
        )

    @app.post("/v1/upload-slots", response_model=UploadSlotResponse, status_code=201)
    def create_upload_slot(
        body: UploadSlotRequest,
        user_id: UserID,
        idempotency_key: IdempotencyKey,
    ) -> UploadSlotResponse:
        def operation() -> UploadSlotResponse:
            slot = proof_storage.create_slot(
                owner_user_id=user_id,
                content_type=body.content_type,
            )
            return UploadSlotResponse(
                upload_url=slot.upload_url or f"/v1/uploads/{slot.token}",
                image_key=slot.image_key,
                expires_at=slot.expires_at,
                required_content_type=slot.content_type,
            )

        return idempotency.execute(
            scope=f"upload-slot:{user_id}",
            key=idempotency_key,
            fingerprint=body.model_dump_json(),
            operation=operation,
        )

    @app.put("/v1/uploads/{token}", status_code=204)
    async def upload_image(token: str, request: Request) -> None:
        content_type = request.headers.get("content-type", "")
        proof_storage.upload(
            token=token,
            content_type=content_type,
            body=await request.body(),
        )

    @app.post("/v1/sessions", response_model=SessionResponse, status_code=201)
    def create_session(
        body: CreateSessionRequest,
        user_id: UserID,
        idempotency_key: IdempotencyKey,
    ) -> SessionResponse:
        return idempotency.execute(
            scope=f"create-session:{user_id}",
            key=idempotency_key,
            fingerprint=body.model_dump_json(),
            operation=lambda: SessionResponse.from_record(
                session_service.create_session(
                    owner_user_id=user_id,
                    active_member_ids=body.active_member_ids,
                    default_penalty=body.default_penalty,
                )
            ),
        )

    @app.get("/v1/sessions", response_model=list[SessionResponse])
    def list_sessions(user_id: UserID) -> list[SessionResponse]:
        return [
            SessionResponse.from_record(record)
            for record in session_service.list_sessions(actor_user_id=user_id)
        ]

    @app.get("/v1/sessions/{session_id}", response_model=SessionResponse)
    def get_session(session_id: str, user_id: UserID) -> SessionResponse:
        return SessionResponse.from_record(
            session_service.get_session(session_id=session_id, actor_user_id=user_id)
        )

    @app.post("/v1/sessions/{session_id}/start", response_model=SessionResponse)
    def start_session(
        session_id: str,
        user_id: UserID,
        idempotency_key: IdempotencyKey,
    ) -> SessionResponse:
        return idempotency.execute(
            scope=f"start-session:{session_id}:{user_id}",
            key=idempotency_key,
            fingerprint="start",
            operation=lambda: SessionResponse.from_record(
                session_service.start_viewing(
                    session_id=session_id,
                    actor_user_id=user_id,
                )
            ),
        )

    @app.post("/v1/sessions/{session_id}/end", response_model=SessionResponse)
    def end_session(
        session_id: str,
        user_id: UserID,
        idempotency_key: IdempotencyKey,
    ) -> SessionResponse:
        return idempotency.execute(
            scope=f"end-session:{session_id}:{user_id}",
            key=idempotency_key,
            fingerprint="end",
            operation=lambda: SessionResponse.from_record(
                session_service.end_viewing(
                    session_id=session_id,
                    actor_user_id=user_id,
                )
            ),
        )

    @app.post("/v1/sessions/{session_id}/penalties", response_model=SessionResponse)
    def select_penalty(
        session_id: str,
        body: SelectPenaltyRequest,
        user_id: UserID,
        idempotency_key: IdempotencyKey,
    ) -> SessionResponse:
        return idempotency.execute(
            scope=f"select-penalty:{session_id}:{user_id}",
            key=idempotency_key,
            fingerprint=body.model_dump_json(),
            operation=lambda: SessionResponse.from_record(
                session_service.select_penalty(
                    session_id=session_id,
                    actor_user_id=user_id,
                    penalty=body.penalty,
                )
            ),
        )

    @app.post(
        "/v1/sessions/{session_id}/proofs",
        response_model=ProofResponse,
        status_code=201,
    )
    def submit_proof(
        session_id: str,
        body: SubmitProofRequest,
        user_id: UserID,
        idempotency_key: IdempotencyKey,
    ) -> ProofResponse:
        proof_storage.require_uploaded(
            image_key=body.image_key,
            owner_user_id=user_id,
        )
        return idempotency.execute(
            scope=f"submit-proof:{session_id}:{user_id}",
            key=idempotency_key,
            fingerprint=body.model_dump_json(),
            operation=lambda: ProofResponse.from_record(
                session_service.submit_proof(
                    session_id=session_id,
                    actor_user_id=user_id,
                    image_key=body.image_key,
                )
            ),
        )

    @app.post(
        "/v1/sessions/{session_id}/analyze",
        response_model=AnalysisResponse,
    )
    def analyze_proof(
        session_id: str,
        user_id: UserID,
        idempotency_key: IdempotencyKey,
    ) -> AnalysisResponse:
        record = session_service.get_session(
            session_id=session_id,
            actor_user_id=user_id,
        )
        if user_id != record.session.owner_user_id:
            raise PermissionDeniedError("only the session owner can request analysis")
        active_proof = record.session.active_proof
        if active_proof is None:
            raise DomainError("session has no active proof")

        def operation() -> AnalysisResponse:
            analysis = analyzer.analyze(
                image_path=proof_storage.path_for(active_proof.image_key)
            )
            updated = session_service.record_ai_analysis(
                session_id=session_id,
                actor_user_id="vlm_worker",
                analysis=analysis,
            )
            return AnalysisResponse(
                session=SessionResponse.from_record(updated),
                analysis=_analysis_dict(analysis),
            )

        return idempotency.execute(
            scope=f"analyze-proof:{session_id}:{active_proof.proof_id}",
            key=idempotency_key,
            fingerprint=active_proof.image_key,
            operation=operation,
        )

    @app.post(
        "/v1/sessions/{session_id}/analysis-jobs",
        response_model=AnalysisJobResponse,
        status_code=202,
    )
    def start_analysis_job(
        session_id: str,
        user_id: UserID,
        idempotency_key: IdempotencyKey,
    ) -> AnalysisJobResponse:
        if workflow is None:
            raise HTTPException(status_code=501, detail="async analysis is not configured")
        record = session_service.get_session(
            session_id=session_id,
            actor_user_id=user_id,
        )
        if user_id != record.session.owner_user_id:
            raise PermissionDeniedError("only the session owner can request analysis")
        proof = record.session.active_proof
        if proof is None:
            raise DomainError("session has no active proof")
        job = idempotency.execute(
            scope=f"analysis-job:{session_id}:{proof.proof_id}",
            key=idempotency_key,
            fingerprint=proof.image_key,
            operation=lambda: workflow.start(
                session_id=session_id,
                proof_id=proof.proof_id,
            ),
        )
        return _analysis_job_response(job)

    @app.get(
        "/v1/analysis-jobs/{job_id}",
        response_model=AnalysisJobResponse,
    )
    def get_analysis_job(job_id: str, user_id: UserID) -> AnalysisJobResponse:
        if workflow is None:
            raise HTTPException(status_code=501, detail="async analysis is not configured")
        job = workflow.get(job_id)
        record = session_service.get_session(
            session_id=job.session_id,
            actor_user_id=user_id,
        )
        output_analysis = job.output.get("analysis") if job.output else None
        return AnalysisJobResponse(
            analysis_job_id=job.job_id,
            session_id=job.session_id,
            status=job.status,
            session=(
                SessionResponse.from_record(record)
                if job.status == "SUCCEEDED"
                else None
            ),
            analysis=output_analysis if isinstance(output_analysis, dict) else None,
            error=job.error,
        )

    @app.post("/v1/sessions/{session_id}/review", response_model=SessionResponse)
    def resolve_review(
        session_id: str,
        body: ResolveReviewRequest,
        user_id: UserID,
        idempotency_key: IdempotencyKey,
    ) -> SessionResponse:
        return idempotency.execute(
            scope=f"review:{session_id}:{user_id}",
            key=idempotency_key,
            fingerprint=body.model_dump_json(),
            operation=lambda: SessionResponse.from_record(
                session_service.resolve_human_review(
                    session_id=session_id,
                    actor_user_id=user_id,
                    passed=body.passed,
                )
            ),
        )

    return app


def _vlm_from_environment() -> VLMClient:
    endpoint_url = os.getenv("RUNPOD_ENDPOINT_URL")
    endpoint_id = os.getenv("RUNPOD_ENDPOINT_ID")
    api_key = os.getenv("RUNPOD_API_KEY") or _runpod_key_from_secret()
    if endpoint_id and api_key:
        endpoint_url = (
            f"https://api.runpod.ai/v2/{endpoint_id}/openai/v1/chat/completions"
        )
    if endpoint_url and api_key:
        return RunPodVLMClient(
            endpoint_url=endpoint_url,
            api_key=api_key,
            model_id=os.getenv(
                "RUNPOD_MODEL_ID", "Qwen/Qwen2.5-VL-3B-Instruct"
            ),
            timeout_seconds=130,
        )
    return DeterministicDemoVLM()


def _runpod_key_from_secret() -> str | None:
    secret_id = os.getenv("RUNPOD_API_KEY_SECRET_ARN")
    if not secret_id:
        return None
    try:
        import boto3

        value = boto3.client("secretsmanager").get_secret_value(SecretId=secret_id)
        secret = value.get("SecretString", "")
        try:
            payload = __import__("json").loads(secret)
        except ValueError:
            return secret or None
        return payload.get("RUNPOD_API_KEY") or payload.get("api_key")
    except Exception:
        return None


def _analysis_dict(analysis: AIAnalysis) -> dict[str, Any]:
    return {
        "analysis_id": analysis.analysis_id,
        "detected_activities": [
            {
                "activity_id": activity.activity_id,
                "confidence": activity.confidence,
                "visual_evidence": list(activity.visual_evidence),
            }
            for activity in analysis.detected_activities
        ],
        "decision": analysis.decision.value,
        "decision_confidence": analysis.decision_confidence,
        "matched_policy_ids": list(analysis.matched_policy_ids),
        "reason": analysis.reason,
        "requires_human_review": analysis.requires_human_review,
    }


def _database_path_from_environment() -> Path | None:
    value = os.getenv("OFFMATE_DB_PATH")
    return Path(value) if value else None


def _repository_from_environment() -> SessionRepository | None:
    table_name = os.getenv("OFFMATE_DYNAMODB_TABLE")
    return DynamoDBSessionRepository(table_name) if table_name else None


def _storage_from_environment() -> ProofStorage | None:
    bucket_name = os.getenv("OFFMATE_PROOF_BUCKET")
    return S3ProofStorage(bucket_name) if bucket_name else None


def _workflow_from_environment() -> StepFunctionsAnalysisWorkflow | None:
    state_machine_arn = os.getenv("OFFMATE_ANALYSIS_STATE_MACHINE_ARN")
    return (
        StepFunctionsAnalysisWorkflow(state_machine_arn)
        if state_machine_arn
        else None
    )


def _analysis_job_response(job: AnalysisJob) -> AnalysisJobResponse:
    return AnalysisJobResponse(
        analysis_job_id=job.job_id,
        session_id=job.session_id,
        status=job.status,
        error=job.error,
    )


app = create_app(
    repository=_repository_from_environment(),
    database_path=_database_path_from_environment(),
    storage=_storage_from_environment(),
)


def run() -> None:
    import uvicorn

    uvicorn.run("penalty_app.api:app", host="127.0.0.1", port=8000, reload=True)
