import json
import unittest
from unittest.mock import patch
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory

from penalty_app.ai_analysis import AIAnalysis, AIAnalysisValidationError
from penalty_app.domain import AIAnalysisDecision
from penalty_app.vlm import (
    RunPodVLMClient,
    VLMUnavailableError,
    _normalized_image_data_url,
)


def valid_analysis() -> dict[str, object]:
    return {
        "analysis_id": "analysis_123",
        "detected_activities": [
            {
                "activity_id": "reading_book",
                "confidence": 0.93,
                "visual_evidence": ["open book", "user looking at pages"],
            }
        ],
        "decision": "PASS",
        "decision_confidence": 0.91,
        "matched_policy_ids": ["policy_self_development"],
        "reason": "The image provides evidence of reading.",
        "requires_human_review": False,
    }


class AIAnalysisTests(unittest.TestCase):
    def test_accepts_a_contract_compliant_response(self) -> None:
        analysis = AIAnalysis.from_json(json.dumps(valid_analysis()))
        self.assertEqual(analysis.decision, AIAnalysisDecision.PASS)
        self.assertEqual(analysis.detected_activities[0].activity_id, "reading_book")

    def test_rejects_an_unknown_activity(self) -> None:
        payload = valid_analysis()
        payload["detected_activities"][0]["activity_id"] = "go_to_the_gym"

        with self.assertRaises(AIAnalysisValidationError):
            AIAnalysis.from_dict(payload)

    def test_rejects_an_unlock_action_injected_into_the_response(self) -> None:
        payload = valid_analysis()
        payload["action"] = "unlock"

        with self.assertRaises(AIAnalysisValidationError):
            AIAnalysis.from_dict(payload)

    def test_human_review_flag_must_match_the_decision(self) -> None:
        payload = valid_analysis()
        payload["decision"] = "HUMAN_REVIEW"

        with self.assertRaises(AIAnalysisValidationError):
            AIAnalysis.from_dict(payload)


class RunPodVLMClientTests(unittest.TestCase):
    def test_uses_openai_vlm_contract_then_applies_backend_policy(self) -> None:
        response_payload = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "activity_id": "reading_book",
                                "confidence": 0.93,
                                "visual_evidence": ["open book"],
                            }
                        )
                    }
                }
            ]
        }
        response = _FakeHTTPResponse(json.dumps(response_payload).encode("utf-8"))

        with TemporaryDirectory() as directory:
            image_path = Path(directory) / "proof.jpg"
            image_path.write_bytes(b"image")
            with patch("penalty_app.vlm.urlopen", return_value=response) as mocked:
                analysis = RunPodVLMClient(
                    endpoint_url=(
                        "https://api.runpod.ai/v2/endpoint/openai/v1/chat/completions"
                    ),
                    api_key="secret",
                ).analyze(image_path=image_path)

        request = mocked.call_args.args[0]
        request_body = json.loads(request.data.decode("utf-8"))
        self.assertEqual(request.get_header("Authorization"), "Bearer secret")
        self.assertEqual(request_body["model"], "Qwen/Qwen2.5-VL-3B-Instruct")
        image_url = request_body["messages"][1]["content"][0]["image_url"]["url"]
        self.assertTrue(image_url.startswith("data:image/jpeg;base64,"))
        self.assertEqual(analysis.decision, AIAnalysisDecision.PASS)

    def test_model_cannot_inject_a_decision(self) -> None:
        response_payload = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "activity_id": "playing_video_game",
                                "confidence": 0.99,
                                "visual_evidence": ["game screen"],
                                "decision": "PASS",
                            }
                        )
                    }
                }
            ]
        }
        response = _FakeHTTPResponse(json.dumps(response_payload).encode("utf-8"))
        with TemporaryDirectory() as directory:
            image_path = Path(directory) / "proof.jpg"
            image_path.write_bytes(b"image")
            with patch("penalty_app.vlm.urlopen", return_value=response):
                analysis = RunPodVLMClient(
                    endpoint_url=(
                        "https://api.runpod.ai/v2/endpoint/openai/v1/chat/completions"
                    ),
                    api_key="secret",
                ).analyze(image_path=image_path)

        self.assertEqual(analysis.decision, AIAnalysisDecision.HUMAN_REVIEW)

    def test_large_photo_is_normalized_before_upload(self) -> None:
        try:
            from PIL import Image
        except ImportError:
            self.skipTest("Pillow is not installed")

        with TemporaryDirectory() as directory:
            image_path = Path(directory) / "camera.png"
            Image.new("RGB", (2400, 1600), color=(240, 240, 240)).save(image_path)
            data_url = _normalized_image_data_url(image_path)

        self.assertTrue(data_url.startswith("data:image/jpeg;base64,"))
        encoded = data_url.split(",", 1)[1]
        normalized = Image.open(BytesIO(__import__("base64").b64decode(encoded)))
        self.assertLessEqual(max(normalized.size), 768)

    def test_non_completed_runpod_job_is_not_accepted(self) -> None:
        response = _FakeHTTPResponse(
            json.dumps({"id": "job_1", "status": "IN_QUEUE"}).encode("utf-8")
        )
        with TemporaryDirectory() as directory:
            image_path = Path(directory) / "proof.jpg"
            image_path.write_bytes(b"image")
            with patch("penalty_app.vlm.urlopen", return_value=response):
                with self.assertRaises(VLMUnavailableError):
                    RunPodVLMClient(
                        endpoint_url="https://api.runpod.ai/v2/endpoint/runsync",
                        api_key="secret",
                    ).analyze(image_path=image_path)


class _FakeHTTPResponse(BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()


if __name__ == "__main__":
    unittest.main()
