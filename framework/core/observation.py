"""Observation structures consumed by the agent."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class Mark:
    """Single Set-of-Mark entry."""

    id: str
    bbox: Tuple[int, int, int, int]
    name: Optional[str] = None

    def center(self) -> List[int]:
        x, y, w, h = self.bbox
        return [int(x + w / 2), int(y + h / 2)]


@dataclass
class Observation:
    """Container for everything the model sees at a step."""

    screenshot: Optional[Any] = None
    marks: Dict[str, Mark] = field(default_factory=dict)
    som_elements: List[Dict[str, Any]] = field(default_factory=list)
    a11y_tree: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def lookup_mark(self, mark_id: str) -> Optional[List[int]]:
        if mark_id in self.marks:
            return self.marks[mark_id].center()
        for element in self.som_elements:
            if element.get("id") == mark_id:
                bbox = element.get("bbox")
                if bbox:
                    x, y, w, h = bbox
                    return [int(x + w / 2), int(y + h / 2)]
                if "center" in element:
                    cx, cy = element["center"]
                    return [int(cx), int(cy)]
        return None

    def lookup_named_element(self, name: str) -> Optional[List[int]]:
        needle = name.lower()
        for element in self.som_elements:
            label = (element.get("name") or "").lower()
            if label == needle:
                bbox = element.get("bbox")
                if bbox:
                    x, y, w, h = bbox
                    return [int(x + w / 2), int(y + h / 2)]
        return None
