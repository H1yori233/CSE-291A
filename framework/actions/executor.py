"""
Action executor for ECUA agent
Executes actions via GUI automation and system commands
"""

import os
import shlex
import time
import platform
import shutil
import subprocess
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path

from PIL import Image

from framework.utils.display import ensure_display

ensure_display()
import pyautogui

from framework.actions.schema import Action, ActionList
from framework.utils.coords import find_text_location


LINUX_APP_COMMANDS = {
    "terminal": [
        ["xfce4-terminal"],
        ["gnome-terminal"],
        ["xterm"],
        ["lxterminal"],
    ],
    "gedit": [
        ["gedit"],
    ],
    "gimagereader": [
        ["gimagereader-gtk"],
        ["gimagereader-qt"],
    ],
    "gimagereader-gtk": [
        ["gimagereader-gtk"],
    ],
}

LINUX_WINDOW_ALIASES = {
    "terminal": ["xfce4-terminal", "xterm", "terminal"],
    "gedit": ["gedit", "text editor"],
    "gimagereader": ["gimagereader", "image reader", "gimagereader-gtk"],
    "gimagereader-gtk": ["gimagereader-gtk", "gimagereader"],
}

LINUX_APP_BINARIES = {
    cmd[0].lower()
    for variants in LINUX_APP_COMMANDS.values()
    for cmd in variants
    if cmd
}


