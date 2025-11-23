# Installation Guide

## Quick Install (Core Dependencies Only)

The framework now has **required** and **optional** dependencies separated to make installation easier.

### Step 1: Install Core Dependencies

```bash
pip install -r requirements.txt
```

This installs only the essential packages needed to run the agent with OpenAI backend and Tesseract OCR.

### Step 2: Install System Dependencies

**macOS:**
```bash
brew install tesseract
```

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install tesseract-ocr wmctrl xdotool xvfb scrot x11-apps
```

**Windows:**
- Download Tesseract: https://github.com/UB-Mannheim/tesseract/wiki
- Install and add to PATH

### Step 2b: Headless (AWS/EC2) Desktop Stack

For servers without a physical monitor you also need a virtual framebuffer + window manager so PyAutoGUI can interact with real apps.

```bash
sudo apt-get update
sudo apt-get install -y \
  xfce4 xfce4-goodies \
  xvfb x11-apps dbus-x11 scrot x11vnc \
  wmctrl xdotool tesseract-ocr

chmod +x scripts/start_headless_desktop.sh
./scripts/start_headless_desktop.sh   # starts Xvfb on :99, XFCE, and x11vnc
```

The helper script writes the exported display value to `~/.ecua_headless/display.env`. Subsequent agent runs will automatically bootstrap a virtual display using Xvfb + `pyvirtualdisplay` if `DISPLAY` is absent, so the automation loop just works on CI/servers.

### Step 3: Set API Key

```bash
export OPENAI_API_KEY="your-api-key-here"
```

### Step 4: Test Installation

```bash
python scripts/example_usage.py
```

## Optional Dependencies

Install these only if you need the specific features:

### For Anthropic Claude Models

```bash
pip install anthropic
export ANTHROPIC_API_KEY="your-key"
```

### For PaddleOCR (Better OCR Accuracy)

```bash
pip install paddleocr
```

### For Ollama (Local LLM)

```bash
# Install Ollama from https://ollama.ai
# Then install Python client
pip install ollama

# Pull a model
ollama pull llama3.1:8b-instruct
```

### For llama.cpp (Local CPU/GPU Inference)

⚠️ **This requires compilation and is more complex to install.**

**macOS (with Apple Silicon Metal GPU):**
```bash
CMAKE_ARGS="-DLLAMA_METAL=on" pip install llama-cpp-python
```

**Linux (with NVIDIA CUDA):**
```bash
CMAKE_ARGS="-DLLAMA_CUDA=on" pip install llama-cpp-python
```

**CPU-only (all platforms):**
```bash
pip install llama-cpp-python
```

**Note:** If llama.cpp installation fails, you can use Ollama instead, which is much easier to set up.

## Troubleshooting

### Issue: "llama-cpp-python failed to build"

**Solution:** This is expected! llama-cpp-python is optional and requires compilation. The framework works fine without it. If you need local LLM support:

1. **Option A (Recommended):** Use Ollama instead
   ```bash
   pip install ollama
   # Download from https://ollama.ai
   ```

2. **Option B:** Install build tools first
   ```bash
   # macOS
   xcode-select --install
   
   # Ubuntu
   sudo apt-get install build-essential cmake
   
   # Then try installing llama-cpp-python again
   CMAKE_ARGS="-DLLAMA_METAL=on" pip install llama-cpp-python
   ```

3. **Option C:** Skip it and use OpenAI API (simplest)
   - No installation needed
   - Just set your API key

### Issue: "paddleocr failed to build"

**Solution:** PaddleOCR is optional. The framework uses Tesseract by default, which works well for most cases.

```bash
# Skip PaddleOCR and use Tesseract (default)
# Already installed with brew install tesseract
```

If you really need PaddleOCR:
```bash
# Try installing with --no-cache-dir
pip install --no-cache-dir paddleocr
```

### Issue: "Tesseract not found"

**Solution:**
```bash
# macOS
brew install tesseract

# Ubuntu
sudo apt-get install tesseract-ocr

# Verify installation
tesseract --version
```

### Issue: "OpenAI API key not provided"

**Solution:**
```bash
# Set environment variable
export OPENAI_API_KEY="sk-your-key-here"

# Or create .env file
echo "OPENAI_API_KEY=sk-your-key-here" > .env
```

### Issue: "anthropic package not installed"

**Solution:** Anthropic is optional. Either install it or use OpenAI:
```bash
# Option A: Install Anthropic
pip install anthropic

# Option B: Use OpenAI instead
model = create_model_client('openai')  # instead of 'anthropic'
```

## Minimal Working Setup

For a minimal working setup, you only need:

1. ✅ Python 3.8+
2. ✅ Core dependencies (`pip install -r requirements.txt`)
3. ✅ Tesseract (`brew install tesseract`)
4. ✅ OpenAI API key

Everything else is optional!

## What Works with Core Installation?

With just the core dependencies, you can:

- ✅ Use OpenAI models (GPT-4, GPT-3.5)
- ✅ Use Tesseract OCR
- ✅ Run all GUI automation features
- ✅ Execute all 10 example tasks
- ✅ Generate evaluation metrics
- ✅ View logs and screenshots

## What Requires Optional Dependencies?

- ❌ Anthropic Claude → `pip install anthropic`
- ❌ PaddleOCR → `pip install paddleocr`
- ❌ Ollama → `pip install ollama` + Ollama app
- ❌ llama.cpp → Complex compilation (use Ollama instead)

## Recommended Setup Paths

### Path 1: Quick Start (API-based)
```bash
pip install -r requirements.txt
brew install tesseract  # macOS
export OPENAI_API_KEY="your-key"
python scripts/example_usage.py
```
✅ Fastest, easiest, no compilation needed

### Path 2: Local LLM with Ollama
```bash
pip install -r requirements.txt
pip install ollama
brew install tesseract
# Install Ollama from https://ollama.ai
ollama pull llama3.1:8b-instruct
```
✅ Local inference, no API costs, easier than llama.cpp

### Path 3: Advanced (Everything)
```bash
pip install -r requirements.txt
pip install anthropic ollama paddleocr
brew install tesseract
# Optionally: CMAKE_ARGS="-DLLAMA_METAL=on" pip install llama-cpp-python
```
⚠️ More complex, may require troubleshooting

## Testing Your Installation

```bash
# Test core functionality
python -c "from framework.core.loop import run_task; print('✅ Core installed')"

# Test OpenAI
python -c "from framework.core.model_client import create_model_client; m = create_model_client('openai'); print('✅ OpenAI available')"

# Test Tesseract
tesseract --version

# Run example
python scripts/example_usage.py
```

## Next Steps

Once installation is complete:

1. Read QUICKSTART.md for usage examples
2. Run example: `python scripts/example_usage.py`
3. Run evaluation: `python scripts/run_eval.py --tasks phase1_tasks/tasks --limit 3`
4. Read README.md for comprehensive documentation

## Getting Help

If you encounter issues not covered here:

1. Check that Python 3.8+ is installed: `python --version`
2. Verify Tesseract is installed: `tesseract --version`
3. Make sure API key is set: `echo $OPENAI_API_KEY`
4. Try with minimal setup first, then add optional features
5. Check the error message - it will suggest alternatives

