# ECUA Quick Start Guide

Get up and running with the ECUA agent in 5 minutes.

## Prerequisites

- Python 3.8+
- macOS, Linux, or Windows
- (For OpenAI) An OpenAI API key

## Installation

### 1. Install Core Dependencies

```bash
pip install -r requirements.txt
```

**Note:** If you get errors about `llama-cpp-python` or `paddleocr`, that's OK! These are optional dependencies. See [INSTALL.md](INSTALL.md) for detailed troubleshooting.

### 2. Install System Dependencies

**macOS:**
```bash
brew install tesseract
```

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install tesseract-ocr wmctrl xdotool
```

**Windows:**
- Download Tesseract from: https://github.com/UB-Mannheim/tesseract/wiki
- Install and add to PATH

### 3. Set Up API Key

```bash
export OPENAI_API_KEY="sk-your-key-here"
```

**Having Installation Issues?** → See [INSTALL.md](INSTALL.md) for detailed troubleshooting guide.

## Run Your First Task

### Example 1: Simple Python Script

Create a file `test_agent.py`:

```python
from framework.core.loop import run_task
from framework.core.model_client import create_model_client

# Create model
model = create_model_client('openai', model='gpt-4-turbo-preview')

# Run task
result = run_task(
    task_description="Open Finder application",
    model_client=model,
    max_steps=10
)

print(f"✅ Success: {result['success']}")
print(f"📊 Steps: {result['current_step']}")
print(f"⏱️  Time: {result['statistics']['execution_time']:.1f}s")
```

Run it:
```bash
python test_agent.py
```

### Example 2: Use Provided Script

```bash
python scripts/example_usage.py
```

### Example 3: Run Evaluation

```bash
python scripts/run_eval.py --tasks tasks --limit 3
```

## What Happens?

1. **Perception**: Agent captures screenshot and extracts text via OCR
2. **Planning**: LLM generates JSON action plan
3. **Execution**: Agent executes actions (mouse clicks, keyboard input, etc.)
4. **Repeat**: Continues until task completes or max steps reached

## View Results

Results are saved in `results/`:

```bash
# View latest run
ls -lt results/ | head -n 5

# View logs
cat results/run_*/agent.log

# View screenshots
open results/run_*/screenshots/
```

## Common Issues

### Issue: "Tesseract not found"

**Solution:**
```bash
# macOS
brew install tesseract

# Ubuntu
sudo apt-get install tesseract-ocr

# Windows - download from:
# https://github.com/UB-Mannheim/tesseract/wiki
```

### Issue: "OpenAI API key not provided"

**Solution:**
```bash
export OPENAI_API_KEY="your-key-here"
```

### Issue: Actions execute too fast

**Solution:**
```python
result = run_task(
    task_description="...",
    model_client=model,
    action_delay=1.0  # Increase delay
)
```

### Issue: OCR not detecting text

**Solution:**
Try PaddleOCR:
```python
result = run_task(
    task_description="...",
    model_client=model,
    ocr_engine='paddle'  # More accurate
)
```

## Using Local LLMs

### Ollama

1. Install Ollama: https://ollama.ai
2. Pull a model:
```bash
ollama pull llama3.1:8b-instruct
```

3. Use in code:
```python
model = create_model_client('ollama', model='llama3.1:8b-instruct')
```

### llama.cpp

1. Download a GGUF model
2. Use in code:
```python
model = create_model_client('llamacpp', model_path='path/to/model.gguf')
```

## Next Steps

1. ✅ Run the example tasks
2. 📝 Create your own tasks in `phase1_tasks/tasks/`
3. 🧪 Experiment with different models
4. 📊 Analyze results with evaluation metrics
5. 🔧 Customize the framework for your use case

## Getting Help

- Read the full README: `README.md`
- Check task examples: `phase1_tasks/tasks/`
- View code documentation in source files
- Review evaluation metrics: `agent/eval/metrics.py`

## Example Tasks

Try these tasks to test the agent:

```python
tasks = [
    "Open Calculator and compute 15 * 3",
    "Create a folder named 'TestFolder' on Desktop",
    "Open Safari and navigate to google.com",
    "Open TextEdit and type 'Hello World'",
]

for task in tasks:
    result = run_task(task, model, max_steps=10)
    print(f"{task}: {'✅' if result['success'] else '❌'}")
```

Happy automating! 🚀

