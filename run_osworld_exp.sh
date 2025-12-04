#!/bin/bash

# Ensure we are in the OSWorld directory where the script resides
# Assuming this script is in the project root and OSWorld is a subdirectory
cd "$(dirname "$0")/OSWorld" || exit

echo "Running OSWorld experiment with local serving..."

python run_multienv_qwen3vl.py \
    --model "Qwen/Qwen3-VL-8B-Instruct" \
    --num_envs 5 \
    --test_all_meta_path "evaluation_examples/test_small_custom.json" \
    --result_dir "./results_qwen3_8b_api" \
    --provider_name "docker" \
    --headless \
    --api_backend "local" \
    --local_model_url "http://localhost:8000/v1"

