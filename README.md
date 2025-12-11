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

The agent uses a structured action space that maps to GUI operations.

| Action | Description | Parameters (JSON) |
|--------|-------------|-------------------|
| `MOVE_CURSOR` | Move mouse to coordinates | `target: {type: "coordinate", x: int, y: int}` |
| `LEFT_CLICK` | Left click at location | `target: {type: "coordinate", x: int, y: int}` |
| `RIGHT_CLICK` | Right click at location | `target: {type: "coordinate", x: int, y: int}` |
| `DOUBLE_CLICK` | Double click at location | `target: {type: "coordinate", x: int, y: int}` |
| `DRAG_AND_DROP` | Drag from source to target | `source: {...}, target: {...}` |
| `SCROLL_UP` | Scroll up | `target: {...}, scroll_amount: int` |
| `SCROLL_DOWN` | Scroll down | `target: {...}, scroll_amount: int` |
| `TYPE` | Type text | `text: "string"` |
| `PRESS_KEY` | Press single key | `key: "name"` |
| `HOTKEY` | Press key combination | `keys: ["ctrl", "c"]` |
| `WAIT` | Wait (no op) | `metadata: {reason: "string"}` |
| `DONE` | Task completed | - |
| `FAIL` | Task failed | `metadata: {reason: "string"}` |

### Example Action JSON

```json
{
  "thought": "I will open the file explorer.",
  "plan": "1. Click on the folder icon\n2. Wait for window",
  "actions": [
    {
      "action": "LEFT_CLICK", 
      "target": {"type": "coordinate", "x": 100, "y": 200}
    }
  ]
}
```

## 🛠️ Advanced Usage

### Using the Framework Adapter

The framework is designed to plug into the OSWorld environment via `FrameworkAgentAdapter`.

```python
from framework.core.agent import AgentConfig
from framework.osworld_adapter import build_adapter

# 1. Configure the agent
config = AgentConfig(
    max_steps=15,
    temperature=0.2,
    max_tokens=600
)

# 2. Build the adapter (connects to vLLM)
agent = build_adapter(
    base_url="http://localhost:8000/v1/chat/completions",
    model="Qwen/Qwen3-VL-8B-Instruct",
    agent_config=config
)

# 3. Use in your loop (pseudo-code)
# env = ... (DesktopEnv)
# instruction = "Open Calculator"
# obs = env.reset(instruction)
#
# raw_response, actions = agent.predict(instruction, obs)
# for action in actions:
#     env.step(action)
```

## 🐛 Debugging

### View Logs

The agent uses standard Python logging.

```python
import logging
logging.basicConfig(level=logging.INFO)
# logs will appear in stdout
```

When running via `run_framework_adapter.py`, logs are also saved to the results directory structure:
- `agent.log`: Full debug logs from the agent.
- `action_history.json`: Structured history of actions taken.

### Verbose Mode

Set logging level to DEBUG to see full prompt construction and raw model outputs:

```python
logging.getLogger("framework").setLevel(logging.DEBUG)
```

## 🔧 Configuration

### Environment Variables

```bash
# OpenAI (if using OpenAI backend instead of vLLM)
export OPENAI_API_KEY="sk-..."
```

## 📈 Performance Tips

1. **vLLM Optimization**: Use `launch_serving.sh` which enables `prefix-caching` and `chunked-prefill`.
2. **Coordinate Precision**: The agent uses precise coordinate targeting. Ensure screen resolution matches the model's expected aspect ratio (usually 16:9).
3. **Action Batching**: The model can output multiple actions in one step (e.g., move then click).

## 🧪 Testing

```bash
# Run a quick test on a single task
cd OSWorld
python run_framework_adapter.py --domain onboard --limit 1 --max_steps 5
```

## 📝 Example Tasks

The `tasks/` directory in the repository (and OSWorld submodule) contains standard evaluation tasks.

## 🤝 Contributing

To extend the framework:
1. **New Actions**: Modify `framework/actions/schema.py` and update `_translate_action` in `framework/osworld_adapter.py`.
2. **Prompt Engineering**: Update templates in `framework/core/prompt_builder.py`.

## 📄 License

[Your License Here]

## 🙏 Acknowledgments

- OSWorld-Human for agent evaluation methodology
- Course: CSE 291A – Systems for LLMs & AI Agents

---

**Author**: [Your Name / Team]  
**Course**: CSE 291A – Systems for LLMs & AI Agents  
**Date**: Fall 2024