class ActionExecutor:
    """
    Executes actions on the system using GUI automation and system commands.
    """
    
    def __init__(self, delay: float = 0.5):
        """
        Initialize the action executor.
        
        Args:
            delay: Default delay between actions (seconds)
        """
        self.delay = delay
        self.platform = platform.system()
        
        # Configure PyAutoGUI
        pyautogui.FAILSAFE = False  # Disable failsafe for automation
        pyautogui.PAUSE = 0.1  # Small pause between PyAutoGUI commands
    
    def execute(
        self, 
        action: Action,
        ocr_results: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        Execute a single action.
        
        Args:
            action: Action to execute
            ocr_results: OCR results for resolving target_text
            
        Returns:
            Dict with 'success', 'message', and optional 'result' keys
        """
        try:
            action_type = action.action
            
            if action_type == "CLICK":
                return self._execute_click(action, ocr_results)
            elif action_type == "MOVE":
                return self._execute_move(action, ocr_results)
            elif action_type == "SCROLL":
                return self._execute_scroll(action)
            elif action_type == "TYPE":
                return self._execute_type(action)
            elif action_type == "KEY":
                return self._execute_key(action)
            elif action_type == "FOCUS_APP":
                return self._execute_focus_app(action)
            elif action_type == "OPEN":
                return self._execute_open(action)
            elif action_type == "EXECUTE":
                return self._execute_command(action)
            elif action_type == "VERIFY_FILE":
                return self._execute_verify_file(action)
            elif action_type == "WAIT":
                return self._execute_wait(action)
            else:
                return {
                    'success': False,
                    'message': f"Unknown action type: {action_type}"
                }
        except Exception as e:
            return {
                'success': False,
                'message': f"Action execution failed: {str(e)}"
            }
    
    def execute_batch(
        self, 
        actions: ActionList,
        ocr_results: Optional[List[Dict]] = None
    ) -> List[Dict[str, Any]]:
        """
        Execute a batch of actions.
        
        Args:
            actions: ActionList to execute
            ocr_results: OCR results for resolving target_text
            
        Returns:
            List of result dicts
        """
        results = []
        for action in actions.actions:
            result = self.execute(action, ocr_results)
            results.append(result)
            
            # Stop on failure if critical
            if not result['success']:
                # For now, continue even on failure
                # In production, you might want configurable behavior
                pass
            
            # Add delay between actions
            if self.delay > 0:
                time.sleep(self.delay)
        
        return results
    
    def _resolve_coordinates(
        self, 
        action: Action,
        ocr_results: Optional[List[Dict]] = None
    ) -> Optional[tuple]:
        """
        Resolve action coordinates from x/y or target_text.
        
        Args:
            action: Action with coordinates or target_text
            ocr_results: OCR results for text lookup
            
        Returns:
            (x, y) tuple or None if unable to resolve
        """
        # If x and y are provided, use them
        if action.x is not None and action.y is not None:
            return (action.x, action.y)
        
        # If target_text is provided, look it up in OCR results
        if action.target_text and ocr_results:
            coords = find_text_location(action.target_text, ocr_results)
            if coords:
                return coords
            else:
                print(f"Warning: Could not find text '{action.target_text}' on screen")
                return None
        
        return None
    
    def _execute_click(
        self, 
        action: Action,
        ocr_results: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """Execute CLICK action"""
        coords = self._resolve_coordinates(action, ocr_results)
        
        if coords is None:
            return {
                'success': False,
                'message': "Could not resolve click coordinates"
            }
        
        x, y = coords
        pyautogui.click(x, y)
        
        return {
            'success': True,
            'message': f"Clicked at ({x}, {y})",
            'coordinates': coords
        }
    
    def _execute_move(
        self, 
        action: Action,
        ocr_results: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """Execute MOVE action"""
        coords = self._resolve_coordinates(action, ocr_results)
        
        if coords is None:
            return {
                'success': False,
                'message': "Could not resolve move coordinates"
            }
        
        x, y = coords
        pyautogui.moveTo(x, y)
        
        return {
            'success': True,
            'message': f"Moved to ({x}, {y})",
            'coordinates': coords
        }
    
    def _execute_scroll(self, action: Action) -> Dict[str, Any]:
        """Execute SCROLL action"""
        amount = action.amount or 1
        
        # PyAutoGUI scroll: positive = up, negative = down
        # We use opposite convention: positive = down, negative = up
        pyautogui.scroll(-amount)
        
        return {
            'success': True,
            'message': f"Scrolled by {amount}",
            'amount': amount
        }
    
    def _execute_type(self, action: Action) -> Dict[str, Any]:
        """Execute TYPE action"""
        if not action.arg:
            return {
                'success': False,
                'message': "No text provided for TYPE action"
            }
        
        pyautogui.write(action.arg, interval=0.05)
        
        return {
            'success': True,
            'message': f"Typed: {action.arg[:50]}...",
            'text': action.arg
        }
    
    def _execute_key(self, action: Action) -> Dict[str, Any]:
        """Execute KEY action"""
        if not action.arg:
            return {
                'success': False,
                'message': "No key provided for KEY action"
            }
        
        # Handle key combinations like "cmd+c", "ctrl+v"
        keys = action.arg.split('+')
        
        if len(keys) == 1:
            pyautogui.press(keys[0])
        else:
            # Convert platform-specific modifiers
            normalized_keys = []
            for key in keys:
                key = key.strip().lower()
                # Map "cmd" to "command" for macOS
                if key == 'cmd':
                    key = 'command'
                normalized_keys.append(key)
            
            pyautogui.hotkey(*normalized_keys)
        
        return {
            'success': True,
            'message': f"Pressed key: {action.arg}",
            'key': action.arg
        }
    
    def _execute_focus_app(self, action: Action) -> Dict[str, Any]:
        """Execute FOCUS_APP action"""
        if not action.arg:
            return {
                'success': False,
                'message': "No app name provided for FOCUS_APP action"
            }
        
        app_name = action.arg
        
        try:
            if self.platform == "Darwin":  # macOS
                script = f'tell application "{app_name}" to activate'
                subprocess.run(['osascript', '-e', script], check=True)
            elif self.platform == "Linux":
                if self._focus_linux_window(app_name):
                    return {
                        'success': True,
                        'message': f"Focused app: {app_name}",
                        'app': app_name
                    }

                launched = self._launch_linux_app(app_name)
                if launched:
                    time.sleep(2)
                    if self._focus_linux_window(app_name):
                        return {
                            'success': True,
                            'message': f"Launched and focused app: {app_name}",
                            'app': app_name
                        }
                    return {
                        'success': True,
                        'message': f"Launched app '{app_name}', focus pending",
                        'app': app_name
                    }

                raise RuntimeError("wmctrl focus failed and no launch command succeeded")
            elif self.platform == "Windows":
                # On Windows, you might use pywinauto or similar
                # For now, simple implementation
                subprocess.run(['start', app_name], shell=True, check=True)
            
            return {
                'success': True,
                'message': f"Focused app: {app_name}",
                'app': app_name
            }
        except Exception as e:
            return {
                'success': False,
                'message': f"Failed to focus app '{app_name}': {str(e)}"
            }
    
    def _execute_open(self, action: Action) -> Dict[str, Any]:
        """Execute OPEN action"""
        if not action.arg:
            return {
                'success': False,
                'message': "No path/URL provided for OPEN action"
            }
        
        target = action.arg
        
        try:
            if self.platform == "Darwin":  # macOS
                subprocess.run(['open', target], check=True)
            elif self.platform == "Linux":
                subprocess.Popen(
                    ['xdg-open', target],
                    env=os.environ.copy(),
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                )
            elif self.platform == "Windows":
                os.startfile(target)
            
            return {
                'success': True,
                'message': f"Opened: {target}",
                'target': target
            }
        except Exception as e:
            return {
                'success': False,
                'message': f"Failed to open '{target}': {str(e)}"
            }
    
    def _execute_command(self, action: Action) -> Dict[str, Any]:
        """Execute EXECUTE action"""
        if not action.arg:
            return {
                'success': False,
                'message': "No command provided for EXECUTE action"
            }
        
        command = action.arg
        
        handled, result = self._maybe_launch_background_gui(command)
        if handled:
            return result
        
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            return {
                'success': result.returncode == 0,
                'message': f"Executed: {command}",
                'command': command,
                'returncode': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr
            }
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'message': f"Command timed out: {command}"
            }
        except Exception as e:
            return {
                'success': False,
                'message': f"Failed to execute '{command}': {str(e)}"
            }
    
    def _execute_verify_file(self, action: Action) -> Dict[str, Any]:
        """Execute VERIFY_FILE action"""
        if not action.arg:
            return {
                'success': False,
                'message': "No file path provided for VERIFY_FILE action"
            }
        
        filepath = Path(action.arg).expanduser()
        exists = filepath.exists()
        
        return {
            'success': exists,
            'message': f"File {'exists' if exists else 'does not exist'}: {filepath}",
            'path': str(filepath),
            'exists': exists
        }
    
    def _execute_wait(self, action: Action) -> Dict[str, Any]:
        """Execute WAIT action"""
        amount = action.amount or 1
        time.sleep(amount)
        
        return {
            'success': True,
            'message': f"Waited {amount} seconds",
            'duration': amount
        }

    def _maybe_launch_background_gui(self, command: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Detect long-running GUI commands (e.g., gimagereader-gtk) and launch them
        in the background so EXECUTE actions do not hang waiting for the process
        to exit.
        """
        if self.platform != "Linux":
            return False, {}

        try:
            parts = shlex.split(command)
        except ValueError:
            return False, {}

        if not parts:
            return False, {}

        executable = parts[0]
        binary_name = Path(executable).name.lower()

        if binary_name not in LINUX_APP_BINARIES:
            return False, {}

        resolved_exec = executable
        if shutil.which(resolved_exec) is None:
            resolved_exec = shutil.which(binary_name)
            if resolved_exec is None:
                return True, {
                    'success': False,
                    'message': f"Command not found: {executable}",
                    'command': command,
                }
            parts[0] = resolved_exec

        try:
            subprocess.Popen(
                parts,
                env=os.environ.copy(),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            return True, {
                'success': True,
                'message': f"Launched GUI command: {command}",
                'command': command,
            }
        except Exception as exc:
            return True, {
                'success': False,
                'message': f"Failed to launch '{command}': {exc}",
                'command': command,
            }

    def _focus_linux_window(self, app_name: str) -> bool:
        if shutil.which("wmctrl") is None:
            return False

        try:
            subprocess.run(['wmctrl', '-a', app_name], check=True)
            return True
        except subprocess.CalledProcessError:
            pass

        try:
            proc = subprocess.run(
                ['wmctrl', '-lx'],
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError:
            return False

        search_terms = [app_name.lower()]
        search_terms.extend(LINUX_WINDOW_ALIASES.get(app_name.lower(), []))

        for line in proc.stdout.splitlines():
            lower_line = line.lower()
            if any(term in lower_line for term in search_terms):
                parts = line.split()
                if not parts:
                    continue
                window_id = parts[0]
                try:
                    subprocess.run(['wmctrl', '-ia', window_id], check=True)
                    return True
                except subprocess.CalledProcessError:
                    continue
        return False

    def _launch_linux_app(self, app_name: str) -> bool:
        commands = LINUX_APP_COMMANDS.get(app_name.lower())
        if not commands:
            return False

        env = os.environ.copy()
        for cmd in commands:
            binary = cmd[0]
            if shutil.which(binary) is None:
                continue
            try:
                subprocess.Popen(
                    cmd,
                    env=env,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                )
                return True
            except Exception:
                continue
        return False


# Global executor instance
_executor = None


def get_executor(delay: float = 0.5) -> ActionExecutor:
    """
    Get or create global ActionExecutor instance.
    
    Args:
        delay: Default delay between actions
        
    Returns:
        ActionExecutor instance
    """
    global _executor
    if _executor is None:
        _executor = ActionExecutor(delay=delay)
    return _executor

