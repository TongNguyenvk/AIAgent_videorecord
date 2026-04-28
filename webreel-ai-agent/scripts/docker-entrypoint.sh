#!/bin/bash
# ============================================================
# Docker Entrypoint: Xvfb + VNC + noVNC + Worker
#
# Starts a virtual display, VNC server, and web-based VNC client
# so you can see and interact with Chrome from your browser.
#
# Access noVNC at: http://<vps-ip>:6080/vnc.html
# ============================================================

set -e

# Virtual display config
DISPLAY_NUM="${DISPLAY_NUM:-99}"
SCREEN_RES="${SCREEN_RES:-1920x1080x24}"
VNC_PORT="${VNC_PORT:-5900}"
NOVNC_PORT="${NOVNC_PORT:-6080}"

export DISPLAY=":${DISPLAY_NUM}"

# Cleanup function
cleanup() {
    echo "[entrypoint] Shutting down..."
    # Kill processes gracefully
    for pid in $NOVNC_PID $X11VNC_PID $XVFB_PID; do
        if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
            kill "$pid" 2>/dev/null || true
        fi
    done
    # Wait for processes to exit
    sleep 1
    # Force kill if still running
    for pid in $NOVNC_PID $X11VNC_PID $XVFB_PID; do
        if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
            kill -9 "$pid" 2>/dev/null || true
        fi
    done
    # Cleanup lock files
    rm -f /tmp/.X${DISPLAY_NUM}-lock /tmp/.X11-unix/X${DISPLAY_NUM} 2>/dev/null || true
    echo "[entrypoint] All services stopped."
}
trap cleanup EXIT INT TERM

# Kill any existing processes on our display/ports
echo "[entrypoint] Cleaning up any existing processes..."
pkill -f "Xvfb :${DISPLAY_NUM}" 2>/dev/null || true
pkill -f "x11vnc.*${VNC_PORT}" 2>/dev/null || true
pkill -f "websockify.*${NOVNC_PORT}" 2>/dev/null || true
sleep 1

# Remove stale lock files
rm -f /tmp/.X${DISPLAY_NUM}-lock /tmp/.X11-unix/X${DISPLAY_NUM} 2>/dev/null || true

echo "[entrypoint] Starting Xvfb on display :${DISPLAY_NUM} (${SCREEN_RES})..."
Xvfb ":${DISPLAY_NUM}" -screen 0 "${SCREEN_RES}" -ac +extension GLX +render -noreset &
XVFB_PID=$!
sleep 2

# Verify Xvfb is running
if ! kill -0 $XVFB_PID 2>/dev/null; then
    echo "[entrypoint] ERROR: Xvfb failed to start!"
    exit 1
fi
echo "[entrypoint] Xvfb running (PID: $XVFB_PID)"

echo "[entrypoint] Starting x11vnc on port ${VNC_PORT}..."
x11vnc \
    -display ":${DISPLAY_NUM}" \
    -forever \
    -shared \
    -nopw \
    -rfbport "${VNC_PORT}" \
    -xkb \
    -noxrecord \
    -noxfixes \
    -noxdamage \
    -wait 5 \
    -defer 5 \
    2>/dev/null &
X11VNC_PID=$!
sleep 2
echo "[entrypoint] x11vnc running (PID: $X11VNC_PID)"

echo "[entrypoint] Starting noVNC (websockify) on port ${NOVNC_PORT}..."
websockify \
    --web /usr/share/novnc \
    "${NOVNC_PORT}" \
    "localhost:${VNC_PORT}" \
    2>/dev/null &
NOVNC_PID=$!
sleep 1
echo "[entrypoint] noVNC running (PID: $NOVNC_PID)"
echo "[entrypoint] ================================================"
echo "[entrypoint] noVNC ready at: http://localhost:${NOVNC_PORT}/vnc.html"
echo "[entrypoint] ================================================"

# Run the main command (e.g., python -m worker.web_worker)
echo "[entrypoint] Starting worker: $@"
exec "$@"

