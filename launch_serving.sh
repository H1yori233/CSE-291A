#!/bin/bash

# Configuration
MODEL_NAME="Qwen/Qwen3-VL-8B-Instruct"  # Replace with your actual model path/name
PORT=8000
HOST="0.0.0.0"

echo "Starting vLLM server with model: $MODEL_NAME on port $PORT..."

# Launch vLLM OpenAI API server
# Adjust arguments like --gpu-memory-utilization or --tensor-parallel-size as needed for your hardware
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
python -m vllm.entrypoints.openai.api_server \
    --model "$MODEL_NAME" \
    --host "$HOST" \
    --port "$PORT" \
    --trust-remote-code \
    --gpu-memory-utilization 0.8 \
    --max-model-len 4096 \
    --max-num-seqs 16 \
    --dtype bfloat16 \
    --enforce-eager \
    --served-model-name "$MODEL_NAME"

