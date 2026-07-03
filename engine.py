import key
import base64
import requests
import json
import defaults

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
    
def numTokens(response):
    # Check if the response has 'usage' key
    if 'usage' in response:
        # Extracting prompt_tokens and completion_tokens
        prompt_tokens = response['usage']['prompt_tokens']
        completion_tokens = response['usage']['completion_tokens']
        total_tokens = prompt_tokens+completion_tokens
    else:
        # Default values if 'usage' key is not present
        prompt_tokens, completion_tokens, total_tokens = -1, -1, -2

    return prompt_tokens, completion_tokens, total_tokens

def getCost(prompt_tokens, completion_tokens):
    return (prompt_tokens*0.01/1000) + (completion_tokens*0.03/1000)

# Gets recycling info 
def query_recycling_info(image_path, town, state, object=defaults.getDefaultObject(), personality=defaults.getDefaultPersonality()):
    
    # Final check to force default on empty strings
    if(object==''):
        object = defaults.getDefaultObject()
    if(personality==''):
        personality = defaults.getDefaultPersonality()  
    
    print('Loading...')
    print(personality)
    # OpenAI API Key
    api_key = key.getKey()

    # Combine town and state
    if(town != '' and state !=''):
        combinedLocation = ' in ' + town + ',' + state
    else:
        combinedLocation=''

    # Getting the base64 string
    base64_image = encode_image(image_path)

    # Setup headers
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    # Setup payload
    payload = {
        #Allows image uploads
        "model": defaults.getDefaultModel(), 
        
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
                            "url": f"data:image/jpeg;base64,{base64_image}",
                            
                            #Compresses image to optimize token usage
                            "detail":"low"
                        }
                    }
                ]
            }
        ],
        "response_format": RECYCLING_RESPONSE_FORMAT,
        #Hard cap on token usage (near impossible to reach). About $0.01 - $0.03
        "max_tokens": 1000
    }

    # Send request
    response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)

    # Process response
    if response.status_code == 200:
        raw_response = response.json()
        return raw_response

    else:
        print(str(response))
        return "Error code 11: Error in API call"
    
# Parses the structured JSON response. Expects answer, object, and details.
def separate_answer_and_details(combined_response):
    print(combined_response)

    textResponse = str(combined_response)

    if("Error code" in textResponse):
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
