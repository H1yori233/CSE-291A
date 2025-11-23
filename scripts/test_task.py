#!/usr/bin/env python3
"""
Test script to run a single task from a JSON file
"""

import json
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from framework.core.loop import run_task
from framework.core.model_client import create_model_client


def main():
    """Run a task from a JSON file"""
    
    # Load task - can specify task number as argument
    task_num = sys.argv[1] if len(sys.argv) > 1 else "01"
    task_file = Path(__file__).parent.parent / "tasks" / f"task_{task_num}.json"
    
    if not task_file.exists():
        print(f"Error: Task file not found: {task_file}")
        return
    
    with open(task_file, 'r') as f:
        task_def = json.load(f)
    
    # Get task description (try 'instruction' first, then 'description')
    task_description = task_def.get('instruction') or task_def.get('description') or task_def.get('task_name', '')
    
    print("="*70)
    print(f"Task: {task_def.get('task_name', 'Unknown')}")
    print(f"Description: {task_description}")
    print("="*70)
    print()
    
    # Create model client
    print("Creating model client...")
    model = create_model_client('openai', model='gpt-4o')
    
    # Run task with more steps for complex tasks
    print(f"\nRunning task: {task_description}")
    print("="*70)
    
    result = run_task(
        task_description=task_description,
        model_client=model,
        max_steps=30,  # More steps for complex tasks
        verbose=True,
        action_delay=1.0,  # Slightly longer delay for complex operations
        ocr_engine='tesseract'
    )
    
    # Print result
    print("\n" + "="*70)
    print("RESULT")
    print("="*70)
    print(f"Success: {result['success']}")
    print(f"Steps taken: {result['current_step']}")
    print(f"Total actions: {result['statistics']['total_actions']}")
    print(f"Execution time: {result['statistics']['execution_time']:.2f}s")
    if result.get('metadata', {}).get('run_dir'):
        print(f"Run directory: {result['metadata']['run_dir']}")
    print()


if __name__ == '__main__':
    main()

