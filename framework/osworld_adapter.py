"""Adapter to run the refactored framework agent inside OSWorld runners."""

from __future__ import annotations

import logging
from io import BytesIO
from typing import Dict, List, Optional, Sequence, Tuple, Union

from PIL import Image, UnidentifiedImageError

from framework.actions import ActionType, GroundedAction, GroundingResolver
from framework.core.agent import AgentConfig, QwenOSWorldAgent
from framework.core.model_client import ModelClient, create_model_client
from framework.core.observation import Observation


Coordinate = Optional[List[int]]
ActionPayload = Union[str, Dict[str, object]]


class SafeGroundingResolver(GroundingResolver):
    """Grounder that degrades to WAIT when targets are missing."""

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger("framework.adapter")

    def resolve(self, action: GroundedAction, observation: "Observation") -> GroundedAction:  # type: ignore[override]
        try:
            result = super().resolve(action, observation)  # type: ignore[arg-type]
            self.logger.info("[DEBUG] SafeGroundingResolver: action=%s resolved successfully", action.action)
            return result
        except Exception as exc:
            # Fallback to a WAIT to avoid hard failure in runner
            self.logger.warning("[DEBUG] SafeGroundingResolver: FALLBACK to WAIT due to: %s (action was: %s)", exc, action)
            return GroundedAction(action=ActionType.WAIT, metadata={"fallback": str(exc)})


