# Recycle_Bot
Learn how to recycle anything! Upload an image, add your location and silly personality, and get a response straight from GPT.

Supported image uploads are JPEG, PNG, WebP, and non-animated GIF.

## Setup
- Configure an OpenAI API key for Recycle_Bot.
  - For local development, set `OPENAI_API_KEY` in your shell environment or enter a key in the app UI.
  - For Render, add `OPENAI_API_KEY` as an environment variable on the web service and redeploy.
  - Users can still enter their own optional key in the UI; if they leave it blank, the server-side key is used.
- Configure a Google Maps API key for device location autofill.
  - Enable the Google Geocoding API in Google Cloud.
  - Set `GOOGLE_MAPS_API_KEY` in your local shell or Render environment variables.
  - Restrict the key to the Geocoding API and set Google-side quota limits to control costs.
- Setup a virtual environment
  - Windows: run ```python -m venv openai-env``` in the main directory
  - Mac: run ```python3 -m venv openai-env``` in the main directory
- After you've created a virtual environment, activate it with one of the following
  - Windows: ```openai-env\Scripts\activate```
  - Mac: ```source openai-env/bin/activate```
- Install dependencies
  - Run ```pip install --upgrade -r requirements.txt```
- Run app.py to load Recycle_Bot!
## Recycle_Bot Features
### Basic Functions
- Upload images and receive realtime responses from GPT-4o or GPT-5.6 Luna
  - GPT-5.6 Luna uses low reasoning effort for a faster, lower-cost classification path
- Adaptive location to tailor instructions to local recycling programs
- Customizable personality with continued accuracy
- Robust hand-crafted prompt, keeping responses concise and helpful (even with absurd or malicious parameters)
- Structured OpenAI API responses replace brittle bracket parsing for answer, object, and disposal details
- Dynamic prompting template, avoiding hardcoded settings
- Vision API token optimization to ~300 per check

### Quality of Life Upgrades
- Optional GUI input for users who want to bring their own API key
- Uses a server-side `OPENAI_API_KEY` environment variable when no user key is provided
- Saves the optional API key, town, state, and personality in browser-local storage as they are edited; delete a field's value to clear it
- Autofills town and state from device location when `GOOGLE_MAPS_API_KEY` is configured
- Correctly encoded JPEG, PNG, WebP, and non-animated GIF image inputs
- Popup sidebar menu for settings input

### Security protections
- Simple prompt protection against malicious injection attacks
- Rate-limited server-side geocoding proxy for device location lookup
- Limited error handling
- Debugging and cost quantification system enabling token and cost tracking (currently disabled to avoid UI clutter)
