"""Action schema aligned with the Computer_13 space described in GUIDE.md."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Iterable, List, Optional, Sequence


class ActionType(str, Enum):
    """Enumeration of allowed primitive actions."""

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
    """Target for pointer actions.

    type may be "mark" (Set-of-Mark id) or "coordinate" (absolute pixels).
    """

    type: str
    id: Optional[str] = None
    x: Optional[int] = None
    y: Optional[int] = None

    def as_coordinate(self) -> Optional[List[int]]:
        """Return a `[x, y]` list if enough info is available."""

        if self.type == "coordinate" and self.x is not None and self.y is not None:
            return [int(self.x), int(self.y)]
        return None


@dataclass
class Action:
    """Structured action emitted by the language model."""

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
        """Create an action from model JSON."""

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

        if "target" in payload and isinstance(payload["target"], dict):
            t = payload["target"]
            target = ActionTarget(
                type=t.get("type", "coordinate"),
                id=t.get("id"),
                x=t.get("x"),
                y=t.get("y"),
            )

        keys = payload.get("keys")
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
    """Group of actions emitted in a single reasoning step."""

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
    """Parse the user-provided JSON `actions` field into structured objects."""

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
