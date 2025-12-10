import time
import requests
import json
import argparse
import os

# Configuration
API_URL = "http://localhost:8000/v1/chat/completions"
# Using a high-resolution placeholder to simulate a desktop screenshot (OSWorld)
# Qwen-VL handles high-res images by splitting them into patches (increasing token count).
IMAGE_URL = "https://qianwen-res.oss-cn-beijing.aliyuncs.com/Qwen-VL/assets/demo.jpeg"
MODEL_NAME = "Qwen/Qwen3-VL-8B-Instruct-FP8"

# Simulating an OSWorld-like long system prompt / history
OSWORLD_PROMPT = """
You are an intelligent agent capable of controlling a desktop operating system. 
You can view the screen and perform actions like clicking, typing, and scrolling.
Your goal is to complete tasks given by the user.

History of actions:
1. Clicked on "Start Menu" at (50, 1050).
2. Typed "Terminal" into the search bar.
3. Pressed ENTER.
4. Waited for window "Terminal" to appear.
5. Typed "ls -la" into the terminal.
6. Saw a list of files including 'benchmark.sh', 'logs/', 'src/'.
... [Simulating 2000+ tokens of history] ...
""" + (" The quick brown fox jumps over the lazy dog." * 100)  # Padding text to increase prefill load

def measure_request(run_name, request_type="Cold", prompt_len="Short"):
    """
    Sends a request to the vLLM server and measures TTFT and TPOT.
    """
    
    final_prompt = "Describe the current state of the screen and suggest the next action."
    if prompt_len == "Long":
        system_content = OSWORLD_PROMPT
    else:
        system_content = "You are a helpful assistant."

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {
                "role": "system",
                "content": system_content
            },
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": IMAGE_URL}},
                    {"type": "text", "text": final_prompt}
                ]
            }
        ],
        "max_tokens": 128,  # OSWorld usually needs short, precise action outputs
        "stream": True
    }

    start_time = time.perf_counter()
    first_token_time = None
    token_count = 0
    
    print(f"[{run_name}] Sending {request_type} request (Prompt: {prompt_len})...")
    
    try:
        response = requests.post(API_URL, json=payload, stream=True)
        response.raise_for_status()

        for line in response.iter_lines():
            if line:
                line = line.decode('utf-8')
                if line.startswith("data: "):
                    if line == "data: [DONE]":
                        break
                    
                    try:
                        chunk_json = json.loads(line[6:])
                        if "choices" not in chunk_json or not chunk_json["choices"]:
                             continue
                             
                        delta = chunk_json["choices"][0].get("delta", {})
                        content = delta.get("content", "")
                        
                        if not content:
                            continue
                            
                        if first_token_time is None:
                            first_token_time = time.perf_counter()
                        
                        token_count += 1
                        
                    except json.JSONDecodeError:
                        continue
                    
        end_time = time.perf_counter()

        if first_token_time is None:
            print(f"[{run_name}] Error: No tokens received.")
            return None

        ttft = (first_token_time - start_time) * 1000  # ms
        total_time = (end_time - start_time) * 1000 # ms
        decoding_time = (end_time - first_token_time) * 1000 # ms
        
        if token_count > 1:
            tpot = decoding_time / (token_count - 1)
        else:
            tpot = 0

        tokens_per_sec = token_count / (total_time / 1000)

        result = {
            "run_name": run_name,
            "type": request_type,
            "prompt_len": prompt_len,
            "ttft_ms": round(ttft, 2),
            "tpot_ms": round(tpot, 2),
            "total_time_ms": round(total_time, 2),
            "tokens_per_sec": round(tokens_per_sec, 2),
            "total_tokens": token_count
        }
        
        print(f"[{run_name}] {request_type} ({prompt_len}) Results: TTFT={ttft:.2f}ms, TPOT={tpot:.2f}ms")
        return result

    except Exception as e:
        print(f"[{run_name}] Error during request: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description="Profile vLLM Serving Latency")
    parser.add_argument("--run-name", type=str, default="default", help="Name of the configuration being tested")
    parser.add_argument("--log-file", type=str, default="logs/benchmark_results.jsonl", help="Path to log file")
    args = parser.parse_args()

    os.makedirs(os.path.dirname(args.log_file), exist_ok=True)

    # 1. Warm-up Request (Short)
    print("--- Warming up ---")
    measure_request(args.run_name, "Warmup", "Short")
    time.sleep(2)

    # 2. Long Context Request (OSWorld Simulation) - First time (Cold-ish for this prompt)
    print("--- Testing OSWorld Simulation (Long Context) ---")
    long_result_1 = measure_request(args.run_name, "Long_Context_1", "Long")
    
    # 3. Long Context Request - Second time (Should hit Prefix Cache)
    time.sleep(2)
    print("--- Testing OSWorld Simulation (Cached) ---")
    long_result_2 = measure_request(args.run_name, "Long_Context_Cached", "Long")

    # Log results
    with open(args.log_file, "a") as f:
        if long_result_1: f.write(json.dumps(long_result_1) + "\n")
        if long_result_2: f.write(json.dumps(long_result_2) + "\n")

if __name__ == "__main__":
    main()
