from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

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
        
        if hasattr(self.model, 'reset_cache'):
            self.model.reset_cache()
            
        self._initial_plan_text = self._plan_task(task_instruction)

    def predict(self, observation: Observation) -> AgentStepOutput:
        if not self.plan:
            self.plan.update_from_text(self._plan_task(self._task_instruction))

        self._step += 1
        
        loop_severity = self.memory.get_loop_severity()
        if loop_severity >= 3:
            from framework.actions import ActionType
            alternative_action = self._get_loop_breaker_action()
            self.memory.note_actions(self._step, [alternative_action])
            return AgentStepOutput(
                raw_response="[LOOP BREAKER: Forced alternative action due to repeated failures]",
                payload={"thought": "loop_breaker_triggered", "plan": "break_loop", "actions": []},
                actions=ActionBatch(actions=[]),
                grounded_actions=[alternative_action],
            )
        
        plan_text = self.plan.as_prompt()
        history = self.memory.recent_summary()
        messages = self.prompts.step_messages(
            instruction=self._task_instruction,
            plan_text=plan_text,
            step=self._step,
            max_steps=self.config.max_steps,
            history=history,
            observation=observation,
            memory=self.memory,
        )
        raw = self.model.generate(
            messages,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
            image=observation.screenshot,
        )
        
        try:
            payload = self._parse_response(raw)
        except Exception as e:
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
        
        next_hint = payload.get("next_element_hint")
        if next_hint and isinstance(next_hint, str) and next_hint.strip():
            self.memory.set_next_element_hint(next_hint.strip())
        else:
            self.memory.set_next_element_hint(None)
        
        actions = unpack_actions(payload.get("actions"))
        grounded = [self.grounder.resolve(action, observation) for action in actions]
        
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

    def _get_loop_breaker_action(self) -> GroundedAction:
        from framework.actions import ActionType
        
        strategy = self.memory.loop_count % 3
        
        if strategy == 0:
            return GroundedAction(action=ActionType.PRESS_KEY, key="escape")
        elif strategy == 1:
            return GroundedAction(action=ActionType.SCROLL_DOWN, scroll_amount=300)
        else:
            return GroundedAction(action=ActionType.PRESS_KEY, key="tab")
