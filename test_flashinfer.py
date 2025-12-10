import os
import sys

# FORCE vLLM to use FlashInfer. 
# If FlashInfer is missing or incompatible, this will likely crash with an error.
os.environ["VLLM_ATTENTION_BACKEND"] = "FLASHINFER"

try:
    from vllm import LLM, SamplingParams
    print("Successfully imported vLLM.")
except ImportError:
    print("vLLM not installed.")
    sys.exit(1)

# Use a tiny model for a fast test, or use your Qwen model if already cached.
# 'facebook/opt-125m' is very small and good for quick backend checks.
model_name = "facebook/opt-125m" 

print(f"Initializing vLLM with model: {model_name}")
print(f"Forced Backend: {os.environ.get('VLLM_ATTENTION_BACKEND')}")

try:
    # Initialize LLM. This triggers the attention backend selection.
    llm = LLM(model=model_name, enforce_eager=True)
    
    # Run a tiny inference
    prompts = ["Hello, my name is"]
    sampling_params = SamplingParams(temperature=0.8, top_p=0.95, max_tokens=10)
    outputs = llm.generate(prompts, sampling_params)

    for output in outputs:
        prompt = output.prompt
        generated_text = output.outputs[0].text
        print(f"Prompt: {prompt!r}, Generated text: {generated_text!r}")
        
    print("\nSUCCESS: vLLM successfully ran using the FlashInfer backend!")

except Exception as e:
    print(f"\nFAILURE: Could not run vLLM with FlashInfer.\nError: {e}")