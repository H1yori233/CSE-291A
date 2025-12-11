from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Iterable, List, Optional, Sequence


class ActionType(str, Enum):
    MOVE_CURSOR = "MOVE_CURSOR"
    LEFT_CLICK = "LEFT_CLICK"
    RIGHT_CLICK = "RIGHT_CLICK"
    DOUBLE_CLICK = "DOUBLE_CLICK"
    DRAG_AND_DROP = "DRAG_AND_DROP"
    SCROLL_UP = "SCROLL_UP"
    SCROLL_DOWN = "SCROLL_DOWN"
    TYPE = "TYPE"
    PRESS_KEY = "PRESS_KEY"
    HOTKEY = "HOTKEY"
    WAIT = "WAIT"
    DONE = "DONE"
    FAIL = "FAIL"


@dataclass
class ActionTarget:
    type: str
    id: Optional[str] = None
    x: Optional[int] = None
    y: Optional[int] = None
    name: Optional[str] = None
    element_id: Optional[int] = None  # SoM element ID for precise matching

    def as_coordinate(self) -> Optional[List[int]]:
        if self.type == "coordinate" and self.x is not None and self.y is not None:
            return [int(self.x), int(self.y)]
        return None
    
    def is_element(self) -> bool:
        return self.type == "element" and (self.name is not None or self.element_id is not None)


@dataclass
class Action:
    action: ActionType
    source: Optional[ActionTarget] = None
    target: Optional[ActionTarget] = None
    text: Optional[str] = None
    key: Optional[str] = None
    keys: Optional[List[str]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_special(self) -> bool:
        return self.action in {ActionType.WAIT, ActionType.DONE, ActionType.FAIL}

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "Action":
        if "action" not in payload:
            raise ValueError("Action is missing the 'action' field")

        action_type = ActionType(payload["action"].upper())
        source = None
        target = None
        if "source" in payload and isinstance(payload["source"], dict):
            s = payload["source"]
            source = ActionTarget(
                type=s.get("type", "coordinate"),
                id=s.get("id"),
                x=s.get("x"),
                y=s.get("y"),
            )

        if "target" in payload:
            t = payload["target"]
            if isinstance(t, dict):
                # Parse element_id - can be in 'element_id' or 'id' if type is element
                elem_id = t.get("element_id")
                if elem_id is None and t.get("type") == "element" and isinstance(t.get("id"), int):
                    elem_id = t.get("id")
                target = ActionTarget(
                    type=t.get("type", "coordinate"),
                    id=t.get("id") if not isinstance(t.get("id"), int) else None,
                    x=t.get("x"),
                    y=t.get("y"),
                    name=t.get("name"),  # For element-based targeting
                    element_id=elem_id,  # SoM element ID
                )
            elif isinstance(t, int):
                # Model output just an ID number - treat as element ID
                target = ActionTarget(
                    type="element",
                    element_id=t,
                )
            elif isinstance(t, str):
                # Model output a string target - treat as element name
                target = ActionTarget(
                    type="element",
                    name=t,
                )

        # Extract keys - try root level first, then fallback to target.keys
        keys = payload.get("keys")
        if keys is None and "target" in payload and isinstance(payload["target"], dict):
            # Model may have nested keys in target (e.g. {"target": {"type": "hotkey", "keys": [...]}})
            keys = payload["target"].get("keys")
        if isinstance(keys, str):
            keys = [keys]

        metadata = {
            k: v
            for k, v in payload.items()
            if k not in {"action", "source", "target", "text", "key", "keys"}
        }

        return cls(
            action=action_type,
            source=source,
            target=target,
            text=payload.get("text"),
            key=payload.get("key"),
            keys=keys,
            metadata=metadata,
        )


@dataclass
class ActionBatch:
    actions: List[Action]

    def __iter__(self):
        return iter(self.actions)

    def __len__(self):
        return len(self.actions)

    @classmethod
    def parse(cls, raw_actions: Sequence[Dict[str, Any]]) -> "ActionBatch":
        actions = [Action.from_dict(item) for item in raw_actions]
        return cls(actions)


def unpack_actions(action_block: Any) -> ActionBatch:
    if action_block in (None, ""):
        return ActionBatch(actions=[])

    if isinstance(action_block, dict):
        # Some models emit a single action as dict instead of list
        action_block = [action_block]

    if not isinstance(action_block, Iterable):
        raise ValueError("actions must be a list of dicts")

    parsed: List[Dict[str, Any]] = []
    for item in action_block:
        if not isinstance(item, dict):
            raise ValueError("Each action entry must be a dict")
        parsed.append(item)

    return ActionBatch.parse(parsed)
