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
    
    def format_compact(self) -> str:
        """Ultra-compact format: [id]tag|name|(x,y) - saves ~70% tokens"""
        label = self.name or self.text or self.tag
        # Truncate long names
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
        
        original_name = name  # Keep original for context hints
        
        # FIRST: Extract and remove coordinate hint (e.g., "@ (1771, 79)")
        coord_hint = None
        coord_match = re.search(r'@\s*\((\d+),\s*(\d+)\)', original_name)
        if coord_match:
            coord_hint = (int(coord_match.group(1)), int(coord_match.group(2)))
            # Remove coord hint from name for cleaner matching
            name = re.sub(r'\s*@\s*\(\d+,\s*\d+\)', '', name).strip()
        
        needle = name.lower().strip()
        
        # Try to extract quoted string if model included extra formatting
        quoted_match = re.search(r'"([^"]+)"', name)
        if quoted_match:
            needle = quoted_match.group(1).lower().strip()
        
        # Extract type hint if present (e.g., "Close (push-button)" -> type_hint = "push-button")
        type_hint = None
        type_match = re.search(r'\(([^)]+)\)', name)
        if type_match:
            type_hint = type_match.group(1).lower().strip()
            # Remove type hint from needle for cleaner matching
            needle_without_type = re.sub(r'\s*\([^)]+\)\s*$', '', needle).strip()
            if needle_without_type:
                needle = needle_without_type
        
        # Find ALL matching elements first
        exact_matches = []
        fuzzy_matches = []
        
        # Multi-pass matching with scoring
        for elem in self.a11y_elements:
            elem_name = (elem.name or "").lower().strip()
            elem_text = (elem.text or "").lower().strip()
            
            # Exact match - highest priority
            if elem_name == needle or elem_text == needle:
                exact_matches.append(elem)
            # Fuzzy match - only if no exact match found
            elif fuzzy:
                # Method 1: needle is substring of element name (e.g., "close" in "close window")
                # Require that element name is not significantly longer than needle
                if needle in elem_name:
                    length_ratio = len(needle) / len(elem_name) if elem_name else 0
                    if length_ratio >= 0.7:  # needle should be at least 70% of elem_name length
                        fuzzy_matches.append(elem)
                elif needle in elem_text:
                    length_ratio = len(needle) / len(elem_text) if elem_text else 0
                    if length_ratio >= 0.7:
                        fuzzy_matches.append(elem)
                # Method 2: element name is substring of needle
                elif elem_name and len(elem_name) >= 5 and elem_name in needle:
                    if len(elem_name) >= len(needle) * 0.4:
                        fuzzy_matches.append(elem)
                # Method 3: Word-level matching - for cases like "Bing" matching "Microsoft Bing"
                # or "More actions for Bing" matching "More actions for Microsoft Bing"
                else:
                    # Extract key words (skip common words)
                    skip_words = {'the', 'a', 'an', 'for', 'to', 'of', 'in', 'on', 'with', 'by', 'button', 'icon', 'menu'}
                    needle_words = set(w for w in needle.split() if w not in skip_words and len(w) > 2)
                    elem_words = set(w for w in elem_name.split() if w not in skip_words and len(w) > 2)
                    
                    if needle_words and elem_words:
                        # Check how many words overlap
                        overlap = needle_words & elem_words
                        # Match if significant overlap (at least 60% of needle words found in elem)
                        if len(overlap) >= len(needle_words) * 0.6 and len(overlap) >= 2:
                            fuzzy_matches.append(elem)
        
        # Use exact matches first, fallback to fuzzy
        matches = exact_matches if exact_matches else fuzzy_matches
        
        if not matches:
            return None
        
        # If we have coordinate hint, find the element closest to that coordinate
        if coord_hint and len(matches) > 1:
            def distance_to_hint(elem):
                center = elem.center()
                if not center:
                    return float('inf')
                return abs(center[0] - coord_hint[0]) + abs(center[1] - coord_hint[1])
            matches.sort(key=distance_to_hint)
            best_match = matches[0]
            best_distance = distance_to_hint(best_match)
            # Always use the closest A11y element - coordinates are just a disambiguation hint
            # Do NOT reject based on distance; trust name match over model's coordinate prediction
            if best_distance < 100:
                logger.info("[DEBUG] High confidence match: '%s' at %s (distance %dpx)", 
                           best_match.name, best_match.center(), best_distance)
            elif best_distance < 300:
                logger.info("[DEBUG] Medium confidence match: '%s' at %s (distance %dpx from hint)",
                           best_match.name, best_match.center(), best_distance)
            else:
                # Distance is high, but still use A11y element - model's coords are likely wrong
                logger.warning("[DEBUG] Low confidence but using A11y match: '%s' at %s (distance %dpx from hint, but trusting name match)",
                              best_match.name, best_match.center(), best_distance)
            return best_match.center()
        
        # If we have type hint, filter by element type
        if type_hint and len(matches) > 1:
            typed_matches = [m for m in matches if type_hint in m.tag.lower()]
            if typed_matches:
                matches = typed_matches
        
        # Smart container handling: prioritize interactive elements over containers
        interactive_matches = [m for m in matches if m.tag.lower() not in self.NON_INTERACTIVE_TAGS]
        container_matches = [m for m in matches if m.tag.lower() in self.NON_INTERACTIVE_TAGS]
        
        # If we have interactive matches, use the first one
        if interactive_matches:
            # If multiple interactive matches with same name, prefer push-button, check-box, spin-button
            if len(interactive_matches) > 1:
                PREFERRED_TYPES = ['push-button', 'check-box', 'spin-button', 'combo-box', 'text', 'menu-item']
                for ptype in PREFERRED_TYPES:
                    for m in interactive_matches:
                        if m.tag.lower() == ptype:
                            return m.center()
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
        
        lines = ["AVAILABLE ELEMENTS (use element_id number to target):"]
        for elem in interactive_elements[:max_elements]:
            lines.append(str(elem))
        
        if len(interactive_elements) > max_elements:
            lines.append(f"... and {len(interactive_elements) - max_elements} more elements")
        
        return "\n".join(lines)
    
    def format_a11y_compact(self, max_chars: int = 8000, filter_containers: bool = True) -> str:
        """Ultra-compact format with char limit instead of element count.
        Format: [id]tag|name|(x,y) per line. Model outputs element_id."""
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
        """Prioritized format that sorts elements by relevance.
        
        Sorting criteria:
        1. Name similarity to next_element_hint (if provided)
        2. Spatial proximity to last_coordinate (if provided)
        
        This helps the model find the element it's looking for faster,
        especially in complex nested menus.
        """
        import math
        
        if not self.a11y_elements:
            return ""
        
        if filter_containers:
            elements = [e for e in self.a11y_elements if self.is_interactive_element(e)]
        else:
            elements = self.a11y_elements
        
        # Calculate relevance score for each element
        def score_element(elem: A11yElement) -> float:
            score = 0.0
            elem_name = (elem.name or "").lower()
            
            # Name similarity score (0-100)
            if next_element_hint:
                hint_lower = next_element_hint.lower()
                # Exact match: highest priority
                if elem_name == hint_lower:
                    score += 100
                # Hint is a substring of element name
                elif hint_lower in elem_name:
                    score += 80
                # Element name is a substring of hint  
                elif elem_name and elem_name in hint_lower:
                    score += 60
                # Word overlap
                else:
                    hint_words = set(hint_lower.split())
                    elem_words = set(elem_name.split())
                    overlap = hint_words & elem_words
                    if overlap:
                        score += 40 * (len(overlap) / max(len(hint_words), 1))
            
            # Spatial proximity score (0-50)
            # Elements closer to last click are more likely to be relevant
            if last_coordinate and elem.bbox:
                elem_center = elem.center()
                if elem_center:
                    dx = elem_center[0] - last_coordinate[0]
                    dy = elem_center[1] - last_coordinate[1]
                    distance = math.sqrt(dx*dx + dy*dy)
                    # Closer elements get higher score, max 50 points at distance 0
                    # Score decreases as distance increases, reaching ~0 at 500px
                    proximity_score = 50 * max(0, 1 - distance / 500)
                    score += proximity_score
            
            return score
        
        # Sort elements by score (descending) while maintaining original order for equal scores
        scored_elements = [(score_element(e), i, e) for i, e in enumerate(elements)]
        scored_elements.sort(key=lambda x: (-x[0], x[1]))  # Sort by score desc, then by original index
        sorted_elements = [e for _, _, e in scored_elements]
        
        # Format output
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
