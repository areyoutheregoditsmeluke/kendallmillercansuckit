# KendallMillerCanSuckIt — Raspberry Pi Research Bot

A Telegram bot running on Raspberry Pi that provides AI-powered research capabilities using either local Ollama or Claude API, with optional Instapaper integration for e-reader sync.

---

## Features

- **AI Research**: Request research on any topic via Telegram
  - `research: <topic>` — Free local research using Ollama (llama3.2:3b)
  - `research-claude: <topic>` — Premium research using Claude API
- **Instapaper Integration**: Automatically save research articles to Instapaper, which syncs to Kobo e-readers
- **Private**: Only responds to your Telegram user ID
- **Simple**: One systemd service, minimal dependencies

---

## Prerequisites

| Item | Notes |
|---|---|
| Raspberry Pi | Any Pi with network connectivity (tested on Pi 4) |
| Raspberry Pi OS | Bookworm or newer recommended |
| Ollama (optional) | For local AI research - install from ollama.ai |
| Claude API key (optional) | For premium research - get from console.anthropic.com |
| Instapaper account (optional) | For e-reader sync - sign up at instapaper.com |

---

## Setup

### 1. Clone the repository

```bash
cd ~
git clone <your-repo-url> kendallmillercansuckit
cd kendallmillercansuckit
```

### 2. Install Python dependencies

```bash
cd pi
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Create environment file

```bash
cat > ~/.pi_badge_env << 'ENVEOF'
# Telegram (required)
TELEGRAM_BOT_TOKEN=<your-bot-token>
TELEGRAM_USER_ID=<your-numeric-user-id>

# Claude API (optional - for research-claude feature)
CLAUDE_API_KEY=<your-claude-api-key>

# Instapaper (optional - for e-reader sync)
INSTAPAPER_CONSUMER_KEY=<your-consumer-key>
INSTAPAPER_CONSUMER_SECRET=<your-consumer-secret>
INSTAPAPER_OAUTH_TOKEN=<your-oauth-token>
INSTAPAPER_OAUTH_TOKEN_SECRET=<your-oauth-token-secret>
ENVEOF

chmod 600 ~/.pi_badge_env
```

#### Getting Telegram credentials

1. **Bot Token**: Message @BotFather on Telegram
   - Send `/newbot` and follow prompts
   - You'll receive a token like `1234567890:ABCdefGhIjKlmNoPqRsTuVwXyz`
   
2. **User ID**: Message @userinfobot on Telegram
   - It will reply with your numeric user ID (e.g. `987654321`)

#### Getting Instapaper credentials (optional)

1. Go to https://www.instapaper.com/api
2. Register for API access to get consumer key/secret
3. Use OAuth flow to get access tokens (see scripts/telegram_research_bot.py --setup for helper)

### 4. Install Ollama (optional, for local research)

```bash
curl -fsSL https://ollama.ai/install.sh | sh
ollama pull llama3.2:3b
```

### 5. Set up systemd service

```bash
sudo cat > /etc/systemd/system/kendallmiller-bot.service << 'SERVICEEOF'
[Unit]
Description=KendallMillerCanSuckIt Telegram Bot
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=luke
WorkingDirectory=/home/luke/kendallmillercansuckit/pi
EnvironmentFile=/home/luke/.pi_badge_env
ExecStart=/home/luke/kendallmillercansuckit/pi/venv/bin/python3 /home/luke/kendallmillercansuckit/pi/telegram_bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
SERVICEEOF

sudo systemctl daemon-reload
sudo systemctl enable kendallmiller-bot
sudo systemctl start kendallmiller-bot
```

### 6. Verify it's running

```bash
sudo systemctl status kendallmiller-bot
sudo journalctl -u kendallmiller-bot -f
```

---

## Usage

### Commands

| Command | Description |
|---|---|
| `/start` | Show help and available features |
| `/status` | Check server health (Ollama status, etc.) |
| `research: <topic>` | Request research using Ollama (free, local) |
| `research-claude: <topic>` | Request research using Claude API (requires API key) |

### Examples

```
research: quantum computing
research-claude: history of the internet
```

The bot will:
1. Acknowledge your request
2. Conduct research (2-3 minutes for Ollama, ~30-60 seconds for Claude)
3. Post results to Instapaper if configured
4. Reply with a preview and confirmation

---

## Known Issues

- Dev morale

---

## Troubleshooting

### Bot doesn't respond

```bash
# Check service status
sudo systemctl status kendallmiller-bot

# Check logs
sudo journalctl -u kendallmiller-bot -n 50

# Verify environment file
cat ~/.pi_badge_env

# Test bot manually
source ~/kendallmillercansuckit/pi/venv/bin/activate
source ~/.pi_badge_env
python3 ~/kendallmillercansuckit/pi/telegram_bot.py
```

### Ollama research fails

```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Start Ollama if needed
ollama serve

# Check model is installed
ollama list
```

### Claude API research fails

- Verify `CLAUDE_API_KEY` is set in `~/.pi_badge_env`
- Check API key is valid at console.anthropic.com
- Ensure you have API credits

### Instapaper sync not working

- Verify all 4 Instapaper credentials are set in `~/.pi_badge_env`
- Test OAuth tokens are still valid
- Check logs for specific error messages

---

## Maintenance

### Update the bot

```bash
cd ~/kendallmillercansuckit
git pull
sudo systemctl restart kendallmiller-bot
```

### View logs

```bash
# Recent logs
sudo journalctl -u kendallmiller-bot -n 100

# Follow logs in real-time
sudo journalctl -u kendallmiller-bot -f

# Logs since last boot
sudo journalctl -u kendallmiller-bot -b
```

### Stop/restart service

```bash
sudo systemctl stop kendallmiller-bot
sudo systemctl start kendallmiller-bot
sudo systemctl restart kendallmiller-bot
```

---

## Advanced Configuration

### Change Ollama model

Edit `pi/telegram_bot.py` and change the model in `research_with_ollama()`:

```python
data = {
    "model": "llama3.2:3b",  # Change to any installed model
    # ...
}
```

Then:
```bash
ollama pull <model-name>
sudo systemctl restart kendallmiller-bot
```

### Change Claude model

Edit `pi/telegram_bot.py` and change the model in `research_with_claude()`:

```python
data = {
    "model": "claude-sonnet-4-5-20250929",  # Change to any available model
    # ...
}
```

### Disable features

Remove or comment out credentials in `~/.pi_badge_env` to disable:
- Claude research: remove `CLAUDE_API_KEY`
- Instapaper sync: remove `INSTAPAPER_*` keys

---

## Architecture

```
┌─────────────────────────┐
│  Your Phone (Telegram)  │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│  Raspberry Pi           │
│  ├─ Telegram Bot        │◄───┐
│  ├─ Ollama (optional)   │    │ Research
│  └─ Systemd service     │────┘
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│  External Services      │
│  ├─ Claude API          │
│  └─ Instapaper API      │
└─────────────────────────┘
            │
            ▼
┌─────────────────────────┐
│  Kobo E-Reader          │
│  (auto-syncs from       │
│   Instapaper)           │
└─────────────────────────┘
```

---

## File Structure

```
kendallmillercansuckit/
├── pi/
│   ├── telegram_bot.py        # Main bot code
│   ├── requirements.txt       # Python dependencies
│   └── .env.example          # Environment template
├── SETUP.md                   # This file
└── scripts/                   # Helper scripts (legacy)
```

---

## Credits

Built for research and learning, inspired by the desire to have AI research delivered directly to an e-reader.
