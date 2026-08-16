from __future__ import annotations

import argparse
import json
from pathlib import Path
import time

import boto3

from penalty_app.application import SessionService
from penalty_app.domain import PenaltyType, SessionState
from penalty_app.persistence import DynamoDBSessionRepository
from penalty_app.storage import S3ProofStorage


def main() -> None:
    parser = argparse.ArgumentParser(description="Run one real OFFMate AWS VLM flow")
    parser.add_argument("image", type=Path)
    parser.add_argument("--profile", default="OFFMateDev")
    parser.add_argument("--region", default="ap-northeast-2")
    parser.add_argument("--stack", default="offmate-dev")
    args = parser.parse_args()

    if not args.image.is_file():
        raise SystemExit(f"image not found: {args.image}")

    aws = boto3.Session(profile_name=args.profile, region_name=args.region)
    outputs = _stack_outputs(aws.client("cloudformation"), args.stack)
    dynamodb = aws.client("dynamodb")
    s3 = aws.client("s3")
    stepfunctions = aws.client("stepfunctions")
    repository = DynamoDBSessionRepository(outputs["DynamoDBTableName"], client=dynamodb)
    storage = S3ProofStorage(outputs["ProofBucketName"], client=s3)
    service = SessionService(repository)

    record = service.create_session(
        owner_user_id="aws_smoke_user_a",
        active_member_ids=["aws_smoke_user_b"],
        default_penalty=PenaltyType.OBSTRUCTION,
    )
    session_id = record.session.session_id
    service.start_viewing(session_id=session_id, actor_user_id="aws_smoke_user_a")
    service.end_viewing(session_id=session_id, actor_user_id="aws_smoke_user_a")

    slot = storage.create_slot(
        owner_user_id="aws_smoke_user_a",
        content_type="image/jpeg",
    )
    s3.put_object(
        Bucket=outputs["ProofBucketName"],
        Key=slot.image_key,
        Body=args.image.read_bytes(),
        ContentType="image/jpeg",
    )
    storage.require_uploaded(
        image_key=slot.image_key,
        owner_user_id="aws_smoke_user_a",
    )
    proof = service.submit_proof(
        session_id=session_id,
        actor_user_id="aws_smoke_user_a",
        image_key=slot.image_key,
    )

    execution = stepfunctions.start_execution(
        stateMachineArn=outputs["AnalysisStateMachineArn"],
        input=json.dumps(
            {
                "session_id": session_id,
                "proof_id": proof.proof.proof_id,
            }
        ),
    )
    result = _wait_for_execution(stepfunctions, execution["executionArn"])
    updated = repository.get(session_id)
    output = json.loads(result["output"])
    decision = output["analysis"]["decision"]
    if decision != "PASS" or updated.session.state is not SessionState.COMPLETED:
        raise SystemExit(
            f"unexpected result: decision={decision}, state={updated.session.state.value}"
        )
    print(
        json.dumps(
            {
                "execution_arn": execution["executionArn"],
                "session_id": session_id,
                "decision": decision,
                "state": updated.session.state.value,
            },
            indent=2,
        )
    )


def _stack_outputs(client, stack_name: str) -> dict[str, str]:
    stack = client.describe_stacks(StackName=stack_name)["Stacks"][0]
    return {item["OutputKey"]: item["OutputValue"] for item in stack["Outputs"]}


def _wait_for_execution(client, execution_arn: str) -> dict[str, object]:
    deadline = time.monotonic() + 360
    while time.monotonic() < deadline:
        result = client.describe_execution(executionArn=execution_arn)
        if result["status"] == "SUCCEEDED":
            return result
        if result["status"] in {"FAILED", "TIMED_OUT", "ABORTED"}:
            raise SystemExit(
                f"Step Functions {result['status']}: "
                f"{result.get('error', '')} {result.get('cause', '')}"
            )
        time.sleep(3)
    raise SystemExit("Step Functions smoke test timed out")


if __name__ == "__main__":
    main()
