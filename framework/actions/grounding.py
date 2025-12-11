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
            # Store element name in metadata for better history tracking
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
        
        import logging
        logger = logging.getLogger("framework.grounding")
        
        # Build coord hint if coordinates are provided (for disambiguation)
        coord_hint = None
        if target.x is not None and target.y is not None:
            coord_hint = (int(target.x), int(target.y))
        
        # PRIORITY 1: Name + coord hint (most robust approach)
        # Search by name in full a11y tree, use coord to disambiguate if multiple matches
        if target.name:
            name_with_hint = target.name
            if coord_hint:
                # Append coord hint for lookup_a11y_element_by_name to use
                name_with_hint = f"{target.name} @ ({coord_hint[0]}, {coord_hint[1]})"
            logger.info("[DEBUG] Looking up by name+coord: '%s'", name_with_hint)
            coords = observation.lookup_a11y_element_by_name(name_with_hint, fuzzy=True)
            if coords:
                logger.info("[DEBUG] Found '%s' at coords: %s", target.name, coords)
                return coords
            # Also try som_elements
            coords = observation.lookup_named_element(target.name)
            if coords:
                logger.info("[DEBUG] Found '%s' in som_elements at: %s", target.name, coords)
                return coords
            logger.warning("[DEBUG] Name '%s' not found", target.name)
        
        # PRIORITY 2: Element ID only (fallback if name not given)
        if target.element_id is not None:
            elem_id = target.element_id
            logger.info("[DEBUG] Looking up by element_id: [%d]", elem_id)
            for elem in observation.a11y_elements:
                if elem.id == elem_id:
                    coords = elem.center()
                    if coords:
                        logger.info("[DEBUG] Found element [%d] '%s' at coords: %s", 
                                   elem_id, elem.name, coords)
                        return coords
            logger.warning("[DEBUG] Element ID [%d] NOT FOUND in %d elements", 
                          elem_id, len(observation.a11y_elements))
        
        # PRIORITY 3: Direct x,y coordinates (fallback if name not found, or name not given)
        if coord_hint:
            coord = [coord_hint[0], coord_hint[1]]
            if target.name:
                logger.warning("[DEBUG] Name '%s' not found, falling back to coords: %s", target.name, coord)
            else:
                logger.info("[DEBUG] Using direct coordinates: %s", coord)
            if observation.original_size:
                scaled_x, scaled_y = observation.scale_coordinates(coord[0], coord[1])
                return [scaled_x, scaled_y]
            return coord
        
        # Handle coordinate type (legacy format)
        if target_type == "coordinate":
            coord = target.as_coordinate()
            if coord and observation.original_size:
                # Scale coordinates from screenshot space to original screen space
                scaled_x, scaled_y = observation.scale_coordinates(coord[0], coord[1])
                return [scaled_x, scaled_y]
            return coord
        
        # Handle element type - PRIORITY: ID > name
        if target_type == "element":
            import logging
            logger = logging.getLogger("framework.grounding")
            
            # First: Try element_id (SoM ID) - PRECISE, NO GUESSING
            if target.element_id is not None:
                elem_id = target.element_id
                logger.info("[DEBUG] Looking for element by ID: [%d]", elem_id)
                
                # Find element by ID
                for elem in observation.a11y_elements:
                    if elem.id == elem_id:
                        coords = elem.center()
                        if coords:
                            logger.info("[DEBUG] Found element [%d] '%s' at coords: %s", 
                                       elem_id, elem.name, coords)
                            return coords
                
                logger.warning("[DEBUG] Element ID [%d] NOT FOUND in %d elements", 
                              elem_id, len(observation.a11y_elements))
                return None
            
            # Fallback: Try name matching (less reliable)
            if target.name:
                logger.info("[DEBUG] Looking for element by name: '%s' in %d a11y_elements", 
                           target.name, len(observation.a11y_elements))
                
                coords = observation.lookup_a11y_element_by_name(target.name, fuzzy=True)
                if coords:
                    logger.info("[DEBUG] Found element '%s' at coords: %s", target.name, coords)
                    return coords
                
                # Fallback: try som_elements
                coords = observation.lookup_named_element(target.name)
                if coords:
                    logger.info("[DEBUG] Found element '%s' in som_elements at: %s", target.name, coords)
                    return coords
                
                # Log available element names for debugging
                available_names = [e.name for e in observation.a11y_elements[:20] if e.name]
                logger.warning("[DEBUG] Element '%s' NOT FOUND. Available names: %s", 
                              target.name, available_names)
            
            return None
        
        # Handle mark type (SoM IDs)
        if target_type == "mark" and target.id:
            return observation.lookup_mark(target.id)
        
        # Handle legacy named_element type
        if target_type == "named_element" and target.id:
            return observation.lookup_named_element(target.id)
        
        return None
