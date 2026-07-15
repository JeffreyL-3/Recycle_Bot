# Recycle_Bot

Recycle_Bot identifies an item from an uploaded image and provides location-aware recycling or disposal guidance.

## Requirements

- Python 3
- An OpenAI API key supplied through the app or a server-side `OPENAI_API_KEY`
- An optional server-side `GOOGLE_MAPS_API_KEY` for device-location autofill

Users can enter an optional custom API key in the app. It is saved in browser-local storage and used for that browser's requests. If the field is empty, the application uses the server-side `OPENAI_API_KEY`.

If OpenAI rejects a custom key with an authentication error, the app asks the user to update it or clear the field. It does not silently retry with the server key. After the custom field is cleared, subsequent requests use the server-side `OPENAI_API_KEY` when it is configured.

## Setup

1. Create a virtual environment:
   - Windows: `python -m venv openai-env`
   - macOS/Linux: `python3 -m venv openai-env`
2. Activate it:
   - Windows: `openai-env\Scripts\activate`
   - macOS/Linux: `source openai-env/bin/activate`
3. Install dependencies: `pip install --upgrade -r requirements.txt`
4. Set `OPENAI_API_KEY` in the server environment to provide the default key.
5. Optionally set `GOOGLE_MAPS_API_KEY` and enable the Google Geocoding API.
6. Run the application: `python app.py`

For Render, configure the environment variables on the web service and redeploy. Restrict the Google key to the Geocoding API and configure provider-side quotas.

## Models and API compatibility

The model picker supports:

- `gpt-4o` (default)
- `gpt-5.6-luna`, using `reasoning_effort: "low"` and `verbosity: "low"`

The application intentionally keeps the existing Chat Completions integration. Requests use Structured Outputs, `max_completion_tokens`, and Base64 data URLs whose media type is detected from the uploaded bytes. Supported image inputs are JPEG, PNG, WebP, and non-animated GIF. Unknown model values fall back to `gpt-4o`.

The in-code cost estimate uses standard token rates and does not apply cached-input discounts, cache-write charges, regional uplifts, or alternate service-tier pricing.

## Features

- Upload an image or capture a photo
- Choose GPT-4o or GPT-5.6 Luna
- Add a town and state manually or through device-location autofill
- Customize the response personality
- Receive schema-validated answers, identified objects, and disposal instructions
- Persist the optional custom API key, town, state, and personality locally in the browser
- Reject unsupported image signatures before calling OpenAI
- Rate-limit server-side reverse-geocoding requests

## Verification

Run the automated checks from the repository root:

```bash
openai-env/bin/python -m unittest discover -s tests -v
openai-env/bin/python -m compileall -q app.py defaults.py engine.py interface.py tests
node --check static/script.js
```

The tests mock OpenAI network requests; they validate request payloads without using a live API key or incurring API charges.
