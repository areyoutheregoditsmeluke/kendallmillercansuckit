#!/bin/bash
set -e

# ── Default toggles ─────────────────────────────────────────────────────────
export ENABLE_TELEGRAM="${ENABLE_TELEGRAM:-true}"
export ENABLE_POLLER="${ENABLE_POLLER:-true}"

# ── Clone repo if not present ────────────────────────────────────────────────
REPO_PATH="${REPO_PATH:-/repo}"
REPO_URL="${REPO_URL:-https://github.com/areyoutheregoditsmeluke/kendallmillercansuckit.git}"
REPO_BRANCH="${REPO_BRANCH:-claude/pi-github-device-interface-vdRro}"

if [ ! -d "$REPO_PATH/.git" ]; then
    echo "[entrypoint] Cloning $REPO_URL branch $REPO_BRANCH into $REPO_PATH..."
    git clone --branch "$REPO_BRANCH" --single-branch "$REPO_URL" "$REPO_PATH"
else
    echo "[entrypoint] Repo already exists at $REPO_PATH, fetching latest..."
    git -C "$REPO_PATH" fetch origin "$REPO_BRANCH"
    git -C "$REPO_PATH" reset --hard "origin/$REPO_BRANCH"
fi

# ── Ensure data directory exists ─────────────────────────────────────────────
mkdir -p /data

# ── Validate Telegram config ────────────────────────────────────────────────
if [ "$ENABLE_TELEGRAM" = "true" ] && [ -z "$TELEGRAM_BOT_TOKEN" ]; then
    echo "[entrypoint] WARNING: TELEGRAM_BOT_TOKEN not set. Disabling Telegram bot."
    export ENABLE_TELEGRAM="false"
fi

# ── Launch supervisord ───────────────────────────────────────────────────────
echo "[entrypoint] Starting services..."
echo "  server:       always"
echo "  telegram_bot: $ENABLE_TELEGRAM"
echo "  git_poller:   $ENABLE_POLLER"
echo "  USB mode:     ${USB_MODE:-direct}"

exec supervisord -c /etc/supervisord.conf
