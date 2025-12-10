#!/bin/bash

# Configuration
LOG_FILE="logs/long_prompt_benchmark_results.jsonl"
MODEL_NAME="Qwen/Qwen3-VL-8B-Instruct-FP8"
PORT=8000
HOST="0.0.0.0"

# Create logs directory
mkdir -p logs

# Function to wait for vLLM to be ready
wait_for_server() {
    echo "Waiting for vLLM to start..."
    for i in {1..300}; do # Wait up to 5 minutes (model loading can be slow)
        if curl -s -f http://localhost:$PORT/v1/models > /dev/null; then
            echo "vLLM is ready!"
            return 0
        fi
        sleep 2
    done
    echo "Timeout waiting for vLLM to start."
    return 1
}

# Function to run a benchmark case
run_benchmark() {
    local RUN_NAME=$1
    local EXTRA_ENV=$2
    local FLAGS=$3

    echo "========================================================"
    echo "Starting Benchmark: $RUN_NAME"
    echo "Env: $EXTRA_ENV"
    echo "Flags: $FLAGS"
    echo "========================================================"

    # 1. Cleanup
    echo "Cleaning up..."
    pkill -9 -i -f "vllm"
    pkill -9 -f "VLLM"
    sleep 10

    # 2. Start Server
    # Construct the full command
    # We use 'eval' to properly handle environment variables passed as a string
    CMD="$EXTRA_ENV python3 -m vllm.entrypoints.openai.api_server \
        --model $MODEL_NAME \
        --host $HOST \
        --port $PORT \
        --trust-remote-code \
        --gpu-memory-utilization 0.90 \
        --max-model-len 8192 \
        --limit-mm-per-prompt '{\"image\": 1, \"video\": 1}' \
        --dtype auto \
        --kv-cache-dtype auto \
        --disable-log-stats \
        --served-model-name $MODEL_NAME \
        $FLAGS"
    
    echo "Executing: $CMD"
    eval "$CMD" > logs/server_$RUN_NAME.log 2>&1 &
    SERVER_PID=$!

    # 3. Wait for Ready
    if wait_for_server; then
        # 4. Run Profiling
        echo "Running Profiling..."
        python3 profiling_serving.py --run-name "$RUN_NAME" --log-file "$LOG_FILE"
    else
        echo "Skipping profiling due to server failure."
    fi

    # 5. Cleanup
    echo "Stopping server (PID $SERVER_PID)..."
    kill -9 $SERVER_PID
    pkill -9 -i -f "vllm"
    pkill -9 -f "VLLM"
    sleep 5
}

# Clear previous results
# rm -f $LOG_FILE

# Common Env Vars
COMMON_ENV="export HF_HUB_ENABLE_HF_TRANSFER=0; export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True;"

# --- CONFIG 1: Baseline 0 (High Throughput / Eager) ---
# --max-num-seqs 64 (Default-ish high batch)
# --enforce-eager (Disable CUDA Graphs)
# No prefix caching
run_benchmark "Baseline_0_Throughput" \
    "$COMMON_ENV export OMP_NUM_THREADS=4;" \
    "--max-num-seqs 64 --enforce-eager"

# --- CONFIG 2: Baseline 1 (Batch 1 / Eager) ---
# --max-num-seqs 1
# --enforce-eager (Disable CUDA Graphs)
# No prefix caching
run_benchmark "Baseline_1_Batch1_Eager" \
    "$COMMON_ENV export OMP_NUM_THREADS=1;" \
    "--max-num-seqs 1 --enforce-eager"

# --- CONFIG 3: Baseline 2 (Optimized) ---
# --max-num-seqs 1
# (No --enforce-eager -> Enables CUDA Graphs)
# --enable-prefix-caching
# FlashInfer Backend REMOVED (Not supported by Qwen3-VL yet)
run_benchmark "Baseline_2_Optimized" \
    "$COMMON_ENV export OMP_NUM_THREADS=1; export MKL_NUM_THREADS=1;" \
    "--max-num-seqs 1 --enable-prefix-caching"

echo "========================================================"
echo "Benchmark Complete! Results saved to $LOG_FILE"
echo "========================================================"
cat $LOG_FILE

