# Edge Computer-Use Agent

Desktop automation agent using VLM for OSWorld benchmark.
![logo](./data/logo.png)

## Configuration

- **Environment**: Ubuntu 22.04 LTS
- **GPU**: Single NVIDIA RTX 3090 (24 GB VRAM)
- **Model**: `Qwen/Qwen3-VL-8B-Instruct-FP8` deployed via vLLM

## Structure

```
framework/       # Agent framework
  actions/       # Action schema and grounding
  core/          # Agent, memory, model client
  prompts/       # Prompt templates
inference/       # vLLM serving scripts
scripts/         # Evaluation scripts
OSWorld/         # OSWorld benchmark (submodule)
result/          # Evaluation results
```

## Quick Start

**1. Start vLLM server**

```bash
cd inference && bash launch_serving.sh
```

> Modify `inference/launch_serving.sh` based on your GPU configuration.

**2. Move evaluation script to OSWorld**

```bash
cp scripts/run_framework_adapter.py OSWorld/
```

> Run the agent in OSWorld's environment for convenience.

**3. Run benchmark**

```bash
cd OSWorld
uv run python run_framework_adapter.py \
    --base-url http://localhost:8000/v1/chat/completions \
    --model Qwen/Qwen3-VL-8B-Instruct-FP8 \
    --provider_name docker \
    --headless \
    --observation_type screenshot_a11y_tree \
    --test_all_meta_path "evaluation_examples/test_simple.json" \
    --max_steps 15 \
    --max-tokens 400
```

## Results

Evaluation results are stored in `result/`. Due to space constraints, only successful tasks are kept.
