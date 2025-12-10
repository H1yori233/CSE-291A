echo "Cleaning up old processes..."
pkill -9 -f "vllm"
pkill -9 -f "python3 -m vllm"
sleep 2

MODEL_NAME="Qwen/Qwen3-VL-8B-Instruct-FP8"
PORT=8000
HOST="0.0.0.0"

echo "Starting vLLM server with model: $MODEL_NAME on port $PORT..."

export HF_HOME=/workspace/test/inference
export HF_HUB_ENABLE_HF_TRANSFER=0 
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True 
export CUDA_VISIBLE_DEVICES=0
TARGET_VRAM_GB=24
GPU_TOTAL_MB=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits | head -n1)
if [ -z "$GPU_TOTAL_MB" ]; then echo "No GPU detected"; exit 1; fi
GPU_TOTAL_GB=$(python - <<'PY'
import os
mb=float(os.environ["GPU_TOTAL_MB"])
print(int(mb//1024))
PY
)
if [ "$GPU_TOTAL_GB" -lt "$TARGET_VRAM_GB" ]; then echo "GPU too small"; exit 1; fi
GPU_MEM_UTIL=$(python - <<'PY'
import os
target=float(os.environ["TARGET_VRAM_GB"])
total=float(os.environ["GPU_TOTAL_GB"])
print(f"{min(0.98,(target+0.0001)/total):.4f}")
PY
)

python -m vllm.entrypoints.openai.api_server \
    --model "$MODEL_NAME" \
    --host "$HOST" \
    --port "$PORT" \
    --api-key "EMPTY" \
    --trust-remote-code \
    --gpu-memory-utilization "$GPU_MEM_UTIL" \
    --max-model-len 3072 \
    --max-num-seqs 1 \
    --limit-mm-per-prompt '{"video": 1, "image": 1}' \
    --dtype auto \
    --enforce-eager \
    --enable-prefix-caching \
    --enable-chunked-prefill \
    --served-model-name "$MODEL_NAME"