"""
Prompt templates for the ECUA agent planner
"""

import re
from pathlib import Path
from typing import List, Dict, Optional
from framework.actions.schema import get_action_schema_description


SYSTEM_PROMPT = """You are an autonomous computer control agent. Your task is to control a computer to complete user-specified tasks by observing the screen and taking actions.

You will receive:
1. Task description - what you need to accomplish
2. Current screen state (OCR text from screenshot)
3. Action history - what actions have been taken so far
4. Step budget - how many steps remain

You must respond with ONLY a JSON object containing a list of actions to execute. Do not include any explanatory text, comments, or markdown formatting - just the raw JSON.

{action_schema}

Guidelines:
1. **Respond with JSON ONLY** - no text before or after the JSON
2. **Check if task is already complete FIRST** - Before taking any actions, verify if the task goal is already achieved by examining the current screen
3. **For "Open [App]" tasks** - If you see the app's menu bar (e.g., "File Edit View Go Window" for Finder) or app-specific UI elements, the app is already open. Return an empty action list.
4. **Plan incrementally** - Limit to 3-5 actions per step. Take one small step, observe the result, then plan the next step. This allows adaptation if something goes wrong.
5. **Be efficient** - use the minimum number of actions needed for the current step
6. **Use target_text when possible** - it's more reliable than coordinates
7. **Verify your actions** - think about whether the action will achieve the goal
8. **For file creation tasks** - After creating files, use VERIFY_FILE to confirm they exist before marking task complete
9. **Stop when done** - if the task is complete, return an empty action list: {{"actions": []}}

Example response format:
{{
  "actions": [
    {{"action": "CLICK", "target_text": "Finder"}},
    {{"action": "KEY", "arg": "cmd+n"}},
    {{"action": "TYPE", "arg": "Documents"}},
    {{"action": "KEY", "arg": "enter"}}
  ]
}}

Remember: Output ONLY the JSON object, nothing else."""


def create_system_prompt() -> str:
    """
    Create the system prompt with action schema.
    
    Returns:
        Complete system prompt string
    """
    action_schema = get_action_schema_description()
    return SYSTEM_PROMPT.format(action_schema=action_schema)


def create_user_prompt(
    task_description: str,
    current_screen: str,
    action_history: List[Dict],
    step: int,
    max_steps: int,
    additional_context: Optional[str] = None
) -> str:
    """
    Create the user prompt for the current step.
    
    Args:
        task_description: Description of the task to complete
        current_screen: OCR text from current screenshot
        action_history: List of previous actions taken
        step: Current step number
        max_steps: Maximum number of steps allowed
        additional_context: Optional additional context
        
    Returns:
        User prompt string
    """
    prompt_parts = []
    
    # Task description
    prompt_parts.append(f"**Task**: {task_description}")
    prompt_parts.append("")
    
    # Step info
    prompt_parts.append(f"**Current Step**: {step}/{max_steps}")
    prompt_parts.append("")
    
    # Current screen state
    prompt_parts.append("**Current Screen (OCR Text)**:")
    if current_screen.strip():
        # Limit screen text length to avoid token overflow
        max_screen_length = 2000
        if len(current_screen) > max_screen_length:
            current_screen = current_screen[:max_screen_length] + "\n... (truncated)"
        prompt_parts.append(current_screen)
    else:
        prompt_parts.append("(No text detected on screen)")
    prompt_parts.append("")
    
    # Action history
    if action_history:
        prompt_parts.append("**Previous Actions**:")
        # Show last 5 actions to avoid context overflow
        recent_actions = action_history[-5:]
        for i, action in enumerate(recent_actions, 1):
            action_str = f"{action.get('action', 'UNKNOWN')}"
            if 'target_text' in action and action['target_text']:
                action_str += f" (target: {action['target_text']})"
            elif 'arg' in action and action['arg']:
                action_str += f" (arg: {action['arg'][:50]})"
            prompt_parts.append(f"  {i}. {action_str}")
        prompt_parts.append("")
    
    # Additional context
    if additional_context:
        prompt_parts.append("**Additional Context**:")
        prompt_parts.append(additional_context)
        prompt_parts.append("")
    
    # Instructions
    prompt_parts.append("**Instructions**:")
    prompt_parts.append("1. FIRST, check if the task is already complete by examining the current screen.")
    prompt_parts.append("2. For 'Open [Application]' tasks: If you see the application's menu bar or UI elements, it's already open - return empty actions.")
    prompt_parts.append("3. Only take actions if the task is NOT yet complete.")
    prompt_parts.append("4. Respond with ONLY a JSON object containing the actions. No other text.")
    
    return "\n".join(prompt_parts)


def create_messages(
    task_description: str,
    current_screen: str,
    action_history: List[Dict],
    step: int,
    max_steps: int,
    additional_context: Optional[str] = None
) -> List[Dict[str, str]]:
    """
    Create the full message list for the LLM.
    
    Args:
        task_description: Description of the task to complete
        current_screen: OCR text from current screenshot
        action_history: List of previous actions taken
        step: Current step number
        max_steps: Maximum number of steps allowed
        additional_context: Optional additional context
        
    Returns:
        List of message dicts with 'role' and 'content' keys
    """
    return [
        {
            'role': 'system',
            'content': create_system_prompt()
        },
        {
            'role': 'user',
            'content': create_user_prompt(
                task_description=task_description,
                current_screen=current_screen,
                action_history=action_history,
                step=step,
                max_steps=max_steps,
                additional_context=additional_context
            )
        }
    ]


