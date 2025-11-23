#!/usr/bin/env bash
#
# Start a lightweight virtual desktop for ECUA on headless Linux servers.
# This spins up Xvfb, launches a window manager (XFCE if available, otherwise Openbox),
# and optionally exposes the session via x11vnc so you can inspect the UI remotely.
#
# Usage:
#   chmod +x scripts/start_headless_desktop.sh
#   ./scripts/start_headless_desktop.sh
#
# Environment variables (all optional):
#   DISPLAY_NUMBER   - Numeric part of the X display to use (default: 99 → :99)
#   SCREEN_SIZE      - Resolution/depth string for Xvfb (default: 1920x1080x24)
#   VNC_PORT         - Port passed to x11vnc when available (default: 5901)
#   ECUA_HEADLESS_LOG_DIR - Where to store logs (default: ~/.ecua_headless)

set -euo pipefail

DISPLAY_NUMBER="${DISPLAY_NUMBER:-99}"
SCREEN_SIZE="${SCREEN_SIZE:-1920x1080x24}"
VNC_PORT="${VNC_PORT:-5901}"
LOG_DIR="${ECUA_HEADLESS_LOG_DIR:-$HOME/.ecua_headless}"
mkdir -p "$LOG_DIR"

display_name=":$DISPLAY_NUMBER"

log() {
  echo "[headless] $*"
}

require_binary() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required binary '$1'. Install it via apt/yum before rerunning."
    exit 1
  fi
}

require_binary Xvfb

if pgrep -f "Xvfb $display_name" >/dev/null 2>&1; then
  log "Reuse existing Xvfb on $display_name"
else
  log "Starting Xvfb on $display_name ($SCREEN_SIZE)"
  Xvfb "$display_name" -screen 0 "$SCREEN_SIZE" -ac +extension RANDR \
    >"$LOG_DIR/xvfb.log" 2>&1 &
  sleep 2
fi

export DISPLAY="$display_name"
echo "DISPLAY=$DISPLAY" >"$LOG_DIR/display.env"
log "DISPLAY exported as $DISPLAY"

start_wm() {
  if command -v xfce4-session >/dev/null 2>&1; then
    if ! pgrep -f "xfce4-session" >/dev/null 2>&1; then
      log "Launching XFCE desktop"
      dbus-run-session -- bash -c "startxfce4 >'$LOG_DIR/xfce4.log' 2>&1" &
    else
      log "XFCE already running"
    fi
  elif command -v openbox >/dev/null 2>&1; then
    if ! pgrep -f "openbox" >/dev/null 2>&1; then
      log "Launching Openbox window manager"
      openbox >"$LOG_DIR/openbox.log" 2>&1 &
    else
      log "Openbox already running"
    fi
  else
    log "No desktop environment found. Install xfce4 or openbox for best results."
  fi
}

start_wm

if command -v x11vnc >/dev/null 2>&1; then
  if ! pgrep -f "x11vnc.*$display_name" >/dev/null 2>&1; then
    log "Starting x11vnc on port $VNC_PORT (connect with: vncviewer localhost:$((VNC_PORT-5900)))"
    x11vnc -display "$display_name" -forever -rfbport "$VNC_PORT" \
      -shared -nopw -bg -o "$LOG_DIR/x11vnc.log"
  else
    log "x11vnc already running"
  fi
else
  log "x11vnc not installed; skipping VNC server (optional)"
fi

log "Headless desktop ready. Run ECUA with DISPLAY=$DISPLAY"

