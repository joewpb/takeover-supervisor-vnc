#!/usr/bin/env python3
"""
Transport-agnostic human-takeover supervisor.

Works regardless of how the browser is driven (Playwright, Puppeteer,
raw Firefox, raw Chromium). The supervisor owns the display, the VNC
exposure, the notification, and the resume gate.

AGENT HOOK (5 lines per agent):
    # When stuck on a CAPTCHA/bot-detection:
    Path("/tmp/takeover/stuck").touch()
    # Then block until the human clears it:
    while Path("/tmp/takeover/stuck").exists():
        time.sleep(1)
    # Human has signaled resume — continue browsing.
"""

import os
import sys
import time
import signal
import subprocess

import requests

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------
DISPLAY        = ":99"
SCREEN         = "1920x1080x24"
TAILNET_IP     = "100.103.42.109"
VNC_PORT       = 5900
NOVNC_PORT     = 6080

# Secrets from the environment — never hardcode tokens.
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT  = os.environ.get("TELEGRAM_CHAT", "")

# File-based signalling between agent and supervisor.
SIG_DIR        = "/tmp/takeover"
STUCK          = os.path.join(SIG_DIR, "stuck")
RESUME         = os.path.join(SIG_DIR, "resume")
TAKEOVER_URL   = f"http://{TAILNET_IP}:{NOVNC_PORT}/vnc.html"

# Paths — resolve relative to this script so the project is relocatable.
_PROJECT_ROOT  = os.path.dirname(os.path.abspath(__file__))
NOVNC_WEB      = os.path.join(_PROJECT_ROOT, "novnc")
WEBSOCKIFY     = "websockify"
X11VNC         = os.path.expanduser("~/.local/bin/x11vnc-wrapper")
XVFB           = "Xvfb"

# Child process handles for cleanup.
_children: list[subprocess.Popen] = []


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------
def _check_binary(name: str) -> str:
    """Resolve a binary; exit early if it's missing."""
    path = subprocess.run(
        ["which", name], capture_output=True, text=True
    ).stdout.strip()
    if not path:
        print(f"[FATAL] '{name}' not found in PATH. Install it first.")
        sys.exit(1)
    return path


def _safe_remove(path: str) -> None:
    """Remove a file, silently ignoring if it's already gone."""
    try:
        os.remove(path)
    except FileNotFoundError:
        pass


def _cleanup(*_args) -> None:
    """Stop all child processes on exit."""
    print("\n[supervisor] shutting down children...")
    for child in _children:
        try:
            child.terminate()
        except Exception:
            pass
    for child in _children:
        try:
            child.wait(timeout=3)
        except Exception:
            child.kill()
    _safe_remove(STUCK)
    _safe_remove(RESUME)
    print("[supervisor] done.")


# ---------------------------------------------------------------------------
# DISPLAY + VNC
# ---------------------------------------------------------------------------
def start_display() -> None:
    """Launch Xvfb, x11vnc, and websockify/noVNC. All bound to Tailscale only."""
    os.makedirs(SIG_DIR, exist_ok=True)

    # Verify binaries
    _check_binary(XVFB)
    _check_binary(WEBSOCKIFY)
    _check_binary(X11VNC)

    if not os.path.isdir(NOVNC_WEB):
        print(f"[FATAL] noVNC web root not found at {NOVNC_WEB}")
        sys.exit(1)

    # 1. Virtual framebuffer
    xvfb = subprocess.Popen([XVFB, DISPLAY, "-screen", "0", SCREEN])
    _children.append(xvfb)

    # Wait for the X socket to actually appear.
    for _ in range(30):
        if os.path.exists(f"/tmp/.X{DISPLAY.replace(':', '')}-lock"):
            break
        time.sleep(0.5)
    else:
        print("[FATAL] Xvfb did not start within 15 seconds")
        _cleanup()
        sys.exit(1)

    # 2. VNC server — listen on the Tailscale interface ONLY.
    #    Do NOT pass -localhost; it conflicts with -listen and blocks
    #    remote (Tailscale-routed) connections.
    x11vnc = subprocess.Popen([
        X11VNC,
        "-display", DISPLAY,
        "-rfbport", str(VNC_PORT),
        "-listen", TAILNET_IP,
        "-shared", "-forever",
        "-nopw",                # no password — Tailscale is the auth layer
        "-quiet",
    ])
    _children.append(x11vnc)

    # 3. noVNC bridge — WebSocket on the Tailscale interface.
    ws = subprocess.Popen([
        WEBSOCKIFY,
        "--web", NOVNC_WEB,
        f"{TAILNET_IP}:{NOVNC_PORT}",
        f"{TAILNET_IP}:{VNC_PORT}",
    ])
    _children.append(ws)

    print(f"[display] up on {DISPLAY}, takeover → {TAKEOVER_URL}")


# ---------------------------------------------------------------------------
# NOTIFY
# ---------------------------------------------------------------------------
def notify_telegram() -> None:
    """Send a Telegram message with the takeover URL."""
    if not (TELEGRAM_TOKEN and TELEGRAM_CHAT):
        print("[notify] creds missing — printing instead")
        print(f"[notify] TAKE OVER: {TAKEOVER_URL}")
        return
    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            data={
                "chat_id": TELEGRAM_CHAT,
                "text": f"Puzzle hit. Take over: {TAKEOVER_URL}",
            },
            timeout=10,
        )
        if not resp.ok:
            print(f"[notify] Telegram API error: {resp.status_code} {resp.text[:200]}")
    except requests.RequestException as e:
        print(f"[notify] failed: {e}")


# ---------------------------------------------------------------------------
# MAIN LOOP
# ---------------------------------------------------------------------------
def supervise() -> None:
    start_display()

    print("[supervisor] watching for stuck signal...")
    while True:
        if os.path.exists(STUCK):
            print("[supervisor] agent is stuck → notifying")
            notify_telegram()
            _safe_remove(STUCK)

            print("[supervisor] waiting for human to solve puzzle...")
            while not os.path.exists(RESUME):
                time.sleep(1)
            _safe_remove(RESUME)
            print("[supervisor] resume received → agent continues")
        time.sleep(1)


# ---------------------------------------------------------------------------
# ENTRYPOINT
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    signal.signal(signal.SIGINT, _cleanup)
    signal.signal(signal.SIGTERM, _cleanup)
    supervise()
