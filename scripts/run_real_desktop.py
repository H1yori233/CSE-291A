#!/usr/bin/env python3
"""
Run the Agent on the REAL Windows Desktop (Read-Only / Dry-Run).
This script captures the current screen, sends it to the VLM, and prints the planned actions.
"""

import sys
import time
import json
import argparse
from pathlib import Path
from PIL import Image, ImageGrab, ImageDraw

# Ensure framework package is importable
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from framework.core import AgentConfig, AgentLoop, QwenOSWorldAgent
from framework.core.model_client import create_model_client
from framework.core.observation import Observation
from framework.core.prompt_builder import PromptBuilder
from framework.actions.grounding import GroundingResolver

class RealDesktopEnv:
    """
    Environment that captures the real screen.
    By default, it DOES NOT execute actions (Safe Mode), only prints them.
    """
    def __init__(self, execute=False):
        self.execute = execute
        self.width = 0
        self.height = 0
        self.original_size = None
        self._update_screenshot()

    def _update_screenshot(self):
        # Capture full screen
        self.screenshot = ImageGrab.grab()
        
        # Record original size before any resizing
        original_width, original_height = self.screenshot.size
        
        # Resize if too large (e.g., max width 1280) to save tokens/memory
        max_width = 1280
        if self.screenshot.width > max_width:
            ratio = max_width / self.screenshot.width
            new_height = int(self.screenshot.height * ratio)
            self.screenshot = self.screenshot.resize((max_width, new_height), Image.Resampling.LANCZOS)
            self.original_size = (original_width, original_height)
        else:
            self.original_size = None  # No resize needed
            
        self.width, self.height = self.screenshot.size
        print(f"\n[Env] Captured screenshot: {self.width}x{self.height}")
        if self.original_size:
            print(f"[Env] Original size: {self.original_size[0]}x{self.original_size[1]} (scaled down)")

    def reset(self, task_config):
        print(f"\n[Env] Resetting for task: {task_config.get('instruction')}")
        self._update_screenshot()
        # Return observation with NO marks (raw vision mode)
        return Observation(
            screenshot=self.screenshot,
            marks={},
            som_elements=[],
            original_size=self.original_size
        )

    def step(self, action):
        print("\n" + "!" * 40)
        print(f"[Env] Agent wants to: {action.get('action')}")
        
        # Show scaled coordinates if applicable
        if self.original_size and 'coordinate' in action:
            print(f"[Env] Coordinates (scaled to original): {action.get('coordinate')}")
        
        print(f"[Env] Full payload: {json.dumps(action, indent=2)}")
        print("!" * 40 + "\n")

        # In a real implementation, we would use pyautogui here.
        # For now, we just wait a bit and take a new screenshot.
        if action.get('action') in ["DONE", "FAIL"]:
            return self.reset({}), 0.0, True, {"success": action.get('action') == "DONE"}
        
        time.sleep(1) # Simulate action time
        self._update_screenshot()
        
        # Return new observation
        obs = Observation(
            screenshot=self.screenshot,
            marks={},
            som_elements=[],
            original_size=self.original_size
        )
        return obs, 0.0, False, {}

def run_real_task(args):
    client = create_model_client(
        "qwen_vl",
        model=args.model,
        base_url=args.base_url,
    )
    
    # Use COORDINATE MODE for native coordinate prediction
    prompt_builder = PromptBuilder(mode="coordinate")
    
    # Use a slightly higher temperature for creativity if needed, 
    # but 0.1 is good for instruction following.
    agent = QwenOSWorldAgent(
        model_client=client,
        config=AgentConfig(max_steps=args.max_steps, temperature=0.1),
        prompt_builder=prompt_builder,
        grounder=GroundingResolver()
    )
    
    env = RealDesktopEnv(execute=False)
    loop = AgentLoop(agent=agent, env=env, observation_adapter=lambda obs: obs)

    task = {
        "id": "real_desktop_01",
        "instruction": args.instruction
    }

    print(f"\n=== Running Real Desktop Task ===")
    print(f"Instruction: {task['instruction']}")
    print("Please switch to the window you want the agent to see immediately!")
    print("Waiting 3 seconds before starting...")
    time.sleep(3)

    result = loop.run_task(task, max_steps=args.max_steps)
    
    print("\n=== Task Finished ===")
    print(f"Success: {result.success}")
    print(f"Steps taken: {result.steps}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run agent on real desktop (Dry Run).")
    parser.add_argument("--instruction", type=str, default="Describe what you see on the screen and click the Start menu icon.", help="Task instruction")
    parser.add_argument("--model", type=str, default="Qwen/Qwen3-VL-8B-Instruct")
    parser.add_argument("--base_url", type=str, default="http://127.0.0.1:8000/v1/chat/completions")
    parser.add_argument("--max-steps", type=int, default=3)
    
    args = parser.parse_args()
    run_real_task(args)
