#!/usr/bin/env python3
"""
Run the Agent on the REAL Windows Desktop WITH EXECUTION.
WARNING: This script will ACTUALLY CONTROL YOUR MOUSE AND KEYBOARD!
"""

import sys
import time
import json
import argparse
from pathlib import Path
from PIL import Image, ImageGrab
import pyautogui

# Ensure framework package is importable
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from framework.core import AgentConfig, AgentLoop, QwenOSWorldAgent
from framework.core.model_client import create_model_client
from framework.core.observation import Observation
from framework.core.prompt_builder import PromptBuilder
from framework.actions.grounding import GroundingResolver

# Safety: Add a small pause to prevent too-fast actions
pyautogui.PAUSE = 0.5

class ExecutableDesktopEnv:
    """
    Environment that ACTUALLY executes actions on the real desktop.
    WARNING: This will move your mouse and type on your keyboard!
    """
    def __init__(self):
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
            self.original_size = None
            
        self.width, self.height = self.screenshot.size
        print(f"\n[Env] Captured screenshot: {self.width}x{self.height}")
        if self.original_size:
            print(f"[Env] Original size: {self.original_size[0]}x{self.original_size[1]} (scaled)")

    def reset(self, task_config):
        print(f"\n[Env] Resetting for task: {task_config.get('instruction')}")
        self._update_screenshot()
        return Observation(
            screenshot=self.screenshot,
            marks={},
            som_elements=[],
            original_size=self.original_size
        )

    def step(self, action):
        action_type = action.get('action', '')
        print(f"\n{'='*50}")
        print(f"[Env] Executing: {action_type}")
        print(f"[Env] Payload: {json.dumps(action, indent=2)}")
        print(f"{'='*50}")

        try:
            # Handle different action types
            if action_type == "MOVE_CURSOR":
                coord = action.get('coordinate')
                if coord:
                    pyautogui.moveTo(coord[0], coord[1], duration=0.3)
                    print(f"✓ Moved cursor to {coord}")
            
            elif action_type == "LEFT_CLICK":
                coord = action.get('coordinate')
                if coord:
                    pyautogui.click(coord[0], coord[1])
                    print(f"✓ Clicked at {coord}")
                else:
                    pyautogui.click()
                    print(f"✓ Clicked at current position")
            
            elif action_type == "RIGHT_CLICK":
                coord = action.get('coordinate')
                if coord:
                    pyautogui.rightClick(coord[0], coord[1])
                    print(f"✓ Right-clicked at {coord}")
                else:
                    pyautogui.rightClick()
                    print(f"✓ Right-clicked at current position")
            
            elif action_type == "DOUBLE_CLICK":
                coord = action.get('coordinate')
                if coord:
                    pyautogui.doubleClick(coord[0], coord[1])
                    print(f"✓ Double-clicked at {coord}")
                else:
                    pyautogui.doubleClick()
                    print(f"✓ Double-clicked at current position")
            
            elif action_type == "TYPE":
                text = action.get('text', '')
                pyautogui.write(text, interval=0.05)
                print(f"✓ Typed: {text}")
            
            elif action_type == "PRESS_KEY":
                key = action.get('key', '')
                pyautogui.press(key)
                print(f"✓ Pressed key: {key}")
            
            elif action_type == "HOTKEY":
                keys = action.get('keys', [])
                pyautogui.hotkey(*keys)
                print(f"✓ Pressed hotkey: {'+'.join(keys)}")
            
            elif action_type == "SCROLL_UP":
                amount = action.get('scroll_amount', 3)
                pyautogui.scroll(amount)
                print(f"✓ Scrolled up {amount} clicks")
            
            elif action_type == "SCROLL_DOWN":
                amount = action.get('scroll_amount', 3)
                pyautogui.scroll(-amount)
                print(f"✓ Scrolled down {amount} clicks")
            
            elif action_type == "WAIT":
                duration = action.get('metadata', {}).get('duration', 1)
                time.sleep(duration)
                print(f"✓ Waited {duration}s")
            
            elif action_type == "DONE":
                print("✓ Task completed")
                return self.reset({}), 0.0, True, {"success": True}
            
            elif action_type == "FAIL":
                print("✗ Task failed")
                return self.reset({}), 0.0, True, {"success": False}
            
            else:
                print(f"⚠ Unknown action: {action_type}")
        
        except Exception as e:
            print(f"✗ Error executing action: {e}")
        
        # Wait a bit and take new screenshot
        time.sleep(1)
        self._update_screenshot()
        
        obs = Observation(
            screenshot=self.screenshot,
            marks={},
            som_elements=[],
            original_size=self.original_size
        )
        return obs, 0.0, False, {}


def run_real_task(args):
    print("\n" + "!"*60)
    print("⚠️  WARNING: EXECUTION MODE ENABLED")
    print("⚠️  The agent will CONTROL your mouse and keyboard!")
    print("⚠️  Move your mouse to the TOP-LEFT corner to emergency stop.")
    print("!"*60)
    print("\nStarting in 5 seconds... (Press Ctrl+C to cancel)")
    
    try:
        for i in range(5, 0, -1):
            print(f"{i}...", end=" ", flush=True)
            time.sleep(1)
        print("\n")
    except KeyboardInterrupt:
        print("\n\nCancelled by user.")
        return
    
    # Set up PyAutoGUI failsafe
    pyautogui.FAILSAFE = True  # Move mouse to corner to stop
    
    client = create_model_client(
        "qwen_vl",
        model=args.model,
        base_url=args.base_url,
        api_key=args.api_key,
    )
    
    prompt_builder = PromptBuilder(mode="coordinate")
    
    agent = QwenOSWorldAgent(
        model_client=client,
        config=AgentConfig(max_steps=args.max_steps, temperature=0.1),
        prompt_builder=prompt_builder,
        grounder=GroundingResolver()
    )
    
    env = ExecutableDesktopEnv()
    loop = AgentLoop(agent=agent, env=env, observation_adapter=lambda obs: obs)

    task = {
        "id": "real_desktop_exec",
        "instruction": args.instruction
    }

    print(f"\n=== Running Task (EXECUTION MODE) ===")
    print(f"Instruction: {task['instruction']}")
    print(f"Max steps: {args.max_steps}")
    print("\n")

    try:
        result = loop.run_task(task, max_steps=args.max_steps)
        
        print("\n" + "="*60)
        print("=== Task Finished ===")
        print(f"Success: {result.success}")
        print(f"Steps taken: {result.steps}")
        print("="*60)
    except pyautogui.FailSafeException:
        print("\n\n🛑 EMERGENCY STOP: Mouse moved to corner!")
        print("Task aborted for safety.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="⚠️ Run agent on real desktop WITH EXECUTION. WARNING: This will control your computer!"
    )
    parser.add_argument(
        "--instruction", 
        type=str, 
        default="Open Notepad and type 'Hello from AI Agent'", 
        help="Task instruction"
    )
    parser.add_argument("--model", type=str, default="Qwen/Qwen3-VL-8B-Instruct")
    parser.add_argument("--base_url", type=str, default="http://127.0.0.1:8000/v1/chat/completions")
    parser.add_argument("--api-key", type=str, default="EMPTY", help="API Key for the model service")
    parser.add_argument("--max-steps", type=int, default=5)
    
    args = parser.parse_args()
    run_real_task(args)
