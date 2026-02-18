#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# Pi Badge System — Setup Script
# Run once on a fresh Raspberry Pi OS installation.
# ─────────────────────────────────────────────────────────────────────────────
set -e

REPO_DIR="$HOME/kendallmillercansuckit"
BRANCH="claude/pi-github-device-interface-vdRro"
VENV="$REPO_DIR/venv"

echo "=== Pi Badge System Setup ==="
echo ""

# ── 1. System packages ────────────────────────────────────────────────────────
echo "[1/6] Installing system packages…"
sudo apt-get update -qq
sudo apt-get install -y python3 python3-pip python3-venv git

# ── 2. Clone / update repo ────────────────────────────────────────────────────
echo "[2/6] Cloning repo…"
if [ ! -d "$REPO_DIR" ]; then
    # Replace this URL with your actual repo remote
    git clone --branch "$BRANCH" https://github.com/areyoutheregoditsmeluke/kendallmillercansuckit.git "$REPO_DIR"
else
    echo "  Repo already exists. Pulling latest…"
    git -C "$REPO_DIR" fetch origin "$BRANCH"
    git -C "$REPO_DIR" reset --hard "origin/$BRANCH"
fi

# ── 3. Python venv + deps ─────────────────────────────────────────────────────
echo "[3/6] Setting up Python virtual environment…"
python3 -m venv "$VENV"
"$VENV/bin/pip" install --quiet --upgrade pip
"$VENV/bin/pip" install --quiet -r "$REPO_DIR/pi/requirements.txt"

# ── 4. Environment file ───────────────────────────────────────────────────────
ENV_FILE="$HOME/.pi_badge_env"
echo "[4/6] Creating environment template at $ENV_FILE…"
if [ ! -f "$ENV_FILE" ]; then
    cat > "$ENV_FILE" <<'EOF'
# Fill in these values before starting the services.
# Get your bot token from @BotFather on Telegram.
# Get your user ID from @userinfobot on Telegram.
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_USER_ID=your_numeric_user_id_here
PI_SERVER_URL=http://localhost:8765
EOF
    echo "  Created $ENV_FILE — edit it before starting services!"
else
    echo "  $ENV_FILE already exists, skipping."
fi

# ── 5. Systemd services ───────────────────────────────────────────────────────
echo "[5/6] Installing systemd services…"

sudo tee /etc/systemd/system/pi-badge-server.service > /dev/null <<EOF
[Unit]
Description=Pi Badge Message Server
After=network.target

[Service]
User=$USER
WorkingDirectory=$REPO_DIR
ExecStart=$VENV/bin/python pi/server.py
Environment=PYTHONUNBUFFERED=1
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo tee /etc/systemd/system/pi-badge-telegram.service > /dev/null <<EOF
[Unit]
Description=Pi Badge Telegram Bot
After=network.target pi-badge-server.service

[Service]
User=$USER
WorkingDirectory=$REPO_DIR
ExecStart=$VENV/bin/python pi/telegram_bot.py
EnvironmentFile=$HOME/.pi_badge_env
Environment=PYTHONUNBUFFERED=1
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo tee /etc/systemd/system/pi-badge-poller.service > /dev/null <<EOF
[Unit]
Description=Pi Badge Git Poller
After=network.target

[Service]
User=$USER
WorkingDirectory=$REPO_DIR
ExecStart=$VENV/bin/python pi/git_poller.py
EnvironmentFile=$HOME/.pi_badge_env
Environment=PYTHONUNBUFFERED=1
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable pi-badge-server pi-badge-telegram pi-badge-poller

# ── 6. Finish ─────────────────────────────────────────────────────────────────
echo "[6/6] Done!"
echo ""
echo "══════════════════════════════════════════════════════"
echo " Next steps:"
echo "══════════════════════════════════════════════════════"
echo ""
echo " 1. Edit $ENV_FILE"
echo "    → add your TELEGRAM_BOT_TOKEN and TELEGRAM_USER_ID"
echo ""
echo " 2. Find your Pi's IP address:"
echo "    hostname -I"
echo "    → update PI_HOST in badge/secrets.py on the badge"
echo ""
echo " 3. Start services:"
echo "    sudo systemctl start pi-badge-server"
echo "    sudo systemctl start pi-badge-telegram"
echo "    sudo systemctl start pi-badge-poller"
echo ""
echo " 4. Tail logs:"
echo "    journalctl -u pi-badge-server   -f"
echo "    journalctl -u pi-badge-telegram -f"
echo "    journalctl -u pi-badge-poller   -f"
echo ""
echo " 5. Deploy badge app (badge must be plugged in via USB-C):"
echo "    mpremote cp -r badge/pi_messages/ :system/apps/pi_messages/"
echo "    mpremote reset"
echo ""
