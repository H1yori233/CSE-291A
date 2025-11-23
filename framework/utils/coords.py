"""
Coordinate and bounding box utilities
"""

from typing import Tuple, Optional, List, Dict
from dataclasses import dataclass


@dataclass
class BoundingBox:
    """Represents a bounding box on screen"""
    x: int
    y: int
    width: int
    height: int
    text: Optional[str] = None
    
    @property
    def center(self) -> Tuple[int, int]:
        """Get center point of the bounding box"""
        return (self.x + self.width // 2, self.y + self.height // 2)
    
    @property
    def top_left(self) -> Tuple[int, int]:
        """Get top-left corner"""
        return (self.x, self.y)
    
    @property
    def bottom_right(self) -> Tuple[int, int]:
        """Get bottom-right corner"""
        return (self.x + self.width, self.y + self.height)
    
    def contains_point(self, x: int, y: int) -> bool:
        """Check if a point is inside the bounding box"""
        return (self.x <= x <= self.x + self.width and 
                self.y <= y <= self.y + self.height)
    
    def overlaps(self, other: 'BoundingBox') -> bool:
        """Check if this box overlaps with another"""
        return not (self.x + self.width < other.x or
                   other.x + other.width < self.x or
                   self.y + self.height < other.y or
                   other.y + other.height < self.y)
    
    def area(self) -> int:
        """Calculate area of the bounding box"""
        return self.width * self.height


def find_text_location(
    text: str, 
    ocr_results: List[Dict],
    case_sensitive: bool = False
) -> Optional[Tuple[int, int]]:
    """
    Find the center coordinates of text in OCR results.
    
    Args:
        text: Text to search for
        ocr_results: List of OCR results with 'text' and 'bbox' keys
        case_sensitive: Whether to match case
        
    Returns:
        (x, y) tuple of center coordinates, or None if not found
    """
    search_text = text if case_sensitive else text.lower()
    
    for result in ocr_results:
        result_text = result.get('text', '')
        if not case_sensitive:
            result_text = result_text.lower()
        
        if search_text in result_text or result_text in search_text:
            bbox = result.get('bbox')
            if bbox:
                # bbox format: (x, y, width, height)
                if len(bbox) == 4:
                    x, y, w, h = bbox
                    return (x + w // 2, y + h // 2)
                # Alternative bbox format: ((x1, y1), (x2, y2), (x3, y3), (x4, y4))
                elif len(bbox) == 4 and isinstance(bbox[0], (list, tuple)):
                    xs = [p[0] for p in bbox]
                    ys = [p[1] for p in bbox]
                    return ((min(xs) + max(xs)) // 2, (min(ys) + max(ys)) // 2)
    
    return None


def get_screen_region(
    x: int, 
    y: int, 
    width: int, 
    height: int,
    screen_width: int,
    screen_height: int
) -> BoundingBox:
    """
    Get a bounded screen region ensuring coordinates stay within screen bounds.
    
    Args:
        x, y: Top-left corner
        width, height: Region dimensions
        screen_width, screen_height: Screen dimensions
        
    Returns:
        BoundingBox clipped to screen bounds
    """
    x = max(0, min(x, screen_width - 1))
    y = max(0, min(y, screen_height - 1))
    width = min(width, screen_width - x)
    height = min(height, screen_height - y)
    
    return BoundingBox(x, y, width, height)


def normalize_coordinates(
    x: int, 
    y: int,
    from_width: int,
    from_height: int,
    to_width: int,
    to_height: int
) -> Tuple[int, int]:
    """
    Normalize coordinates from one resolution to another.
    Useful when OCR is done on scaled images.
    
    Args:
        x, y: Coordinates in source resolution
        from_width, from_height: Source resolution
        to_width, to_height: Target resolution
        
    Returns:
        (x, y) in target resolution
    """
    scale_x = to_width / from_width
    scale_y = to_height / from_height
    
    return (int(x * scale_x), int(y * scale_y))


def distance(p1: Tuple[int, int], p2: Tuple[int, int]) -> float:
    """Calculate Euclidean distance between two points"""
    return ((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2) ** 0.5


def find_closest_text(
    target_point: Tuple[int, int],
    ocr_results: List[Dict]
) -> Optional[Dict]:
    """
    Find the OCR result closest to a target point.
    
    Args:
        target_point: (x, y) coordinates
        ocr_results: List of OCR results with bbox information
        
    Returns:
        Closest OCR result dict, or None if no results
    """
    if not ocr_results:
        return None
    
    min_dist = float('inf')
    closest = None
    
    for result in ocr_results:
        bbox = result.get('bbox')
        if bbox:
            if len(bbox) == 4 and isinstance(bbox[0], int):
                x, y, w, h = bbox
                center = (x + w // 2, y + h // 2)
            elif len(bbox) == 4 and isinstance(bbox[0], (list, tuple)):
                xs = [p[0] for p in bbox]
                ys = [p[1] for p in bbox]
                center = ((min(xs) + max(xs)) // 2, (min(ys) + max(ys)) // 2)
            else:
                continue
            
            dist = distance(target_point, center)
            if dist < min_dist:
                min_dist = dist
                closest = result
    
    return closest

