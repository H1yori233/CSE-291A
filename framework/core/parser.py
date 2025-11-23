"""
JSON parser for LLM output
Handles parsing and validation of action JSON from LLM responses
"""

import json
import re
from typing import Dict, List, Optional, Tuple
from pydantic import ValidationError

from framework.actions.schema import ActionList, Action


class ParserError(Exception):
    """Exception raised when parsing fails"""
    pass


def extract_json_from_text(text: str) -> str:
    """
    Extract JSON from text that might contain markdown or other formatting.
    
    Args:
        text: Raw text that might contain JSON
        
    Returns:
        Extracted JSON string
        
    Raises:
        ParserError: If no JSON found
    """
    # Remove markdown code blocks
    text = re.sub(r'```json\s*', '', text)
    text = re.sub(r'```\s*', '', text)
    
    # Try to find JSON object or array
    # Look for outermost braces/brackets
    json_match = re.search(r'(\{.*\}|\[.*\])', text, re.DOTALL)
    
    if json_match:
        return json_match.group(1)
    
    # If no match, return original text (will fail later with better error)
    return text.strip()


def parse_action_json(json_str: str) -> ActionList:
    """
    Parse JSON string into ActionList.
    
    Args:
        json_str: JSON string containing actions
        
    Returns:
        Validated ActionList object
        
    Raises:
        ParserError: If parsing or validation fails
    """
    try:
        # Extract JSON from potentially formatted text
        clean_json = extract_json_from_text(json_str)
        
        # Parse JSON
        try:
            data = json.loads(clean_json)
        except json.JSONDecodeError as e:
            raise ParserError(f"Invalid JSON: {str(e)}\nText: {json_str[:200]}")
        
        # Validate structure
        if not isinstance(data, dict):
            raise ParserError(f"Expected JSON object, got {type(data)}")
        
        if 'actions' not in data:
            raise ParserError("JSON missing 'actions' key")
        
        if not isinstance(data['actions'], list):
            raise ParserError(f"'actions' must be a list, got {type(data['actions'])}")
        
        # Validate using Pydantic
        try:
            action_list = ActionList(**data)
            return action_list
        except ValidationError as e:
            raise ParserError(f"Action validation failed: {str(e)}")
    
    except ParserError:
        raise
    except Exception as e:
        raise ParserError(f"Unexpected parsing error: {str(e)}")


def parse_llm_response(response: str) -> Tuple[ActionList, Optional[str]]:
    """
    Parse LLM response into ActionList.
    
    Args:
        response: Raw LLM response text
        
    Returns:
        Tuple of (ActionList, error_message)
        If parsing succeeds, error_message is None
        If parsing fails, ActionList contains empty actions and error_message explains why
    """
    try:
        action_list = parse_action_json(response)
        return action_list, None
    except ParserError as e:
        # Return empty action list and error message
        return ActionList(actions=[]), str(e)
    except Exception as e:
        return ActionList(actions=[]), f"Unexpected error: {str(e)}"


def parse_success_check(response: str) -> Tuple[bool, str]:
    """
    Parse success check response from LLM.
    
    Args:
        response: Raw LLM response
        
    Returns:
        Tuple of (completed: bool, reason: str)
    """
    try:
        clean_json = extract_json_from_text(response)
        data = json.loads(clean_json)
        
        completed = data.get('completed', False)
        reason = data.get('reason', 'No reason provided')
        
        return completed, reason
    except Exception as e:
        # If parsing fails, assume not completed
        return False, f"Failed to parse success check: {str(e)}"


def validate_action(action: Action) -> Tuple[bool, Optional[str]]:
    """
    Validate an individual action for common issues.
    
    Args:
        action: Action to validate
        
    Returns:
        Tuple of (is_valid: bool, error_message: Optional[str])
    """
    action_type = action.action
    
    # Check required fields for each action type
    if action_type in ["CLICK", "MOVE"]:
        if action.x is None and action.y is None and action.target_text is None:
            return False, f"{action_type} requires either (x,y) or target_text"
    
    elif action_type == "SCROLL":
        if action.amount is None:
            return False, "SCROLL requires amount"
    
    elif action_type == "TYPE":
        if not action.arg:
            return False, "TYPE requires arg (text to type)"
    
    elif action_type == "KEY":
        if not action.arg:
            return False, "KEY requires arg (key to press)"
    
    elif action_type in ["FOCUS_APP", "OPEN", "EXECUTE", "VERIFY_FILE"]:
        if not action.arg:
            return False, f"{action_type} requires arg"
    
    elif action_type == "WAIT":
        if action.amount is None:
            action.amount = 1  # Default wait time
    
    return True, None


def validate_action_list(action_list: ActionList) -> List[str]:
    """
    Validate all actions in an ActionList.
    
    Args:
        action_list: ActionList to validate
        
    Returns:
        List of error messages (empty if all valid)
    """
    errors = []
    
    for i, action in enumerate(action_list.actions):
        is_valid, error = validate_action(action)
        if not is_valid:
            errors.append(f"Action {i+1}: {error}")
    
    return errors


# Convenience function for the main loop
def parse_and_validate(response: str) -> Tuple[ActionList, List[str]]:
    """
    Parse and validate LLM response in one step.
    
    Args:
        response: Raw LLM response
        
    Returns:
        Tuple of (ActionList, list of errors/warnings)
    """
    action_list, parse_error = parse_llm_response(response)
    
    if parse_error:
        return action_list, [f"Parse error: {parse_error}"]
    
    validation_errors = validate_action_list(action_list)
    
    return action_list, validation_errors

