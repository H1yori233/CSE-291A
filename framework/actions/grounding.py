from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, TYPE_CHECKING

from .schema import Action, ActionTarget, ActionType

if TYPE_CHECKING:
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
            metadata = dict(action.metadata) if action.metadata else {}
            if action.target and action.target.name:
                metadata["element_name"] = action.target.name
            return GroundedAction(
                action=action.action,
                coordinate=coordinate,
                metadata=metadata,
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

        target_type = (target.type or "").lower()
        
        coord_hint = None
        if target.x is not None and target.y is not None:
            coord_hint = (int(target.x), int(target.y))
        
        if target.name:
            name_with_hint = target.name
            if coord_hint:
                name_with_hint = f"{target.name} @ ({coord_hint[0]}, {coord_hint[1]})"
            coords = observation.lookup_a11y_element_by_name(name_with_hint, fuzzy=True)
            if coords:
                return coords
            coords = observation.lookup_named_element(target.name)
            if coords:
                return coords
        
        if target.element_id is not None:
            elem_id = target.element_id
            for elem in observation.a11y_elements:
                if elem.id == elem_id:
                    coords = elem.center()
                    if coords:
                        return coords
        
        if coord_hint:
            coord = [coord_hint[0], coord_hint[1]]
            if observation.original_size:
                scaled_x, scaled_y = observation.scale_coordinates(coord[0], coord[1])
                return [scaled_x, scaled_y]
            return coord
        
        if target_type == "coordinate":
            coord = target.as_coordinate()
            if coord and observation.original_size:
                scaled_x, scaled_y = observation.scale_coordinates(coord[0], coord[1])
                return [scaled_x, scaled_y]
            return coord
        
        if target_type == "element":
            if target.element_id is not None:
                elem_id = target.element_id
                for elem in observation.a11y_elements:
                    if elem.id == elem_id:
                        coords = elem.center()
                        if coords:
                            return coords
                return None
            
            if target.name:
                coords = observation.lookup_a11y_element_by_name(target.name, fuzzy=True)
                if coords:
                    return coords
                coords = observation.lookup_named_element(target.name)
                if coords:
                    return coords
            
            return None
        
        if target_type == "mark" and target.id:
            return observation.lookup_mark(target.id)
        
        if target_type == "named_element" and target.id:
            return observation.lookup_named_element(target.id)
        
        return None
