#!/bin/bash

# 1. CLEANUP: Aggressive cleanup to ensure zero VRAM contention
echo "Cleaning up old processes..."
pkill -9 -i -f "vllm"
pkill -9 -f "VLLM"
sleep 5

# Clear Python compiled cache files to prevent weird import errors after forceful kills
find . -type d -name "__pycache__" -exec rm -r {} +

sleep 3

# Configuration
# Note: Using Qwen2.5-VL as requested in optimization (Qwen3-VL might not be available publicly yet)
# If you have a private Qwen3 path, revert this string.
MODEL_NAME="Qwen/Qwen3-VL-8B-Instruct-FP8" 
PORT=8000
HOST="0.0.0.0"

echo "Starting vLLM server with single-request optimization..."

# Detect RunPod environment and print external endpoint
if [ -n "$RUNPOD_PUBLIC_IP" ]; then
    echo "----------------------------------------------------------------"
    echo "RunPod Detected!"
    echo "Internal Port: $PORT"
    # Dynamic variable lookup for the external port
    VAR_NAME="RUNPOD_TCP_PORT_$PORT"
    EXTERNAL_PORT="${!VAR_NAME}"
    
    if [ -n "$EXTERNAL_PORT" ]; then
        echo "External Endpoint: $RUNPOD_PUBLIC_IP:$EXTERNAL_PORT"
        echo "Connection URL: http://$RUNPOD_PUBLIC_IP:$EXTERNAL_PORT/v1"
    else
        echo "External IP: $RUNPOD_PUBLIC_IP"
        echo "Make sure the internal port $PORT is exposed in RunPod settings."
    fi
    echo "----------------------------------------------------------------"
fi

# 2. ENVIRONMENT OPTIMIZATIONS (CRITICAL FOR LATENCY)

# NOTE: FlashInfer is NOT supported by Qwen3-VL yet.
# Removing strict backend enforcement to let vLLM use the default (FlashAttention).
# export VLLM_ATTENTION_BACKEND=FLASHINFER

# Prevent CPU thread contention. vLLM is heavy on the GPU; 
# excessive CPU threads for OMP can actually slow down the scheduling loop.
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1

# Disable HF transfer (safer for debugging)
export HF_HUB_ENABLE_HF_TRANSFER=0 

# Memory fragmentation help
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True 

# 3. LAUNCH SERVER

# Changes for Optimization:
# - REMOVED --enforce-eager: CUDA Graphs are ESSENTIAL for low latency at Batch=1.
# - ADDED --enable-prefix-caching: As requested.
# - ADDED --kv-cache-dtype auto: Ensures optimal cache format.
# - ADDED --disable-log-stats: Reduces console I/O overhead.
# - TUNED --gpu-memory-utilization: 0.90 to allow some headroom
# - TUNED limit-mm-per-prompt: Added image support

python3 -m vllm.entrypoints.openai.api_server \
    --model "$MODEL_NAME" \
    --host "$HOST" \
    --port "$PORT" \
    --api-key "EMPTY" \
    --trust-remote-code \
    --gpu-memory-utilization 0.90 \
    --max-model-len 8192 \
    --max-num-seqs 1 \
    --limit-mm-per-prompt '{"image": 1, "video": 1}' \
    --dtype auto \
    --kv-cache-dtype auto \
    --enable-prefix-caching \
    --disable-log-stats \
    --served-model-name "$MODEL_NAME"
