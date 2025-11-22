export HF_HUB_ENABLE_HF_TRANSFER=0
vllm serve Qwen/Qwen3-VL-8B-Instruct \
  --gpu-memory-utilization 0.90 \
  --max-model-len 4096 \
  --max-num-seqs 1 \
  --limit-mm-per-prompt.image 1 \
  --limit-mm-per-prompt.video 0 \
  --async-scheduling