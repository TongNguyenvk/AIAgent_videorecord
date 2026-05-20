#!/bin/bash
# ============================================================
# Session Manager Start Script
# Starts Xvfb + VNC + noVNC + Chrome + Internal API
# ============================================================

set -e

DISPLAY_NUM="${DISPLAY_NUM:-99}"
VNC_PORT="${VNC_PORT:-5900}"
NOVNC_PORT="${NOVNC_PORT:-6080}"

export DISPLAY=":${DISPLAY_NUM}"

cleanup_display() {
    echo "[session-manager] Cleaning up display :${DISPLAY_NUM}..."
    pkill -9 -f "Xvfb :${DISPLAY_NUM}" 2>/dev/null || true
    pkill -9 -f "x11vnc.*${VNC_PORT}" 2>/dev/null || true
    pkill -9 -f "websockify.*${NOVNC_PORT}" 2>/dev/null || true
    sleep 1
    rm -f "/tmp/.X${DISPLAY_NUM}-lock" 2>/dev/null || true
    rm -f "/tmp/.X11-unix/X${DISPLAY_NUM}" 2>/dev/null || true
    mkdir -p /tmp/.X11-unix
    chmod 1777 /tmp/.X11-unix
    echo "[session-manager] Cleanup complete."
}

cleanup_on_exit() {
    echo "[session-manager] Shutting down..."
    for pid in $NOVNC_PID $X11VNC_PID $XVFB_PID $CHROME_PID; do
        if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
            kill "$pid" 2>/dev/null || true
        fi
    done
    echo "[session-manager] Stopped."
}
trap cleanup_on_exit EXIT INT TERM

cleanup_display

# Start Xvfb
echo "[session-manager] Starting Xvfb on display :${DISPLAY_NUM}..."
Xvfb ":${DISPLAY_NUM}" -screen 0 1920x1080x24 -ac +extension GLX +render -noreset &
XVFB_PID=$!
sleep 2

if ! kill -0 $XVFB_PID 2>/dev/null; then
    echo "[session-manager] ERROR: Xvfb failed to start"
    exit 1
fi
echo "[session-manager] Xvfb running (PID: $XVFB_PID)"

# Start x11vnc
echo "[session-manager] Starting x11vnc on port ${VNC_PORT}..."
x11vnc -display ":${DISPLAY_NUM}" -forever -shared -nopw -rfbport "${VNC_PORT}" -xkb -noxrecord -noxfixes -noxdamage -wait 5 -defer 5 2>/dev/null &
X11VNC_PID=$!
sleep 1
echo "[session-manager] x11vnc running (PID: $X11VNC_PID)"

# Start noVNC
echo "[session-manager] Starting noVNC on port ${NOVNC_PORT}..."
websockify --web /usr/share/novnc "${NOVNC_PORT}" "localhost:${VNC_PORT}" 2>/dev/null &
NOVNC_PID=$!
sleep 1
echo "[session-manager] noVNC running (PID: $NOVNC_PID)"

echo "[session-manager] VNC services started"
echo "[session-manager] noVNC: http://localhost:${NOVNC_PORT}/vnc.html"

# Clean Chrome profile locks
CHROME_PROFILE="${CHROME_PROFILE_DIR:-/app/chrome_master}"
mkdir -p "$CHROME_PROFILE"
echo "[session-manager] Cleaning Chrome profile locks in ${CHROME_PROFILE}..."
rm -f "${CHROME_PROFILE}/SingletonLock" 2>/dev/null || true
rm -f "${CHROME_PROFILE}/SingletonSocket" 2>/dev/null || true
rm -f "${CHROME_PROFILE}/SingletonCookie" 2>/dev/null || true
rm -f "${CHROME_PROFILE}/Default/SingletonLock" 2>/dev/null || true
rm -f "${CHROME_PROFILE}/Default/SingletonSocket" 2>/dev/null || true
rm -f "${CHROME_PROFILE}/Default/SingletonCookie" 2>/dev/null || true

# Kill any orphan Chrome processes
pkill -9 -f "chrome" 2>/dev/null || true
pkill -9 -f "chromium" 2>/dev/null || true
sleep 1

# Start Chrome
echo "[session-manager] Starting Chrome..."

if command -v google-chrome &> /dev/null; then
    CHROME_BIN="google-chrome"
elif [ -f /opt/pw-browsers/chromium-*/chrome-linux/chrome ]; then
    CHROME_BIN=$(ls /opt/pw-browsers/chromium-*/chrome-linux/chrome 2>/dev/null | head -1)
elif command -v chromium-browser &> /dev/null; then
    CHROME_BIN="chromium-browser"
else
    CHROME_BIN="/opt/pw-browsers/chromium-1217/chrome-linux64/chrome"
fi

echo "[session-manager] Using Chrome binary: $CHROME_BIN"

"$CHROME_BIN" \
    --display=:99 \
    --disable-gpu \
    --no-sandbox \
    --disable-dev-shm-usage \
    --disable-background-networking \
    --disable-default-apps \
    --disable-extensions \
    --disable-sync \
    --disable-translate \
    --start-maximized \
    --home-page "https://www.office.com" \
    --user-data-dir="$CHROME_PROFILE" \
    > /tmp/chrome.log 2>&1 &

CHROME_PID=$!
echo "[session-manager] Chrome started (PID: $CHROME_PID)"
sleep 3

if kill -0 $CHROME_PID 2>/dev/null; then
    echo "[session-manager] Chrome is running"
else
    echo "[session-manager] WARN: Chrome may have failed to start"
    echo "[session-manager] Chrome log:"
    cat /tmp/chrome.log
fi

# Start internal API
echo "[session-manager] Starting internal API on port 8001..."
cd /app/webreel-ai-agent
python -c "
import uvicorn
from session_manager.app import app
uvicorn.run(app, host='0.0.0.0', port=8001)
"