#!/usr/bin/env python3
"""Print the raw JSON that QwenOSWorldAgent produces for a single observation."""

import argparse
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from framework.actions.grounding import GroundedAction, GroundingResolver  # noqa: E402
from framework.core import AgentConfig, QwenOSWorldAgent  # noqa: E402
from framework.core.model_client import create_model_client  # noqa: E402
from framework.core.observation import Mark, Observation  # noqa: E402


def build_demo_observation() -> Observation:
    width, height = 640, 360
    img = Image.new("RGB", (width, height), color="white")
    draw = ImageDraw.Draw(img)
    draw.rectangle((120, 200, 260, 260), outline="black", width=3)
    draw.text((125, 205), "Logo (A1)", fill="black")
    draw.rectangle((300, 200, 440, 260), outline="black", width=3)
    draw.text((305, 205), "Resize (A2)", fill="black")
    marks = {
        "A1": Mark(id="A1", bbox=(120, 200, 140, 60), name="Logo file"),
        "A2": Mark(id="A2", bbox=(300, 200, 140, 60), name="Resize button"),
    }
    som_elements = [
        {"id": "A1", "name": "Logo file", "bbox": [120, 200, 140, 60]},
        {"id": "A2", "name": "Resize button", "bbox": [300, 200, 140, 60]},
    ]
    return Observation(screenshot=img, marks=marks, som_elements=som_elements)


class ForgivingGrounder(GroundingResolver):
    """Resolve pointer actions, but tolerate missing targets for demo screenshots."""

    def resolve(self, action, observation):  # type: ignore[override]
        try:
            return super().resolve(action, observation)
        except ValueError as exc:
            if "requires a resolvable target" in str(exc):
                return GroundedAction(action=action.action, coordinate=[0, 0], metadata=action.metadata)
            raise


def main():
    parser = argparse.ArgumentParser(description="Show agent JSON output for a dummy observation.")
    parser.add_argument("--instruction", type=str, default="Resize the logo to 2x and save it.")
    parser.add_argument("--base-url", type=str, default="http://127.0.0.1:8000/v1/chat/completions")
    parser.add_argument("--model", type=str, default="Qwen/Qwen3-VL-8B-Instruct")
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--max-steps", type=int, default=5)
    args = parser.parse_args()

    client = create_model_client("qwen_vl", model=args.model, base_url=args.base_url)
    agent = QwenOSWorldAgent(
        model_client=client,
        config=AgentConfig(max_steps=args.max_steps, temperature=args.temperature),
        grounder=ForgivingGrounder(),
    )

    observation = build_demo_observation()
    agent.reset(args.instruction)
    result = agent.predict(observation)
    print("\nRaw model response:\n", result.raw_response)
    print("\nParsed payload:\n", result.payload)


if __name__ == "__main__":
    main()
