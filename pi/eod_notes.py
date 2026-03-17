#!/usr/bin/env python3
"""
EOD Notes — End-of-Day note capture and retrieval
───────────────────────────────────────────────────
Stores end-of-day notes sent via Telegram /eod command.
Notes are plain text files in ~/eod_notes/YYYY-MM-DD.txt.

The morning_brief.py script reads the most recent note and
includes it in the morning summary.

Usage (from Telegram bot):
  /eod Finished the data platform design doc. Still need to follow
       up with Jack about the API contract. Big 2.0 meeting went
       well — Christian seems aligned.

Usage (from morning_brief.py):
  from eod_notes import get_last_eod_note
  note = get_last_eod_note()
"""

import os
from datetime import datetime, timedelta
from pathlib import Path

EOD_DIR = Path.home() / "eod_notes"


def _ensure_dir() -> None:
    EOD_DIR.mkdir(exist_ok=True)


def save_eod_note(text: str, timestamp: datetime = None) -> Path:
    """Save an EOD note for today. Appends if called multiple times."""
    _ensure_dir()
    if timestamp is None:
        timestamp = datetime.now()

    date_str = timestamp.strftime("%Y-%m-%d")
    path = EOD_DIR / f"{date_str}.txt"

    # Append with timestamp if file already exists
    if path.exists():
        with open(path, "a") as f:
            f.write(f"\n\n--- {timestamp.strftime('%I:%M %p')} ---\n{text.strip()}\n")
    else:
        with open(path, "w") as f:
            f.write(f"--- {timestamp.strftime('%A, %B %d, %Y')} ---\n")
            f.write(f"--- {timestamp.strftime('%I:%M %p')} ---\n")
            f.write(f"{text.strip()}\n")

    return path


def get_last_eod_note() -> dict | None:
    """
    Return the most recent EOD note.
    
    Checks in order:
    1. Today's file (if exists) - for late-night/early-morning notes about today
    2. Yesterday's file - for evening notes about tomorrow
    3. Up to 3 days back - in case you missed a day
    
    Returns dict with 'date', 'text', 'path' or None if no note found.
    """
    _ensure_dir()
    now = datetime.now()
    
    # Check today first (for late-night notes about today)
    today_str = now.strftime("%Y-%m-%d")
    today_path = EOD_DIR / f"{today_str}.txt"
    if today_path.exists():
        text = today_path.read_text().strip()
        if text:
            return {
                "date": today_str,
                "date_label": "Last night / this morning",
                "text": text,
                "path": today_path,
                "days_ago": 0,
            }
    
    # Then check yesterday and previous days
    for days_back in range(1, 4):
        target = now - timedelta(days=days_back)
        date_str = target.strftime("%Y-%m-%d")
        path = EOD_DIR / f"{date_str}.txt"

        if path.exists():
            text = path.read_text().strip()
            if text:
                label = "Yesterday" if days_back == 1 else target.strftime("%A, %B %d")
                return {
                    "date": date_str,
                    "date_label": label,
                    "text": text,
                    "path": path,
                    "days_ago": days_back,
                }

    return None


def get_eod_note_for_date(date_str: str) -> str | None:
    """Return note text for a specific date (YYYY-MM-DD), or None."""
    _ensure_dir()
    path = EOD_DIR / f"{date_str}.txt"
    if path.exists():
        return path.read_text().strip() or None
    return None
