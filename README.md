# Recycle_Bot
Learn how to recycle anything! Upload an image, add your location and silly personality, and get a response straight from GPT.

Note: using a .jpg or .png image is recommended. Limited file conversion is implemented, but not all file types are supported.

## Setup
- Configure an OpenAI API key for Recycle_Bot.
  - For local development, set `OPENAI_API_KEY` in your shell environment or enter a key in the app UI.
  - For Render, add `OPENAI_API_KEY` as an environment variable on the web service and redeploy.
  - Users can still enter their own optional key in the UI; if they leave it blank, the server-side key is used.
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
- Upload images and receive realtime responses from GPT-4o
  - Plug-in support for other models is available by editing defaults.py
- Adaptive location to tailor instructions to local recycling programs
- Customizable personality with continued accuracy
- Robust hand-crafted prompt, keeping responses concise and helpful (even with absurd or malicious parameters)
- Structured OpenAI API responses replace brittle bracket parsing for answer, object, and disposal details
- Dynamic prompting template, avoiding hardcoded settings
- Vision API token optimization to ~300 per check

### Quality of Life Upgrades
- Optional GUI input for users who want to bring their own API key
- Uses a server-side `OPENAI_API_KEY` environment variable when no user key is provided
- Saves optional API key and settings for future use
- Support for .jpg and .png images, with limited support for converting other file types
- Popup sidebar menu for settings input

### Security protections
- Simple prompt protection against malicious injection attacks 
- Limited error handling
- Debugging and cost quantification system enabling token and cost tracking (currently disabled to avoid UI clutter)