class FrameworkAgentAdapter:
    """Bridges `QwenOSWorldAgent` to OSWorld's `run_single_example` interface."""

    def __init__(
        self,
        model_client: ModelClient,
        agent_config: Optional[AgentConfig] = None,
        prompt_mode: str = "coordinate",
        logger: Optional[logging.Logger] = None,
    ):
        self.logger = logger or logging.getLogger("framework.adapter")
        
        # Import PromptBuilder here to avoid circular import
        from framework.core.prompt_builder import PromptBuilder
        
        self.agent = QwenOSWorldAgent(
            model_client=model_client,
            config=agent_config,
            prompt_builder=PromptBuilder(mode=prompt_mode),
            grounder=SafeGroundingResolver(),
        )
        self._initialized = False
        self._instruction: str = ""
        self._prompt_mode = prompt_mode

    # The OSWorld runner calls agent.reset(runtime_logger, vm_ip=env.vm_ip)
    def reset(self, runtime_logger=None, vm_ip=None):
        if runtime_logger:
            self.logger = runtime_logger
        self._initialized = False
        self._instruction = ""
        # vm_ip is not required for this agent but kept for signature compatibility

    def predict(self, instruction: str, obs: Dict) -> Tuple[str, List[ActionPayload]]:
        if not self._initialized or instruction != self._instruction:
            self.agent.reset(instruction)
            self._instruction = instruction
            self._initialized = True

        observation = self._adapt_observation(obs)
        step_output = self.agent.predict(observation)
        actions = self._grounded_to_osworld(step_output.grounded_actions)

        return step_output.raw_response, actions

    def _adapt_observation(self, obs: Dict) -> Observation:
        screenshot = obs.get("screenshot")
        image = None
        original_size = None
        if screenshot:
            try:
                image = Image.open(BytesIO(screenshot)).convert("RGB")
                original_size = image.size
            except (UnidentifiedImageError, OSError):
                self.logger.warning("Failed to decode screenshot; proceeding without image.")
                image = None
                original_size = None

        a11y_tree_raw = obs.get("accessibility_tree")
        
        observation = Observation(
            screenshot=image,
            a11y_tree=a11y_tree_raw,
            som_elements=[],
            marks={},
            original_size=original_size,
        )
        
        # Debug: log parsed a11y elements
        self.logger.info("[DEBUG] a11y_tree raw length: %d", len(a11y_tree_raw) if a11y_tree_raw else 0)
        self.logger.info("[DEBUG] Parsed a11y_elements count: %d", len(observation.a11y_elements))
        # Print all elements for debugging
        for elem in observation.a11y_elements:
            self.logger.info("[DEBUG] A11y Element: %s", elem)
        
        return observation

    def _grounded_to_osworld(self, grounded_actions: Sequence[GroundedAction]) -> List[ActionPayload]:
        self.logger.info("[DEBUG] _grounded_to_osworld: received %d grounded actions", len(grounded_actions))
        translated: List[ActionPayload] = []
        for i, action in enumerate(grounded_actions):
            mapped = self._translate_action(action)
            self.logger.info("[DEBUG] _grounded_to_osworld: action[%d] %s -> mapped=%s", i, action.action, mapped)
            if isinstance(mapped, list):
                translated.extend(mapped)
            elif mapped:
                translated.append(mapped)

        if not translated:
            self.logger.warning("[DEBUG] _grounded_to_osworld: no actions translated, defaulting to WAIT")
            translated.append("WAIT")
        
        self.logger.info("[DEBUG] _grounded_to_osworld: final translated actions: %s", translated)
        return translated

    def _translate_action(self, action: GroundedAction) -> Union[ActionPayload, List[ActionPayload], None]:
        a = action.action

        if a == ActionType.WAIT:
            return "WAIT"
        if a == ActionType.DONE:
            return "DONE"
        if a == ActionType.FAIL:
            return "FAIL"

        if a == ActionType.MOVE_CURSOR:
            coord = self._coord(action.coordinate)
            return self._move_to(coord)

        if a == ActionType.LEFT_CLICK:
            coord = self._coord(action.coordinate)
            return self._click(coord, button="left")

        if a == ActionType.RIGHT_CLICK:
            coord = self._coord(action.coordinate)
            return self._click(coord, button="right")

        if a == ActionType.DOUBLE_CLICK:
            coord = self._coord(action.coordinate)
            return self._double_click(coord)

        if a == ActionType.DRAG_AND_DROP:
            if not action.drag:
                return None
            source, target = action.drag
            src = self._coord(source)
            tgt = self._coord(target)
            if not src or not tgt:
                return None
            return [self._move_to(src), self._drag_to(tgt)]

        if a == ActionType.SCROLL_UP:
            amount = action.scroll_amount or 150
            coord = self._coord(action.coordinate)
            return self._scroll(dy=amount, coord=coord)

        if a == ActionType.SCROLL_DOWN:
            amount = action.scroll_amount or 150
            coord = self._coord(action.coordinate)
            return self._scroll(dy=-abs(amount), coord=coord)

        if a == ActionType.TYPE:
            return {
                "action_type": "TYPING",
                "parameters": {"text": action.text or ""},
            }

        if a == ActionType.PRESS_KEY:
            key = action.key or (action.keys[0] if action.keys else None)
            if not key:
                return None
            return {
                "action_type": "PRESS",
                "parameters": {"key": key},
            }

        if a == ActionType.HOTKEY:
            keys = action.keys or ([action.key] if action.key else None)
            if not keys:
                return None
            return {
                "action_type": "HOTKEY",
                "parameters": {"keys": keys},
            }

        return None

    def _coord(self, coordinate: Coordinate) -> Optional[Dict[str, int]]:
        if not coordinate:
            return None
        x, y = coordinate
        return {"x": int(x), "y": int(y)}

    def _move_to(self, coord: Optional[Dict[str, int]]) -> Optional[Dict[str, object]]:
        if not coord:
            return None
        return {"action_type": "MOVE_TO", "parameters": coord}

    def _click(self, coord: Optional[Dict[str, int]], button: str) -> Optional[Dict[str, object]]:
        if not coord:
            return None
        return {"action_type": "CLICK", "parameters": {**coord, "button": button}}

    def _double_click(self, coord: Optional[Dict[str, int]]) -> Optional[Dict[str, object]]:
        if not coord:
            return None
        return {"action_type": "DOUBLE_CLICK", "parameters": coord}

    def _drag_to(self, coord: Optional[Dict[str, int]]) -> Optional[Dict[str, object]]:
        if not coord:
            return None
        return {"action_type": "DRAG_TO", "parameters": coord}

    def _scroll(self, dy: int, coord: Optional[Dict[str, int]] = None) -> Dict[str, object]:
        params = {"dy": int(dy)}
        if coord:
            params.update(coord)
        return {"action_type": "SCROLL", "parameters": params}


def build_adapter(
    base_url: str,
    model: str,
    api_key: str = "EMPTY",
    agent_config: Optional[AgentConfig] = None,
) -> FrameworkAgentAdapter:
    client = create_model_client(
        name="qwen_vl",
        model=model,
        base_url=base_url,
        api_key=api_key,
    )
    return FrameworkAgentAdapter(model_client=client, agent_config=agent_config)

