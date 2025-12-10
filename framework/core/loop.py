from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

from framework.core.agent import QwenOSWorldAgent
from framework.core.observation import Observation

ObservationAdapter = Callable[[Any], Observation]


@dataclass
class LoopResult:
    success: bool
    steps: int
    last_observation: Optional[Observation]
    info: Dict[str, Any]


class AgentLoop:
    def __init__(
        self,
        agent: QwenOSWorldAgent,
        env: Any,
        observation_adapter: ObservationAdapter,
    ):
        self.agent = agent
        self.env = env
        self.adapt_observation = observation_adapter

    def run_task(self, task_config: Dict[str, Any], max_steps: Optional[int] = None) -> LoopResult:
        max_steps = max_steps or self.agent.config.max_steps
        instruction = task_config.get("instruction") or task_config.get("task") or ""
        self.agent.reset(instruction)
        raw_obs = self.env.reset(task_config)
        observation = self._ensure_observation(raw_obs)
        done = False
        info: Dict[str, Any] = {}
        for _ in range(max_steps):
            step_output = self.agent.predict(observation)
            last_reward = None
            for action in step_output.grounded_actions:
                raw_obs, last_reward, done, info = self.env.step(action.to_payload())
                if done:
                    break
            if done:
                return LoopResult(
                    success=bool(last_reward),
                    steps=self.agent._step,
                    last_observation=observation,
                    info=info,
                )
            observation = self._ensure_observation(raw_obs)
            if not step_output.grounded_actions:
                self.agent.maybe_reflect(obstacle="No actions produced")
        return LoopResult(
            success=False,
            steps=max_steps,
            last_observation=observation,
            info=info,
        )

    def _ensure_observation(self, raw_obs: Any) -> Observation:
        if isinstance(raw_obs, Observation):
            return raw_obs
        if not callable(self.adapt_observation):
            raise ValueError("No observation adapter provided")
        return self.adapt_observation(raw_obs)
