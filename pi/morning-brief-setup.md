# Morning Brief Setup

Automated daily briefing sent via Telegram at 6am weekdays.

## What You Get

Every morning at 6am (Monday-Friday), receive a Telegram message with:

- **AI News** — Nathan B Jones video summary (if posted)
- **Energy Forecast** — Oura readiness score & sleep quality  
- **Calendar** — Today's meetings and time blocks
- **Weather** — Temperature and forecast

## Setup

### 1. Install Dependencies

Already done if you set up the research bot. Otherwise:

```bash
cd ~/kendallmillercansuckit
source venv/bin/activate
pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib youtube-transcript-api
```

### 2. Configure Environment

Add to `~/.pi_badge_env`:

```bash
# Required
TELEGRAM_BOT_TOKEN=your-bot-token
TELEGRAM_USER_ID=your-numeric-user-id
YOUTUBE_API_KEY=your-youtube-api-key

# Optional (recommended)
OURA_API_KEY=your-oura-personal-access-token
WEATHER_API_KEY=your-openweathermap-api-key
WEATHER_LAT=37.7749  # Your latitude
WEATHER_LON=-122.4194  # Your longitude
USE_CLAUDE_FOR_BRIEF=true  # Use Claude (fast) vs Ollama (free but slower)
```

### 3. Copy Calendar Token

If you use Google Calendar integration, copy your OAuth token:

```bash
# From your Mac
scp ~/.claude/calendar_token.pickle pi@<pi-ip>:~/.morning_brief_calendar_token.pickle
```

Or create a new one:
```bash
python3 pi/morning_brief.py  # Will trigger OAuth flow
```

### 4. Enable Timer

```bash
sudo systemctl enable morning-brief.timer
sudo systemctl start morning-brief.timer
```

## Getting API Keys

### YouTube API (Free)
1. Go to https://console.cloud.google.com
2. Create project → Enable YouTube Data API v3
3. Create credentials → API Key
4. Copy key to `YOUTUBE_API_KEY`

### Oura Ring API (Free for personal use)
1. Go to https://cloud.ouraring.com/personal-access-tokens
2. Create personal access token
3. Copy to `OURA_API_KEY`

### OpenWeatherMap (Free tier)
1. Sign up at https://openweathermap.org/api
2. Get free API key (60 calls/min)
3. Copy to `WEATHER_API_KEY`

### Google Calendar
Run the script once and it will open OAuth flow in browser:
```bash
cd ~/kendallmillercansuckit
source venv/bin/activate
python3 pi/morning_brief.py
```

## Usage

### Test Manually

```bash
sudo systemctl start morning-brief.service
```

Check Telegram for the message.

### View Logs

```bash
sudo journalctl -u morning-brief.service -n 50
```

### Check Timer Status

```bash
sudo systemctl status morning-brief.timer
```

Shows next scheduled run time.

### Disable

```bash
sudo systemctl stop morning-brief.timer
sudo systemctl disable morning-brief.timer
```

## Customization

Edit `pi/morning_brief.py` to:
- Change message format
- Add/remove data sources
- Adjust scheduling (edit `/etc/systemd/system/morning-brief.timer`)
- Use different AI model for summaries

## Troubleshooting

### No Telegram message
- Check `sudo journalctl -u morning-brief.service`
- Verify `TELEGRAM_BOT_TOKEN` and `TELEGRAM_USER_ID` in `~/.pi_badge_env`
- Test manually: `sudo systemctl start morning-brief.service`

### No Nathan AI News
- Verify `YOUTUBE_API_KEY` in env file
- Check Nathan posted today (he posts daily)
- Logs will show "No new video" if nothing published

### No Oura data
- Verify `OURA_API_KEY` in env file
- Check token at https://cloud.ouraring.com/personal-access-tokens
- Oura data only available after waking up (syncs overnight)

### No Calendar
- Verify `~/.morning_brief_calendar_token.pickle` exists
- Token may be expired, run script manually to refresh OAuth
- Check Google Calendar API is enabled in Cloud Console

### No Weather
- Get free API key from https://openweathermap.org/api
- Set `WEATHER_LAT` and `WEATHER_LON` to your location
- Verify `WEATHER_API_KEY` in env file

## Files

- `pi/morning_brief.py` — Main script
- `~/.pi_badge_env` — Credentials (keep secure!)
- `~/.morning_brief_calendar_token.pickle` — Google OAuth token
- `/etc/systemd/system/morning-brief.service` — systemd service
- `/etc/systemd/system/morning-brief.timer` — Timer (6am weekdays)

## Privacy & Security

- All API keys stored locally in `~/.pi_badge_env` (chmod 600)
- No data sent to external services except the APIs you configure
- Calendar token grants read-only access
- Your friends can use their own API keys
