# ECUA - Edge Computer-Use Agent

**Perception → Planning → Execution**

A modular framework for building autonomous computer control agents using LLMs. The agent observes the screen via OCR, plans actions using an LLM, and executes actions through GUI automation.

## 🎯 Overview

ECUA (Edge Computer-Use Agent) implements a perception-planning-execution loop inspired by OSWorld-Human agent evaluation. The framework is designed to:

- ✅ Support multiple LLM backends (OpenAI, Ollama, llama.cpp, Anthropic)
- ✅ Enable easy swapping between remote APIs and local LLMs
- ✅ Provide structured logging and comprehensive metrics
- ✅ Work cross-platform (macOS, Linux, Windows)

### Architecture

```
┌─────────────────────────────────────────────┐
│           ECUA Agent Loop                   │
├─────────────────────────────────────────────┤
│                                             │
│  1. Perception:  Screenshot → OCR           │
│  2. Planning:    LLM → JSON Actions         │
│  3. Execution:   Execute Actions            │
│  4. Repeat until task complete              │
│                                             │
└─────────────────────────────────────────────┘
```

## 🚀 Quick Start

### 1. Installation

```bash
# Clone the repository
cd CSE-291A

# Install dependencies
pip install -r requirements.txt

# Install system dependencies (macOS)
brew install tesseract

# Install system dependencies (Ubuntu)
sudo apt-get install tesseract-ocr wmctrl xdotool xvfb scrot x11-apps
```

### 2. Set up API key (for OpenAI)

```bash
export OPENAI_API_KEY="your-api-key-here"
```

### 3. Run a simple example

```python
from framework.core.loop import run_task
from framework.core.model_client import create_model_client

# Create model client
model = create_model_client('openai', model='gpt-4-turbo-preview')

# Run task
result = run_task(
    task_description="Open Finder application",
    model_client=model,
    max_steps=10
)

print(f"Success: {result['success']}")
print(f"Steps: {result['current_step']}")
```

Or use the example script:

```bash
python scripts/example_usage.py
```

### Running on Headless AWS/EC2

If you're on a server with no physical display, install a lightweight desktop stack and start the virtual screen:

```bash
sudo apt-get update
sudo apt-get install -y xfce4 xfce4-goodies x11vnc xvfb x11-apps dbus-x11 scrot wmctrl xdotool tesseract-ocr

# start the desktop (sets DISPLAY=:99 by default)
chmod +x scripts/start_headless_desktop.sh
./scripts/start_headless_desktop.sh
```

The agent now auto-creates a virtual display (via Xvfb + pyvirtualdisplay) whenever `DISPLAY` is unset, so you can simply run:

```bash
python scripts/run_eval.py --tasks tasks --backend ollama --model llama3.1:8b-instruct
```

Use `x11vnc` (started by the helper script) to inspect the UI with any VNC viewer if needed.

### 4. Run evaluation on tasks

```bash
python scripts/run_eval.py --tasks tasks --max-steps 20
```

## 📁 Repository Structure

```
CSE-291A/
├── framework/
│   ├── core/
│   │   ├── loop.py              # Main perception-planning-execution loop
│   │   ├── state.py             # Agent state management
│   │   ├── model_client.py      # LLM client abstraction
│   │   ├── prompts.py           # Prompt templates
│   │   └── parser.py            # JSON parser for LLM output
│   ├── perception/
│   │   ├── capture.py           # Screenshot capture
│   │   └── ocr.py               # OCR (Tesseract/PaddleOCR)
│   ├── actions/
│   │   ├── schema.py            # Action definitions
│   │   └── executor.py          # Action execution (GUI automation)
│   ├── eval/
│   │   └── metrics.py           # Evaluation metrics (WES+, WES-)
│   └── utils/
│       ├── log.py               # Structured logging
│       └── coords.py            # Coordinate utilities
├── tasks/                       # Task definitions (JSON)
├── scripts/
│   ├── run_eval.py              # Batch evaluation script
│   └── example_usage.py         # Simple usage example
├── results/                     # Execution logs and metrics
├── requirements.txt
└── README.md                    # This file
```

## 🎬 Action Schema

The agent supports the following actions (OSWorld-Human style):

| Action | Description | Parameters |
|--------|-------------|------------|
| `CLICK` | Click at coordinates or text | `x, y` or `target_text` |
| `MOVE` | Move mouse cursor | `x, y` |
| `SCROLL` | Scroll up/down | `amount` |
| `TYPE` | Type text | `arg` (text) |
| `KEY` | Press keyboard key | `arg` (key combo) |
| `FOCUS_APP` | Bring app to focus | `arg` (app name) |
| `OPEN` | Open file/URL | `arg` (path/URL) |
| `EXECUTE` | Run shell command | `arg` (command) |
| `VERIFY_FILE` | Check file exists | `arg` (path) |
| `WAIT` | Wait for seconds | `amount` |

### Example Action JSON

```json
{
  "actions": [
    {"action": "FOCUS_APP", "arg": "Finder"},
    {"action": "KEY", "arg": "cmd+n"},
    {"action": "CLICK", "target_text": "Desktop"},
    {"action": "TYPE", "arg": "New Folder"}
  ]
}
```

## 🔄 Switching LLM Backends

### OpenAI (Default)

```python
model = create_model_client('openai', model='gpt-4-turbo-preview')
```

### Ollama (Local)

```python
model = create_model_client('ollama', model='llama3.1:8b-instruct')
```

### llama.cpp (CPU/GPU)

```python
model = create_model_client('llamacpp', model_path='models/llama.gguf')
```

### Anthropic Claude

