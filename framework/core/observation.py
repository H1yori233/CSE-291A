from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
import math


STATE_NS_UBUNTU = "https://accessibility.ubuntu.example.org/ns/state"
STATE_NS_WINDOWS = "https://accessibility.windows.example.org/ns/state"
COMPONENT_NS_UBUNTU = "https://accessibility.ubuntu.example.org/ns/component"
COMPONENT_NS_WINDOWS = "https://accessibility.windows.example.org/ns/component"
VALUE_NS_UBUNTU = "https://accessibility.ubuntu.example.org/ns/value"
VALUE_NS_WINDOWS = "https://accessibility.windows.example.org/ns/value"


@dataclass
class A11yElement:
    id: int
    tag: str
    name: str
    text: Optional[str] = None
    bbox: Optional[Tuple[int, int, int, int]] = None
    
    def center(self) -> Optional[List[int]]:
        if not self.bbox:
            return None
        x, y, w, h = self.bbox
        return [int(x + w / 2), int(y + h / 2)]
    
    def __str__(self) -> str:
        label = self.name or self.text or self.tag
        if self.bbox:
            x, y, w, h = self.bbox
            cx, cy = int(x + w / 2), int(y + h / 2)
            return f'[{self.id}] "{label}" ({self.tag}) @ ({cx}, {cy})'
        return f'[{self.id}] "{label}" ({self.tag})'
    
    def format_compact(self) -> str:
        label = self.name or self.text or self.tag
        if len(label) > 30:
            label = label[:27] + "..."
        if self.bbox:
            x, y, w, h = self.bbox
            cx, cy = int(x + w / 2), int(y + h / 2)
            return f"[{self.id}]{self.tag}|{label}|({cx},{cy})"
        return f"[{self.id}]{self.tag}|{label}"


@dataclass
class Mark:
    id: str
    bbox: Tuple[int, int, int, int]
    name: Optional[str] = None

    def center(self) -> List[int]:
        x, y, w, h = self.bbox
        return [int(x + w / 2), int(y + h / 2)]


NON_INTERACTIVE_TAGS = {
    'panel', 'frame', 'layered-pane', 'filler', 'scroll-pane', 
    'viewport', 'separator', 'unknown', 'section', 'document',
    'application', 'root-pane', 'glass-pane', 'content-pane',
    'internal-frame', 'desktop-pane', 'option-pane',
}


