"""Memory helpers for the agent."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Deque, List, Optional, Sequence

from framework.actions.grounding import GroundedAction
from framework.actions.schema import ActionType
from .plan import Plan


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

    def note_actions(self, step: int, actions: Sequence[GroundedAction]):
        if not actions:
            return
        for act in actions:
            entry = MemoryEntry(
                step=step,
                summary=_summarise_single(act),
                action_type=act.action,
                target_name=act.metadata.get("element_name") if act.metadata else None,
                coordinate=act.coordinate,
            )
            self.recent.append(entry)

    def recent_summary(self) -> str:
        """Get a brief one-line summary for backward compatibility."""
        if not self.recent:
            return ""
        return " | ".join(f"Step {e.step}: {e.summary}" for e in self.recent)
    
    def recent_actions_detailed(self, n: int = 5) -> str:
        """Return detailed action history for structured reasoning prompt."""
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
        """
        Check if recent actions show a repetitive pattern (behavioral loop).
        Returns a warning message if loop detected, None otherwise.
        """
        if len(self.recent) < window:
            return None
        
        recent_entries = list(self.recent)[-window:]
        
        # Check if all recent actions are the same type with similar targets
        first_type = recent_entries[0].action_type
        first_summary = recent_entries[0].summary
        
        same_action_count = sum(
            1 for e in recent_entries 
            if e.action_type == first_type and e.summary == first_summary
        )
        
        if same_action_count >= window:
            return (
                f"WARNING: You have repeated the same action '{first_summary}' "
                f"{window} times without progress. Try a DIFFERENT approach!"
            )
        
        # Check for WAIT loop (multiple consecutive WAITs)
        wait_count = sum(1 for e in recent_entries if e.action_type == ActionType.WAIT)
        if wait_count >= window:
            return (
                f"WARNING: You have executed WAIT {wait_count} times consecutively. "
                "The element you're looking for may not exist. Try a DIFFERENT approach!"
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
    """Summarize a single action."""
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
    """Summarize multiple actions into one line."""
    return ", ".join(_summarise_single(act) for act in actions)
