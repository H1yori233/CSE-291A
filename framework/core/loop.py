"""
Main execution loop for ECUA agent
Implements the Perception → Planning → Execution cycle
"""

import time
from pathlib import Path
from typing import Optional, Dict, Any

from framework.core.state import (
    AgentState, 
    create_observation, 
    create_action_result, 
    create_planning_result
)
from framework.core.model_client import ModelClient
from framework.core.prompts import create_messages, detect_app_open, extract_output_files
from framework.core.parser import parse_and_validate
from framework.perception.capture import get_screen_capture
from framework.perception.ocr import get_ocr_manager
from framework.actions.executor import get_executor
from framework.actions.schema import ActionList
from framework.utils.log import get_logger


class AgentLoop:
    """
    Main agent execution loop.
    Coordinates perception, planning, and execution.
    """
    
    def __init__(
        self,
        model_client: ModelClient,
        verbose: bool = True,
        run_dir: Optional[str] = None,
        action_delay: float = 0.5,
        ocr_engine: str = 'tesseract'
    ):
        """
        Initialize the agent loop.
        
        Args:
            model_client: LLM client for planning
            verbose: Whether to log verbosely
            run_dir: Directory for logs and screenshots
            action_delay: Delay between actions
            ocr_engine: OCR engine to use ('tesseract' or 'paddle')
        """
        self.model = model_client
        self.logger = get_logger(run_dir=run_dir, verbose=verbose)
        self.screen_capture = get_screen_capture()
        self.ocr = get_ocr_manager(engine=ocr_engine)
        self.executor = get_executor(delay=action_delay)
        self.verbose = verbose
    
    def run_task(
        self,
        task_description: str,
        max_steps: int = 20,
        auto_success_check: bool = False,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Run a complete task execution.
        
        Args:
            task_description: Description of the task to complete
            max_steps: Maximum number of steps to take
            auto_success_check: Whether to automatically check for success (experimental)
            metadata: Optional metadata about the task
            
        Returns:
            Dict with execution results and statistics
        """
        self.logger.info(f"Starting task: {task_description}")
        self.logger.info(f"Max steps: {max_steps}")
        self.logger.info(f"Model: {self.model.get_model_name()}")
        
        # Initialize state
        state = AgentState(
            task_description=task_description,
            max_steps=max_steps,
            metadata=metadata
        )
        
        try:
            # Main loop
            while not state.is_budget_exhausted() and not state.completed:
                state.increment_step()
                self.logger.step(state.current_step, f"Starting step {state.current_step}/{max_steps}")
                
                # 1. Perception
                observation = self._perception_step(state)
                state.add_observation(observation)
                
                # Check if app is already open (for "Open [App]" tasks)
                if detect_app_open(state.task_description, observation.ocr_text):
                    self.logger.info("Application appears to be already open - task complete")
                    state.mark_completed(success=True, reason="Application already open")
                    break
                
                # 2. Planning
                planning_result = self._planning_step(state, observation)
                state.add_planning_result(planning_result)
                
                # Check for parsing errors
                if planning_result.parse_errors:
                    self.logger.warning(f"Planning errors: {planning_result.parse_errors}")
                    # Continue anyway - might be recoverable
                
                # If no actions planned, check if we're done
                if not planning_result.parsed_actions:
                    self.logger.info("No actions to execute - checking if task is complete")
                    
                    # Verify output files if task mentions file creation
                    output_files = extract_output_files(state.task_description)
                    if output_files:
                        self.logger.info(f"Task mentions output files: {output_files}")
                        missing_files = []
                        for file_path in output_files:
                            expanded_path = Path(file_path).expanduser()
                            if not expanded_path.exists():
                                missing_files.append(str(expanded_path))
                        
                        if missing_files:
                            self.logger.warning(
                                f"Task marked complete but output files missing: {missing_files}. "
                                f"Continuing execution..."
                            )
                            # Don't mark as complete - continue to try creating files
                        else:
                            self.logger.info("All output files exist - task complete")
                            state.mark_completed(success=True, reason="No more actions needed and all output files exist")
                            break
                    else:
                        # No file verification needed
                        state.mark_completed(success=True, reason="No more actions needed")
                        break
                
                # 3. Execution
                action_results = self._execution_step(state, planning_result.parsed_actions, observation)
                for result in action_results:
                    state.add_action_result(result)
                
                # 4. Check for completion (optional)
                if auto_success_check and state.current_step % 5 == 0:
                    # Periodically check if task is complete
                    # This is experimental and adds overhead
                    pass
            
            # Task finished
            if state.is_budget_exhausted() and not state.completed:
                self.logger.warning("Step budget exhausted")
                state.mark_completed(success=False, reason="Step budget exhausted")
            elif not state.completed:
                # Assume success if we got here without failure
                state.mark_completed(success=True, reason="Task completed")
            
        except KeyboardInterrupt:
            self.logger.warning("Task interrupted by user")
            state.mark_completed(success=False, reason="Interrupted by user")
        except Exception as e:
            self.logger.error(f"Task failed with error: {str(e)}")
            state.mark_completed(success=False, reason=f"Error: {str(e)}")
            raise
        finally:
            # Save summary
            self._save_summary(state)
        
        return state.to_dict()
    
    def _perception_step(self, state: AgentState):
        """
        Execute perception step: capture screenshot and run OCR.
        
        Args:
            state: Current agent state
            
        Returns:
            ObservationState
        """
        self.logger.info("Capturing screenshot...")
        
        # Capture screenshot
        screenshot = self.screen_capture.capture_screenshot()
        
        # Save screenshot
        self.logger.save_screenshot(
            screenshot,
            state.current_step,
            label="screen"
        )
        
        # Run OCR
        self.logger.info("Running OCR...")
        ocr_result = self.ocr.process_screenshot(screenshot, include_boxes=True)
        
        ocr_text = ocr_result['text']
        ocr_regions = ocr_result['regions']
        
        self.logger.log_perception(
            state.current_step,
            ocr_text,
            len(ocr_regions)
        )
        
        # Create observation
        observation = create_observation(
            screenshot=screenshot,
            ocr_text=ocr_text,
            ocr_regions=ocr_regions
        )
        
        return observation
    
    def _planning_step(self, state: AgentState, observation):
        """
        Execute planning step: get next actions from LLM.
        
        Args:
            state: Current agent state
            observation: Current observation
            
        Returns:
            PlanningResult
        """
        self.logger.info("Planning next actions...")
        
        # Create prompt
        messages = create_messages(
            task_description=state.task_description,
            current_screen=observation.ocr_text,
            action_history=state.get_action_history(),
            step=state.current_step,
            max_steps=state.max_steps
        )
        
        # Call LLM
        start_time = time.time()
        try:
            response = self.model.generate(
                messages=messages,
                temperature=0.0,
                max_tokens=2000
            )
            planning_time = time.time() - start_time
            
            self.logger.info(f"Planning completed in {planning_time:.2f}s")
            
        except Exception as e:
            self.logger.error(f"Planning failed: {str(e)}")
            # Return empty planning result
            return create_planning_result(
                raw_response="",
                parsed_actions=[],
                parse_errors=[f"LLM call failed: {str(e)}"],
                model_name=self.model.get_model_name(),
                planning_time=time.time() - start_time
            )
        
        # Parse response
        action_list, errors = parse_and_validate(response)
        
        # Convert to dict format
        parsed_actions = [action.model_dump() for action in action_list.actions]
        
        # Limit actions per step to prevent over-planning (max 5 actions)
        # This encourages incremental planning and better adaptation
        MAX_ACTIONS_PER_STEP = 5
        if len(parsed_actions) > MAX_ACTIONS_PER_STEP:
            self.logger.warning(
                f"Too many actions planned ({len(parsed_actions)}). "
                f"Limiting to {MAX_ACTIONS_PER_STEP} actions per step for better incremental planning."
            )
            parsed_actions = parsed_actions[:MAX_ACTIONS_PER_STEP]
        
        # Log plan
        self.logger.log_plan(
            state.current_step,
            response,
            parsed_actions,
            errors[0] if errors else None
        )
        
        # Create planning result
        planning_result = create_planning_result(
            raw_response=response,
            parsed_actions=parsed_actions,
            parse_errors=errors,
            model_name=self.model.get_model_name(),
            planning_time=planning_time
        )
        
        return planning_result
    
    def _execution_step(self, state: AgentState, actions, observation):
        """
        Execute actions step.
        
        Args:
            state: Current agent state
            actions: List of action dicts to execute
            observation: Current observation (for target_text resolution)
            
        Returns:
            List of ActionResult objects
        """
        self.logger.info(f"Executing {len(actions)} action(s)...")
        
        results = []
        
        for i, action_dict in enumerate(actions):
            self.logger.info(f"Action {i+1}/{len(actions)}: {action_dict.get('action')}")
            
            # Convert dict to Action object
            from framework.actions.schema import Action
            try:
                action = Action(**action_dict)
            except Exception as e:
                # Invalid action format
                result = create_action_result(
                    action=action_dict,
                    success=False,
                    message=f"Invalid action format: {str(e)}"
                )
                results.append(result)
                self.logger.log_action(state.current_step, action_dict, "failed", str(e))
                continue
            
            # Execute action
            start_time = time.time()
            exec_result = self.executor.execute(
                action,
                ocr_results=observation.ocr_regions
            )
            execution_time = time.time() - start_time
            
            # Create result
            result = create_action_result(
                action=action_dict,
                success=exec_result['success'],
                message=exec_result['message'],
                execution_time=execution_time,
                **{k: v for k, v in exec_result.items() if k not in ['success', 'message']}
            )
            results.append(result)
            
            # Log action
            status = "executed" if result.success else "failed"
            error = None if result.success else result.message
            self.logger.log_action(state.current_step, action_dict, status, error)
        
        return results
    
    def _save_summary(self, state: AgentState):
        """
        Save execution summary.
        
        Args:
            state: Final agent state
        """
        stats = state.get_statistics()
        
        self.logger.save_summary(
            task_description=state.task_description,
            success=state.success,
            total_steps=state.current_step,
            execution_time=state.get_execution_time(),
            metrics=stats
        )


def run_task(
    task_description: str,
    model_client: ModelClient,
    max_steps: int = 20,
    verbose: bool = True,
    run_dir: Optional[str] = None,
    action_delay: float = 0.5,
    ocr_engine: str = 'tesseract',
    metadata: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    Convenience function to run a task with default settings.
    
    Args:
        task_description: Description of the task to complete
        model_client: LLM client for planning
        max_steps: Maximum number of steps
        verbose: Whether to log verbosely
        run_dir: Directory for logs
        action_delay: Delay between actions
        ocr_engine: OCR engine to use
        metadata: Optional metadata
        
    Returns:
        Dict with execution results
        
    Example:
        from agent.core.model_client import create_model_client
        from agent.core.loop import run_task
        
        model = create_model_client('openai', model='gpt-4o')
        result = run_task(
            "Open the Downloads folder and list files",
            model_client=model,
            max_steps=10
        )
        
        print(f"Success: {result['success']}")
        print(f"Steps taken: {result['current_step']}")
    """
    loop = AgentLoop(
        model_client=model_client,
        verbose=verbose,
        run_dir=run_dir,
        action_delay=action_delay,
        ocr_engine=ocr_engine
    )
    
    return loop.run_task(
        task_description=task_description,
        max_steps=max_steps,
        metadata=metadata
    )

