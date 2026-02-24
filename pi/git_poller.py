#!/usr/bin/env python3
"""
Git Poller
──────────
Watches this repo's branch for new commits. When badge/ files change,
it pushes them to the badge via USB using mpremote.

This is the "make a code suggestion here → it ends up on the badge" pipeline:
  1. Changes committed to this repo (e.g. by Claude Code in a conversation)
  2. This script detects the new commit
  3. If badge/ files changed → syncs to badge via USB / WiFi
  4. Posts a notification message to the badge display

Requirements on the Pi:
  pip install mpremote requests

Run: python3 git_poller.py
     (or via systemd — see setup.sh)
"""

import os
import sys
import time
import subprocess
import requests

# ── Config ───────────────────────────────────────────────────────────────────
REPO_PATH      = os.environ.get("REPO_PATH", "/repo")
BRANCH         = os.environ.get("REPO_BRANCH", "claude/pi-github-device-interface-vdRro")
BADGE_APP_DIR  = os.path.join(REPO_PATH, "badge", "pi_messages")
BADGE_APP_DEST = os.environ.get("BADGE_APP_DEST", ":system/apps/pi_messages/")
POLL_INTERVAL  = int(os.environ.get("POLL_INTERVAL", "30"))
SERVER_URL     = os.environ.get("PI_SERVER_URL", "http://localhost:8765")
TRIGGER_FILE   = os.environ.get("TRIGGER_FILE", "/data/.pi_badge_poll_now")
USB_MODE       = os.environ.get("USB_MODE", "direct")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _run(cmd: list, cwd: str = REPO_PATH) -> tuple[int, str, str]:
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)
    return r.returncode, r.stdout.strip(), r.stderr.strip()


def _current_commit() -> str:
    _, out, _ = _run(["git", "rev-parse", "HEAD"])
    return out


def _fetch_and_reset() -> bool:
    code, _, err = _run(["git", "fetch", "origin", BRANCH])
    if code != 0:
        print(f"  fetch error: {err}")
        return False
    code, _, err = _run(["git", "reset", "--hard", f"origin/{BRANCH}"])
    if code != 0:
        print(f"  reset error: {err}")
        return False
    return True


def _changed_files(old_commit: str, new_commit: str) -> list[str]:
    _, out, _ = _run(["git", "diff", "--name-only", f"{old_commit}..{new_commit}"])
    return [f for f in out.splitlines() if f]


def _notify(text: str, sender: str = "System") -> None:
    """Post a message to the badge display via the HTTP server."""
    try:
        requests.post(
            f"{SERVER_URL}/message",
            json={"text": text, "from": sender},
            timeout=3,
        )
    except Exception:
        pass


def _sync_badge_usb(short_sha: str) -> None:
    """Copy badge app files to badge via USB using mpremote."""
    if USB_MODE == "host":
        print(f"  USB_MODE=host — skipping mpremote (run from host)")
        _notify(
            f"Badge code updated (commit {short_sha}). "
            f"Flash from host: mpremote cp -r badge/pi_messages/ :system/apps/pi_messages/ && mpremote reset",
            "Git",
        )
        return

    print(f"  Syncing badge app via USB (mpremote)…")

    # Create remote directory if it doesn't exist
    _run_mpremote(["mkdir", BADGE_APP_DEST.rstrip("/")])

    # Copy all Python files
    result = subprocess.run(
        ["mpremote", "cp", "-r", f"{BADGE_APP_DIR}/", BADGE_APP_DEST],
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        print(f"  Sync OK. Soft-resetting badge…")
        subprocess.run(["mpremote", "reset"], capture_output=True)
        _notify(f"Badge updated! Commit {short_sha}. Restarting app…", "Git")
    else:
        print(f"  mpremote error: {result.stderr}")
        print("  (Is the badge plugged in via USB-C? Is mpremote installed?)")
        _notify(
            f"New code available (commit {short_sha}) but badge not connected via USB.",
            "Git",
        )


def _run_mpremote(args: list) -> None:
    subprocess.run(["mpremote"] + args, capture_output=True)


def _check_trigger_file() -> bool:
    """Returns True if the Telegram /poll command dropped a trigger file."""
    if os.path.exists(TRIGGER_FILE):
        os.remove(TRIGGER_FILE)
        return True
    return False


# ── Main loop ─────────────────────────────────────────────────────────────────

def main() -> None:
    if not os.path.isdir(REPO_PATH):
        print(f"ERROR: repo not found at {REPO_PATH}")
        print(f"  git clone <your-repo-url> {REPO_PATH}")
        sys.exit(1)

    last_commit = _current_commit()
    print(f"Git poller started. Branch: {BRANCH}")
    print(f"Repo:        {REPO_PATH}")
    print(f"Poll every:  {POLL_INTERVAL}s")
    print(f"Starting at: {last_commit[:8]}")

    while True:
        time.sleep(POLL_INTERVAL)

        forced = _check_trigger_file()
        if forced:
            print("Trigger file detected — forcing immediate pull.")

        print(f"Checking for updates… ({time.strftime('%H:%M:%S')})")

        if not _fetch_and_reset():
            continue

        new_commit = _current_commit()

        if new_commit == last_commit and not forced:
            print("  No changes.")
            continue

        if new_commit != last_commit:
            changed = _changed_files(last_commit, new_commit)
            short   = new_commit[:8]
            print(f"  New commit: {short} — {len(changed)} file(s) changed")
            last_commit = new_commit

            badge_changed = any(f.startswith("badge/") for f in changed)
            pi_changed    = any(f.startswith("pi/")    for f in changed)

            if badge_changed:
                print("  badge/ files changed — syncing to hardware…")
                _sync_badge_usb(short)
            elif pi_changed:
                print("  pi/ files changed — restart services to apply.")
                _notify(f"Pi code updated: {short}. Restart services to apply.", "Git")
            else:
                print("  Other files changed (docs / config).")
        elif forced:
            print("  Already at latest commit, nothing to sync.")


if __name__ == "__main__":
    main()
