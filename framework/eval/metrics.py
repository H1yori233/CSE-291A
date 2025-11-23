"""
Evaluation metrics for ECUA agent
Calculates success rate, WES+, WES-, and resource usage
"""

import json
import psutil
import os
from typing import List, Dict, Any, Optional
from pathlib import Path
from dataclasses import dataclass
import pandas as pd


@dataclass
class TaskResult:
    """
    Result of a single task execution.
    """
    task_id: str
    task_description: str
    success: bool
    steps_taken: int
    max_steps: int
    execution_time: float  # seconds
    total_actions: int
    successful_actions: int
    failed_actions: int
    cpu_time: float = 0.0
    memory_peak_mb: float = 0.0
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class MetricsCalculator:
    """
    Calculates various metrics for agent evaluation.
    """
    
    @staticmethod
    def calculate_success_rate(results: List[TaskResult]) -> float:
        """
        Calculate overall success rate.
        
        Args:
            results: List of task results
            
        Returns:
            Success rate (0.0 to 1.0)
        """
        if not results:
            return 0.0
        
        successes = sum(1 for r in results if r.success)
        return successes / len(results)
    
    @staticmethod
    def calculate_wes_plus(results: List[TaskResult]) -> float:
        """
        Calculate WES+ (Weighted Efficiency Score - Positive).
        WES+ = (successes / total_tasks) * (1 - avg_steps_ratio_for_successes)
        
        Rewards completing tasks with fewer steps.
        
        Args:
            results: List of task results
            
        Returns:
            WES+ score (0.0 to 1.0)
        """
        if not results:
            return 0.0
        
        successful = [r for r in results if r.success]
        
        if not successful:
            return 0.0
        
        # Success rate
        success_rate = len(successful) / len(results)
        
        # Average step efficiency for successful tasks
        avg_steps_ratio = sum(r.steps_taken / r.max_steps for r in successful) / len(successful)
        efficiency = 1 - avg_steps_ratio
        
        # WES+ combines success rate and efficiency
        wes_plus = success_rate * efficiency
        
        return wes_plus
    
    @staticmethod
    def calculate_wes_minus(results: List[TaskResult]) -> float:
        """
        Calculate WES- (Weighted Efficiency Score - Negative).
        WES- = (failures / total_tasks) * avg_steps_ratio_for_failures
        
        Penalizes tasks that fail after many steps.
        Lower is better.
        
        Args:
            results: List of task results
            
        Returns:
            WES- score (0.0 to 1.0, lower is better)
        """
        if not results:
            return 0.0
        
        failed = [r for r in results if not r.success]
        
        if not failed:
            return 0.0
        
        # Failure rate
        failure_rate = len(failed) / len(results)
        
        # Average step ratio for failed tasks
        avg_steps_ratio = sum(r.steps_taken / r.max_steps for r in failed) / len(failed)
        
        # WES- combines failure rate and wasted steps
        wes_minus = failure_rate * avg_steps_ratio
        
        return wes_minus
    
    @staticmethod
    def calculate_average_steps(results: List[TaskResult], success_only: bool = False) -> float:
        """
        Calculate average steps taken.
        
        Args:
            results: List of task results
            success_only: Only count successful tasks
            
        Returns:
            Average steps taken
        """
        if not results:
            return 0.0
        
        if success_only:
            results = [r for r in results if r.success]
        
        if not results:
            return 0.0
        
        return sum(r.steps_taken for r in results) / len(results)
    
    @staticmethod
    def calculate_average_time(results: List[TaskResult], success_only: bool = False) -> float:
        """
        Calculate average execution time.
        
        Args:
            results: List of task results
            success_only: Only count successful tasks
            
        Returns:
            Average execution time in seconds
        """
        if not results:
            return 0.0
        
        if success_only:
            results = [r for r in results if r.success]
        
        if not results:
            return 0.0
        
        return sum(r.execution_time for r in results) / len(results)
    
    @staticmethod
    def calculate_action_success_rate(results: List[TaskResult]) -> float:
        """
        Calculate success rate of individual actions.
        
        Args:
            results: List of task results
            
        Returns:
            Action success rate (0.0 to 1.0)
        """
        total_actions = sum(r.total_actions for r in results)
        
        if total_actions == 0:
            return 0.0
        
        successful_actions = sum(r.successful_actions for r in results)
        
        return successful_actions / total_actions
    
    @staticmethod
    def generate_summary(results: List[TaskResult]) -> Dict[str, Any]:
        """
        Generate comprehensive metrics summary.
        
        Args:
            results: List of task results
            
        Returns:
            Dict with all metrics
        """
        calc = MetricsCalculator()
        
        return {
            'total_tasks': len(results),
            'successful_tasks': sum(1 for r in results if r.success),
            'failed_tasks': sum(1 for r in results if not r.success),
            'success_rate': calc.calculate_success_rate(results),
            'wes_plus': calc.calculate_wes_plus(results),
            'wes_minus': calc.calculate_wes_minus(results),
            'avg_steps': calc.calculate_average_steps(results),
            'avg_steps_success': calc.calculate_average_steps(results, success_only=True),
            'avg_time_seconds': calc.calculate_average_time(results),
            'avg_time_success_seconds': calc.calculate_average_time(results, success_only=True),
            'action_success_rate': calc.calculate_action_success_rate(results),
            'total_actions': sum(r.total_actions for r in results),
            'total_execution_time': sum(r.execution_time for r in results),
        }


