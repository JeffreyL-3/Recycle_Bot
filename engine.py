import base64
import os
import requests
import json
import defaults

MODEL_TOKEN_COSTS_PER_MILLION = {
    "gpt-4o": (2.50, 10.00),
    "gpt-5.6-luna": (1.00, 6.00),
}

RECYCLING_RESPONSE_FORMAT = {
    "type": "json_schema",
    "json_schema": {
        "name": "recycling_answer",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "answer": {
                    "type": "string",
                    "description": "Whether the object is recyclable.",
                    "enum": ["Yes", "Yes, but...", "No."]
                },
                "object": {
                    "type": "string",
                    "description": "The identified object in the uploaded image."
                },
                "details": {
                    "type": "string",
                    "description": "Brief, accurate disposal or recycling instructions."
                }
            },
            "required": ["answer", "object", "details"],
            "additionalProperties": False
        }
    }
}

# Function to encode the image
def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def get_image_media_type(image_path):
    """Detect an OpenAI-supported image type from the file signature."""
    with open(image_path, "rb") as image_file:
        header = image_file.read(12)

    if header.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if header.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif"
    if header.startswith(b"RIFF") and header[8:12] == b"WEBP":
        return "image/webp"

    raise ValueError("Unsupported image format")
    
def numTokens(response):
    # Check if the response has 'usage' key
    if 'usage' in response:
        # Extracting prompt_tokens and completion_tokens
        prompt_tokens = response['usage']['prompt_tokens']
        completion_tokens = response['usage']['completion_tokens']
        total_tokens = prompt_tokens+completion_tokens
    else:
        # Default values if 'usage' key is not present
        prompt_tokens, completion_tokens, total_tokens = 0, 0, 0

    return prompt_tokens, completion_tokens, total_tokens

def getCost(prompt_tokens, completion_tokens, model=defaults.getDefaultModel()):
    """Return token cost for a supported model, excluding cached-input discounts."""
    model = defaults.getModel(model)
    input_cost, output_cost = MODEL_TOKEN_COSTS_PER_MILLION[model]
    return (
        prompt_tokens * input_cost / 1_000_000
        + completion_tokens * output_cost / 1_000_000
    )

def get_openai_api_key(user_api_key=None):
    user_api_key = (user_api_key or "").strip()
    if user_api_key:
        return user_api_key

    return os.environ.get("OPENAI_API_KEY", "").strip()

# Gets recycling info
def query_recycling_info(image_path, town, state, object=defaults.getDefaultObject(), personality=defaults.getDefaultPersonality(), api_key=None, model=defaults.getDefaultModel()):
    
    # Final check to force default on empty strings
    if(object==''):
        object = defaults.getDefaultObject()
    if(personality==''):
        personality = defaults.getDefaultPersonality()
    model = defaults.getModel(model)
    
    print('Loading...')
    print(personality)
    using_custom_api_key = bool((api_key or "").strip())
    api_key = get_openai_api_key(api_key)
    if not api_key:
        return "Error code 12: OpenAI API key is not configured"

    # Combine town and state
    if(town != '' and state !=''):
        combinedLocation = ' in ' + town + ',' + state
    else:
        combinedLocation=''

    # Build a data URL whose media type matches the uploaded image bytes.
    try:
        image_media_type = get_image_media_type(image_path)
        base64_image = encode_image(image_path)
    except (OSError, ValueError):
        return "Error code 13: Unsupported image format"

    # Setup headers
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    # Setup payload
    payload = {
        #Allows image uploads
        "model": model,
        
        #Prompt
        "messages": [
            {
                # Most of the prompt is included here because GPT4 tends to adhere to answer format (which includes personality) better in the dedicated system role, rather than the user prompt
                "role": "system", "content": "You are a helpful local waste management director" + combinedLocation + " helping others decide if their object is recyclable. Phrase your recycling instructions in the style of " + personality + " while maintaining complete accuracy.",
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Is this " + object + " recyclable" + combinedLocation + "? Classify the answer as exactly one of: \"Yes\", \"Yes, but...\", or \"No.\" Identify the object and give concise disposal or recycling instructions.",
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{image_media_type};base64,{base64_image}",
                            
                            #Compresses image to optimize token usage
                            "detail":"low"
                        }
                    }
                ]
            }
        ],
        "response_format": RECYCLING_RESPONSE_FORMAT,
        "max_completion_tokens": 4000 if model == "gpt-5.6-luna" else 1000
    }

    if model == "gpt-5.6-luna":
        payload["reasoning_effort"] = "low"

    # Send request
    try:
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=60
        )
    except requests.RequestException:
        return "Error code 11: Error in API call"

    # Process response
    if response.status_code == 200:
        try:
            return response.json()
        except ValueError:
            return "Error code 11: Error in API call"

    else:
        print("OpenAI API error: " + str(response.status_code))
        if response.status_code == 401:
            key_source = "custom" if using_custom_api_key else "server"
            return "Error code 14: " + key_source + " OpenAI API key was rejected"
        return "Error code 11: Error in API call"
    
# Parses the structured JSON response. Expects answer, object, and details.
def separate_answer_and_details(combined_response):
    print(combined_response)

    textResponse = str(combined_response)

    if("Error code" in textResponse):
        if "Error code 12" in textResponse:
            return str(textResponse), "this", "Add OPENAI_API_KEY on Render, or enter your own API key in the optional field."
        if "Error code 14" in textResponse:
            if "custom OpenAI API key" in textResponse:
                return str(textResponse), "this", "Your custom OpenAI API key was rejected. Update it, or clear the field to use the server key."
            return str(textResponse), "this", "The server OPENAI_API_KEY was rejected. Check the server configuration."
        return str(textResponse), "this", "This is probably because you took a photo of something the program didn't expect."

    try:
        structured_response = combined_response if isinstance(combined_response, dict) else json.loads(textResponse)
    except json.JSONDecodeError:
        return "Error code 31: Structured response could not be parsed", "this", "The model did not return valid structured JSON."

    try:
        answer = structured_response["answer"]
        object = structured_response["object"]
        details = structured_response["details"]
    except KeyError:
        return "Error code 32: Structured response missing required field", "this", "The model response was missing expected recycling details."

    return answer, object, details

def extract_message(json_response):
    if isinstance(json_response, str) and "Error code" in json_response:
        return json_response

    # Navigate through the JSON structure to extract the message content
    # Assuming 'json_response' is the JSON object you provided
    if not isinstance(json_response, dict):
        return "Error code 20: API response was not valid JSON"

    if 'choices' in json_response and json_response['choices']:
        first_choice = json_response['choices'][0]
        if first_choice.get('finish_reason') == "content_filter":
            return "Error code 24: Response blocked by content filter"
        if 'message' in first_choice:
            message = first_choice['message']
            if message.get('refusal'):
                return "Error code 23: " + str(message['refusal'])
            if 'content' in message and message['content']:
                return message['content']
            return "Error code 21: Message content not found"
        else:
            return "Error code 21: Message content not found"
    else:
        return "Error code 22: Choices not found in response"
