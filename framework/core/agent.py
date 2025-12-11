from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("framework.agent")

from framework.actions import (
    ActionBatch,
    GroundedAction,
    GroundingResolver,
    unpack_actions,
)
from framework.core.memory import AgentMemory
from framework.core.model_client import ModelClient
from framework.core.observation import Observation
from framework.core.plan import Plan
from framework.core.prompt_builder import PromptBuilder


@dataclass
class AgentConfig:
    max_steps: int = 50
    reflection_threshold: float = 0.8
    temperature: float = 0.2
    max_tokens: int = 600


@dataclass
class AgentStepOutput:
    raw_response: str
    payload: Dict[str, Any]
    actions: ActionBatch
    grounded_actions: List[GroundedAction]


class QwenOSWorldAgent:
    """Agent that follows the GUIDE.md architecture."""

    def __init__(
        self,
        model_client: ModelClient,
        config: AgentConfig | None = None,
        prompt_builder: PromptBuilder | None = None,
        grounder: GroundingResolver | None = None,
    ):
        self.model = model_client
        self.config = config or AgentConfig()
        self.prompts = prompt_builder or PromptBuilder()
        self.grounder = grounder or GroundingResolver()
        self.memory = AgentMemory()
        self._task_instruction: str = ""
        self._step: int = 0

    @property
    def plan(self) -> Plan:
        return self.memory.plan

    def reset(self, task_instruction: str) -> None:
        self._task_instruction = task_instruction
        self._step = 0
        self.memory = AgentMemory()
        
        # Clear model cache if available
        if hasattr(self.model, 'reset_cache'):
            self.model.reset_cache()
            
        self._initial_plan_text = self._plan_task(task_instruction)

    def predict(self, observation: Observation) -> AgentStepOutput:
        if not self.plan:
            self.plan.update_from_text(self._plan_task(self._task_instruction))

        self._step += 1
        plan_text = self.plan.as_prompt()
        history = self.memory.recent_summary()
        messages = self.prompts.step_messages(
            instruction=self._task_instruction,
            plan_text=plan_text,
            step=self._step,
            max_steps=self.config.max_steps,
            history=history,
            observation=observation,
            memory=self.memory,  # Pass memory for detailed history & loop detection
        )
        raw = self.model.generate(
            messages,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
            image=observation.screenshot,
        )
        
        # DEBUG: Log raw model response
        logger.info("[DEBUG] Raw model response:\n%s", raw[:2000] if len(raw) > 2000 else raw)
        
        try:
            payload = self._parse_response(raw)
            logger.info("[DEBUG] Parsed payload: %s", json.dumps(payload, indent=2, ensure_ascii=False)[:1000])
        except Exception as e:
            logger.error("[DEBUG] Failed to parse response: %s", e)
            # Return a WAIT action on parse failure
            from framework.actions import ActionType
            return AgentStepOutput(
                raw_response=raw,
                payload={"thought": "parse_error", "plan": "", "actions": []},
                actions=ActionBatch(actions=[]),
                grounded_actions=[GroundedAction(action=ActionType.WAIT, metadata={"error": str(e)})],
            )
        
        plan_update = payload.get("plan")
        if isinstance(plan_update, str) and plan_update.strip():
            self.plan.update_from_text(plan_update)
        
        # Extract and save next_element_hint for element prioritization in next step
        next_hint = payload.get("next_element_hint")
        if next_hint and isinstance(next_hint, str) and next_hint.strip():
            self.memory.set_next_element_hint(next_hint.strip())
        else:
            # Clear hint if not provided (don't carry over stale hints)
            self.memory.set_next_element_hint(None)
        
        actions = unpack_actions(payload.get("actions"))
        logger.info("[DEBUG] Unpacked actions count: %d", len(actions))
        for i, act in enumerate(actions):
            logger.info("[DEBUG] Action[%d]: %s", i, act)
        
        grounded = [self.grounder.resolve(action, observation) for action in actions]
        logger.info("[DEBUG] Grounded actions count: %d", len(grounded))
        for i, ga in enumerate(grounded):
            logger.info("[DEBUG] GroundedAction[%d]: action=%s, coord=%s, text=%s", 
                       i, ga.action, ga.coordinate, ga.text)
        
        self.memory.note_actions(self._step, grounded)
        return AgentStepOutput(
            raw_response=raw,
            payload=payload,
            actions=actions,
            grounded_actions=grounded,
        )

    def maybe_reflect(self, obstacle: str = "") -> Optional[str]:
        if not self.memory.should_reflect(
            step=self._step,
            max_steps=self.config.max_steps,
            threshold=self.config.reflection_threshold,
        ):
            return None
        self.memory.reflection_count += 1
        plan_text = self.plan.as_prompt()
        history = self.memory.recent_summary()
        messages = self.prompts.reflection_messages(
            instruction=self._task_instruction,
            plan_text=plan_text,
            step=self._step,
            max_steps=self.config.max_steps,
            history=history,
            obstacle=obstacle,
        )
        response = self.model.generate(
            messages,
            temperature=self.config.temperature,
            max_tokens=400,
        )
        self.plan.update_from_text(response)
        return response

    def _plan_task(self, task_instruction: str) -> str:
        messages = self.prompts.planning_messages(task_instruction)
        response = self.model.generate(messages, temperature=0.1, max_tokens=256)
        self.plan.update_from_text(response)
        return response

    def _parse_response(self, raw: str) -> Dict[str, Any]:
        text = raw.strip()
        fenced = re.search(r"```json(.*?)```", text, re.DOTALL)
        if not fenced:
            fenced = re.search(r"```(.*?)```", text, re.DOTALL)
        if fenced:
            text = fenced.group(1)
        # Remove trailing commas in JSON arrays and objects which are common in LLM output
        text = re.sub(r",\s*([\]}])", r"\1", text)
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Model response is not valid JSON: {text}") from exc
        required = {"thought", "plan", "actions"}
        missing = required - set(data.keys())
        if missing:
            raise ValueError(f"Model response missing keys: {missing}")
        return data
