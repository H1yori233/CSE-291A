# OSWorld Agent Framework (Refactored)

This package is a clean-room rewrite that follows the architecture described in `code/test/GUIDE.md`.  The new layout explicitly separates planning, execution, grounding, and memory so that a single Qwen‑3 VL 8B model can orchestrate the entire OSWorld workflow with minimal overhead.

## Module Overview

| Module | Purpose |
| --- | --- |
| `core.agent` | Implements `QwenOSWorldAgent`, the orchestrator that owns planning, per-step reasoning, reflection, memory and action compilation. |
| `core.prompt_builder` | Emits the system, step, and reflection prompts defined in the guide, including structured JSON requirements. |
| `core.plan` & `core.memory` | Track high-level plan steps, progress markers, and compact history summaries that are injected into prompts. |
| `actions.schema` | Defines the Computer_13 action schema (targets, typing, keys, WAIT/DONE/FAIL) and helpers for parsing LLM output. |
| `actions.grounding` | Resolves SoM marks or textual descriptions into pixel coordinates so the executor never guesses. |
| `core.model_client` | OpenAI-compatible client plus a Qwen VL helper for talking to the local vLLM endpoint. |
| `core.loop` | Minimal driver that wires an environment (e.g., OSWorld `DesktopEnv`) with the agent, executes grouped actions, and gathers results. |
| `utils` | Utility helpers for logging, JSON parsing, and summarising history. |
| `prompts.templates` | Houses the literal text of the prompts (system/step/reflection) so that they stay consistent with the design document. |

## Key Concepts from the Guide

- **Planner vs Executor** – the agent plans once via `_plan_task()` and only revisits the planner when the reflection policy triggers.
- **Structured Output** – every assistant response must satisfy the JSON schema (`thought`, `plan`, `actions`).  `actions.schema` contains validators to ensure this before anything is sent to the OS.
- **Grounder** – all marks/coordinates flow through `actions.grounding.GroundingResolver`, enforcing the "never guess coordinates" rule.
- **Memory** – `core.memory.AgentMemory` tracks plan progress plus the last few action summaries so the prompts stay short but informative.
- **Reflection** – `core.agent` checks the current step against `AgentConfig.reflection_threshold` and re-plans via `_reflect_and_replan()` when progress stalls.

The framework is intentionally headless: it does not own windowing automation or OS hooks.  Instead, `core.loop.AgentLoop` accepts a callable `executor` so that future work can integrate with custom OSWorld runners or simulators.

Refer to `code/test/GUIDE.md` for the rationale and a deep dive into each architectural choice.

## 快速测试套件

为了在无 GUI 的 Linux 机器上验证框架，我们提供了一个轻量级的模拟环境：

1. 任务集位于 `code/test/tasks/dummy_suite.json`，每个任务要求在虚拟控制台输入特定文字后结束。
2. 运行 `python code/test/scripts/run_dummy_suite.py`（必要时设置 `PYTHONPATH=/workspace/code/test`）即可启动 QwenOSWorldAgent、连接本地 vLLM，并针对所有任务输出通过情况。
3. 如需自定义 vLLM 地址或步数限制，可使用 `--base-url`、`--model`、`--max-steps`、`--temperature` 等参数。

该脚本使用 `DummyDesktopEnv` 模拟一个简单窗口，主要用于验证：模型连通性、提示格式遵循、动作解析/grounding 以及 DONE/FAIL 信号处理。
