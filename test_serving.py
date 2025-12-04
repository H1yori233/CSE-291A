import openai
import base64
import os
import requests

# Configuration matching launch_serving.sh
API_URL = "http://localhost:8000/v1"
MODEL_NAME = "Qwen/Qwen3-VL-8B-Instruct"
API_KEY = "EMPTY"

def test_api():
    print(f"Testing API at {API_URL} with model {MODEL_NAME}...")
    
    client = openai.OpenAI(
        api_key=API_KEY,
        base_url=API_URL,
    )

    # Simple text test
    try:
        print("\n1. Testing text-only completion...")
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "user", "content": "Hello! Who are you?"}
            ],
            max_tokens=50
        )
        print("Response:", completion.choices[0].message.content)
    except Exception as e:
        print(f"Text test failed: {e}")
        return

    # Image test (using a small 1x1 pixel base64 image if no file exists)
    # 1x1 red pixel png
    dummy_image = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
    
    try:
        print("\n2. Testing vision completion (with dummy image)...")
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "user", 
                    "content": [
                        {"type": "text", "text": "What color is this image?"},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{dummy_image}"}}
                    ]
                }
            ],
            max_tokens=50
        )
        print("Response:", completion.choices[0].message.content)
        print("\n✅ API is working correctly!")
    except Exception as e:
        print(f"Vision test failed: {e}")

if __name__ == "__main__":
    test_api()