def load_task_result_from_file(result_dir: str) -> Optional[TaskResult]:
    """
    Load a TaskResult from a result directory.
    
    Args:
        result_dir: Path to result directory containing summary.json
        
    Returns:
        TaskResult object or None if loading fails
    """
    result_path = Path(result_dir)
    summary_file = result_path / "summary.json"
    
    if not summary_file.exists():
        return None
    
    try:
        with open(summary_file, 'r') as f:
            data = json.load(f)
        
        # Extract task ID from directory name
        task_id = result_path.name
        
        # Create TaskResult
        result = TaskResult(
            task_id=task_id,
            task_description=data.get('task', ''),
            success=data.get('success', False),
            steps_taken=data.get('total_steps', 0),
            max_steps=data.get('metrics', {}).get('max_steps', 20),
            execution_time=data.get('execution_time', 0.0),
            total_actions=data.get('metrics', {}).get('total_actions', 0),
            successful_actions=data.get('metrics', {}).get('successful_actions', 0),
            failed_actions=data.get('metrics', {}).get('failed_actions', 0),
            metadata=data
        )
        
        return result
    except Exception as e:
        print(f"Error loading result from {result_dir}: {e}")
        return None


def load_results_from_directory(results_dir: str) -> List[TaskResult]:
    """
    Load all task results from a results directory.
    
    Args:
        results_dir: Path to directory containing result subdirectories
        
    Returns:
        List of TaskResult objects
    """
    results = []
    results_path = Path(results_dir)
    
    if not results_path.exists():
        return results
    
    # Look for subdirectories with summary.json
    for subdir in results_path.iterdir():
        if subdir.is_dir():
            result = load_task_result_from_file(str(subdir))
            if result:
                results.append(result)
    
    return results


def create_summary_dataframe(results: List[TaskResult]) -> pd.DataFrame:
    """
    Create a pandas DataFrame from task results.
    
    Args:
        results: List of task results
        
    Returns:
        DataFrame with task results
    """
    data = []
    
    for result in results:
        data.append({
            'task_id': result.task_id,
            'task_description': result.task_description,
            'success': result.success,
            'steps_taken': result.steps_taken,
            'max_steps': result.max_steps,
            'execution_time': result.execution_time,
            'total_actions': result.total_actions,
            'successful_actions': result.successful_actions,
            'failed_actions': result.failed_actions,
            'step_efficiency': result.steps_taken / result.max_steps if result.max_steps > 0 else 0,
        })
    
    return pd.DataFrame(data)


def save_metrics_report(
    results: List[TaskResult],
    output_file: str,
    format: str = 'json'
):
    """
    Save metrics report to file.
    
    Args:
        results: List of task results
        output_file: Output file path
        format: Output format ('json' or 'csv')
    """
    calc = MetricsCalculator()
    summary = calc.generate_summary(results)
    
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    if format == 'json':
        with open(output_path, 'w') as f:
            json.dump(summary, f, indent=2)
    elif format == 'csv':
        df = create_summary_dataframe(results)
        df.to_csv(output_path, index=False)
        
        # Also save summary metrics
        summary_path = output_path.parent / f"{output_path.stem}_summary.json"
        with open(summary_path, 'w') as f:
            json.dump(summary, f, indent=2)
    else:
        raise ValueError(f"Unknown format: {format}")


def print_metrics_summary(results: List[TaskResult]):
    """
    Print a formatted metrics summary.
    
    Args:
        results: List of task results
    """
    calc = MetricsCalculator()
    summary = calc.generate_summary(results)
    
    print("\n" + "="*60)
    print("ECUA AGENT EVALUATION METRICS")
    print("="*60)
    print(f"\nTotal Tasks: {summary['total_tasks']}")
    print(f"  ✓ Successful: {summary['successful_tasks']}")
    print(f"  ✗ Failed: {summary['failed_tasks']}")
    print(f"\nSuccess Rate: {summary['success_rate']:.2%}")
    print(f"\nEfficiency Metrics:")
    print(f"  WES+ (higher is better): {summary['wes_plus']:.3f}")
    print(f"  WES- (lower is better):  {summary['wes_minus']:.3f}")
    print(f"\nStep Metrics:")
    print(f"  Average steps (all): {summary['avg_steps']:.1f}")
    print(f"  Average steps (success only): {summary['avg_steps_success']:.1f}")
    print(f"\nTime Metrics:")
    print(f"  Average time (all): {summary['avg_time_seconds']:.1f}s")
    print(f"  Average time (success only): {summary['avg_time_success_seconds']:.1f}s")
    print(f"  Total execution time: {summary['total_execution_time']:.1f}s")
    print(f"\nAction Metrics:")
    print(f"  Total actions: {summary['total_actions']}")
    print(f"  Action success rate: {summary['action_success_rate']:.2%}")
    print("="*60 + "\n")

