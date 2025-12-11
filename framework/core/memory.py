from __future__ import annotations

import logging
from collections import deque
from dataclasses import dataclass, field
from typing import Deque, List, Optional, Sequence

from framework.actions.grounding import GroundedAction
from framework.actions.schema import ActionType
from .plan import Plan

logger = logging.getLogger(__name__)


@dataclass
class MemoryEntry:
    step: int
    summary: str
    action_type: Optional[ActionType] = None
    target_name: Optional[str] = None  # For element-based actions
    coordinate: Optional[List[int]] = None


@dataclass 
class AgentMemory:
    plan: Plan = field(default_factory=Plan)
    recent: Deque[MemoryEntry] = field(default_factory=lambda: deque(maxlen=10))
    reflection_count: int = 0
    # For element prioritization: model's hint about the next element to interact with
    next_element_hint: Optional[str] = None
    # Coordinate of the last click action (for spatial proximity sorting)
    last_coordinate: Optional[List[int]] = None
    # Loop severity tracking for forced loop breaker
    loop_count: int = 0


    def note_actions(self, step: int, actions: Sequence[GroundedAction]):
        if not actions:
            return
        click_types = {ActionType.LEFT_CLICK, ActionType.RIGHT_CLICK, ActionType.DOUBLE_CLICK}
        for act in actions:
            target_name = act.metadata.get("element_name") if act.metadata else None
            summary = _summarise_single(act)
            entry = MemoryEntry(
                step=step,
                summary=summary,
                action_type=act.action,
                target_name=target_name,
                coordinate=act.coordinate,
            )
            self.recent.append(entry)
            # Update last_coordinate for click actions (used for element prioritization)
            if act.action in click_types and act.coordinate:
                self.last_coordinate = act.coordinate
            logger.info("[DEBUG] Memory recorded: Step %d, %s (target=%s)", step, summary, target_name)
    
    def set_next_element_hint(self, hint: Optional[str]):
        """Set the model's prediction for the next element to interact with."""
        self.next_element_hint = hint
        if hint:
            logger.info("[DEBUG] Next element hint set: %s", hint)

    def get_loop_severity(self) -> int:
        """Return loop severity: 0=none, 1=mild, 2=severe, 3=fatal.
        
        Used by the loop breaker mechanism to force alternative actions.
        """
        loop_warning = self.detect_loop()
        if not loop_warning:
            self.loop_count = 0
            return 0
        self.loop_count += 1
        severity = min(self.loop_count, 3)
        logger.warning("[LOOP SEVERITY] Level %d detected (consecutive loops: %d)", 
                      severity, self.loop_count)
        return severity


    def recent_summary(self) -> str:
        if not self.recent:
            return ""
        return " | ".join(f"Step {e.step}: {e.summary}" for e in self.recent)
    
    def recent_actions_detailed(self, n: int = 5) -> str:
        if not self.recent:
            return "No previous actions taken yet."
        
        entries = list(self.recent)[-n:]
        lines = []
        for i, entry in enumerate(entries):
            if entry.coordinate:
                lines.append(f"  {i+1}. Step {entry.step}: {entry.summary} at ({entry.coordinate[0]}, {entry.coordinate[1]})")
            else:
                lines.append(f"  {i+1}. Step {entry.step}: {entry.summary}")
        return "\n".join(lines)
    
    def detect_loop(self, window: int = 3) -> Optional[str]:
        if len(self.recent) < 2:  # Reduced minimum to catch loops earlier
            return None
        
        recent_entries = list(self.recent)[-window:] if len(self.recent) >= window else list(self.recent)
        
        # Check 1: Exact same action repeated
        first_type = recent_entries[0].action_type
        first_summary = recent_entries[0].summary
        
        same_action_count = sum(
            1 for e in recent_entries 
            if e.action_type == first_type and e.summary == first_summary
        )
        
        if same_action_count >= min(window, len(recent_entries)) and len(recent_entries) >= 2:
            return (
                f"WARNING: You have repeated '{first_summary}' "
                f"{same_action_count} times in a row. This action is NOT working! "
                "Look at the screen - if nothing changed, try clicking a DIFFERENT element or button!"
            )
        
        # Check 2: Click actions on same target element (may have slightly different summaries)
        click_actions = {ActionType.LEFT_CLICK, ActionType.RIGHT_CLICK, ActionType.DOUBLE_CLICK}
        click_entries = [e for e in recent_entries if e.action_type in click_actions]
        if len(click_entries) >= 2:
            # Check if clicking same target repeatedly
            targets = [e.target_name for e in click_entries if e.target_name]
            if len(targets) >= 2 and len(set(targets)) == 1:  # All same target
                return (
                    f"WARNING: You clicked '{targets[0]}' multiple times but it's not doing what you expect! "
                    "Look for a CONFIRM button like 'Set as default', 'OK', 'Apply', or 'Save'!"
                )
            
            # Check if clicking same coordinates repeatedly (different targets but same location)
            coords = [tuple(e.coordinate) for e in click_entries if e.coordinate]
            if len(coords) >= 2:
                # Check if all coordinates are very close (within 20 pixels)
                first_coord = coords[0]
                close_count = sum(1 for c in coords if abs(c[0] - first_coord[0]) < 20 and abs(c[1] - first_coord[1]) < 20)
                if close_count >= 2:
                    return (
                        f"WARNING: You clicked the same area ({first_coord[0]}, {first_coord[1]}) "
                        f"{close_count} times! The element may not exist there. "
                        "Check the AVAILABLE ELEMENTS list and use the EXACT element name!"
                    )
        
        # Check 3: WAIT loop (multiple consecutive WAITs)
        wait_count = sum(1 for e in recent_entries if e.action_type == ActionType.WAIT)
        if wait_count >= 2:
            return (
                f"WARNING: You have executed WAIT {wait_count} times. "
                "The element you're looking for may not exist. Try a DIFFERENT approach! "
                "Consider using HOTKEY to open applications (e.g., HOTKEY ctrl+alt+t for terminal)."
            )
        
        # Check 4: Fallback pattern - element not found leading to wrong action
        if len(recent_entries) >= 2:
            # Check if we're stuck trying to find non-existent elements
            type_actions = [e for e in recent_entries if e.action_type == ActionType.TYPE]
            click_actions_recent = [e for e in recent_entries if e.action_type in click_actions]
            
            # If we have interspersed TYPE and CLICK actions at the same coordinate, might be failing
            if len(type_actions) >= 1 and len(click_actions_recent) >= 2:
                coords = [tuple(e.coordinate) for e in click_actions_recent if e.coordinate]
                if len(set(coords)) == 1:  # All clicks at same location
                    return (
                        "WARNING: You seem to be typing into the wrong location! "
                        "The input fields may not be where you're clicking. "
                        "Look for spin-button, text, or combo-box elements with specific values like '80' or '24'."
                    )
        
        return None

    def should_reflect(self, step: int, max_steps: int, threshold: float) -> bool:
        if not threshold:
            return False
        if self.reflection_count > 0:
            return False
        # Also trigger reflection if loop detected
        if self.detect_loop():
            return True
        return step / max_steps >= threshold


def _summarise_single(act: GroundedAction) -> str:
    if act.action in {ActionType.LEFT_CLICK, ActionType.RIGHT_CLICK, ActionType.DOUBLE_CLICK}:
        if act.metadata and act.metadata.get("element_name"):
            return f"{act.action.value} on \"{act.metadata['element_name']}\""
        elif act.coordinate:
            return f"{act.action.value} at {act.coordinate}"
        return act.action.value
    elif act.action == ActionType.TYPE and act.text:
        return f'Typed "{act.text[:20]}..."' if len(act.text) > 20 else f'Typed "{act.text}"'
    elif act.action in {ActionType.PRESS_KEY, ActionType.HOTKEY}:
        key = act.key or "+".join(act.keys or [])
        return f"Pressed {key}"
    elif act.action == ActionType.SCROLL_DOWN:
        return "Scrolled down"
    elif act.action == ActionType.SCROLL_UP:
        return "Scrolled up"
    else:
        return act.action.value


def _summarise(actions: Sequence[GroundedAction]) -> str:
    return ", ".join(_summarise_single(act) for act in actions)
