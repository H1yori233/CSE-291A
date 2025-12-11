import os
import argparse
from openai import OpenAI

def test_remote_connection(base_url, api_key, model_name):
    print(f"Testing connection to: {base_url}")
    print(f"Model: {model_name}")
    
    try:
        client = OpenAI(
            base_url=base_url,
            api_key=api_key,
        )

        # 1. List models to verify connectivity and model availability
        print("\n--- Checking available models ---")
        models = client.models.list()
        available_models = [m.id for m in models.data]
        print(f"Available models: {available_models}")
        
        if model_name not in available_models:
            print(f"WARNING: The requested model '{model_name}' was not found in the available models list.")
            print(f"Did you start vLLM with --served-model-name '{model_name}'?")
        else:
            print(f"SUCCESS: Found model '{model_name}'")

        # 2. Simple Chat Completion Test
        print(f"\n--- Testing Chat Completion with {model_name} ---")
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello! Are you working correctly?"}
        ]
        
        response = client.chat.completions.create(
            model=model_name,
            messages=messages,
            max_tokens=50
        )
        
        content = response.choices[0].message.content
        print(f"Response: {content}")
        print("\nSUCCESS: Basic text generation works!")

    except Exception as e:
        print(f"\nERROR: Connection failed!")
        print(f"Details: {e}")
        print("\nTroubleshooting tips:")
        print("1. Did you copy the correct Public IP and External Port from RunPod?")
        print("2. Is the vLLM server running on the remote machine?")
        print("3. Did you add the 'Expose TCP Ports' (e.g. 8000) in the RunPod template?")
        print("4. Is the server started with --host 0.0.0.0?")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test remote vLLM connection")
    parser.add_argument("--ip", required=True, help="RunPod Public IP")
    parser.add_argument("--port", required=True, help="RunPod External Port (mapped to 8000)")
    parser.add_argument("--model", default="Qwen/Qwen3-VL-8B-Instruct-FP8", help="Model name to test")
    
    args = parser.parse_args()
    
    # Construct base URL
    base_url = f"http://{args.ip}:{args.port}/v1"
    
    test_remote_connection(base_url, "EMPTY", args.model)

