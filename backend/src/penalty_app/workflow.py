from __future__ import annotations

from dataclasses import dataclass
import json
from uuid import uuid4


@dataclass(frozen=True, slots=True)
class AnalysisJob:
    job_id: str
    session_id: str
    status: str
    output: dict[str, object] | None = None
    error: str | None = None


class StepFunctionsAnalysisWorkflow:
    def __init__(self, state_machine_arn: str, *, client=None) -> None:
        if client is None:
            import boto3

            client = boto3.client("stepfunctions")
        self.state_machine_arn = state_machine_arn
        self._client = client

    def start(self, *, session_id: str, proof_id: str) -> AnalysisJob:
        job_id = f"analysis-{uuid4().hex}"
        self._client.start_execution(
            stateMachineArn=self.state_machine_arn,
            name=job_id,
            input=json.dumps(
                {"session_id": session_id, "proof_id": proof_id},
                separators=(",", ":"),
            ),
        )
        return AnalysisJob(job_id=job_id, session_id=session_id, status="RUNNING")

    def get(self, job_id: str) -> AnalysisJob:
        response = self._client.describe_execution(
            executionArn=self._execution_arn(job_id)
        )
        request_input = json.loads(response["input"])
        status = response["status"]
        output = json.loads(response["output"]) if response.get("output") else None
        return AnalysisJob(
            job_id=job_id,
            session_id=request_input["session_id"],
            status=status,
            output=output,
            error=response.get("cause") or response.get("error"),
        )

    def _execution_arn(self, job_id: str) -> str:
        prefix, name = self.state_machine_arn.rsplit(":stateMachine:", 1)
        return f"{prefix}:execution:{name}:{job_id}"
