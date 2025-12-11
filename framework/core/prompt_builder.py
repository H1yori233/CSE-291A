from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from framework.core.observation import Observation
from framework.core.memory import AgentMemory
from framework.prompts import templates


@dataclass
class PromptBuilder:
    mode: str = "som"
    
    def __post_init__(self):
        if self.mode == "coordinate":
            self.system_prompt = templates.SYSTEM_PROMPT_COORDINATE_MODE
        else:
            self.system_prompt = templates.SYSTEM_PROMPT

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
        memory: Optional[AgentMemory] = None,
    ) -> List[Dict[str, str]]:
        observation_text = self._format_observation(observation, memory=memory)
        
        if memory:
            history_section = memory.recent_actions_detailed(n=5)
            loop_warning = memory.detect_loop(window=3)
            if loop_warning:
                loop_warning_text = (
                    f"\n🚨 WARNING: {loop_warning}\n"
                    f"Try something DIFFERENT!\n"
                )
            else:
                loop_warning_text = ""
        else:
            history_section = history if history else "No previous actions yet."
            loop_warning_text = ""
        
        from framework.prompts.domain_hints import detect_domain, get_domain_hint
        domain = detect_domain(observation.a11y_elements, instruction)
        domain_hint = get_domain_hint(domain, instruction=instruction)
        
        user_prompt = templates.STEP_PROMPT.format(
            instruction=instruction,
            step=step,
            max_steps=max_steps,
            domain_hint=domain_hint,
            history_section=history_section,
            loop_warning=loop_warning_text,
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

    def _format_observation(self, observation: Observation, memory: Optional[AgentMemory] = None) -> str:
        parts: List[str] = []
        
        if observation.a11y_elements:
            if memory and (memory.next_element_hint or memory.last_coordinate):
                last_coord = tuple(memory.last_coordinate) if memory.last_coordinate else None
                parts.append(observation.format_a11y_prioritized(
                    max_chars=8000,
                    next_element_hint=memory.next_element_hint,
                    last_coordinate=last_coord
                ))
            else:
                parts.append(observation.format_a11y_compact(max_chars=8000))
        elif observation.som_elements:
            visible = [
                f"{el.get('id')}: {el.get('name', '')}".strip()
                for el in observation.som_elements[:12]
            ]
            if visible:
                parts.append("Visible UI elements: " + ", ".join(visible))
        elif observation.a11y_tree:
            snippet = observation.a11y_tree.strip()
            if len(snippet) > 2000:
                snippet = snippet[:2000] + "...(truncated)"
            parts.append("Accessibility Tree:\n" + snippet)
        
        return "\n".join(parts)
