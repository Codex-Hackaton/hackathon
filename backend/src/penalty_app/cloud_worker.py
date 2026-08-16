from __future__ import annotations

import json
import os

from .application import SessionService
from .persistence import DynamoDBSessionRepository
from .storage import S3ProofStorage
from .vlm import RunPodVLMClient


def analyze_proof(event: dict[str, object], _context) -> dict[str, object]:
    session_id = str(event["session_id"])
    expected_proof_id = str(event["proof_id"])
    repository = DynamoDBSessionRepository(_required("OFFMATE_DYNAMODB_TABLE"))
    storage = S3ProofStorage(_required("OFFMATE_PROOF_BUCKET"))
    record = repository.get(session_id)
    proof = record.session.active_proof
    if proof is None or proof.proof_id != expected_proof_id:
        raise ValueError("the active proof does not match the analysis job")

    endpoint_id = _required("RUNPOD_ENDPOINT_ID")
    analyzer = RunPodVLMClient(
        endpoint_url=(
            f"https://api.runpod.ai/v2/{endpoint_id}/openai/v1/chat/completions"
        ),
        api_key=_runpod_api_key(),
        model_id=os.getenv(
            "RUNPOD_MODEL_ID", "Qwen/Qwen2.5-VL-3B-Instruct"
        ),
        timeout_seconds=240,
    )
    analysis = analyzer.analyze(image_path=storage.path_for(proof.image_key))
    updated = SessionService(repository).record_ai_analysis(
        session_id=session_id,
        actor_user_id="vlm_worker",
        analysis=analysis,
    )
    return {
        "session_id": session_id,
        "state": updated.session.state.value,
        "analysis": _analysis_dict(analysis),
    }


def _runpod_api_key() -> str:
    import boto3

    secret = boto3.client("secretsmanager").get_secret_value(
        SecretId=_required("RUNPOD_API_KEY_SECRET_ARN")
    ).get("SecretString", "")
    try:
        payload = json.loads(secret)
    except ValueError:
        if secret:
            return secret
        raise RuntimeError("RunPod API key secret is empty")
    value = payload.get("RUNPOD_API_KEY") or payload.get("api_key")
    if not value:
        raise RuntimeError("RunPod API key secret has no API key")
    return value


def _required(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"{name} is required")
    return value


def _analysis_dict(analysis) -> dict[str, object]:
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
