#!/usr/bin/env python3
"""
Pi Telegram Bot
───────────────
Receives messages from Telegram and forwards them to the Pi badge
via the local HTTP server (server.py).

Required environment variables (put in ~/.pi_badge_env):
  TELEGRAM_BOT_TOKEN   — from @BotFather
  TELEGRAM_USER_ID     — your numeric user ID (from @userinfobot)
  PI_SERVER_URL        — default: http://localhost:8765

Commands the bot accepts:
  /start   — greeting + command list
  /status  — ping the message server
  /clear   — wipe all badge messages
  /poll    — trigger an immediate git pull (if git_poller is running)
  Any text — forward to badge display
"""

import os
import sys
import asyncio
import requests

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ── Config ───────────────────────────────────────────────────────────────────
TOKEN          = os.environ.get("TELEGRAM_BOT_TOKEN", "")
ALLOWED_UID    = int(os.environ.get("TELEGRAM_USER_ID", "0"))
SERVER_URL     = os.environ.get("PI_SERVER_URL", "http://localhost:8765")


def _allowed(update: Update) -> bool:
    if ALLOWED_UID == 0:
        return True  # no restriction set
    return update.effective_user.id == ALLOWED_UID


def _post(text: str, sender: str = "Telegram") -> dict:
    r = requests.post(
        f"{SERVER_URL}/message",
        json={"text": text, "from": sender},
        timeout=5,
    )
    return r.json()


# ── Handlers ─────────────────────────────────────────────────────────────────

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Pi Badge Bot is online!\n\n"
        "Send any text → it appears on the badge display.\n\n"
        "Commands:\n"
        "/status — check server health\n"
        "/clear  — clear all badge messages\n"
        "/poll   — trigger git pull now"
    )


async def cmd_status(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not _allowed(update):
        return
    try:
        r    = requests.get(f"{SERVER_URL}/health", timeout=3)
        data = r.json()
        await update.message.reply_text(
            f"Server: OK\n"
            f"Messages stored: {data.get('count', '?')}"
        )
    except Exception as e:
        await update.message.reply_text(f"Server unreachable: {e}")


async def cmd_clear(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not _allowed(update):
        await update.message.reply_text("Unauthorized.")
        return
    try:
        requests.post(f"{SERVER_URL}/clear", timeout=3)
        await update.message.reply_text("Badge messages cleared.")
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")


async def cmd_poll(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Signal the git poller to run immediately by touching a trigger file."""
    if not _allowed(update):
        await update.message.reply_text("Unauthorized.")
        return
    trigger = os.path.expanduser("~/.pi_badge_poll_now")
    open(trigger, "w").close()
    await update.message.reply_text("Git poll triggered. Check back in a moment.")


async def handle_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not _allowed(update):
        await update.message.reply_text("Unauthorized.")
        return

    text   = update.message.text
    sender = update.effective_user.first_name or "Telegram"

    try:
        data  = _post(text, sender)
        total = data.get("total", "?")
        await update.message.reply_text(f"Sent to badge! ({total} messages total)")
    except Exception as e:
        await update.message.reply_text(f"Could not reach badge server: {e}")


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    if not TOKEN:
        print("ERROR: Set TELEGRAM_BOT_TOKEN environment variable.")
        sys.exit(1)

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start",  cmd_start))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("clear",  cmd_clear))
    app.add_handler(CommandHandler("poll",   cmd_poll))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    print("Telegram bot polling for updates…")
    app.run_polling()


if __name__ == "__main__":
    main()
