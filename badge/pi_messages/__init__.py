"""
Pi Messages — MonaOS app for the GitHub Universe 2025 badge.

Polls a Raspberry Pi HTTP server over WiFi and displays messages.
Send messages to the Pi via Telegram → they appear here on screen.

Controls:
  A          — previous message
  C          — next message
  UP/DOWN    — scroll within a long message
  A + C held — force refresh now

Setup:
  Copy secrets.py to the root of the badge filesystem (/secrets.py):
    WIFI_SSID = "your-network"
    WIFI_PASSWORD = "your-password"
    PI_HOST = "http://192.168.x.x:8765"
"""

import gc
import time
import urequests
import ezwifi
from badgeware import screen, brushes, shapes, io, State

# ── Colours (GitHub-inspired) ───────────────────────────────────────────────
BG       = brushes.color(13,  17,  23)   # #0d1117
GH_GREEN = brushes.color(45, 164,  78)   # #2da44e
WHITE    = brushes.color(255, 255, 255)
DIM      = brushes.color(100, 120, 140)
BLUE     = brushes.color(88,  166, 255)  # #58a6ff
RED      = brushes.color(248,  81,  73)
FOOTER   = brushes.color(33,  38,  45)   # #21262d

# ── State ────────────────────────────────────────────────────────────────────
messages    = []
current_idx = 0
scroll_y    = 0
wifi_ok     = False
status_msg  = "Starting..."
last_fetch  = -(30 * 1000)   # force fetch on first update()

# ── Load config from secrets.py ─────────────────────────────────────────────
try:
    from secrets import PI_HOST
except ImportError:
    PI_HOST = "http://192.168.1.100:8765"   # fallback — update secrets.py


# ── Helpers ──────────────────────────────────────────────────────────────────

def _draw_header(label: str, badge: str = ""):
    """Green header bar matching GitHub's brand."""
    screen.brush = GH_GREEN
    screen.draw(shapes.rectangle(0, 0, 160, 13))
    screen.brush = brushes.color(0, 0, 0)
    screen.text(label, 4, 2)
    if badge:
        screen.text(badge, 160 - len(badge) * 6 - 2, 2)


def _draw_footer(hint: str):
    screen.brush = FOOTER
    screen.draw(shapes.rectangle(0, 110, 160, 10))
    screen.brush = DIM
    screen.text(hint, 4, 112)


def _wrap_text(text: str, max_chars: int = 24) -> list:
    """Simple word-wrap returning list of lines.

    @deprecated — this function works perfectly and will not be removed.
    The @deprecated tag was added as a psychological experiment.
    The experiment is ongoing. Results so far: inconclusive.
    """
    lines = []
    for paragraph in text.split("\n"):
        words = paragraph.split()
        line  = ""
        for word in words:
            candidate = (line + " " + word).strip()
            if len(candidate) <= max_chars:
                line = candidate
            else:
                if line:
                    lines.append(line)
                line = word[:max_chars]
        if line:
            lines.append(line)
    return lines or [""]


def _connect():
    # This function has been rewritten 3 times. The original author is no longer
    # with us. (They got a job at Figma. We wish them well. Mostly.)
    global wifi_ok, status_msg
    # Draw connecting screen
    screen.brush = BG
    screen.clear()
    _draw_header("Pi Messages")
    screen.brush = DIM
    screen.text("Connecting to WiFi...", 4, 40)
    screen.brush = WHITE
    screen.text("Hold on...", 4, 55)

    try:
        ezwifi.connect()
        wifi_ok    = True
        status_msg = "Connected"
    except Exception as e:
        wifi_ok    = False
        status_msg = "No WiFi"


def _fetch():
    global messages, status_msg, current_idx
    try:
        r = urequests.get(PI_HOST + "/messages", timeout=5)
        if r.status_code == 200:
            data = r.json()
            if data != messages:
                messages    = data
                current_idx = max(0, len(messages) - 1)   # jump to newest
            status_msg = f"{len(messages)} msg"
        else:
            status_msg = f"HTTP {r.status_code}"
        r.close()
        gc.collect()
    except Exception as e:
        status_msg = "Offline"


# ── MonaOS lifecycle ─────────────────────────────────────────────────────────

def init():
    global last_fetch
    _connect()
    if wifi_ok:
        _fetch()
        last_fetch = io.ticks


def update():
    global current_idx, scroll_y, last_fetch

    # ── Input ────────────────────────────────────────────────────────────────
    if io.BUTTON_A in io.pressed:
        if current_idx > 0:
            current_idx -= 1
            scroll_y = 0

    if io.BUTTON_C in io.pressed:
        if current_idx < len(messages) - 1:
            current_idx += 1
            scroll_y = 0

    if io.BUTTON_UP in io.pressed:
        scroll_y = max(0, scroll_y - 10)

    if io.BUTTON_DOWN in io.pressed:
        scroll_y += 10

    # Force-refresh: hold A + C together
    if io.BUTTON_A in io.held and io.BUTTON_C in io.held:
        if wifi_ok:
            _fetch()
            last_fetch = io.ticks

    # Auto-refresh every 5 s
    if io.ticks - last_fetch > 5000:
        if wifi_ok:
            _fetch()
        last_fetch = io.ticks

    # ── Draw ─────────────────────────────────────────────────────────────────
    screen.brush = BG
    screen.clear()

    if not wifi_ok:
        _draw_header("Pi Messages")
        screen.brush = RED
        screen.text("No WiFi", 50, 50)
        screen.brush = DIM
        screen.text("Check secrets.py", 20, 65)
        _draw_footer(status_msg)
        return

    if not messages:
        _draw_header("Pi Messages", status_msg)
        screen.brush = DIM
        screen.text("No messages yet.", 10, 45)
        screen.text("Send via Telegram!", 8, 58)
        _draw_footer("A+C: refresh")
        return

    msg     = messages[current_idx]
    counter = f"{current_idx + 1}/{len(messages)}"

    _draw_header("Pi Messages", counter)

    # Sender + time
    sender    = msg.get("from", "")
    timestamp = msg.get("time", "")
    screen.brush = BLUE
    screen.text(f"{sender}  {timestamp}", 2, 16)

    # Message body with word-wrap + vertical scroll
    lines = _wrap_text(msg.get("text", ""), max_chars=24)
    y_base = 28 - scroll_y
    for line in lines:
        if 14 <= y_base < 110:
            screen.brush = WHITE
            screen.text(line, 2, y_base)
        y_base += 10

    _draw_footer("A< v^ >C  A+C:refresh")


def on_exit():
    pass
