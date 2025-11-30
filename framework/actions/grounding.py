"""Resolve abstract action targets into executable coordinates."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, TYPE_CHECKING

from .schema import Action, ActionTarget, ActionType

if TYPE_CHECKING:  # pragma: no cover - for typing only
    from framework.core.observation import Observation


_POINTER_ACTIONS = {
    ActionType.MOVE_CURSOR,
    ActionType.LEFT_CLICK,
    ActionType.RIGHT_CLICK,
    ActionType.DOUBLE_CLICK,
}

_SCROLL_ACTIONS = {ActionType.SCROLL_UP, ActionType.SCROLL_DOWN}


@dataclass
class GroundedAction:
    """An action that is ready to be executed inside the environment."""

    action: ActionType
    coordinate: Optional[List[int]] = None
    drag: Optional[Tuple[List[int], List[int]]] = None
    scroll_amount: Optional[int] = None
    text: Optional[str] = None
    key: Optional[str] = None
    keys: Optional[List[str]] = None
    metadata: Dict[str, object] = field(default_factory=dict)

    def to_payload(self) -> Dict[str, object]:
        payload: Dict[str, object] = {"action": self.action.value}
        if self.coordinate is not None:
            payload["coordinate"] = self.coordinate
        if self.drag is not None:
            payload["source"], payload["target"] = self.drag
        if self.scroll_amount is not None:
            payload["amount"] = self.scroll_amount
        if self.text is not None:
            payload["text"] = self.text
        if self.key is not None:
            payload["key"] = self.key
        if self.keys is not None:
            payload["keys"] = self.keys
        if self.metadata:
            payload["metadata"] = self.metadata
        return payload


class GroundingResolver:
    """Translate SoM marks or textual references into concrete coordinates."""

    def __init__(self, default_scroll_amount: int = 150):
        self.default_scroll_amount = default_scroll_amount

    def resolve(self, action: Action, observation: "Observation") -> GroundedAction:
        if action.is_special() or action.action in {ActionType.TYPE, ActionType.PRESS_KEY, ActionType.HOTKEY}:
            return GroundedAction(
                action=action.action,
                text=action.text,
                key=action.key,
                keys=action.keys,
                metadata=action.metadata,
            )

        if action.action == ActionType.DRAG_AND_DROP:
            source = self._resolve_target(action.source, observation)
            target = self._resolve_target(action.target, observation)
            if not source or not target:
                raise ValueError("DRAG_AND_DROP requires both source and target coordinates")
            return GroundedAction(
                action=action.action,
                drag=(source, target),
                metadata=action.metadata,
            )

        if action.action in _POINTER_ACTIONS:
            coordinate = self._resolve_target(action.target, observation)
            if not coordinate:
                raise ValueError(f"{action.action.value} requires a resolvable target")
            return GroundedAction(
                action=action.action,
                coordinate=coordinate,
                metadata=action.metadata,
            )

        if action.action in _SCROLL_ACTIONS:
            amount = self._extract_scroll_amount(action)
            coordinate = self._resolve_target(action.target, observation)
            return GroundedAction(
                action=action.action,
                coordinate=coordinate,
                scroll_amount=amount,
                metadata=action.metadata,
            )

        raise ValueError(f"Unsupported action type: {action.action}")

    def _extract_scroll_amount(self, action: Action) -> int:
        amount = action.metadata.get("amount") if action.metadata else None
        if isinstance(amount, int):
            return amount
        return self.default_scroll_amount

    def _resolve_target(self, target: Optional[ActionTarget], observation: "Observation") -> Optional[List[int]]:
        if target is None:
            return None

        target_type = (target.type or "mark").lower()
        if target_type == "coordinate":
            coord = target.as_coordinate()
            if coord and observation.original_size:
                # Scale coordinates from screenshot space to original screen space
                scaled_x, scaled_y = observation.scale_coordinates(coord[0], coord[1])
                return [scaled_x, scaled_y]
            return coord
        if target_type == "mark" and target.id:
            return observation.lookup_mark(target.id)
        if target_type == "named_element" and target.id:
            return observation.lookup_named_element(target.id)
        return None
