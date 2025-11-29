"""Prompt factory that produces the messages described in the guide."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from framework.core.observation import Observation
from framework.prompts import templates


@dataclass
class PromptBuilder:
    system_prompt: str = templates.SYSTEM_PROMPT

    def system_message(self) -> Dict[str, str]:
        return {"role": "system", "content": self.system_prompt}

    def planning_messages(self, instruction: str) -> List[Dict[str, str]]:
        return [
            self.system_message(),
            {
                "role": "user",
                "content": templates.PLANNING_PROMPT.format(instruction=instruction),
            },
        ]

    def step_messages(
        self,
        instruction: str,
        plan_text: str,
        step: int,
        max_steps: int,
        history: str,
        observation: Observation,
    ) -> List[Dict[str, str]]:
        observation_text = self._format_observation(observation)
        history_section = f"Recent Actions: {history}\n" if history else ""
        user_prompt = templates.STEP_PROMPT.format(
            instruction=instruction,
            plan=plan_text,
            step=step,
            max_steps=max_steps,
            history_section=history_section,
            observation_text=observation_text,
        )
        return [self.system_message(), {"role": "user", "content": user_prompt}]

    def reflection_messages(
        self,
        instruction: str,
        plan_text: str,
        step: int,
        max_steps: int,
        history: str,
        obstacle: str,
    ) -> List[Dict[str, str]]:
        user_prompt = templates.REFLECTION_PROMPT.format(
            instruction=instruction,
            plan=plan_text,
            step=step,
            max_steps=max_steps,
            history=history or "(no recent actions)",
            obstacle=obstacle or "progress stalled",
        )
        return [self.system_message(), {"role": "user", "content": user_prompt}]

    def _format_observation(self, observation: Observation) -> str:
        parts: List[str] = []
        if observation.som_elements:
            visible = [
                f"{el.get('id')}: {el.get('name', '')}".strip()
                for el in observation.som_elements[:12]
            ]
            if visible:
                parts.append("Visible UI elements: " + ", ".join(visible))
        if observation.a11y_tree:
            snippet = observation.a11y_tree.strip()
            if len(snippet) > 400:
                snippet = snippet[:400] + "..."
            parts.append("Accessibility summary: " + snippet)
        return "\n".join(parts)
