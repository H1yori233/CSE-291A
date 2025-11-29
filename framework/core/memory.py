"""Memory helpers for the agent."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Deque, List, Sequence

from framework.actions.grounding import GroundedAction
from framework.actions.schema import ActionType
from .plan import Plan


@dataclass
class MemoryEntry:
    step: int
    summary: str


@dataclass
class AgentMemory:
    plan: Plan = field(default_factory=Plan)
    recent: Deque[MemoryEntry] = field(default_factory=lambda: deque(maxlen=5))
    reflection_count: int = 0

    def note_actions(self, step: int, actions: Sequence[GroundedAction]):
        if not actions:
            return
        summary = _summarise(actions)
        self.recent.append(MemoryEntry(step=step, summary=summary))

    def recent_summary(self) -> str:
        if not self.recent:
            return ""
        return " | ".join(f"Step {entry.step}: {entry.summary}" for entry in self.recent)

    def should_reflect(self, step: int, max_steps: int, threshold: float) -> bool:
        if not threshold:
            return False
        if self.reflection_count > 0:
            return False
        return step / max_steps >= threshold


def _summarise(actions: Sequence[GroundedAction]) -> str:
    summaries: List[str] = []
    for act in actions:
        if act.action in {ActionType.LEFT_CLICK, ActionType.RIGHT_CLICK, ActionType.DOUBLE_CLICK} and act.coordinate:
            summaries.append(f"{act.action.value} at {act.coordinate}")
        elif act.action == ActionType.TYPE and act.text:
            summaries.append(f'Typed "{act.text[:20]}"')
        elif act.action in {ActionType.PRESS_KEY, ActionType.HOTKEY}:
            key = act.key or "+".join(act.keys or [])
            summaries.append(f"Pressed {key}")
        else:
            summaries.append(act.action.value)
    return ", ".join(summaries)
