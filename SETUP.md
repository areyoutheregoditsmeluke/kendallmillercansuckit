# Pi + GitHub Badge System — Setup Guide

Two devices, one little system:

```
┌─────────────────────────┐       WiFi        ┌────────────────────────────┐
│  Raspberry Pi           │ ◄──────────────── │  GitHub Universe 2025 Badge │
│  ─ Flask message server │                   │  (Pimoroni Tufty 2350)     │
│  ─ Telegram bot         │                   │  ─ 2.8" color LCD 320×240  │
│  ─ Git poller           │                   │  ─ 5 buttons               │
│  ─ Claude Code (API)    │                   │  ─ WiFi built-in           │
└─────────────────────────┘                   └────────────────────────────┘
          ▲
          │ git pull (every 30s)
          │
┌─────────────────────────┐
│  This GitHub repo       │
│  (you edit via Claude)  │
└─────────────────────────┘
          ▲
          │ Telegram message
┌─────────────────────────┐
│  Your Phone             │
└─────────────────────────┘
```

---

## Hardware you need

| Item | Notes |
|---|---|
| Raspberry Pi 4 or 5 (4 GB+ recommended) | Pi 3 works but slower |
| MicroSD card (16 GB+) | For Pi OS |
| USB-C cable | For badge ↔ Pi (badge sync only; comms are over WiFi) |
| GitHub Universe 2025 badge | Pimoroni Tufty 2350 variant |
| Your local WiFi network | Both devices connect to this |

---

## Part 1 — Raspberry Pi setup

### 1.1  Flash Pi OS