```python
model = create_model_client('anthropic', model='claude-3-sonnet-20240229')
```

**No changes needed to the rest of the framework!** The modular design allows seamless backend swapping.

## 📊 Evaluation Metrics

The framework computes:

- **Success Rate**: % of tasks completed successfully
- **WES+** (Weighted Efficiency Score): Rewards completing tasks with fewer steps
  - Formula: `(successes / total) × (1 - avg_steps_ratio)`
- **WES-** (Weighted Penalty): Penalizes failed tasks with many steps
  - Formula: `(failures / total) × avg_steps_ratio`
- **Average Steps**: Mean steps taken per task
- **Average Time**: Mean execution time per task
- **Action Success Rate**: % of individual actions that succeeded

### Running Evaluation

```bash
# Run all tasks with OpenAI
python scripts/run_eval.py \
  --tasks tasks \
  --backend openai \
  --model gpt-4-turbo-preview \
  --max-steps 20

# Run with local Ollama
python scripts/run_eval.py \
  --tasks tasks \
  --backend ollama \
  --model llama3.1:8b-instruct \
  --max-steps 20

# Run first 3 tasks only
python scripts/run_eval.py \
  --tasks tasks \
  --limit 3
```

Results are saved to `results/`:
- `evaluation_metrics.json` - Summary metrics
- `evaluation_results.csv` - Per-task results
- `run_*/` - Individual run logs and screenshots

## 🛠️ Advanced Usage

### Custom Task

```python
from framework.core.loop import AgentLoop
from framework.core.model_client import create_model_client

# Create components
model = create_model_client('openai', model='gpt-4-turbo-preview')
loop = AgentLoop(
    model_client=model,
    verbose=True,
    run_dir='my_custom_run',
    action_delay=0.5,
    ocr_engine='tesseract'
)

# Run task
result = loop.run_task(
    task_description="Create a file named test.txt on Desktop",
    max_steps=15,
    metadata={'custom_field': 'value'}
)
```

### Custom Action Execution

```python
from framework.actions.schema import Action
from framework.actions.executor import get_executor

executor = get_executor(delay=0.5)

# Execute single action
action = Action(action="CLICK", x=100, y=200)
result = executor.execute(action)

print(result['success'])
print(result['message'])
```

### OCR with Target Text Resolution

```python
from framework.perception.capture import capture_screen
from framework.perception.ocr import get_ocr_manager

# Capture and OCR
screenshot = capture_screen()
ocr = get_ocr_manager(engine='tesseract')
result = ocr.process_screenshot(screenshot, include_boxes=True)

# Find text location
coords = ocr.find_text(screenshot, "Finder", case_sensitive=False)
if coords:
    print(f"Found 'Finder' at: {coords}")
```

## 🐛 Debugging

### View Logs

All runs save detailed logs:

```bash
# View agent log
cat results/run_<timestamp>/agent.log

# View action history
cat results/run_<timestamp>/action_history.json

# View screenshots
open results/run_<timestamp>/screenshots/
```

### Verbose Mode

Enable verbose logging:

```python
result = run_task(
    task_description="...",
    model_client=model,
    verbose=True  # Print detailed logs
)
```

### Adjust Action Delay

Slow down or speed up execution:

```python
result = run_task(
    task_description="...",
    model_client=model,
    action_delay=1.0  # 1 second between actions
)
```

## 🔧 Configuration

### Environment Variables

```bash
# OpenAI
export OPENAI_API_KEY="sk-..."

# Anthropic
export ANTHROPIC_API_KEY="..."

# Ollama URL (if not localhost)
# Set in code: create_model_client('ollama', base_url='http://...')
```

### OCR Engine

Switch between Tesseract and PaddleOCR:

```python
# Tesseract (faster, English)
result = run_task(..., ocr_engine='tesseract')

# PaddleOCR (multilingual, better for complex layouts)
result = run_task(..., ocr_engine='paddle')
```

## 📈 Performance Tips

1. **Use GPU for local LLMs**: Configure Ollama/llama.cpp with GPU support
2. **Adjust max_steps**: Lower for simple tasks, higher for complex ones
3. **Use target_text over coordinates**: More robust to screen changes
4. **Enable action delay**: Gives UI time to update (0.5-1.0s recommended)
5. **Choose right OCR**: Tesseract for speed, PaddleOCR for accuracy

## 🧪 Testing

```bash
# Test simple task
python scripts/example_usage.py

# Test with single task
python scripts/run_eval.py --tasks tasks --limit 1

# Test different OCR engines
python scripts/run_eval.py --tasks tasks --ocr-engine tesseract --limit 1
python scripts/run_eval.py --tasks tasks --ocr-engine paddle --limit 1
```

## 📝 Example Tasks

The `tasks/` directory contains example task definitions in JSON format covering:
- Application launch
- File operations
- Web browsing
- Text editing
- System navigation
- Command line operations

## 🤝 Contributing

To extend the framework:

1. **Add new actions**: Extend `Action` schema in `framework/actions/schema.py`
2. **Add new LLM backend**: Implement `ModelClient` in `framework/core/model_client.py`
3. **Add new metrics**: Extend `MetricsCalculator` in `framework/eval/metrics.py`
4. **Add new tasks**: Create JSON files in `tasks/`

## 📄 License

[Your License Here]

## 🙏 Acknowledgments

- OSWorld-Human for agent evaluation methodology
- Course: CSE 291A – Systems for LLMs & AI Agents

---

**Author**: [Your Name / Team]  
**Course**: CSE 291A – Systems for LLMs & AI Agents  
**Date**: Fall 2024
