from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List


class StepStatus(str, Enum):
    PENDING = "pending"
    CURRENT = "current"
    DONE = "done"


@dataclass
class PlanStep:
    description: str
    status: StepStatus = StepStatus.PENDING

    def mark_current(self):
        self.status = StepStatus.CURRENT

    def mark_done(self):
        self.status = StepStatus.DONE


@dataclass
class Plan:
    steps: List[PlanStep] = field(default_factory=list)
    current_index: int = 0

    def update_from_text(self, plan_text: str):
        self.steps = []
        for line in _extract_lines(plan_text):
            self.steps.append(PlanStep(description=line))
        if self.steps:
            self.steps[0].mark_current()
            self.current_index = 0

    def mark_progress(self, accomplished: bool):
        if not self.steps:
            return
        if accomplished:
            self.steps[self.current_index].mark_done()
            if self.current_index + 1 < len(self.steps):
                self.current_index += 1
                self.steps[self.current_index].mark_current()

    def as_prompt(self) -> str:
        if not self.steps:
            return "No plan."
        formatted = []
        for idx, step in enumerate(self.steps, start=1):
            suffix = {
                StepStatus.DONE: "(done)",
                StepStatus.CURRENT: "(current)",
                StepStatus.PENDING: "",
            }[step.status]
            formatted.append(f"{idx}) {step.description} {suffix}".strip())
        return " | ".join(formatted)

    def __bool__(self):
        return bool(self.steps)


def _extract_lines(text: str) -> List[str]:
    lines: List[str] = []
    for raw in text.splitlines():
        stripped = raw.strip()
        if not stripped:
            continue
        stripped = stripped.lstrip("-•0123456789. ")
        if stripped:
            lines.append(stripped)
    return lines