@dataclass
class Observation:
    screenshot: Optional[Any] = None
    marks: Dict[str, Mark] = field(default_factory=dict)
    som_elements: List[Dict[str, Any]] = field(default_factory=list)
    a11y_tree: Optional[str] = None
    a11y_elements: List[A11yElement] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    original_size: Optional[Tuple[int, int]] = None
    
    NON_INTERACTIVE_TAGS = NON_INTERACTIVE_TAGS
    
    def __post_init__(self):
        if self.a11y_tree and not self.a11y_elements:
            self.a11y_elements = parse_a11y_tree(self.a11y_tree)
    
    def scale_coordinates(self, x: int, y: int) -> Tuple[int, int]:
        if not self.original_size or not self.screenshot:
            return (x, y)
        
        orig_w, orig_h = self.original_size
        if hasattr(self.screenshot, 'width') and hasattr(self.screenshot, 'height'):
            screen_w, screen_h = self.screenshot.width, self.screenshot.height
        else:
            return (x, y)
        
        scaled_x = round(x * orig_w / screen_w)
        scaled_y = round(y * orig_h / screen_h)
        return (scaled_x, scaled_y)

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
    
    def lookup_a11y_element_by_id(self, element_id: int) -> Optional[List[int]]:
        for elem in self.a11y_elements:
            if elem.id == element_id:
                return elem.center()
        return None
    
    def lookup_a11y_element_by_name(self, name: str, fuzzy: bool = True) -> Optional[List[int]]:
        original_name = name
        
        coord_hint = None
        coord_match = re.search(r'@\s*\((\d+),\s*(\d+)\)', original_name)
        if coord_match:
            coord_hint = (int(coord_match.group(1)), int(coord_match.group(2)))
            name = re.sub(r'\s*@\s*\(\d+,\s*\d+\)', '', name).strip()
        
        needle = name.lower().strip()
        
        quoted_match = re.search(r'"([^"]+)"', name)
        if quoted_match:
            needle = quoted_match.group(1).lower().strip()
        
        type_hint = None
        type_match = re.search(r'\(([^)]+)\)', name)
        if type_match:
            type_hint = type_match.group(1).lower().strip()
            needle_without_type = re.sub(r'\s*\([^)]+\)\s*$', '', needle).strip()
            if needle_without_type:
                needle = needle_without_type
        
        exact_matches = []
        fuzzy_matches = []
        
        for elem in self.a11y_elements:
            elem_name = (elem.name or "").lower().strip()
            elem_text = (elem.text or "").lower().strip()
            
            if elem_name == needle or elem_text == needle:
                exact_matches.append(elem)
            elif fuzzy:
                if needle in elem_name:
                    length_ratio = len(needle) / len(elem_name) if elem_name else 0
                    if length_ratio >= 0.7:
                        fuzzy_matches.append(elem)
                elif needle in elem_text:
                    length_ratio = len(needle) / len(elem_text) if elem_text else 0
                    if length_ratio >= 0.7:
                        fuzzy_matches.append(elem)
                elif elem_name and len(elem_name) >= 5 and elem_name in needle:
                    if len(elem_name) >= len(needle) * 0.4:
                        fuzzy_matches.append(elem)
                else:
                    skip_words = {'the', 'a', 'an', 'for', 'to', 'of', 'in', 'on', 'with', 'by', 'button', 'icon', 'menu'}
                    needle_words = set(w for w in needle.split() if w not in skip_words and len(w) > 2)
                    elem_words = set(w for w in elem_name.split() if w not in skip_words and len(w) > 2)
                    
                    if needle_words and elem_words:
                        overlap = needle_words & elem_words
                        if len(overlap) >= len(needle_words) * 0.6 and len(overlap) >= 2:
                            fuzzy_matches.append(elem)
        
        matches = exact_matches if exact_matches else fuzzy_matches
        
        if not matches:
            return None
        
        if coord_hint and len(matches) > 1:
            def distance_to_hint(elem):
                center = elem.center()
                if not center:
                    return float('inf')
                return abs(center[0] - coord_hint[0]) + abs(center[1] - coord_hint[1])
            matches.sort(key=distance_to_hint)
            best_match = matches[0]
            return best_match.center()
        
        if type_hint and len(matches) > 1:
            typed_matches = [m for m in matches if type_hint in m.tag.lower()]
            if typed_matches:
                matches = typed_matches
        
        interactive_matches = [m for m in matches if m.tag.lower() not in self.NON_INTERACTIVE_TAGS]
        container_matches = [m for m in matches if m.tag.lower() in self.NON_INTERACTIVE_TAGS]
        
        if interactive_matches:
            if len(interactive_matches) > 1:
                PREFERRED_TYPES = ['push-button', 'check-box', 'spin-button', 'combo-box', 'text', 'menu-item']
                for ptype in PREFERRED_TYPES:
                    for m in interactive_matches:
                        if m.tag.lower() == ptype:
                            return m.center()
            return interactive_matches[0].center()
        
        if container_matches:
            container = container_matches[0]
            container_center = container.center()
            
            if container_center:
                nearby_interactive = []
                for elem in self.a11y_elements:
                    if elem.tag.lower() in self.NON_INTERACTIVE_TAGS:
                        continue
                    elem_center = elem.center()
                    if elem_center:
                        dx = abs(elem_center[0] - container_center[0])
                        dy = abs(elem_center[1] - container_center[1])
                        if dx < 200 and dy < 50:
                            nearby_interactive.append((elem, dx + dy))
                
                if nearby_interactive:
                    nearby_interactive.sort(key=lambda x: x[1])
                    chosen = nearby_interactive[0][0]
                    return chosen.center()
            
            return container_center
        
        return matches[0].center()
    
    def is_interactive_element(self, elem: 'A11yElement') -> bool:
        tag = (elem.tag or "").lower()
        if tag in self.NON_INTERACTIVE_TAGS:
            return False
        return True
    
    def format_a11y_elements(self, max_elements: int = 50, filter_containers: bool = True) -> str:
        if not self.a11y_elements:
            return ""
        
        if filter_containers:
            interactive_elements = [e for e in self.a11y_elements if self.is_interactive_element(e)]
        else:
            interactive_elements = self.a11y_elements
        
        lines = ["AVAILABLE ELEMENTS (use element_id number to target):"]
        for elem in interactive_elements[:max_elements]:
            lines.append(str(elem))
        
        if len(interactive_elements) > max_elements:
            lines.append(f"... and {len(interactive_elements) - max_elements} more elements")
        
        return "\n".join(lines)
    
    def format_a11y_compact(self, max_chars: int = 8000, filter_containers: bool = True) -> str:
        if not self.a11y_elements:
            return ""
        
        if filter_containers:
            elements = [e for e in self.a11y_elements if self.is_interactive_element(e)]
        else:
            elements = self.a11y_elements
        
        lines = ["ELEMENTS (use name + approximate coordinates):"]
        total_chars = len(lines[0])
        
        for elem in elements:
            line = elem.format_compact()
            if total_chars + len(line) + 1 > max_chars:
                lines.append(f"...+{len(elements) - len(lines) + 1} more")
                break
            lines.append(line)
            total_chars += len(line) + 1
        
        return "\n".join(lines)
    
    def format_a11y_prioritized(
        self, 
        max_chars: int = 8000, 
        filter_containers: bool = True,
        next_element_hint: Optional[str] = None,
        last_coordinate: Optional[Tuple[int, int]] = None
    ) -> str:
        if not self.a11y_elements:
            return ""
        
        if filter_containers:
            elements = [e for e in self.a11y_elements if self.is_interactive_element(e)]
        else:
            elements = self.a11y_elements
        
        def score_element(elem: A11yElement) -> float:
            score = 0.0
            elem_name = (elem.name or "").lower()
            
            if next_element_hint:
                hint_lower = next_element_hint.lower()
                if elem_name == hint_lower:
                    score += 100
                elif hint_lower in elem_name:
                    score += 80
                elif elem_name and elem_name in hint_lower:
                    score += 60
                else:
                    hint_words = set(hint_lower.split())
                    elem_words = set(elem_name.split())
                    overlap = hint_words & elem_words
                    if overlap:
                        score += 40 * (len(overlap) / max(len(hint_words), 1))
            
            if last_coordinate and elem.bbox:
                elem_center = elem.center()
                if elem_center:
                    dx = elem_center[0] - last_coordinate[0]
                    dy = elem_center[1] - last_coordinate[1]
                    distance = math.sqrt(dx*dx + dy*dy)
                    proximity_score = 50 * max(0, 1 - distance / 500)
                    score += proximity_score
            
            return score
        
        scored_elements = [(score_element(e), i, e) for i, e in enumerate(elements)]
        scored_elements.sort(key=lambda x: (-x[0], x[1]))
        sorted_elements = [e for _, _, e in scored_elements]
        
        lines = ["ELEMENTS (prioritized by relevance):"]
        total_chars = len(lines[0])
        
        for elem in sorted_elements:
            line = elem.format_compact()
            if total_chars + len(line) + 1 > max_chars:
                lines.append(f"...+{len(sorted_elements) - len(lines) + 1} more")
                break
            lines.append(line)
            total_chars += len(line) + 1
        
        return "\n".join(lines)


