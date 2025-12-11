from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional

from framework.core.observation import Observation
from framework.core.memory import AgentMemory
from framework.prompts import templates

logger = logging.getLogger(__name__)


@dataclass
class PromptBuilder:
    mode: str = "som"  # "som" or "coordinate"
    
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
        
        # Debug: log the compact element list sent to model
        logger.info("[DEBUG] Observation text sent to model (first 1500 chars):\n%s", observation_text[:1500] if observation_text else "EMPTY")
        
        # Use detailed history if memory is provided, otherwise use simple history string
        if memory:
            history_section = memory.recent_actions_detailed(n=5)
            loop_warning = memory.detect_loop(window=3)
            if loop_warning:
                # Make loop warning VERY prominent
                loop_warning_text = (
                    f"\n🚨 WARNING: {loop_warning}\n"
                    f"Try something DIFFERENT!\n"
                )
            else:
                loop_warning_text = ""
            # Debug logging
            logger.info("[DEBUG] History section: %s", history_section[:200] if history_section else "EMPTY")
            logger.info("[DEBUG] Loop warning: %s", loop_warning if loop_warning else "None")
        else:
            history_section = history if history else "No previous actions yet."
            loop_warning_text = ""
        
        # Dynamic domain knowledge injection with RAG-based retrieval
        from framework.prompts.domain_hints import detect_domain, get_domain_hint
        domain = detect_domain(observation.a11y_elements, instruction)
        domain_hint = get_domain_hint(domain, instruction=instruction)  # Pass instruction for RAG lookup
        logger.info("[DEBUG] Detected domain: %s", domain)
        
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
        
        # If we have parsed a11y elements, use prioritized format when hints are available
        if observation.a11y_elements:
            # Check if we have prioritization hints from memory
            if memory and (memory.next_element_hint or memory.last_coordinate):
                # Use prioritized format with sorting by relevance
                last_coord = tuple(memory.last_coordinate) if memory.last_coordinate else None
                parts.append(observation.format_a11y_prioritized(
                    max_chars=8000,
                    next_element_hint=memory.next_element_hint,
                    last_coordinate=last_coord
                ))
                logger.info("[DEBUG] Using prioritized element list (hint=%s, last_coord=%s)", 
                           memory.next_element_hint, last_coord)
            else:
                # Use compact format: [id]tag|name|(x,y) - stay within model context limit
                parts.append(observation.format_a11y_compact(max_chars=8000))
        elif observation.som_elements:
            # Fallback to SoM elements
            visible = [
                f"{el.get('id')}: {el.get('name', '')}".strip()
                for el in observation.som_elements[:12]
            ]
            if visible:
                parts.append("Visible UI elements: " + ", ".join(visible))
        elif observation.a11y_tree:
            # Raw a11y tree as last resort
            snippet = observation.a11y_tree.strip()
            if len(snippet) > 2000:
                snippet = snippet[:2000] + "...(truncated)"
            parts.append("Accessibility Tree:\n" + snippet)
        
        return "\n".join(parts)

