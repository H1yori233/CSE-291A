#!/bin/bash

# 1. CLEANUP: Ensure no zombie vLLM/Ray processes are hogging GPU memory
# (Crucial because your logs show messy shutdowns with ^C)
echo "Cleaning up old processes..."
pkill -9 -f "vllm"
pkill -9 -f "python3 -m vllm"
sleep 2

# Configuration
MODEL_NAME="Qwen/Qwen3-VL-8B-Instruct-FP8"
PORT=8000
HOST="0.0.0.0"

echo "Starting vLLM server with model: $MODEL_NAME on port $PORT..."

# 2. ENVIRONMENT OPTIMIZATIONS
# Disable HF transfer if it causes issues, usually safer off for debugging
export HF_HOME=/workspace/test/inference
export HF_HUB_ENABLE_HF_TRANSFER=0 
# Help with memory fragmentation
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True 

# 3. LAUNCH SERVER
python -m vllm.entrypoints.openai.api_server \
    --model "$MODEL_NAME" \
    --host "$HOST" \
    --port "$PORT" \
    --api-key "EMPTY" \
    --trust-remote-code \
    --gpu-memory-utilization 0.95 \
    --max-model-len 3072 \
    --max-num-seqs 1 \
    --limit-mm-per-prompt '{"video": 1, "image": 1}' \
    --dtype auto \
    --enforce-eager \
    --enable-prefix-caching \
    --enable-chunked-prefill \
    --served-model-name "$MODEL_NAME"