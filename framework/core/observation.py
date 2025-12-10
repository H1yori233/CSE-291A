from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


STATE_NS_UBUNTU = "https://accessibility.ubuntu.example.org/ns/state"
STATE_NS_WINDOWS = "https://accessibility.windows.example.org/ns/state"
COMPONENT_NS_UBUNTU = "https://accessibility.ubuntu.example.org/ns/component"
COMPONENT_NS_WINDOWS = "https://accessibility.windows.example.org/ns/component"
VALUE_NS_UBUNTU = "https://accessibility.ubuntu.example.org/ns/value"
VALUE_NS_WINDOWS = "https://accessibility.windows.example.org/ns/value"


@dataclass
class A11yElement:
    id: int  # Index for referencing
    tag: str  # Element type (button, link, etc.)
    name: str  # Element name/label
    text: Optional[str] = None
    bbox: Optional[Tuple[int, int, int, int]] = None  # x, y, w, h
    
    def center(self) -> Optional[List[int]]:
        if not self.bbox:
            return None
        x, y, w, h = self.bbox
        return [int(x + w / 2), int(y + h / 2)]
    
    def __str__(self) -> str:
        # Format: [id] "name" (tag) @ (x, y)
        # This makes it clear that the name is just the quoted part
        label = self.name or self.text or self.tag
        if self.bbox:
            x, y, w, h = self.bbox
            cx, cy = int(x + w / 2), int(y + h / 2)
            return f'[{self.id}] "{label}" ({self.tag}) @ ({cx}, {cy})'
        return f'[{self.id}] "{label}" ({self.tag})'


@dataclass
class Mark:
    id: str
    bbox: Tuple[int, int, int, int]
    name: Optional[str] = None

    def center(self) -> List[int]:
        x, y, w, h = self.bbox
        return [int(x + w / 2), int(y + h / 2)]


@dataclass
class Observation:
    screenshot: Optional[Any] = None
    marks: Dict[str, Mark] = field(default_factory=dict)
    som_elements: List[Dict[str, Any]] = field(default_factory=list)
    a11y_tree: Optional[str] = None
    a11y_elements: List[A11yElement] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    # Scaling: (original_w, original_h) if screenshot was resized
    original_size: Optional[Tuple[int, int]] = None
    
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
            # No resizing occurred
            return (x, y)
        
        # Scale back to original resolution
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
        import re
        import logging
        logger = logging.getLogger("framework.observation")
        
        needle = name.lower().strip()
        
        # Try to extract quoted string if model included extra formatting
        quoted_match = re.search(r'"([^"]+)"', name)
        if quoted_match:
            needle = quoted_match.group(1).lower().strip()
        
        # Find ALL matching elements first
        matches = []
        
        # Exact match
        for elem in self.a11y_elements:
            elem_name = (elem.name or "").lower().strip()
            elem_text = (elem.text or "").lower().strip()
            if elem_name == needle or elem_text == needle:
                matches.append(elem)
        
        # Fuzzy match if no exact match
        if not matches and fuzzy:
            for elem in self.a11y_elements:
                elem_name = (elem.name or "").lower()
                elem_text = (elem.text or "").lower()
                if needle in elem_name or needle in elem_text:
                    matches.append(elem)
                elif elem_name and elem_name in needle:
                    matches.append(elem)
                elif elem_text and elem_text in needle:
                    matches.append(elem)
        
        if not matches:
            return None
        
        # Smart container handling: prioritize interactive elements over containers
        interactive_matches = [m for m in matches if m.tag.lower() not in self.NON_INTERACTIVE_TAGS]
        container_matches = [m for m in matches if m.tag.lower() in self.NON_INTERACTIVE_TAGS]
        
        # If we have interactive matches, use the first one
        if interactive_matches:
            return interactive_matches[0].center()
        
        # If we only have container matches, look for nearby interactive children
        if container_matches:
            container = container_matches[0]
            container_center = container.center()
            
            if container_center:
                # Look for interactive elements near this container
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
                    logger.info(
                        "[DEBUG] Container '%s' clicked, redirecting to nearby '%s' (%s)",
                        container.name, chosen.name, chosen.tag
                    )
                    return chosen.center()
            
            return container_center
        
        return matches[0].center()
    
    # Container element types that are not directly clickable
    NON_INTERACTIVE_TAGS = {
        'panel', 'frame', 'layered-pane', 'filler', 'scroll-pane', 
        'viewport', 'separator', 'unknown', 'section', 'document',
        'application', 'root-pane', 'glass-pane', 'content-pane',
        'internal-frame', 'desktop-pane', 'option-pane',
    }
    
    def is_interactive_element(self, elem: 'A11yElement') -> bool:
        tag = (elem.tag or "").lower()
        if tag in self.NON_INTERACTIVE_TAGS:
            return False
        return True
    
    def format_a11y_elements(self, max_elements: int = 50, filter_containers: bool = True) -> str:
        if not self.a11y_elements:
            return ""
        
        # Filter elements if requested
        if filter_containers:
            interactive_elements = [e for e in self.a11y_elements if self.is_interactive_element(e)]
        else:
            interactive_elements = self.a11y_elements
        
        lines = ["Clickable Elements (use EXACT element name in target):"]
        for elem in interactive_elements[:max_elements]:
            lines.append(str(elem))
        
        if len(interactive_elements) > max_elements:
            lines.append(f"... and {len(interactive_elements) - max_elements} more elements")
        
        return "\n".join(lines)


def parse_a11y_tree(a11y_tree_xml: str, platform: str = "ubuntu") -> List[A11yElement]:
    if not a11y_tree_xml or not a11y_tree_xml.strip():
        return []
    
    try:
        root = ET.fromstring(a11y_tree_xml)
    except ET.ParseError:
        return []
    
    # Select namespaces based on platform
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
        
        # Check visibility and enabled states (similar to OSWorld's judge_node)
        showing = node.get(f"{{{state_ns}}}showing", "false")
        visible = node.get(f"{{{state_ns}}}visible", "false")
        enabled = node.get(f"{{{state_ns}}}enabled", "false")
        editable = node.get(f"{{{state_ns}}}editable", "false")
        expandable = node.get(f"{{{state_ns}}}expandable", "false")
        checkable = node.get(f"{{{state_ns}}}checkable", "false")
        
        # Visibility check
        if platform == "ubuntu":
            if showing != "true" or visible != "true":
                continue
        else:  # windows
            if visible != "true":
                continue
        
        # Enabled/interactive check (at least one must be true)
        if not (enabled == "true" or editable == "true" or expandable == "true" or checkable == "true"):
            continue
        
        # Get name and text
        name = node.get("name", "")
        text = node.text.strip() if node.text else None
        
        # Skip elements without meaningful name/text
        if not name and not text:
            continue
        
        # Get position and size
        coord_str = node.get(f"{{{component_ns}}}screencoord", "")
        size_str = node.get(f"{{{component_ns}}}size", "")
        
        bbox = None
        if coord_str and size_str:
            try:
                # Parse "(x, y)" format - handle spaces around comma
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
        
        # Only include elements with valid bounding boxes
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
