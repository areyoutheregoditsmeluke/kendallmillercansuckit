# KendallMillerCanSuckIt

A Raspberry Pi Telegram bot that provides AI-powered research capabilities. Request research on any topic via Telegram, and get comprehensive summaries delivered to your phone or e-reader.

## Quick Start

```bash
# Clone and install
cd ~
git clone <repo-url> kendallmillercansuckit
cd kendallmillercansuckit/pi
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure (see SETUP.md for details)
nano ~/.pi_badge_env

# Install systemd service
sudo cp kendallmiller-bot.service /etc/systemd/system/
sudo systemctl enable --now kendallmiller-bot
```

See [SETUP.md](SETUP.md) for detailed setup instructions.

## Features

- **Local AI Research** — Free research using Ollama (llama3.2:3b)
- **Claude API Research** — Premium research using Anthropic's Claude
- **Instapaper Integration** — Auto-sync to Kobo e-readers
- **Private & Secure** — Only responds to your Telegram user ID

## Usage

Send your bot a message on Telegram:

```
research: quantum computing
research-claude: history of the internet
```

The bot conducts research and optionally saves to Instapaper for e-reader sync.

## Requirements

- Raspberry Pi (any model with network)
- Python 3.8+
- Telegram bot token
- Optional: Ollama for local research
- Optional: Claude API key for premium research
- Optional: Instapaper account for e-reader sync

## Documentation

- [SETUP.md](SETUP.md) — Complete setup guide
- [Telegram Bot API](https://core.telegram.org/bots) — Create a bot
- [Ollama](https://ollama.ai) — Local LLM installation
- [Anthropic API](https://console.anthropic.com) — Claude API access
- [Instapaper API](https://www.instapaper.com/api) — E-reader integration

## License

MIT
