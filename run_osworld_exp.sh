#!/bin/bash

# Ensure we are in the OSWorld directory where the script resides
# Assuming this script is in the project root and OSWorld is a subdirectory
cd "$(dirname "$0")/OSWorld" || exit

echo "Running OSWorld experiment with local serving (Bare Metal mode)..."

# Ensure Xvfb is running
if ! pgrep -x "Xvfb" > /dev/null; then
    echo "Starting Xvfb..."
    Xvfb :99 -screen 0 1920x1080x24 > /var/log/xvfb.log 2>&1 &
    sleep 3
fi
export DISPLAY=:99

python run_multienv_qwen3vl.py \
    --model "Qwen/Qwen3-VL-8B-Instruct" \
    --num_envs 1 \
    --test_all_meta_path "evaluation_examples/test_small_custom.json" \
    --result_dir "./results_qwen3_8b_api" \
    --provider_name "bare_metal" \
    --headless \
    --api_backend "local" \
    --local_model_url "http://localhost:8000/v1" 2>&1 | tee experiment.log
