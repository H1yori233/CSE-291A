"""
Screenshot capture utilities
"""

import platform
from typing import Optional, Tuple
from PIL import Image

from framework.utils.display import ensure_display

ensure_display()
import pyautogui


class ScreenCapture:
    """
    Cross-platform screenshot capture.
    """
    
    def __init__(self):
        """Initialize screen capture"""
        self.platform = platform.system()
        # Disable PyAutoGUI fail-safe for automated operation
        pyautogui.FAILSAFE = False
    
    def get_screen_size(self) -> Tuple[int, int]:
        """
        Get the screen dimensions.
        
        Returns:
            (width, height) tuple
        """
        return pyautogui.size()
    
    def capture_screenshot(
        self, 
        region: Optional[Tuple[int, int, int, int]] = None
    ) -> Image.Image:
        """
        Capture a screenshot of the entire screen or a region.
        
        Args:
            region: Optional (x, y, width, height) tuple to capture specific region
            
        Returns:
            PIL Image of the screenshot
        """
        if region:
            screenshot = pyautogui.screenshot(region=region)
        else:
            screenshot = pyautogui.screenshot()
        
        return screenshot
    
    def capture_window(self, window_title: str) -> Optional[Image.Image]:
        """
        Capture a specific window by title.
        
        Args:
            window_title: Title of the window to capture
            
        Returns:
            PIL Image of the window, or None if window not found
        """
        # Note: This is a simplified version. For production,
        # you'd want to use platform-specific APIs
        try:
            if self.platform == "Darwin":  # macOS
                # For macOS, you might use pyobjc or applescript
                return self.capture_screenshot()  # Fallback to full screen
            elif self.platform == "Linux":
                # For Linux, you might use wmctrl or xdotool
                return self.capture_screenshot()  # Fallback to full screen
            elif self.platform == "Windows":
                # For Windows, you might use pywin32
                return self.capture_screenshot()  # Fallback to full screen
            else:
                return self.capture_screenshot()
        except Exception as e:
            print(f"Error capturing window: {e}")
            return None
    
    def capture_with_cursor(self) -> Tuple[Image.Image, Tuple[int, int]]:
        """
        Capture screenshot and return cursor position.
        
        Returns:
            (screenshot, (cursor_x, cursor_y)) tuple
        """
        cursor_pos = pyautogui.position()
        screenshot = self.capture_screenshot()
        return screenshot, cursor_pos
    
    def save_screenshot(
        self, 
        filepath: str, 
        region: Optional[Tuple[int, int, int, int]] = None
    ) -> str:
        """
        Capture and save a screenshot directly to file.
        
        Args:
            filepath: Path to save the screenshot
            region: Optional region to capture
            
        Returns:
            Path where screenshot was saved
        """
        screenshot = self.capture_screenshot(region=region)
        screenshot.save(filepath)
        return filepath


# Global instance for convenience
_screen_capture = None


def get_screen_capture() -> ScreenCapture:
    """
    Get or create the global ScreenCapture instance.
    
    Returns:
        Global ScreenCapture instance
    """
    global _screen_capture
    if _screen_capture is None:
        _screen_capture = ScreenCapture()
    return _screen_capture


def capture_screen() -> Image.Image:
    """
    Convenience function to capture full screen.
    
    Returns:
        PIL Image of the screenshot
    """
    return get_screen_capture().capture_screenshot()


def get_screen_size() -> Tuple[int, int]:
    """
    Convenience function to get screen size.
    
    Returns:
        (width, height) tuple
    """
    return get_screen_capture().get_screen_size()

