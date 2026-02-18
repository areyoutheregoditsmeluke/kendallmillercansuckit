#!/usr/bin/env python3
"""
Pi Message Server
─────────────────
A minimal Flask HTTP server that stores messages and serves them to
the GitHub badge over WiFi.

Endpoints:
  GET  /health          — liveness check
  GET  /messages        — return last N messages as JSON array
  POST /message         — add a message  { text, from }
  POST /clear           — wipe all messages

Run: python3 server.py
     (or via systemd — see setup.sh)
"""

import json
import os
from datetime import datetime
from flask import Flask, request, jsonify

app = Flask(__name__)

# ── Persistence ──────────────────────────────────────────────────────────────
DATA_FILE    = os.path.expanduser("~/pi_messages.json")
MAX_MESSAGES = 200    # keep at most this many in the file


def _load() -> list:
    try:
        with open(DATA_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def _save(msgs: list) -> None:
    with open(DATA_FILE, "w") as f:
        json.dump(msgs[-MAX_MESSAGES:], f)


# ── Routes ───────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    msgs = _load()
    return jsonify({"ok": True, "service": "pi-badge-server", "count": len(msgs)})


@app.get("/messages")
def get_messages():
    """Badge polls this every 5 s. Returns last 100 messages, oldest first."""
    msgs = _load()
    return jsonify(msgs[-100:])


@app.post("/message")
def post_message():
    """Add a message. Called by the Telegram bot or the git poller."""
    data = request.get_json(silent=True) or {}
    text = data.get("text", "").strip()
    if not text:
        return jsonify({"error": "Missing text"}), 400

    msgs = _load()
    msg  = {
        "text": text,
        "from": data.get("from", "Pi"),
        "time": datetime.now().strftime("%H:%M"),
        "date": datetime.now().strftime("%Y-%m-%d"),
    }
    msgs.append(msg)
    _save(msgs)
    return jsonify({"ok": True, "total": len(msgs)})


@app.post("/clear")
def clear_messages():
    _save([])
    return jsonify({"ok": True})


# ── Startup ───────────────────────────────────────────────────────────────────

def _send_hello():
    """Post a hello-world message so the badge has something to show immediately."""
    msgs = _load()
    msgs.append({
        "text": "Hello from your Pi! System is online. Send me something via Telegram.",
        "from": "Pi",
        "time": datetime.now().strftime("%H:%M"),
        "date": datetime.now().strftime("%Y-%m-%d"),
    })
    _save(msgs)


if __name__ == "__main__":
    _send_hello()
    port = int(os.environ.get("PORT", 8765))
    print(f"Pi badge server listening on 0.0.0.0:{port}")
    # Use threaded=True so simultaneous badge poll + Telegram post don't block
    app.run(host="0.0.0.0", port=port, threaded=True)
