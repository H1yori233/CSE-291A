#!/usr/bin/env python3
"""
Simple example of using the ECUA agent
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from framework.core.loop import run_task
from framework.core.model_client import create_model_client


def main():
    """Run a simple example task"""
    
    # Create model client (using OpenAI API)
    print("Creating model client...")
    model = create_model_client('openai', model='gpt-4o')
    
    # Define task
    task = "Open Finder application"
    
    print(f"\nTask: {task}")
    print("="*60)
    
    # Run task
    result = run_task(
        task_description=task,
        model_client=model,
        max_steps=10,
        verbose=True
    )
    
    # Print result
    print("\n" + "="*60)
    print("RESULT")
    print("="*60)
    print(f"Success: {result['success']}")
    print(f"Steps taken: {result['current_step']}")
    print(f"Total actions: {result['statistics']['total_actions']}")
    print(f"Execution time: {result['statistics']['execution_time']:.2f}s")
    print(f"Run directory: {result.get('metadata', {}).get('run_dir', 'N/A')}")


if __name__ == '__main__':
    main()

