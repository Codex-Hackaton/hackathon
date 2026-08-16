from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from fastapi.testclient import TestClient

from penalty_app.api import create_app
from penalty_app.storage import LocalProofStorage
from penalty_app.vlm import DeterministicDemoVLM


class OFFMateAPITests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = TemporaryDirectory()
        self.client = TestClient(
            create_app(
                storage=LocalProofStorage(Path(self.temp_dir.name)),
                vlm_client=DeterministicDemoVLM(),
            )
        )

    def tearDown(self) -> None:
        self.client.close()
        self.temp_dir.cleanup()

    def test_book_photo_completes_the_end_to_end_session(self) -> None:
        session = self._create_and_activate_session()
        session_id = session["session_id"]
        controller_id = session["controller_user_id"]

        forbidden = self.client.post(
            f"/v1/sessions/{session_id}/penalties",
            headers=self._headers("user_a", "owner-penalty-1"),
            json={"penalty": "MUTED"},
        )
        self.assertEqual(forbidden.status_code, 403)

        selected = self.client.post(
            f"/v1/sessions/{session_id}/penalties",
            headers=self._headers(controller_id, "friend-penalty-1"),
            json={"penalty": "MUTED"},
        )
        self.assertEqual(selected.status_code, 200)
        self.assertEqual(selected.json()["active_penalty"], "MUTED")

        image_key = self._upload_image(b"book sample image")
        proof = self.client.post(
            f"/v1/sessions/{session_id}/proofs",
            headers=self._headers("user_a", "proof-submit-001"),
            json={"image_key": image_key},
        )
        self.assertEqual(proof.status_code, 201)

        analyzed = self.client.post(
            f"/v1/sessions/{session_id}/analyze",
            headers=self._headers("user_a", "proof-analyze-01"),
        )
        self.assertEqual(analyzed.status_code, 200)
        self.assertEqual(analyzed.json()["analysis"]["decision"], "PASS")
        self.assertEqual(analyzed.json()["session"]["state"], "COMPLETED")
        self.assertIsNone(analyzed.json()["session"]["active_penalty"])

    def test_unclear_photo_requires_only_the_selected_friend(self) -> None:
        session = self._create_and_activate_session()
        session_id = session["session_id"]
        controller_id = session["controller_user_id"]
        image_key = self._upload_image(b"ambiguous sample")

        submitted = self.client.post(
            f"/v1/sessions/{session_id}/proofs",
            headers=self._headers("user_a", "proof-submit-002"),
            json={"image_key": image_key},
        )
        self.assertEqual(submitted.status_code, 201)

        analyzed = self.client.post(
            f"/v1/sessions/{session_id}/analyze",
            headers=self._headers("user_a", "proof-analyze-02"),
        )
        self.assertEqual(analyzed.json()["session"]["state"], "HUMAN_REVIEW")

        outsider = self.client.post(
            f"/v1/sessions/{session_id}/review",
            headers=self._headers("user_outsider", "outsider-review1"),
            json={"passed": True},
        )
        self.assertEqual(outsider.status_code, 403)

        approved = self.client.post(
            f"/v1/sessions/{session_id}/review",
            headers=self._headers(controller_id, "controller-review"),
            json={"passed": True},
        )
        self.assertEqual(approved.status_code, 200)
        self.assertEqual(approved.json()["state"], "COMPLETED")

    def test_ai_fail_cannot_be_overridden_by_friend_review(self) -> None:
        session = self._create_and_activate_session()
        session_id = session["session_id"]
        controller_id = session["controller_user_id"]
        image_key = self._upload_image(b"game sample image")
        self.client.post(
            f"/v1/sessions/{session_id}/proofs",
            headers=self._headers("user_a", "proof-submit-003"),
            json={"image_key": image_key},
        )

        analyzed = self.client.post(
            f"/v1/sessions/{session_id}/analyze",
            headers=self._headers("user_a", "proof-analyze-03"),
        )
        self.assertEqual(analyzed.json()["analysis"]["decision"], "FAIL")
        self.assertEqual(analyzed.json()["session"]["state"], "PENALTY_ACTIVE")

        override = self.client.post(
            f"/v1/sessions/{session_id}/review",
            headers=self._headers(controller_id, "friend-override1"),
            json={"passed": True},
        )
        self.assertEqual(override.status_code, 409)

    def test_idempotency_key_replays_and_rejects_a_different_payload(self) -> None:
        headers = self._headers("user_a", "create-replay-01")
        first = self.client.post(
            "/v1/sessions",
            headers=headers,
            json={"active_member_ids": ["user_b"], "default_penalty": "BLOCK"},
        )
        replay = self.client.post(
            "/v1/sessions",
            headers=headers,
            json={"active_member_ids": ["user_b"], "default_penalty": "BLOCK"},
        )
        conflict = self.client.post(
            "/v1/sessions",
            headers=headers,
            json={"active_member_ids": ["user_b"], "default_penalty": "MUTED"},
        )

        self.assertEqual(first.status_code, 201)
        self.assertEqual(replay.status_code, 201)
        self.assertEqual(first.json()["session_id"], replay.json()["session_id"])
        self.assertEqual(conflict.status_code, 409)

    def test_friend_session_response_contains_no_usage_history(self) -> None:
        session = self._create_and_activate_session()
        response = self.client.get(
            f"/v1/sessions/{session['session_id']}",
            headers={"X-User-ID": session["controller_user_id"]},
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("usage", response.json())
        self.assertNotIn("screen", response.json())

    def _create_and_activate_session(self) -> dict[str, object]:
        created = self.client.post(
            "/v1/sessions",
            headers=self._headers("user_a", "create-session1"),
            json={
                "active_member_ids": ["user_b"],
                "default_penalty": "BLOCK",
            },
        )
        self.assertEqual(created.status_code, 201)
        session_id = created.json()["session_id"]

        started = self.client.post(
            f"/v1/sessions/{session_id}/start",
            headers=self._headers("user_a", "start-session01"),
        )
        self.assertEqual(started.status_code, 200)

        ended = self.client.post(
            f"/v1/sessions/{session_id}/end",
            headers=self._headers("user_a", "end-session-001"),
        )
        self.assertEqual(ended.status_code, 200)
        self.assertEqual(ended.json()["state"], "PENALTY_ACTIVE")
        self.assertEqual(ended.json()["active_penalty"], "BLOCK")
        return ended.json()

    def _upload_image(self, payload: bytes) -> str:
        slot = self.client.post(
            "/v1/upload-slots",
            headers=self._headers("user_a", f"upload-slot-{len(payload):03d}"),
            json={"content_type": "image/jpeg"},
        )
        self.assertEqual(slot.status_code, 201)
        upload = self.client.put(
            slot.json()["upload_url"],
            headers={"Content-Type": "image/jpeg"},
            content=payload,
        )
        self.assertEqual(upload.status_code, 204)
        return slot.json()["image_key"]

    @staticmethod
    def _headers(user_id: str, idempotency_key: str) -> dict[str, str]:
        return {
            "X-User-ID": user_id,
            "Idempotency-Key": idempotency_key,
        }


if __name__ == "__main__":
    unittest.main()
