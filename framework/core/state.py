"""
State management for the ECUA agent
Tracks observation, history, and step budget
"""

from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from PIL import Image


@dataclass
class ObservationState:
    """
    Represents the current observation of the environment.
    """
    screenshot: Optional[Image.Image] = None
    ocr_text: str = ""
    ocr_regions: List[Dict] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    
    def has_text(self) -> bool:
        """Check if any text was detected"""
        return bool(self.ocr_text.strip())
    
    def num_regions(self) -> int:
        """Get number of detected text regions"""
        return len(self.ocr_regions)


@dataclass
class ActionResult:
    """
    Represents the result of executing an action.
    """
    action: Dict[str, Any]
    success: bool
    message: str
    timestamp: datetime = field(default_factory=datetime.now)
    execution_time: float = 0.0  # seconds
    additional_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PlanningResult:
    """
    Represents the result of a planning step.
    """
    raw_response: str
    parsed_actions: List[Dict]
    parse_errors: List[str]
    timestamp: datetime = field(default_factory=datetime.now)
    model_name: str = ""
    planning_time: float = 0.0  # seconds


class AgentState:
    """
    Manages the complete state of the agent during execution.
    Tracks observations, actions, planning, and metrics.
    """
    
    def __init__(
        self,
        task_description: str,
        max_steps: int = 20,
        metadata: Optional[Dict] = None
    ):
        """
        Initialize agent state.
        
        Args:
            task_description: Description of the task to complete
            max_steps: Maximum number of steps allowed
            metadata: Optional metadata about the run
        """
        self.task_description = task_description
        self.max_steps = max_steps
        self.metadata = metadata or {}
        
        # Tracking
        self.current_step = 0
        self.start_time = datetime.now()
        self.end_time: Optional[datetime] = None
        
        # State history
        self.observations: List[ObservationState] = []
        self.action_results: List[ActionResult] = []
        self.planning_results: List[PlanningResult] = []
        
        # Current state
        self.current_observation: Optional[ObservationState] = None
        
        # Completion status
        self.completed = False
        self.success = False
        self.failure_reason: Optional[str] = None
    
    def add_observation(self, observation: ObservationState):
        """Add a new observation to history"""
        self.observations.append(observation)
        self.current_observation = observation
    
    def add_action_result(self, result: ActionResult):
        """Add an action result to history"""
        self.action_results.append(result)
    
    def add_planning_result(self, result: PlanningResult):
        """Add a planning result to history"""
        self.planning_results.append(result)
    
    def increment_step(self):
        """Increment the step counter"""
        self.current_step += 1
    
    def is_budget_exhausted(self) -> bool:
        """Check if step budget is exhausted"""
        return self.current_step >= self.max_steps
    
    def remaining_steps(self) -> int:
        """Get number of remaining steps"""
        return max(0, self.max_steps - self.current_step)
    
    def mark_completed(self, success: bool, reason: Optional[str] = None):
        """
        Mark the task as completed.
        
        Args:
            success: Whether the task succeeded
            reason: Optional reason for failure
        """
        self.completed = True
        self.success = success
        self.end_time = datetime.now()
        if not success and reason:
            self.failure_reason = reason
    
    def get_action_history(self) -> List[Dict]:
        """
        Get action history in a format suitable for prompts.
        
        Returns:
            List of action dicts
        """
        return [result.action for result in self.action_results]
    
    def get_execution_time(self) -> float:
        """
        Get total execution time in seconds.
        
        Returns:
            Execution time in seconds
        """
        end = self.end_time or datetime.now()
        return (end - self.start_time).total_seconds()
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get execution statistics.
        
        Returns:
            Dict with various statistics
        """
        total_actions = len(self.action_results)
        successful_actions = sum(1 for r in self.action_results if r.success)
        failed_actions = total_actions - successful_actions
        
        planning_time = sum(p.planning_time for p in self.planning_results)
        action_time = sum(a.execution_time for a in self.action_results)
        
        return {
            'total_steps': self.current_step,
            'max_steps': self.max_steps,
            'total_actions': total_actions,
            'successful_actions': successful_actions,
            'failed_actions': failed_actions,
            'total_observations': len(self.observations),
            'total_planning_calls': len(self.planning_results),
            'execution_time': self.get_execution_time(),
            'planning_time': planning_time,
            'action_time': action_time,
            'completed': self.completed,
            'success': self.success,
            'failure_reason': self.failure_reason,
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert state to dictionary for serialization.
        
        Returns:
            Dict representation of state
        """
        return {
            'task_description': self.task_description,
            'max_steps': self.max_steps,
            'current_step': self.current_step,
            'completed': self.completed,
            'success': self.success,
            'failure_reason': self.failure_reason,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'statistics': self.get_statistics(),
            'metadata': self.metadata,
            'action_history': self.get_action_history(),
        }
    
    def __repr__(self) -> str:
        """String representation of state"""
        status = "SUCCESS" if self.success else "FAILED" if self.completed else "RUNNING"
        return (
            f"AgentState(task='{self.task_description[:50]}...', "
            f"step={self.current_step}/{self.max_steps}, "
            f"status={status})"
        )


def create_observation(
    screenshot: Image.Image,
    ocr_text: str,
    ocr_regions: List[Dict]
) -> ObservationState:
    """
    Factory function to create an ObservationState.
    
    Args:
        screenshot: Screenshot image
        ocr_text: Extracted OCR text
        ocr_regions: List of OCR regions with bounding boxes
        
    Returns:
        ObservationState instance
    """
    return ObservationState(
        screenshot=screenshot,
        ocr_text=ocr_text,
        ocr_regions=ocr_regions,
        timestamp=datetime.now()
    )


def create_action_result(
    action: Dict[str, Any],
    success: bool,
    message: str,
    execution_time: float = 0.0,
    **additional_data
) -> ActionResult:
    """
    Factory function to create an ActionResult.
    
    Args:
        action: Action that was executed
        success: Whether execution succeeded
        message: Result message
        execution_time: Time taken to execute
        **additional_data: Additional data to store
        
    Returns:
        ActionResult instance
    """
    return ActionResult(
        action=action,
        success=success,
        message=message,
        execution_time=execution_time,
        additional_data=additional_data,
        timestamp=datetime.now()
    )


def create_planning_result(
    raw_response: str,
    parsed_actions: List[Dict],
    parse_errors: List[str],
    model_name: str = "",
    planning_time: float = 0.0
) -> PlanningResult:
    """
    Factory function to create a PlanningResult.
    
    Args:
        raw_response: Raw response from LLM
        parsed_actions: Successfully parsed actions
        parse_errors: List of parse errors
        model_name: Name of the model used
        planning_time: Time taken for planning
        
    Returns:
        PlanningResult instance
    """
    return PlanningResult(
        raw_response=raw_response,
        parsed_actions=parsed_actions,
        parse_errors=parse_errors,
        model_name=model_name,
        planning_time=planning_time,
        timestamp=datetime.now()
    )