def parse_a11y_tree(a11y_tree_xml: str, platform: str = "ubuntu") -> List[A11yElement]:
    if not a11y_tree_xml or not a11y_tree_xml.strip():
        return []
    
    try:
        root = ET.fromstring(a11y_tree_xml)
    except ET.ParseError:
        return []
    
    if platform == "ubuntu":
        state_ns = STATE_NS_UBUNTU
        component_ns = COMPONENT_NS_UBUNTU
    else:
        state_ns = STATE_NS_WINDOWS
        component_ns = COMPONENT_NS_WINDOWS
    
    elements = []
    element_id = 1
    
    for node in root.iter():
        tag = node.tag.lower()
        
        showing = node.get(f"{{{state_ns}}}showing", "false")
        visible = node.get(f"{{{state_ns}}}visible", "false")
        enabled = node.get(f"{{{state_ns}}}enabled", "false")
        editable = node.get(f"{{{state_ns}}}editable", "false")
        expandable = node.get(f"{{{state_ns}}}expandable", "false")
        checkable = node.get(f"{{{state_ns}}}checkable", "false")
        
        if platform == "ubuntu":
            if showing != "true" or visible != "true":
                continue
        else:
            if visible != "true":
                continue
        
        if not (enabled == "true" or editable == "true" or expandable == "true" or checkable == "true"):
            continue
        
        name = node.get("name", "")
        text = node.text.strip() if node.text else None
        
        if not name and not text:
            continue
        
        coord_str = node.get(f"{{{component_ns}}}screencoord", "")
        size_str = node.get(f"{{{component_ns}}}size", "")
        
        bbox = None
        if coord_str and size_str:
            try:
                coord_clean = coord_str.strip("()").replace(" ", "")
                size_clean = size_str.strip("()").replace(" ", "")
                coords = tuple(map(int, coord_clean.split(",")))
                size = tuple(map(int, size_clean.split(",")))
                if len(coords) >= 2 and len(size) >= 2:
                    x, y = coords[0], coords[1]
                    w, h = size[0], size[1]
                    if x >= 0 and y >= 0 and w > 0 and h > 0:
                        bbox = (x, y, w, h)
            except (ValueError, IndexError):
                pass
        
        if bbox:
            elements.append(A11yElement(
                id=element_id,
                tag=tag,
                name=name,
                text=text,
                bbox=bbox
            ))
            element_id += 1
    
    return elements
