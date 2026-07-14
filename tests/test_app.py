import io
import tempfile
import unittest
from unittest.mock import patch

import app as app_module


class ProcessRouteTests(unittest.TestCase):
    def setUp(self):
        self.upload_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.upload_directory.cleanup)
        self.original_upload_folder = app_module.app.config['UPLOAD_FOLDER']
        self.addCleanup(
            lambda: app_module.app.config.update(
                UPLOAD_FOLDER=self.original_upload_folder
            )
        )
        app_module.app.config.update(
            TESTING=True,
            UPLOAD_FOLDER=self.upload_directory.name
        )
        self.client = app_module.app.test_client()

    @patch("app.simple_output")
    def test_process_passes_luna_model_without_accepting_browser_key(self, simple_output):
        simple_output.return_value = (
            2,
            "bottle",
            "Is this bottle recyclable? Yes!",
            "Place it in the recycling bin."
        )

        response = self.client.post(
            "/process",
            data={
                "image": (io.BytesIO(b"\x89PNG\r\n\x1a\nimage"), "item.png"),
                "town": "Boston",
                "state": "MA",
                "object": "bottle",
                "personality": "friendly",
                "model": "gpt-5.6-luna",
                "api_key": "browser-key-must-be-ignored"
            },
            content_type="multipart/form-data"
        )

        self.assertEqual(response.status_code, 200)
        call = simple_output.call_args
        self.assertEqual(call.args[1:], ("Boston", "MA", "bottle", "friendly"))
        self.assertEqual(call.kwargs, {"model": "gpt-5.6-luna"})

    @patch("app.simple_output")
    def test_process_falls_back_to_default_model(self, simple_output):
        simple_output.return_value = (2, "bottle", "Yes", "Recycle it.")

        response = self.client.post(
            "/process",
            data={
                "image": (io.BytesIO(b"RIFF\x04\x00\x00\x00WEBPimage"), "item.webp"),
                "model": "unsupported-model"
            },
            content_type="multipart/form-data"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            simple_output.call_args.kwargs,
            {"model": app_module.defaults.getDefaultModel()}
        )

    def test_process_rejects_missing_image(self):
        response = self.client.post("/process", data={"model": "gpt-5.6-luna"})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json(), {"error": "Invalid file format"})


if __name__ == "__main__":
    unittest.main()
