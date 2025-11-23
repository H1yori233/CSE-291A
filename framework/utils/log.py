"""
Logging utilities for ECUA agent
Handles structured logging, screenshot saving, and action history
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from PIL import Image
import colorama
from colorama import Fore, Style

# Initialize colorama for cross-platform colored output
colorama.init(autoreset=True)


class AgentLogger:
    """
    Structured logger for agent execution.
    Saves screenshots, action history, and structured logs.
    """
    
    def __init__(self, run_dir: Optional[str] = None, verbose: bool = True):
        """
        Initialize the agent logger.
        
        Args:
            run_dir: Directory for this run's logs. If None, creates timestamped dir
            verbose: Whether to print logs to console
        """
        if run_dir is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            run_dir = f"results/run_{timestamp}"
        
        self.run_dir = Path(run_dir)
        self.run_dir.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories
        self.screenshot_dir = self.run_dir / "screenshots"
        self.screenshot_dir.mkdir(exist_ok=True)
        
        self.verbose = verbose
        self.step_count = 0
        self.action_history: List[Dict] = []
        self.events: List[Dict] = []
        
        # Setup file logger
        self.log_file = self.run_dir / "agent.log"
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.log_file),
                logging.StreamHandler() if verbose else logging.NullHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        self.info(f"Starting agent run in: {self.run_dir}")
    
    def info(self, message: str):
        """Log info message"""
        self.logger.info(message)
        if self.verbose:
            print(f"{Fore.CYAN}[INFO]{Style.RESET_ALL} {message}")
    
    def warning(self, message: str):
        """Log warning message"""
        self.logger.warning(message)
        if self.verbose:
            print(f"{Fore.YELLOW}[WARN]{Style.RESET_ALL} {message}")
    
    def error(self, message: str):
        """Log error message"""
        self.logger.error(message)
        if self.verbose:
            print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} {message}")
    
    def success(self, message: str):
        """Log success message"""
        self.logger.info(f"SUCCESS: {message}")
        if self.verbose:
            print(f"{Fore.GREEN}[SUCCESS]{Style.RESET_ALL} {message}")
    
    def step(self, step_num: int, message: str):
        """Log step message"""
        self.logger.info(f"Step {step_num}: {message}")
        if self.verbose:
            print(f"{Fore.MAGENTA}[STEP {step_num}]{Style.RESET_ALL} {message}")
    
    def save_screenshot(
        self, 
        image: Image.Image, 
        step_num: int, 
        label: str = "screen"
    ) -> str:
        """
        Save screenshot for a step.
        
        Args:
            image: PIL Image to save
            step_num: Step number
            label: Label for the screenshot
            
        Returns:
            Path to saved screenshot
        """
        filename = f"step_{step_num:03d}_{label}.png"
        filepath = self.screenshot_dir / filename
        image.save(filepath)
        self.info(f"Saved screenshot: {filename}")
        return str(filepath)
    
    def log_action(
        self, 
        step_num: int, 
        action: Dict[str, Any],
        status: str = "executed",
        error: Optional[str] = None
    ):
        """
        Log an action execution.
        
        Args:
            step_num: Step number
            action: Action dictionary
            status: Status (executed, failed, skipped)
            error: Error message if failed
        """
        action_log = {
            "step": step_num,
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "status": status,
            "error": error
        }
        self.action_history.append(action_log)
        
        action_str = json.dumps(action, indent=2)
        if status == "executed":
            self.info(f"Action executed: {action_str}")
        elif status == "failed":
            self.error(f"Action failed: {action_str}\nError: {error}")
        else:
            self.warning(f"Action {status}: {action_str}")
    
    def log_plan(
        self, 
        step_num: int, 
        plan: str,
        parsed_actions: Optional[List[Dict]] = None,
        parse_error: Optional[str] = None
    ):
        """
        Log LLM planning output.
        
        Args:
            step_num: Step number
            plan: Raw LLM output
            parsed_actions: Successfully parsed actions
            parse_error: Parse error if any
        """
        plan_log = {
            "step": step_num,
            "timestamp": datetime.now().isoformat(),
            "raw_plan": plan,
            "parsed_actions": parsed_actions,
            "parse_error": parse_error
        }
        
        # Save plan to file
        plan_file = self.run_dir / f"plan_step_{step_num:03d}.json"
        with open(plan_file, 'w') as f:
            json.dump(plan_log, f, indent=2)
        
        if parse_error:
            self.error(f"Plan parsing failed: {parse_error}")
        else:
            self.info(f"Plan received with {len(parsed_actions or [])} actions")
    
    def log_perception(
        self, 
        step_num: int,
        ocr_text: str,
        num_regions: int = 0
    ):
        """
        Log perception results.
        
        Args:
            step_num: Step number
            ocr_text: Full OCR text
            num_regions: Number of detected text regions
        """
        perception_file = self.run_dir / f"ocr_step_{step_num:03d}.txt"
        with open(perception_file, 'w') as f:
            f.write(ocr_text)
        
        self.info(f"OCR completed: {num_regions} text regions detected")
    
    def log_event(self, event_type: str, data: Dict[str, Any]):
        """
        Log a custom event.
        
        Args:
            event_type: Type of event
            data: Event data
        """
        event = {
            "timestamp": datetime.now().isoformat(),
            "type": event_type,
            "data": data
        }
        self.events.append(event)
    
    def save_summary(
        self,
        task_description: str,
        success: bool,
        total_steps: int,
        execution_time: float,
        metrics: Optional[Dict] = None
    ):
        """
        Save execution summary.
        
        Args:
            task_description: Description of the task
            success: Whether task succeeded
            total_steps: Number of steps taken
            execution_time: Total execution time in seconds
            metrics: Additional metrics
        """
        summary = {
            "task": task_description,
            "success": success,
            "total_steps": total_steps,
            "execution_time": execution_time,
            "timestamp": datetime.now().isoformat(),
            "run_dir": str(self.run_dir),
            "metrics": metrics or {},
            "action_count": len(self.action_history),
        }
        
        summary_file = self.run_dir / "summary.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        # Save action history
        history_file = self.run_dir / "action_history.json"
        with open(history_file, 'w') as f:
            json.dump(self.action_history, f, indent=2)
        
        # Save events
        events_file = self.run_dir / "events.json"
        with open(events_file, 'w') as f:
            json.dump(self.events, f, indent=2)
        
        if success:
            self.success(f"Task completed in {total_steps} steps ({execution_time:.2f}s)")
        else:
            self.error(f"Task failed after {total_steps} steps ({execution_time:.2f}s)")
        
        self.info(f"Summary saved to: {summary_file}")


def get_logger(run_dir: Optional[str] = None, verbose: bool = True) -> AgentLogger:
    """
    Factory function to create an AgentLogger.
    
    Args:
        run_dir: Directory for this run's logs
        verbose: Whether to print logs to console
        
    Returns:
        Configured AgentLogger instance
    """
    return AgentLogger(run_dir=run_dir, verbose=verbose)

