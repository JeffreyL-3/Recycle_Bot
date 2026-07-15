import base64
import os
import tempfile
import unittest
from unittest.mock import Mock, patch

import defaults
import engine


class EngineCompatibilityTests(unittest.TestCase):
    def make_image(self, contents, suffix):
        image = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
        self.addCleanup(lambda: os.path.exists(image.name) and os.unlink(image.name))
        image.write(contents)
        image.close()
        return image.name

    def successful_response(self):
        response = Mock(status_code=200)
        response.json.return_value = {
            "choices": [{
                "finish_reason": "stop",
                "message": {
                    "content": '{"answer":"Yes","object":"bottle","details":"Recycle it."}'
                }
            }],
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 20,
                "total_tokens": 120
            }
        }
        return response

    @patch("engine.requests.post")
    def test_luna_payload_uses_low_reasoning_and_png_media_type(self, post):
        png_bytes = b"\x89PNG\r\n\x1a\n" + b"test-png-data"
        image_path = self.make_image(png_bytes, ".png")
        post.return_value = self.successful_response()

        result = engine.query_recycling_info(
            image_path,
            "Boston",
            "MA",
            api_key="test-key",
            model="gpt-5.6-luna"
        )

        self.assertIsInstance(result, dict)
        request = post.call_args
        payload = request.kwargs["json"]
        image_url = payload["messages"][1]["content"][1]["image_url"]["url"]

        self.assertEqual(payload["model"], "gpt-5.6-luna")
        self.assertEqual(payload["reasoning_effort"], "low")
        self.assertEqual(payload["max_completion_tokens"], 4000)
        self.assertNotIn("max_tokens", payload)
        self.assertEqual(payload["response_format"], engine.RECYCLING_RESPONSE_FORMAT)
        self.assertEqual(
            payload["messages"][1]["content"][1]["image_url"]["detail"],
            "low"
        )
        self.assertEqual(
            image_url,
            "data:image/png;base64," + base64.b64encode(png_bytes).decode("utf-8")
        )
        self.assertEqual(request.kwargs["timeout"], 60)

    def test_webp_media_type_is_detected_from_bytes(self):
        image_path = self.make_image(b"RIFF\x04\x00\x00\x00WEBPtest", ".webp")
        self.assertEqual(engine.get_image_media_type(image_path), "image/webp")

    @patch("engine.requests.post")
    def test_gpt_4o_payload_remains_non_reasoning_and_detects_jpeg(self, post):
        jpeg_bytes = b"\xff\xd8\xff\xe0" + b"test-jpeg-data"
        image_path = self.make_image(jpeg_bytes, ".jpg")
        post.return_value = self.successful_response()

        engine.query_recycling_info(image_path, "", "", api_key="test-key", model="gpt-4o")

        payload = post.call_args.kwargs["json"]
        image_url = payload["messages"][1]["content"][1]["image_url"]["url"]
        self.assertNotIn("reasoning_effort", payload)
        self.assertEqual(payload["max_completion_tokens"], 1000)
        self.assertTrue(image_url.startswith("data:image/jpeg;base64,"))

    @patch("engine.requests.post")
    def test_server_environment_key_is_used(self, post):
        image_path = self.make_image(b"GIF89a" + b"test-gif-data", ".gif")
        post.return_value = self.successful_response()

        with patch.dict(os.environ, {"OPENAI_API_KEY": "server-key"}):
            engine.query_recycling_info(image_path, "", "", model="gpt-5.6-luna")

        self.assertEqual(post.call_args.kwargs["headers"]["Authorization"], "Bearer server-key")

    @patch("engine.requests.post")
    def test_invalid_image_is_rejected_before_api_call(self, post):
        image_path = self.make_image(b"not-an-image", ".jpg")

        result = engine.query_recycling_info(
            image_path,
            "",
            "",
            api_key="test-key",
            model="gpt-5.6-luna"
        )

        self.assertEqual(result, "Error code 13: Unsupported image format")
        post.assert_not_called()

    @patch("engine.requests.post")
    def test_request_failure_returns_api_error(self, post):
        image_path = self.make_image(b"\xff\xd8\xff\xe0" + b"test-jpeg-data", ".jpg")
        post.side_effect = engine.requests.RequestException("network unavailable")

        result = engine.query_recycling_info(
            image_path,
            "",
            "",
            api_key="test-key",
            model="gpt-5.6-luna"
        )

        self.assertEqual(result, "Error code 11: Error in API call")

    @patch("engine.requests.post")
    def test_invalid_success_response_returns_api_error(self, post):
        image_path = self.make_image(b"\xff\xd8\xff\xe0" + b"test-jpeg-data", ".jpg")
        response = Mock(status_code=200)
        response.json.side_effect = ValueError("invalid JSON")
        post.return_value = response

        result = engine.query_recycling_info(
            image_path,
            "",
            "",
            api_key="test-key",
            model="gpt-5.6-luna"
        )

        self.assertEqual(result, "Error code 11: Error in API call")

    @patch("engine.requests.post")
    def test_rejected_custom_key_returns_actionable_error(self, post):
        image_path = self.make_image(b"\xff\xd8\xff\xe0" + b"test-jpeg-data", ".jpg")
        post.return_value = Mock(status_code=401)

        result = engine.query_recycling_info(
            image_path,
            "",
            "",
            api_key="rejected-key",
            model="gpt-5.6-luna"
        )

        self.assertEqual(
            result,
            "Error code 14: custom OpenAI API key was rejected"
        )
        answer, detected_object, details = engine.separate_answer_and_details(result)
        self.assertEqual(answer, result)
        self.assertEqual(detected_object, "this")
        self.assertEqual(
            details,
            "Your custom OpenAI API key was rejected. Update it, or clear the field to use the server key."
        )

    @patch("engine.requests.post")
    def test_rejected_server_key_returns_server_configuration_error(self, post):
        image_path = self.make_image(b"\xff\xd8\xff\xe0" + b"test-jpeg-data", ".jpg")
        post.return_value = Mock(status_code=401)

        with patch.dict(os.environ, {"OPENAI_API_KEY": "rejected-server-key"}):
            result = engine.query_recycling_info(
                image_path,
                "",
                "",
                model="gpt-5.6-luna"
            )

        self.assertEqual(
            result,
            "Error code 14: server OpenAI API key was rejected"
        )
        answer, detected_object, details = engine.separate_answer_and_details(result)
        self.assertEqual(answer, result)
        self.assertEqual(detected_object, "this")
        self.assertEqual(
            details,
            "The server OPENAI_API_KEY was rejected. Check the server configuration."
        )

    def test_supported_model_selection_and_costs(self):
        self.assertEqual(defaults.getModel("gpt-5.6-luna"), "gpt-5.6-luna")
        self.assertEqual(defaults.getModel("unknown"), defaults.getDefaultModel())
        self.assertAlmostEqual(engine.getCost(1_000_000, 1_000_000, "gpt-5.6-luna"), 7.0)
        self.assertAlmostEqual(engine.getCost(1_000_000, 1_000_000, "gpt-4o"), 12.5)


if __name__ == "__main__":
    unittest.main()
