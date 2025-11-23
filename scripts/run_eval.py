#!/usr/bin/env python3
"""
Evaluation script for ECUA agent
Runs tasks from a task directory and generates evaluation metrics
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import List, Dict
import time

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from framework.core.loop import run_task
from framework.core.model_client import create_model_client
from framework.eval.metrics import (
    TaskResult, 
    MetricsCalculator, 
    save_metrics_report, 
    print_metrics_summary,
    create_summary_dataframe
)


def load_task_definitions(tasks_dir: str) -> List[Dict]:
    """
    Load task definitions from JSON files.
    
    Args:
        tasks_dir: Directory containing task JSON files
        
    Returns:
        List of task definition dicts
    """
    tasks = []
    tasks_path = Path(tasks_dir)
    
    if not tasks_path.exists():
        print(f"Error: Tasks directory not found: {tasks_dir}")
        return tasks
    
    # Load all JSON files
    for task_file in sorted(tasks_path.glob("*.json")):
        try:
            with open(task_file, 'r') as f:
                task_def = json.load(f)
                tasks.append(task_def)
        except Exception as e:
            print(f"Warning: Failed to load {task_file}: {e}")
    
    return tasks


def run_evaluation(
    tasks_dir: str,
    backend: str = 'openai',
    model: str = 'gpt-4o',
    max_steps: int = 20,
    output_dir: str = 'results',
    verbose: bool = True,
    action_delay: float = 0.5,
    ocr_engine: str = 'tesseract',
    limit: int = None
):
    """
    Run evaluation on a set of tasks.
    
    Args:
        tasks_dir: Directory containing task JSON files
        backend: LLM backend ('openai', 'ollama', etc.)
        model: Model name
        max_steps: Maximum steps per task
        output_dir: Directory for results
        verbose: Verbose logging
        action_delay: Delay between actions
        ocr_engine: OCR engine to use
        limit: Optional limit on number of tasks to run
    """
    # Load tasks
    print(f"Loading tasks from: {tasks_dir}")
    task_definitions = load_task_definitions(tasks_dir)
    
    if not task_definitions:
        print("No tasks found!")
        return
    
    if limit:
        task_definitions = task_definitions[:limit]
    
    print(f"Loaded {len(task_definitions)} task(s)")
    
    # Create model client
    print(f"Initializing {backend} model: {model}")
    try:
        if backend == 'openai':
            model_client = create_model_client('openai', model=model)
        elif backend == 'ollama':
            model_client = create_model_client('ollama', model=model)
        elif backend == 'llamacpp':
            model_client = create_model_client('llamacpp', model_path=model)
        elif backend == 'anthropic':
            model_client = create_model_client('anthropic', model=model)
        else:
            print(f"Error: Unknown backend: {backend}")
            return
    except Exception as e:
        print(f"Error: Failed to create model client: {e}")
        return
    
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Run tasks
    task_results = []
    
    for i, task_def in enumerate(task_definitions, 1):
        task_id = task_def.get('task_id', f'task_{i}')
        description = task_def.get('description', '')
        max_steps_task = task_def.get('max_steps', max_steps)
        
        print(f"\n{'='*70}")
        print(f"Task {i}/{len(task_definitions)}: {task_id}")
        print(f"Description: {description}")
        print(f"{'='*70}")
        
        # Create run directory
        run_dir = output_path / f"run_{task_id}_{int(time.time())}"
        
        # Run task
        try:
            result = run_task(
                task_description=description,
                model_client=model_client,
                max_steps=max_steps_task,
                verbose=verbose,
                run_dir=str(run_dir),
                action_delay=action_delay,
                ocr_engine=ocr_engine,
                metadata={
                    'task_id': task_id,
                    'task_definition': task_def
                }
            )
            
            # Create TaskResult
            stats = result.get('statistics', {})
            task_result = TaskResult(
                task_id=task_id,
                task_description=description,
                success=result.get('success', False),
                steps_taken=result.get('current_step', 0),
                max_steps=max_steps_task,
                execution_time=result.get('statistics', {}).get('execution_time', 0.0),
                total_actions=stats.get('total_actions', 0),
                successful_actions=stats.get('successful_actions', 0),
                failed_actions=stats.get('failed_actions', 0),
                metadata=result
            )
            
            task_results.append(task_result)
            
            # Print result
            status = "✓ SUCCESS" if task_result.success else "✗ FAILED"
            print(f"\n{status} - {task_result.steps_taken} steps, {task_result.execution_time:.1f}s")
            
        except KeyboardInterrupt:
            print("\nEvaluation interrupted by user")
            break
        except Exception as e:
            print(f"Error running task {task_id}: {e}")
            # Create failed result
            task_result = TaskResult(
                task_id=task_id,
                task_description=description,
                success=False,
                steps_taken=0,
                max_steps=max_steps_task,
                execution_time=0.0,
                total_actions=0,
                successful_actions=0,
                failed_actions=0,
                metadata={'error': str(e)}
            )
            task_results.append(task_result)
    
    # Generate metrics
    print(f"\n{'='*70}")
    print("EVALUATION COMPLETE")
    print(f"{'='*70}")
    
    if task_results:
        # Print summary
        print_metrics_summary(task_results)
        
        # Save metrics
        metrics_file = output_path / "evaluation_metrics.json"
        save_metrics_report(task_results, str(metrics_file), format='json')
        print(f"Metrics saved to: {metrics_file}")
        
        # Save CSV
        csv_file = output_path / "evaluation_results.csv"
        save_metrics_report(task_results, str(csv_file), format='csv')
        print(f"Results CSV saved to: {csv_file}")
    else:
        print("No results to report")


def main():
    parser = argparse.ArgumentParser(
        description='Run ECUA agent evaluation on a set of tasks'
    )
    
    parser.add_argument(
        '--tasks',
        type=str,
        default='tasks',
        help='Directory containing task JSON files (default: tasks)'
    )
    
    parser.add_argument(
        '--backend',
        type=str,
        default='openai',
        choices=['openai', 'ollama', 'llamacpp', 'anthropic'],
        help='LLM backend to use (default: openai)'
    )
    
    parser.add_argument(
        '--model',
        type=str,
        default='gpt-4o',
        help='Model name (default: gpt-4o)'
    )
    
    parser.add_argument(
        '--max-steps',
        type=int,
        default=20,
        help='Maximum steps per task (default: 20)'
    )
    
    parser.add_argument(
        '--output-dir',
        type=str,
        default='results',
        help='Output directory for results (default: results)'
    )
    
    parser.add_argument(
        '--action-delay',
        type=float,
        default=0.5,
        help='Delay between actions in seconds (default: 0.5)'
    )
    
    parser.add_argument(
        '--ocr-engine',
        type=str,
        default='tesseract',
        choices=['tesseract', 'paddle'],
        help='OCR engine to use (default: tesseract)'
    )
    
    parser.add_argument(
        '--limit',
        type=int,
        default=None,
        help='Limit number of tasks to run (default: all)'
    )
    
    parser.add_argument(
        '--quiet',
        action='store_true',
        help='Quiet mode (less verbose output)'
    )
    
    args = parser.parse_args()
    
    run_evaluation(
        tasks_dir=args.tasks,
        backend=args.backend,
        model=args.model,
        max_steps=args.max_steps,
        output_dir=args.output_dir,
        verbose=not args.quiet,
        action_delay=args.action_delay,
        ocr_engine=args.ocr_engine,
        limit=args.limit
    )


if __name__ == '__main__':
    main()

