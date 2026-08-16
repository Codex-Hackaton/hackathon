from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
import sqlite3
from threading import RLock
from typing import Any

from .ai_analysis import AIAnalysis
from .application import AuditEvent, ProofRecord, ResourceNotFoundError, SessionRecord
from .domain import DomainError, PenaltyType, ProofSubmission, SessionState, ViewingSession


class SQLiteSessionRepository:
    """Durable local adapter; DynamoDB can implement the same repository protocol."""

    def __init__(self, database_path: Path) -> None:
        database_path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(database_path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._lock = RLock()
        with self._connection:
            self._connection.execute("PRAGMA journal_mode=WAL")
            self._connection.execute("PRAGMA foreign_keys=ON")
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    record_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS session_members (
                    session_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    PRIMARY KEY (session_id, user_id),
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
                        ON DELETE CASCADE
                )
                """
            )
            self._connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_session_members_user "
                "ON session_members(user_id)"
            )

    def add(self, record: SessionRecord) -> None:
        payload = json.dumps(_record_to_dict(record), ensure_ascii=False)
        with self._lock, self._connection:
            try:
                self._connection.execute(
                    "INSERT INTO sessions(session_id, record_json, updated_at) "
                    "VALUES (?, ?, ?)",
                    (
                        record.session.session_id,
                        payload,
                        record.updated_at.isoformat(),
                    ),
                )
            except sqlite3.IntegrityError as error:
                raise DomainError("session_id already exists") from error
            self._replace_members(record)

    def save(self, record: SessionRecord) -> None:
        payload = json.dumps(_record_to_dict(record), ensure_ascii=False)
        with self._lock, self._connection:
            cursor = self._connection.execute(
                "UPDATE sessions SET record_json = ?, updated_at = ? "
                "WHERE session_id = ?",
                (
                    payload,
                    record.updated_at.isoformat(),
                    record.session.session_id,
                ),
            )
            if cursor.rowcount != 1:
                raise ResourceNotFoundError("session not found")
            self._replace_members(record)

    def get(self, session_id: str) -> SessionRecord:
        with self._lock:
            row = self._connection.execute(
                "SELECT record_json FROM sessions WHERE session_id = ?",
                (session_id,),
            ).fetchone()
        if row is None:
            raise ResourceNotFoundError("session not found")
        return _record_from_dict(json.loads(row["record_json"]))

    def list_for_user(self, user_id: str) -> tuple[SessionRecord, ...]:
        with self._lock:
            rows = self._connection.execute(
                """
                SELECT sessions.record_json
                FROM sessions
                JOIN session_members
                  ON session_members.session_id = sessions.session_id
                WHERE session_members.user_id = ?
                ORDER BY sessions.updated_at DESC
                """,
                (user_id,),
            ).fetchall()
        return tuple(_record_from_dict(json.loads(row["record_json"])) for row in rows)

    def close(self) -> None:
        with self._lock:
            self._connection.close()

    def _replace_members(self, record: SessionRecord) -> None:
        session_id = record.session.session_id
        self._connection.execute(
            "DELETE FROM session_members WHERE session_id = ?",
            (session_id,),
        )
        self._connection.executemany(
            "INSERT INTO session_members(session_id, user_id) VALUES (?, ?)",
            [(session_id, user_id) for user_id in sorted(record.member_user_ids)],
        )


class DynamoDBSessionRepository:
    """Single-table DynamoDB adapter for sessions and user memberships."""

    def __init__(self, table_name: str, *, client=None) -> None:
        if not table_name:
            raise ValueError("table_name is required")
        if client is None:
            import boto3

            client = boto3.client("dynamodb")
        self.table_name = table_name
        self._client = client

    def add(self, record: SessionRecord) -> None:
        session_id = record.session.session_id
        transaction = [
            {
                "Put": {
                    "TableName": self.table_name,
                    "Item": self._session_item(record),
                    "ConditionExpression": "attribute_not_exists(PK)",
                }
            }
        ]
        transaction.extend(
            {
                "Put": {
                    "TableName": self.table_name,
                    "Item": {
                        "PK": {"S": f"USER#{user_id}"},
                        "SK": {"S": f"SESSION#{session_id}"},
                        "session_id": {"S": session_id},
                    },
                }
            }
            for user_id in sorted(record.member_user_ids)
        )
        try:
            self._client.transact_write_items(TransactItems=transaction)
        except Exception as error:
            if self._error_code(error) == "TransactionCanceledException":
                raise DomainError("session_id already exists") from error
            raise

    def save(self, record: SessionRecord) -> None:
        try:
            self._client.put_item(
                TableName=self.table_name,
                Item=self._session_item(record),
                ConditionExpression="attribute_exists(PK)",
            )
        except Exception as error:
            if self._error_code(error) == "ConditionalCheckFailedException":
                raise ResourceNotFoundError("session not found") from error
            raise

    def get(self, session_id: str) -> SessionRecord:
        response = self._client.get_item(
            TableName=self.table_name,
            Key={
                "PK": {"S": f"SESSION#{session_id}"},
                "SK": {"S": "RECORD"},
            },
            ConsistentRead=True,
        )
        item = response.get("Item")
        if not item:
            raise ResourceNotFoundError("session not found")
        return _record_from_dict(json.loads(item["record_json"]["S"]))

    def list_for_user(self, user_id: str) -> tuple[SessionRecord, ...]:
        session_ids: list[str] = []
        request: dict[str, Any] = {
            "TableName": self.table_name,
            "KeyConditionExpression": "PK = :pk AND begins_with(SK, :prefix)",
            "ExpressionAttributeValues": {
                ":pk": {"S": f"USER#{user_id}"},
                ":prefix": {"S": "SESSION#"},
            },
        }
        while True:
            response = self._client.query(**request)
            session_ids.extend(
                item["session_id"]["S"] for item in response.get("Items", [])
            )
            last_key = response.get("LastEvaluatedKey")
            if not last_key:
                break
            request["ExclusiveStartKey"] = last_key
        records = [self.get(session_id) for session_id in session_ids]
        records.sort(key=lambda record: record.updated_at, reverse=True)
        return tuple(records)

    def _session_item(self, record: SessionRecord) -> dict[str, dict[str, str]]:
        session_id = record.session.session_id
        return {
            "PK": {"S": f"SESSION#{session_id}"},
            "SK": {"S": "RECORD"},
            "record_json": {
                "S": json.dumps(_record_to_dict(record), ensure_ascii=False)
            },
            "updated_at": {"S": record.updated_at.isoformat()},
        }

    @staticmethod
    def _error_code(error: Exception) -> str | None:
        response = getattr(error, "response", {})
        return response.get("Error", {}).get("Code")


def _record_to_dict(record: SessionRecord) -> dict[str, Any]:
    session = record.session
    return {
        "session": {
            "session_id": session.session_id,
            "owner_user_id": session.owner_user_id,
            "state": session.state.value,
            "active_penalty": session.active_penalty.value if session.active_penalty else None,
            "penalty_window_opened_at": _date_or_none(session.penalty_window_opened_at),
            "penalty_window_closes_at": _date_or_none(session.penalty_window_closes_at),
            "active_proof": (
                {
                    "proof_id": session.active_proof.proof_id,
                    "image_key": session.active_proof.image_key,
                }
                if session.active_proof
                else None
            ),
        },
        "controller_user_id": record.controller_user_id,
        "default_penalty": record.default_penalty.value,
        "member_user_ids": sorted(record.member_user_ids),
        "created_at": record.created_at.isoformat(),
        "updated_at": record.updated_at.isoformat(),
        "proofs": [
            {
                "proof": {
                    "proof_id": proof_record.proof.proof_id,
                    "image_key": proof_record.proof.image_key,
                },
                "submitted_at": proof_record.submitted_at.isoformat(),
                "analysis": _analysis_to_dict(proof_record.analysis),
            }
            for proof_record in record.proofs
        ],
        "audit_events": [
            {
                "event_id": event.event_id,
                "session_id": event.session_id,
                "actor_user_id": event.actor_user_id,
                "action": event.action,
                "occurred_at": event.occurred_at.isoformat(),
                "details": event.details,
            }
            for event in record.audit_events
        ],
    }


def _record_from_dict(value: dict[str, Any]) -> SessionRecord:
    raw_session = value["session"]
    raw_active_proof = raw_session["active_proof"]
    session = ViewingSession(
        session_id=raw_session["session_id"],
        owner_user_id=raw_session["owner_user_id"],
        state=SessionState(raw_session["state"]),
        active_penalty=(
            PenaltyType(raw_session["active_penalty"])
            if raw_session["active_penalty"]
            else None
        ),
        penalty_window_opened_at=_date_from_optional(
            raw_session["penalty_window_opened_at"]
        ),
        penalty_window_closes_at=_date_from_optional(
            raw_session["penalty_window_closes_at"]
        ),
        active_proof=(
            ProofSubmission(
                proof_id=raw_active_proof["proof_id"],
                image_key=raw_active_proof["image_key"],
            )
            if raw_active_proof
            else None
        ),
    )
    return SessionRecord(
        session=session,
        controller_user_id=value["controller_user_id"],
        default_penalty=PenaltyType(value["default_penalty"]),
        member_user_ids=frozenset(value["member_user_ids"]),
        created_at=datetime.fromisoformat(value["created_at"]),
        updated_at=datetime.fromisoformat(value["updated_at"]),
        proofs=[
            ProofRecord(
                proof=ProofSubmission(
                    proof_id=raw_proof["proof"]["proof_id"],
                    image_key=raw_proof["proof"]["image_key"],
                ),
                submitted_at=datetime.fromisoformat(raw_proof["submitted_at"]),
                analysis=(
                    AIAnalysis.from_dict(raw_proof["analysis"])
                    if raw_proof["analysis"]
                    else None
                ),
            )
            for raw_proof in value["proofs"]
        ],
        audit_events=[
            AuditEvent(
                event_id=raw_event["event_id"],
                session_id=raw_event["session_id"],
                actor_user_id=raw_event["actor_user_id"],
                action=raw_event["action"],
                occurred_at=datetime.fromisoformat(raw_event["occurred_at"]),
                details=raw_event["details"],
            )
            for raw_event in value["audit_events"]
        ],
    )


def _analysis_to_dict(analysis: AIAnalysis | None) -> dict[str, Any] | None:
    if analysis is None:
        return None
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


def _date_or_none(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _date_from_optional(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None
