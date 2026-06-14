# Human Takeover Supervisor (VNC Edition)

Transport-agnostic human-in-the-loop supervisor for browser automation.

---

## Overview

# Human Takeover Supervisor (VNC Edition)

Transport-agnostic human-in-the-loop supervisor for browser automation. When your
agent hits a CAPTCHA, bot-detection puzzle, or login wall, the supervisor:

1. Detects the "stuck" signal (a file touch from the agent)
2. Notifies you via Telegram with a noVNC link
3. Gives you full mouse/keyboard control over the browser session
4. Waits for your "resume" signal before letting the agent continue

**VNC Edition** — requires a local browser (Chromium/Firefox) on the Xvfb display. For the chat-based version (no VNC needed), see [takeover-supervisor](https://github.com/joewpb/takeover-supervisor).

## How It Works

```
Agent hits puzzle → touches /tmp/takeover/stuck
                                  ↓
Supervisor detects stuck → notifies you on Telegram
                                  ↓
You open the noVNC URL, solve the puzzle
                                  ↓
Supervisor detects /tmp/takeover/resume → agent continues
```

The supervisor owns the display (Xvfb virtual framebuffer), the VNC server
(x11vnc), and the noVNC web bridge (websockify). Agents only need 5 lines of
code to integrate — they never touch display/VNC/notification logic.

## Why Tailscale?

Everything is bound to your Tailscale IP only — never 0.0.0.0, never localhost.
Your phone connects over the Tailnet, which provides WireGuard encryption and
mutual authentication. No passwords, no exposed ports, no reverse proxies.

## Prerequisites

- Linux with Xvfb installed
- [`x11vnc`](https://github.com/LibVNC/x11vnc) (binary + libvncserver/libvncclient)
- [`websockify`](https://github.com/novnc/websockify) (`pip install websockify`)
- [Tailscale](https://tailscale.com/) running on the machine
- A Telegram bot token (from [@BotFather](https://t.me/BotFather))
- Python 3.8+ with `requests`

## Quick Start

```bash
# 1. Clone
git clone https://github.com/<user>/takeover-supervisor.git
cd takeover-supervisor

# 2. Install Python dep
pip install requests

# 3. Set secrets
export TELEGRAM_TOKEN="your-bot-token"
export TELEGRAM_CHAT="your-telegram-user-id"

# 4. Launch
python3 supervisor.py
```

## Agent Integration

The agent only needs to touch two files. Here's the pattern for any
browser-automation framework:

```python
from pathlib import Path
import time

STUCK  = Path("/tmp/takeover/stuck")
RESUME = Path("/tmp/takeover/resume")

def handle_puzzle(driver):
    """Call this when the agent detects a CAPTCHA or bot wall."""
    STUCK.touch()                     # Signal the supervisor
    while STUCK.exists():             # Block until human solves it
        time.sleep(1)
    # Human has touched the resume file — continue browsing
```

That's it. The agent never touches Xvfb, x11vnc, websockify, or noVNC. The
supervisor owns all of that.

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `TAILNET_IP` | auto-detected | Your machine's Tailscale address |
| `VNC_PORT` | `5900` | VNC server port |
| `NOVNC_PORT` | `6080` | noVNC web port |
| `DISPLAY` | `:99` | X11 display number |
| `SCREEN` | `1920x1080x24` | Virtual screen resolution |
| `TELEGRAM_TOKEN` | (env) | Telegram bot token |
| `TELEGRAM_CHAT` | (env) | Telegram user/chat ID |

## How To Get Your Telegram Chat ID

1. Send any message to your bot
2. Visit: `https://api.telegram.org/bot<TOKEN>/getUpdates`
3. Find `"chat":{"id":7482279278}` — that's your chat ID

## Architecture

```
┌─────────────┐     touch /tmp/takeover/stuck     ┌──────────────┐
│  Your Agent │ ─────────────────────────────────→ │  Supervisor  │
│ (Playwright,│                                    │              │
│  Puppeteer, │ ←─── resume when file disappears ─ │  Xvfb :99    │
│  Selenium)  │                                    │  x11vnc      │
└─────────────┘                                    │  websockify  │
                                                   │  noVNC       │
                                                   └──────┬───────┘
                                                          │ Tailscale
                                                          ↓
                                                   ┌──────────────┐
                                                   │  Your Phone  │
                                                   │  (noVNC URL) │
                                                   └──────────────┘
```

## License

MIT


---

## Architecture

### Inputs

### Outputs

### Dependencies
_None specified_

### Data Flow

```mermaid
flowchart LR
    subgraph Inputs
    end

    subgraph Processing
        P[Human Takeover Supervisor (VNC Edition)]
    end

    subgraph Outputs
    end

```


---

## Code References

_None provided_

---

## Provenance

| Field | Value |
|-------|-------|
| Hermes Run ID | discovery |
| Payload Hash | b68a32e924a3abd5c65d28530860e4d39f44ea909a728a0ff7f68756172da2b1 |
| Source Path | /home/hermes/workspace/takeover-supervisor-vnc |
| Published At | 2026-06-14T09:00:46Z |
| Kind | project |
| Destination | existing_repo |