def detect_app_open(task_description: str, ocr_text: str) -> bool:
    """
    Detect if an application is already open based on task description and OCR text.
    
    Args:
        task_description: Task description (e.g., "Open Finder application")
        ocr_text: OCR text from screenshot
        
    Returns:
        True if app appears to be open, False otherwise
    """
    ocr_lower = ocr_text.lower()
    task_lower = task_description.lower()
    
    # Check for "Open [App]" pattern
    if "open" in task_lower:
        # Extract app name from task description
        app_name = None
        
        # Common app names to look for
        app_names = {
            "finder": "finder",
            "calculator": "calculator",
            "safari": "safari",
            "chrome": "chrome",
            "browser": "safari",  # Default browser
            "textedit": "textedit",
            "notes": "notes",
            "mail": "mail",
            "calendar": "calendar",
        }
        
        # Find which app we're looking for
        for key, name in app_names.items():
            if key in task_lower:
                app_name = name
                break
        
        if app_name:
            # Look for the application name in the OCR text
            # The app name should appear in the menu bar, window title, or UI
            # Check for exact match (case insensitive)
            if app_name in ocr_lower:
                # First check: is this likely documentation/code text?
                # If documentation keywords are present, we CANNOT trust any patterns - they might be from docs
                doc_keywords = ["detection", "function", "framework", "code", "prompt", "task", "extract", "parse", "check", "ocr_lower", "if", "return"]
                is_likely_doc = any(keyword in ocr_lower for keyword in doc_keywords)
                
                # For Finder specifically, require actual Finder UI elements
                if app_name == "finder":
                    # If documentation keywords are present, ALL text patterns are unreliable
                    # The menu bar pattern might appear in code comments, sidebar items in docs, etc.
                    # So we must return False - we cannot trust any detection when docs are present
                    if is_likely_doc:
                        return False
                    
                    # No documentation - check for Finder UI elements
                    # Menu bar pattern is the strongest indicator
                    if "edit view go window" in ocr_lower or "file edit view go window" in ocr_lower:
                        return True
                    
                    # Or check for sidebar items (but need multiple to be sure)
                    sidebar_items = ["desktop", "documents", "downloads", "recents", "airdrop"]
                    found_sidebar = sum(1 for item in sidebar_items if item in ocr_lower)
                    if found_sidebar >= 2:
                        return True
                    
                    # If we see "Finder" but no UI elements, it's probably not actually open
                    return False
                
                # For other apps, check if name appears in UI context
                if is_likely_doc:
                    # Documentation present - require strong UI evidence
                    return False
                else:
                    # No documentation - app name is likely from actual UI
                    return True
        
        return False


def extract_output_files(task_description: str) -> List[str]:
    """
    Extract output file paths from task description.
    Looks for patterns like "as notes.pdf", "into Desktop/final_report.pdf", etc.
    
    Args:
        task_description: Task description text
        
    Returns:
        List of file paths mentioned as outputs
    """
    files = []
    
    # Pattern 1: "as filename" or "as path/filename" (e.g., "as notes.pdf", "as Desktop/file.pdf")
    pattern1 = r'as\s+([^\s,\.]+(?:/[^\s,\.]+)?\.(?:pdf|txt|doc|docx|odt|png|jpg|jpeg|gif|mp3|wav|zip|md))'
    matches = re.findall(pattern1, task_description, re.IGNORECASE)
    files.extend(matches)
    
    # Pattern 2: "into path/filename" or "to path/filename" (e.g., "into Desktop/final_report.pdf")
    pattern2 = r'(?:into|to)\s+([^\s,\.]+(?:/[^\s,\.]+)?\.(?:pdf|txt|doc|docx|odt|png|jpg|jpeg|gif|mp3|wav|zip|md))'
    matches = re.findall(pattern2, task_description, re.IGNORECASE)
    files.extend(matches)
    
    # Pattern 3: "save as path/filename" or "save to path/filename"
    pattern3 = r'save\s+(?:as|to)\s+([^\s,\.]+(?:/[^\s,\.]+)?\.(?:pdf|txt|doc|docx|odt|png|jpg|jpeg|gif|mp3|wav|zip|md))'
    matches = re.findall(pattern3, task_description, re.IGNORECASE)
    files.extend(matches)
    
    # Pattern 4: Full paths like "Desktop/final_report.pdf" or "/home/user/Desktop/file.pdf"
    pattern4 = r'(Desktop|Documents|Downloads|Pictures|Music|Videos|/home/[^\s]+)/([^\s,\.]+\.(?:pdf|txt|doc|docx|odt|png|jpg|jpeg|gif|mp3|wav|zip|md))'
    matches = re.findall(pattern4, task_description, re.IGNORECASE)
    for folder, filename in matches:
        files.append(f"{folder}/{filename}")
    
    # Remove duplicates and normalize paths
    unique_files = []
    seen = set()
    for f in files:
        # Expand ~ to home directory and normalize
        expanded = str(Path(f).expanduser().resolve())
        if expanded not in seen:
            seen.add(expanded)
            unique_files.append(expanded)
    
    return unique_files


# Success detection prompt
def create_success_check_prompt(
    task_description: str,
    current_screen: str,
    action_history: List[Dict]
) -> List[Dict[str, str]]:
    """
    Create a prompt to check if the task has been completed.
    
    Args:
        task_description: Description of the task
        current_screen: OCR text from current screenshot
        action_history: List of actions taken
        
    Returns:
        List of message dicts
    """
    user_content = f"""**Task**: {task_description}

**Actions Taken**:
{len(action_history)} actions executed

**Current Screen**:
{current_screen[:1000]}

**Question**: Has the task been successfully completed based on the current screen state?

Respond with ONLY a JSON object in this format:
{{
  "completed": true/false,
  "reason": "brief explanation"
}}"""
    
    return [
        {
            'role': 'system',
            'content': 'You are evaluating whether a computer task has been completed. Respond with ONLY a JSON object.'
        },
        {
            'role': 'user',
            'content': user_content
        }
    ]

