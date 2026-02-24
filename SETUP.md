# Pi + GitHub Badge System — Setup Guide

Two devices, one little system:

```
┌─────────────────────────┐       WiFi        ┌────────────────────────────┐
│  Docker container        │ ◄──────────────── │  GitHub Universe 2025 Badge │
│  (Linux or macOS host)  │                   │  (Pimoroni Tufty 2350)     │
│  ─ Flask message server │                   │  ─ 2.8" color LCD 320×240  │
│  ─ Telegram bot         │                   │  ─ 5 buttons               │
│  ─ Git poller           │                   │  ─ WiFi built-in           │
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

## What you need

| Item | Notes |
|---|---|
| A Linux or macOS host | Raspberry Pi, any Linux box, or a Mac |
| Docker + Docker Compose | [Install Docker](https://docs.docker.com/get-docker/) |
| USB-C cable | For badge ↔ host (code deployment; message comms are WiFi) |
| GitHub Universe 2025 badge | Pimoroni Tufty 2350 variant |
| Your local WiFi network | Both devices connect to this |

---

## Part 1 — Docker setup

### 1.1  Configure environment

```bash
cd pi
cp .env.example .env
```

Edit `.env` with your Telegram bot token and user ID (see Part 2 for how to get these):

```env
TELEGRAM_BOT_TOKEN=1234567890:ABCdef...    # from @BotFather
TELEGRAM_USER_ID=987654321                 # from @userinfobot
```

### 1.2  Start the container

**On Linux** (Raspberry Pi, any Linux host — full USB badge flashing):

```bash
docker compose -f docker-compose.yml -f docker-compose.linux.yml up -d --build
```

**On macOS** (server + telegram + git poller, badge flashing from host):

```bash
docker compose -f docker-compose.yml -f docker-compose.macos.yml up -d --build
```

> **Why two compose files?** Docker Desktop for Mac runs containers in a Linux VM
> that can't access USB devices. On Linux, the badge's USB serial device
> (`/dev/ttyACM0`) is passed directly into the container. On macOS, the git
> poller detects code changes and posts a notification — you then flash the badge
> from the host using `mpremote` (see Part 4).

### 1.3  Verify it's running

```bash
curl http://localhost:8765/health
# → {"count":1,"ok":true,"service":"pi-badge-server"}

docker logs pi-badge-system
```

### 1.4  Find your host's IP address

```bash
# Linux
hostname -I

# macOS
ipconfig getifaddr en0
```

Write this down — you'll need it for the badge's `secrets.py`.

### 1.5  Optional configuration

All settings have defaults and can be overridden in `.env`:

| Variable | Default | Description |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | *(required)* | Token from @BotFather |
| `TELEGRAM_USER_ID` | *(required)* | Your numeric Telegram user ID |
| `REPO_URL` | This repo's URL | Git repo to poll |
| `REPO_BRANCH` | `claude/pi-github-device-interface-vdRro` | Branch to track |
| `USB_MODE` | `direct` | `direct` (Linux) or `host` (macOS) |
| `POLL_INTERVAL` | `30` | Seconds between git fetch checks |
| `ENABLE_TELEGRAM` | `true` | Set `false` to disable the Telegram bot |
| `ENABLE_POLLER` | `true` | Set `false` to disable the git poller |

### Legacy: bare-metal Pi setup

The original systemd-based setup still works. See `pi/setup.sh` for details.
Run `bash pi/setup.sh` on a Pi to install services directly without Docker.

---

## Part 2 — Telegram bot setup

### 2.1  Create a bot

1. Open Telegram, find **@BotFather**
2. Send `/newbot`
3. Follow prompts — you'll get a token like `1234567890:ABCdefGhIjKlmNoPqRsTuVwXyz`
4. Put this in `TELEGRAM_BOT_TOKEN` in `pi/.env`

### 2.2  Find your Telegram user ID

1. Start a chat with **@userinfobot**
2. It replies with your numeric user ID (e.g. `987654321`)
3. Put this in `TELEGRAM_USER_ID` — the bot will ignore anyone else

### 2.3  Test it

Send your bot any message on Telegram. The server stores it, and the badge
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
# Badge mounted as /media/pi/BADGER (Linux) or /Volumes/BADGER (macOS):
cp badge/secrets_template.py /media/pi/BADGER/secrets.py   # adjust path
```