1. Download [Raspberry Pi Imager](https://www.raspberrypi.com/software/)
2. Choose **Raspberry Pi OS Lite (64-bit)** (no desktop needed)
3. In the imager settings, enable SSH and set your WiFi credentials
4. Flash to MicroSD, boot the Pi

### 1.2  SSH in and run setup

```bash
ssh pi@<your-pi-hostname>.local
# or use its IP address

# Clone repo and run setup
git clone https://github.com/areyoutheregoditsmeluke/kendallmillercansuckit.git \
    ~/kendallmillercansuckit
bash ~/kendallmillercansuckit/pi/setup.sh
```

The setup script will:
- Install Python 3 + venv
- Install Flask, python-telegram-bot, mpremote
- Create three systemd services (server, telegram bot, git poller)
- Create `~/.pi_badge_env` for secrets

### 1.3  Configure secrets

Edit `~/.pi_badge_env`:

```bash
nano ~/.pi_badge_env
```

```env
TELEGRAM_BOT_TOKEN=1234567890:ABCdef...    # from @BotFather
TELEGRAM_USER_ID=987654321                 # from @userinfobot
PI_SERVER_URL=http://localhost:8765
```

### 1.4  Find your Pi's IP address

```bash
hostname -I
# e.g. 192.168.1.42
```

Write this down — you'll need it for the badge's `secrets.py`.

### 1.5  Start services

```bash
sudo systemctl start pi-badge-server
sudo systemctl start pi-badge-telegram
sudo systemctl start pi-badge-poller
```

Verify they're running:

```bash
sudo systemctl status pi-badge-server
curl http://localhost:8765/health
```

---

## Part 2 — Telegram bot setup

### 2.1  Create a bot

1. Open Telegram, find **@BotFather**
2. Send `/newbot`
3. Follow prompts — you'll get a token like `1234567890:ABCdefGhIjKlmNoPqRsTuVwXyz`
4. Put this in `TELEGRAM_BOT_TOKEN` in `~/.pi_badge_env`

### 2.2  Find your Telegram user ID

1. Start a chat with **@userinfobot**
2. It replies with your numeric user ID (e.g. `987654321`)
3. Put this in `TELEGRAM_USER_ID` — the bot will ignore anyone else

### 2.3  Test it

Send your bot any message on Telegram. The Pi server stores it, and the badge
will show it on its next poll (within 5 seconds).

---

## Part 3 — Badge setup

### 3.1  Mount the badge as a USB drive

1. Plug the badge into your Pi (or laptop) via USB-C
2. Double-press the **RESET** button on the back
3. The badge mounts as a drive named **BADGER** or **TUFTY2350**

### 3.2  Copy secrets.py

Copy `badge/secrets_template.py` onto the badge drive and rename it `secrets.py`:

```bash
# From your Pi, badge mounted as /media/pi/BADGER (adjust path):
cp ~/kendallmillercansuckit/badge/secrets_template.py \
   /media/pi/BADGER/secrets.py
```

Edit `/media/pi/BADGER/secrets.py`:

```python
WIFI_SSID     = "your-wifi-network"
WIFI_PASSWORD = "your-wifi-password"
PI_HOST       = "http://192.168.1.42:8765"   # ← your Pi's IP
```

Eject the drive (important — LittleFS needs a clean unmount):

```bash
sudo eject /media/pi/BADGER
```

### 3.3  Deploy the badge app via mpremote

```bash
# From your Pi, with badge plugged in via USB-C (not in bootloader mode):
cd ~/kendallmillercansuckit
mpremote cp -r badge/pi_messages/ :system/apps/pi_messages/
mpremote reset
```

The badge will restart, appear in the MonaOS app launcher, and you can launch
**Pi Messages** from the menu.

### 3.4  Badge controls

| Button | Action |
|---|---|
| **A** | Previous message |
| **C** | Next message |
| **UP** | Scroll up within a long message |
| **DOWN** | Scroll down within a long message |
| **A + C held** | Force refresh from Pi now |
| **HOME** | Return to MonaOS menu |

---

## Part 4 — Code sync (Claude → Pi → Badge)

This is the "suggest changes here, they end up on the badge" pipeline.

```
You chat with Claude here
   ↓  Claude commits badge/ changes to this repo
   ↓  git_poller.py on Pi fetches every 30 s
   ↓  Detects badge/ files changed
   ↓  mpremote pushes to badge via USB
   ↓  Badge soft-resets and loads new code
```

### How it works

- `pi/git_poller.py` runs on the Pi as a systemd service
- Every 30 seconds it does `git fetch` + `git reset --hard origin/branch`
- If any file under `badge/` changed, it runs:
  ```bash
  mpremote cp -r badge/pi_messages/ :system/apps/pi_messages/
  mpremote reset
  ```
- It also posts a notification message to the badge display

### Force an immediate poll

Send `/poll` to your Telegram bot. The bot touches a trigger file that the
poller detects and acts on immediately (instead of waiting up to 30 s).

### For the badge to be auto-synced, it must be plugged in via USB-C

The WiFi channel is used only for message passing (badge polls Pi's HTTP API).
Code deployment requires USB (via mpremote). If you don't want to leave the
badge plugged in permanently, manual sync with `mpremote` is fine.

---

## Part 5 — Running Claude Code on the Pi

Claude Code runs on the Pi using the Anthropic API (no local GPU needed).

```bash
# Install Node.js (required by Claude Code)
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
sudo apt-get install -y nodejs

# Install Claude Code
npm install -g @anthropic/claude-code

# Set your API key
echo 'export ANTHROPIC_API_KEY=sk-ant-...' >> ~/.bashrc
source ~/.bashrc

# Run
claude
```

### About "NanoLM / local LLM on Pi"

If you want a fully offline local LLM (no Anthropic API key required), install
**Ollama** and run a small model:

```bash
curl -fsSL https://ollama.ai/install.sh | sh
ollama pull phi3.5          # ~2 GB, works on Pi 4 (4 GB RAM)
# or:
ollama pull llama3.2:3b     # ~2 GB
ollama serve                # runs on localhost:11434
```

Pi 5 with 8 GB RAM is recommended for reasonable speed. Pi 4 with 4 GB can
run phi3.5 at ~2 tokens/s — slow but functional for non-interactive tasks.

---

## Troubleshooting

### Badge shows "No WiFi"
- Check `secrets.py` is at the root of the badge filesystem (`/secrets.py`)
- Verify SSID/password are correct
- Make sure your WiFi is 2.4 GHz (the RP2350 doesn't do 5 GHz)

### Badge shows "Offline" / "Fetch error"
- Confirm the Pi server is running: `curl http://<pi-ip>:8765/health`
- Confirm `PI_HOST` in `secrets.py` has the correct IP and port
- Check the Pi's firewall: `sudo ufw allow 8765` or `sudo ufw disable`

### mpremote can't find the badge
- Badge must be in normal (non-bootloader) mode — just plugged in via USB-C
- Run `mpremote connect list` to see detected devices
- Try a different USB-C cable (some are charge-only)

### Telegram bot doesn't respond
- Check `journalctl -u pi-badge-telegram -f`
- Verify `TELEGRAM_BOT_TOKEN` is correct
- Make sure the Pi has internet access: `curl https://api.telegram.org`

### Git poller not syncing
- Check `journalctl -u pi-badge-poller -f`
- Verify the repo path is correct and the branch exists remotely
- Test manually: `cd ~/kendallmillercansuckit && git fetch origin claude/pi-github-device-interface-vdRro`

---

## Service management quick reference

```bash
# Status
sudo systemctl status pi-badge-server pi-badge-telegram pi-badge-poller

# Restart all
sudo systemctl restart pi-badge-server pi-badge-telegram pi-badge-poller

# Live logs
journalctl -u pi-badge-server   -f
journalctl -u pi-badge-telegram -f
journalctl -u pi-badge-poller   -f

# Deploy badge app manually
mpremote cp -r ~/kendallmillercansuckit/badge/pi_messages/ :system/apps/pi_messages/
mpremote reset
```
