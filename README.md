# KendallMillerCanSuckIt

A Raspberry Pi AI automation suite with Telegram integration. Research any topic, get daily morning briefings, and more.

## Features

### 🧠 AI Research Bot
Request research on any topic via Telegram:
- `research: <topic>` — Free local research using Ollama
- `research-claude: <topic>` — Premium research using Claude API
- Auto-saves to Instapaper for e-reader sync

### 🌅 Morning Briefing (New!)
Automated daily briefing delivered to Telegram at 6am weekdays:
- AI News summary (Nathan B Jones videos)
- Oura Ring readiness score & sleep analysis
- Google Calendar meetings summary
- Weather forecast
- All synthesized into one message before you wake up

## Quick Start

```bash
# Clone and install
git clone <repo-url> kendallmillercansuckit
cd kendallmillercansuckit/pi
python3 -m venv ../venv
source ../venv/bin/activate
pip install -r requirements.txt

# Configure
nano ~/.pi_badge_env  # Add your API keys

# Install services
sudo cp kendallmiller-bot.service /etc/systemd/system/
sudo systemctl enable --now kendallmiller-bot

# Enable morning brief (optional)
sudo cp /home/luke/kendallmillercansuckit/morning-brief.* /etc/systemd/system/
sudo systemctl enable --now morning-brief.timer
```

## Documentation

- [SETUP.md](SETUP.md) — Complete setup guide for research bot
- [pi/morning-brief-setup.md](pi/morning-brief-setup.md) — Morning briefing setup

## Requirements

- Raspberry Pi (any model with network)
- Python 3.8+
- Telegram bot token
- Optional: Ollama for local research
- Optional: Claude API key for premium research
- Optional: Oura, Google Calendar, Weather API keys for morning brief

## Architecture

```
┌─────────────────────────┐
│  Your Phone (Telegram)  │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│  Raspberry Pi           │
│  ├─ Research Bot        │
│  ├─ Morning Brief       │
│  ├─ Ollama (optional)   │
│  └─ Systemd services    │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│  External Services      │
│  ├─ Claude API          │
│  ├─ Instapaper          │
│  ├─ Oura Ring           │
│  ├─ Google Calendar     │
│  ├─ YouTube API         │
│  └─ Weather API         │
└─────────────────────────┘
```

## License

MIT