Edit the copied `secrets.py`:

```python
WIFI_SSID     = "your-wifi-network"
WIFI_PASSWORD = "your-wifi-password"
PI_HOST       = "http://192.168.1.42:8765"   # ← your host's IP
```

Eject the drive (important — LittleFS needs a clean unmount):

```bash
# Linux
sudo eject /media/pi/BADGER

# macOS
diskutil eject /Volumes/BADGER
```

### 3.3  Deploy the badge app via mpremote

```bash
# With badge plugged in via USB-C (not in bootloader mode):
pip install mpremote    # if not already installed
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

## Part 4 — Code sync (Claude → Container → Badge)

This is the "suggest changes here, they end up on the badge" pipeline.

```
You chat with Claude here
   ↓  Claude commits badge/ changes to this repo
   ↓  git_poller.py in the container fetches every 30 s
   ↓  Detects badge/ files changed
   ↓  Linux: mpremote pushes to badge via USB (automatic)
   ↓  macOS: notification posted, you run mpremote from host
   ↓  Badge soft-resets and loads new code
```

### How it works

- `pi/git_poller.py` runs inside the container (managed by supervisord)
- Every 30 seconds it does `git fetch` + `git reset --hard origin/branch`
- If any file under `badge/` changed:
  - **Linux** (`USB_MODE=direct`): runs mpremote inside the container to flash the badge
  - **macOS** (`USB_MODE=host`): posts a notification with the mpremote command to run from the host

### macOS: flashing from the host

When the git poller detects badge changes on macOS, it posts a notification.
Copy the files out of the container and flash:

```bash
cd pi
docker compose cp pi-badge:/repo/badge/pi_messages ./pi_messages_tmp
mpremote cp -r pi_messages_tmp/ :system/apps/pi_messages/
mpremote reset
rm -rf pi_messages_tmp
```

You need `mpremote` installed on the host: `pip install mpremote`

### Force an immediate poll

Send `/poll` to your Telegram bot. The bot touches a trigger file that the
poller detects and acts on immediately (instead of waiting up to 30 s).

### For the badge to be auto-synced, it must be plugged in via USB-C

The WiFi channel is used only for message passing (badge polls the HTTP API).
Code deployment requires USB (via mpremote). If you don't want to leave the
badge plugged in permanently, manual sync with `mpremote` is fine.

---

## Troubleshooting

### Badge shows "No WiFi"
- Check `secrets.py` is at the root of the badge filesystem (`/secrets.py`)
- Verify SSID/password are correct
- Make sure your WiFi is 2.4 GHz (the RP2350 doesn't do 5 GHz)

### Badge shows "Offline" / "Fetch error"
- Confirm the server is running: `curl http://<host-ip>:8765/health`
- Confirm `PI_HOST` in `secrets.py` has the correct IP and port
- Check the host's firewall: `sudo ufw allow 8765` (Linux) or System Settings → Firewall (macOS)

### mpremote can't find the badge
- Badge must be in normal (non-bootloader) mode — just plugged in via USB-C
- Run `mpremote connect list` to see detected devices
- Try a different USB-C cable (some are charge-only)
- On macOS, run mpremote from the host (not inside the container)

### Telegram bot doesn't respond
- Check `docker logs pi-badge-system`
- Verify `TELEGRAM_BOT_TOKEN` is correct in `pi/.env`
- Make sure the host has internet access

### Git poller not syncing
- Check `docker logs pi-badge-system`
- Verify the repo URL and branch exist remotely
- Check `ENABLE_POLLER` is `true` in your `.env`

---

## Container management quick reference

```bash
cd pi

# Start (pick your platform)
docker compose -f docker-compose.yml -f docker-compose.linux.yml up -d --build   # Linux
docker compose -f docker-compose.yml -f docker-compose.macos.yml up -d --build   # macOS

# Logs
docker logs -f pi-badge-system

# Restart
docker compose restart

# Stop
docker compose down

# Stop and remove volumes (deletes messages + cloned repo)
docker compose down -v

# Health check
curl http://localhost:8765/health

# Deploy badge app manually
mpremote cp -r badge/pi_messages/ :system/apps/pi_messages/
mpremote reset
```
