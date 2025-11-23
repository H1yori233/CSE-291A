"""
Action Schema for ECUA Agent
Defines OSWorld-Human style action format
"""

from typing import Optional, List, Literal
from pydantic import BaseModel, Field


class Action(BaseModel):
    """
    Single action that the agent can perform.
    Follows OSWorld-Human action schema.
    """
    action: Literal[
        "CLICK", "MOVE", "SCROLL", "TYPE", "KEY", 
        "FOCUS_APP", "OPEN", "EXECUTE", "VERIFY_FILE", "WAIT"
    ] = Field(..., description="Type of action to perform")
    
    x: Optional[int] = Field(None, description="X coordinate for mouse actions")
    y: Optional[int] = Field(None, description="Y coordinate for mouse actions")
    
    target_text: Optional[str] = Field(
        None, 
        description="Text to locate on screen (will be resolved to coordinates)"
    )
    
    arg: Optional[str] = Field(
        None, 
        description="Argument for action (e.g., text to type, key to press, command to execute)"
    )
    
    amount: Optional[int] = Field(
        None, 
        description="Amount for scroll action"
    )

    class Config:
        extra = "forbid"  # Don't allow extra fields


class ActionList(BaseModel):
    """
    List of actions to be executed in sequence.
    This is the format returned by the LLM planner.
    """
    actions: List[Action] = Field(..., description="Ordered list of actions to execute")
    
    class Config:
        extra = "forbid"


# Action type descriptions for the LLM prompt
ACTION_DESCRIPTIONS = {
    "CLICK": "Click at (x, y) coordinates or at target_text location",
    "MOVE": "Move mouse cursor to (x, y) coordinates",
    "SCROLL": "Scroll by amount (positive=down, negative=up)",
    "TYPE": "Type the string specified in arg",
    "KEY": "Press keyboard key(s) specified in arg (e.g., 'cmd+c', 'enter')",
    "FOCUS_APP": "Bring application to focus (arg = app name)",
    "OPEN": "Open file or URL (arg = path or URL)",
    "EXECUTE": "Execute shell command (arg = command)",
    "VERIFY_FILE": "Check if file exists (arg = file path)",
    "WAIT": "Wait for amount seconds (amount = seconds)",
}


def get_action_schema_description() -> str:
    """
    Returns a formatted description of the action schema for LLM prompts.
    """
    lines = ["Available Actions:"]
    for action_type, description in ACTION_DESCRIPTIONS.items():
        lines.append(f"  - {action_type}: {description}")
    
    lines.append("\nAction Format:")
    lines.append('{')
    lines.append('  "actions": [')
    lines.append('    {')
    lines.append('      "action": "ACTION_TYPE",')
    lines.append('      "x": 100,  // optional, for mouse actions')
    lines.append('      "y": 200,  // optional, for mouse actions')
    lines.append('      "target_text": "Button",  // optional, text to find and click')
    lines.append('      "arg": "text or command",  // optional, depends on action')
    lines.append('      "amount": 5  // optional, for scroll/wait')
    lines.append('    }')
    lines.append('  ]')
    lines.append('}')
    
    return "\n".join(lines)


# Example actions for testing
EXAMPLE_ACTIONS = ActionList(
    actions=[
        Action(action="CLICK", x=320, y=540),
        Action(action="TYPE", arg="Hello World"),
        Action(action="KEY", arg="enter"),
    ]
)

