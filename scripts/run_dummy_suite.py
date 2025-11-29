#!/usr/bin/env python3
"""Run the refactored agent against a small synthetic task suite."""

import argparse
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

# Ensure framework package is importable when script is executed directly
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from framework.actions.grounding import GroundedAction, GroundingResolver  # noqa: E402
from framework.core import AgentConfig, AgentLoop, QwenOSWorldAgent  # noqa: E402
from framework.core.model_client import create_model_client  # noqa: E402
from framework.core.observation import Mark, Observation  # noqa: E402


class DummyDesktopEnv:
    """Minimal environment that rewards the agent for typing provided text."""

    def __init__(self):
        self.observation = self._build_observation()
        self.expected_text = ""
        self.typed = False

    def _build_observation(self) -> Observation:
        width, height = 640, 360
        img = Image.new("RGB", (width, height), color="white")
        draw = ImageDraw.Draw(img)
        input_box = (120, 220, 520, 280)
        draw.rectangle(input_box, outline="black", width=3)
        draw.text((130, 230), "Console Input (A1)", fill="black")
        som_elements = [
            {"id": "A1", "name": "Console input field", "bbox": [120, 220, 400, 60]},
            {"id": "A2", "name": "Submit button", "bbox": [530, 220, 80, 60]},
        ]
        marks = {
            "A1": Mark(id="A1", bbox=(120, 220, 400, 60), name="Console input field"),
            "A2": Mark(id="A2", bbox=(530, 220, 80, 60), name="Submit button"),
        }
        return Observation(screenshot=img, marks=marks, som_elements=som_elements)

    # DesktopEnv-like API -------------------------------------------------
    def reset(self, task_config):
        self.expected_text = task_config.get("expected_text", "").lower()
        self.typed = False
        return self.observation

    def step(self, action):
        action_type = (action or {}).get("action", "")
        info = {"typed": self.typed}

        if action_type == "TYPE":
            text = (action.get("text") or "").lower()
            if self.expected_text and self.expected_text in text:
                self.typed = True
                info["typed"] = True

        if action_type == "DONE":
            success = self.typed
            reward = 1.0 if success else 0.0
            info["success"] = success
            return self.observation, reward, True, info

        if action_type == "FAIL":
            info["success"] = False
            return self.observation, 0.0, True, info

        # Keep running for other actions (clicks, waits, etc.)
        return self.observation, 0.0, False, info


class ForgivingGrounder(GroundingResolver):
    """Grounder that tolerates missing targets for synthetic tests."""

    def resolve(self, action, observation):  # type: ignore[override]
        try:
            return super().resolve(action, observation)
        except ValueError as exc:
            if "requires a resolvable target" in str(exc):
                return GroundedAction(action=action.action, coordinate=[0, 0], metadata=action.metadata)
            raise


def run_suite(args):
    tasks = json.loads(Path(args.tasks).read_text())
    if not tasks:
        print("No tasks found in", args.tasks)
        return

    client = create_model_client(
        "qwen_vl",
        model=args.model,
        base_url=args.base_url,
    )
    agent = QwenOSWorldAgent(
        model_client=client,
        config=AgentConfig(max_steps=args.max_steps, temperature=args.temperature),
        grounder=ForgivingGrounder(),
    )
    env = DummyDesktopEnv()
    loop = AgentLoop(agent=agent, env=env, observation_adapter=lambda obs: obs)

    results = []
    for task in tasks:
        print("\n=== Task:", task["id"], "===")
        print("Instruction:", task["instruction"])
        result = loop.run_task(task, max_steps=args.max_steps)
        print("Success:", result.success)
        print("Steps:", result.steps)
        print("Info:", result.info)
        results.append((task["id"], result.success))

    passed = sum(1 for _, ok in results if ok)
    print("\nSummary: {}/{} tasks passed".format(passed, len(results)))


def parse_args():
    parser = argparse.ArgumentParser(description="Run the dummy OSWorld suite.")
    parser.add_argument(
        "--tasks",
        type=str,
        default=str(ROOT / "tasks" / "dummy_suite.json"),
        help="Path to dummy task JSON file",
    )
    parser.add_argument("--model", type=str, default="Qwen/Qwen3-VL-8B-Instruct")
    parser.add_argument("--base-url", type=str, default="http://127.0.0.1:8000/v1/chat/completions")
    parser.add_argument("--max-steps", type=int, default=8)
    parser.add_argument("--temperature", type=float, default=0.2)
    return parser.parse_args()


if __name__ == "__main__":
    run_suite(parse_args())
