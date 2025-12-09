#!/usr/bin/env python3
import sys, json, argparse
from pathlib import Path
from desktop_env.desktop_env import DesktopEnv

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from framework.core import AgentConfig, AgentLoop, QwenOSWorldAgent
from framework.core.prompt_builder import PromptBuilder
from framework.core.model_client import create_model_client
from framework.core.observation import Observation
from framework.actions.grounding import GroundingResolver

def adapt_observation(raw):
    # OSWorld 默认返回 {"screenshot": img, "accessibility_tree": ..., "terminal": ...}
    return Observation(
        screenshot=raw.get("screenshot"),
        marks={},                       # 如启用 SoM/标注，可在此填充
        som_elements=[],
        a11y_tree=raw.get("accessibility_tree"),
        original_size=None,             # 如您对截图做了缩放，可在此传原始尺寸
    )

def main(args):
    tasks = json.loads(Path(args.task_file).read_text())
    if isinstance(tasks, dict):
        tasks = [tasks]

    client = create_model_client(
        "qwen_vl",
        model=args.model,
        base_url=args.base_url,
    )
    agent = QwenOSWorldAgent(
        model_client=client,
        config=AgentConfig(max_steps=args.max_steps, temperature=args.temperature),
        prompt_builder=PromptBuilder(mode="coordinate"),
        grounder=GroundingResolver(),
    )

    env = DesktopEnv(
        provider_name=args.provider,
        os_type=args.os_type,
        action_space="computer_13",
        headless=args.headless,
    )
    loop = AgentLoop(agent=agent, env=env, observation_adapter=adapt_observation)

    for task in tasks:
        print(f"\n=== Task {task.get('id')} ===")
        print("Instruction:", task.get("instruction"))
        result = loop.run_task(task, max_steps=args.max_steps)
        print("Success:", result.success)
        print("Steps:", result.steps)
        print("Info:", result.info)

    env.close()

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--task-file", type=str, required=True, help="OSWorld 任务 JSON (单个或列表)")
    p.add_argument("--provider", type=str, default="docker")
    p.add_argument("--os_type", type=str, default="Ubuntu")
    p.add_argument("--headless", action="store_true", default=True)
    p.add_argument("--model", type=str, default="Qwen/Qwen3-VL-8B-Instruct-FP8")
    p.add_argument("--base-url", type=str, default="http://194.68.245.78:22068/v1")
    p.add_argument("--max-steps", type=int, default=10)
    p.add_argument("--temperature", type=float, default=0.1)
    args = p.parse_args()
    main(args)