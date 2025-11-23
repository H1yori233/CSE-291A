"""
Utilities for ensuring a usable DISPLAY is available.

This is required when running on headless Linux servers (e.g., AWS EC2)
so that pyautogui can capture screenshots and emit mouse/keyboard events.
"""

from __future__ import annotations

import atexit
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Optional

_virtual_display: Optional["Display"] = None
_desktop_bootstrapped: bool = False


def ensure_display(
    width: int = 1920,
    height: int = 1080,
    color_depth: int = 24,
) -> str:
    """
    Make sure the DISPLAY environment variable points to a running X server.

    On headless servers, we first try to bootstrap the bundled headless desktop
    (Xvfb + XFCE/Openbox) so screenshots contain real UI content. If that is
    unavailable we fall back to pyvirtualdisplay.

    Args:
        width: Width of the virtual framebuffer
        height: Height of the virtual framebuffer
        color_depth: Color depth for the framebuffer

    Returns:
        The DISPLAY value that was verified or created.

    Raises:
        RuntimeError: If no display is available and we cannot create one.
    """

    existing_display = os.environ.get("DISPLAY")
    if existing_display:
        if _display_is_live(existing_display):
            _ensure_window_manager(existing_display)
            return existing_display
        else:
            os.environ.pop("DISPLAY", None)

    file_display = _read_display_from_file()
    if file_display and _display_is_live(file_display):
        os.environ["DISPLAY"] = file_display
        _ensure_window_manager(file_display)
        return file_display

    helper_display = _try_launch_headless_helper()
    if helper_display and _display_is_live(helper_display):
        os.environ["DISPLAY"] = helper_display
        _ensure_window_manager(helper_display)
        return helper_display

    if os.environ.get("ECUA_DISABLE_VDISPLAY") == "1":
        raise RuntimeError(
            "DISPLAY is not set and virtual display creation is disabled. "
            "Set DISPLAY manually or unset ECUA_DISABLE_VDISPLAY."
        )

    try:
        from pyvirtualdisplay import Display
    except ImportError as exc:  # pragma: no cover - import error path
        raise RuntimeError(
            "No DISPLAY detected and pyvirtualdisplay is not installed. "
            "Install it (`pip install pyvirtualdisplay`) or start an X server."
        ) from exc

    if shutil.which("Xvfb") is None:
        raise RuntimeError(
            "No DISPLAY detected and Xvfb is missing. "
            "Install it via `sudo apt-get install xvfb`."
        )

    global _virtual_display
    if _virtual_display is None or not _virtual_display.is_alive():
        _virtual_display = Display(
            visible=False,
            size=(width, height),
            color_depth=color_depth,
        )
        _virtual_display.start()
        atexit.register(stop_virtual_display)

    os.environ["DISPLAY"] = f":{_virtual_display.display}"
    _ensure_window_manager(os.environ["DISPLAY"])
    return os.environ["DISPLAY"]


def stop_virtual_display():
    """Terminate the managed virtual display if running."""
    global _virtual_display
    if _virtual_display is None:
        return
    try:
        if _virtual_display.is_alive():
            _virtual_display.stop()
    finally:
        _virtual_display = None


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _headless_log_dir() -> Path:
    return Path(os.environ.get("ECUA_HEADLESS_LOG_DIR", Path.home() / ".ecua_headless"))


def _display_env_file() -> Path:
    return _headless_log_dir() / "display.env"


def _read_display_from_file() -> Optional[str]:
    env_file = _display_env_file()
    if not env_file.exists():
        return None

    try:
        content = env_file.read_text().strip()
    except OSError:
        return None

    if not content:
        return None

    if "=" in content:
        _, value = content.split("=", 1)
        value = value.strip()
    else:
        value = content.strip()

    if not value or not value.startswith(":"):
        return None

    return value


def _wait_for_display_file(timeout: float = 10.0) -> Optional[str]:
    deadline = time.time() + timeout
    while time.time() < deadline:
        value = _read_display_from_file()
        if value:
            return value
        time.sleep(0.2)
    return None


def _try_launch_headless_helper() -> Optional[str]:
    """
    Attempt to start the helper shell script that brings up Xvfb + XFCE/VNC.
    """

    if os.environ.get("ECUA_DISABLE_HEADLESS_SCRIPT") == "1":
        return None

    script_path = _project_root() / "scripts" / "start_headless_desktop.sh"
    if not script_path.exists():
        return None

    display_value = _read_display_from_file()
    if display_value:
        return display_value

    try:
        subprocess.run(
            ["bash", str(script_path)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception as exc:  # pragma: no cover - external dependency
        print(f"[display] Failed to start headless desktop helper: {exc}")
        return None

    return _wait_for_display_file()


def _ensure_window_manager(display_value: str):
    """
    Make sure some lightweight desktop environment is running on the virtual display.
    This is necessary so that screenshots capture real UI instead of a blank framebuffer.
    """

    global _desktop_bootstrapped

    if _desktop_bootstrapped or os.environ.get("ECUA_DISABLE_DESKTOP_BOOTSTRAP") == "1":
        return

    def _process_running(name: str) -> bool:
        try:
            result = subprocess.run(
                ["pgrep", "-f", name],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return result.returncode == 0
        except FileNotFoundError:
            # pgrep missing; assume not running
            return False

    if _process_running("openbox") or _process_running("xfce4-session"):
        _desktop_bootstrapped = True
        return

    env = os.environ.copy()
    env["DISPLAY"] = display_value
    log_dir = _headless_log_dir()
    log_dir.mkdir(parents=True, exist_ok=True)

    _set_root_background(env)

    wm_candidates = []

    if shutil.which("openbox"):
        wm_candidates.append(
            (
                "openbox",
                ["openbox"],
                log_dir / "openbox.log",
            )
        )

    if shutil.which("xfce4-session"):
        wm_candidates.append(
            (
                "xfce4-session",
                [
                    "dbus-run-session",
                    "--",
                    "bash",
                    "-lc",
                    f"startxfce4 >>'{log_dir / 'xfce4.log'}' 2>&1",
                ],
                log_dir / "xfce4.log",
            )
        )

    if not wm_candidates:
        print(
            "[display] No window manager found (install openbox or xfce4) – screenshots may remain blank."
        )
        return

    started = False
    for name, cmd, log_path in wm_candidates:
        try:
            with open(log_path, "ab") as log_fp:
                subprocess.Popen(
                    cmd,
                    env=env,
                    stdout=log_fp,
                    stderr=log_fp,
                )
            started = True
            _desktop_bootstrapped = True
            break
        except Exception as exc:  # pragma: no cover - external dependency
            print(f"[display] Failed to start {name}: {exc}")

    if not started:
        return

    # Give the window manager a moment to draw the root window.
    time.sleep(3)


def _set_root_background(env):
    if not shutil.which("xsetroot"):
        return
    try:
        result = subprocess.run(
            ["xsetroot", "-solid", "#2b2b2b"],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        if result.returncode != 0:
            print("[display] xsetroot failed to set background")
    except Exception as exc:
        print(f"[display] xsetroot error: {exc}")


def _display_is_live(display_value: str) -> bool:
    """
    Check whether the given DISPLAY can be connected to.
    """

    env = os.environ.copy()
    env["DISPLAY"] = display_value

    try:
        subprocess.run(
            ["xdpyinfo"],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
        return True
    except FileNotFoundError:
        return True
    except subprocess.CalledProcessError:
        return False

