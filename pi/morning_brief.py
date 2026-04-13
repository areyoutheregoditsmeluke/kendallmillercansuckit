#!/usr/bin/env python3
"""
Morning Brief Service
Generates and sends daily briefing via Telegram at 6am

Components:
- Nathan AI News check (YouTube + transcript)
- Oura readiness score
- Google Calendar summary
- Weather forecast
- EOD notes from previous evening (via /eod Telegram command)
- AI synthesis with Ollama or Claude
"""

import os
import sys
import json
import pickle
import requests
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List

# EOD notes module (in same directory)
sys.path.insert(0, os.path.dirname(__file__))
from eod_notes import get_last_eod_note
from eod_processor import process_eod_with_ai, format_processed_eod

# ── Configuration ────────────────────────────────────────────────────────────

YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY", "")
OURA_API_KEY = os.environ.get("OURA_API_KEY", "")
WEATHER_API_KEY = os.environ.get("WEATHER_API_KEY", "")
CLAUDE_API_KEY = os.environ.get("CLAUDE_API_KEY", "")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_USER_ID = int(os.environ.get("TELEGRAM_USER_ID", "0"))

# Paths
CALENDAR_TOKEN_PATH = Path.home() / ".morning_brief_calendar_token.pickle"
CREDENTIALS_PATH = Path.home() / ".morning_brief_google_credentials.json"

# Config
NATHAN_CHANNEL_ID = "UC0C-17n9iuUQPylguM1d-lQ"
WEATHER_LAT = os.environ.get("WEATHER_LAT", "37.7749")  # Default SF
WEATHER_LON = os.environ.get("WEATHER_LON", "-122.4194")

USE_CLAUDE = os.environ.get("USE_CLAUDE_FOR_BRIEF", "false").lower() == "true"


# ── Nathan AI News ───────────────────────────────────────────────────────────

def check_nathan_video() -> Optional[Dict[str, Any]]:
    """Check for Nathan B Jones video published today"""
    if not YOUTUBE_API_KEY:
        return None

    try:
        from googleapiclient.discovery import build

        youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)

        # Get videos from last 24 hours
        yesterday = (datetime.now() - timedelta(days=1)).isoformat() + 'Z'

        request = youtube.search().list(
            part='snippet',
            channelId=NATHAN_CHANNEL_ID,
            maxResults=5,
            order='date',
            type='video',
            publishedAfter=yesterday
        )
        response = request.execute()

        if not response.get('items'):
            return None

        # Get most recent video
        video = response['items'][0]
        video_id = video['id']['videoId']

        # Get video details for duration
        details = youtube.videos().list(
            part='contentDetails,statistics',
            id=video_id
        ).execute()

        duration_iso = details['items'][0]['contentDetails']['duration']

        return {
            'video_id': video_id,
            'title': video['snippet']['title'],
            'description': video['snippet']['description'],
            'url': f"https://youtube.com/watch?v={video_id}",
            'published_at': video['snippet']['publishedAt'],
            'duration': duration_iso,
            'thumbnail': video['snippet']['thumbnails']['high']['url']
        }

    except Exception as e:
        print(f"Nathan check error: {e}")
        return None


def get_video_transcript(video_id: str) -> Optional[str]:
    """Fetch YouTube transcript"""
    try:
        from youtube_transcript_api import YouTubeTranscriptApi

        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        transcript = ' '.join([item['text'] for item in transcript_list])
        return transcript

    except Exception as e:
        print(f"Transcript error: {e}")
        return None


def summarize_nathan_video(video: Dict[str, Any], transcript: Optional[str]) -> Dict[str, Any]:
    """Generate AI summary of Nathan's video"""

    # Build prompt
    source = transcript[:3000] if transcript else video['description'][:1000]

    prompt = f"""Analyze this AI news video from Nathan B Jones and provide a structured summary.

Title: {video['title']}
Content: {source}

Respond with JSON:
{{
  "summary": "2 sentence summary",
  "key_points": ["point 1", "point 2", "point 3"],
  "relevance": 8,
  "topics": ["Topic 1", "Topic 2"]
}}"""

    # Use Claude API or Ollama
    if USE_CLAUDE and CLAUDE_API_KEY:
        try:
            response = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": CLAUDE_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                },
                json={
                    "model": "claude-haiku-4-5-20251001",
                    "max_tokens": 500,
                    "messages": [{"role": "user", "content": prompt}]
                },
                timeout=60
            )
            result = response.json()['content'][0]['text']

            # Extract JSON
            if '```json' in result:
                result = result.split('```json')[1].split('```')[0].strip()
            elif '```' in result:
                result = result.split('```')[1].split('```')[0].strip()

            return json.loads(result)

        except Exception as e:
            print(f"Claude summary error: {e}")

    # Fallback: Ollama (local, free)
    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "llama3.2:3b",
                "prompt": prompt,
                "stream": False
            },
            timeout=180
        )
        result = response.json()['response']

        # Extract JSON
        if '```json' in result:
            result = result.split('```json')[1].split('```')[0].strip()
        elif '```' in result:
            result = result.split('```')[1].split('```')[0].strip()

        return json.loads(result)

    except Exception as e:
        print(f"Ollama summary error: {e}")

    # Ultimate fallback
    return {
        "summary": f"Nathan discusses: {video['title']}",
        "key_points": ["See video for details"],
        "relevance": 5,
        "topics": ["AI News"]
    }


# ── Oura Ring ────────────────────────────────────────────────────────────────

def get_oura_readiness() -> Optional[Dict[str, Any]]:
    """Fetch Oura readiness, sleep score, and sleep duration.

    Uses /sleep endpoint for duration fields (daily_sleep lacks them)
    and filters for the long_sleep record to exclude naps.
    Uses /daily_sleep for the sleep score.
    Returns None silently if token is invalid/expired.
    """
    if not OURA_API_KEY:
        return None

    try:
        today = datetime.now().strftime("%Y-%m-%d")

        response = requests.get(
            "https://api.ouraring.com/v2/usercollection/daily_readiness",
            headers={"Authorization": f"Bearer {OURA_API_KEY}"},
            params={"start_date": today, "end_date": today},
            timeout=10
        )

        data = response.json()

        if not data.get("data"):
            return None

        readiness = data["data"][0]

        # Use /sleep endpoint for duration fields (daily_sleep lacks these)
        # Query yesterday->today and pick the long_sleep record (not naps)
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        sleep_response = requests.get(
            "https://api.ouraring.com/v2/usercollection/sleep",
            headers={"Authorization": f"Bearer {OURA_API_KEY}"},
            params={"start_date": yesterday, "end_date": today},
            timeout=10
        )

        sleep_data = sleep_response.json()
        sleep_records = sleep_data.get("data", [])
        sleep = next(
            (s for s in sleep_records if s.get("type") == "long_sleep"),
            sleep_records[0] if sleep_records else {}
        )

        # Get daily_sleep for the sleep score
        daily_sleep_resp = requests.get(
            "https://api.ouraring.com/v2/usercollection/daily_sleep",
            headers={"Authorization": f"Bearer {OURA_API_KEY}"},
            params={"start_date": today, "end_date": today},
            timeout=10
        )
        daily_sleep_data = daily_sleep_resp.json()
        daily_sleep = daily_sleep_data["data"][0] if daily_sleep_data.get("data") else {}

        return {
            "score": readiness.get("score"),
            "hrv_balance": readiness["contributors"].get("hrv_balance"),
            "resting_hr": readiness["contributors"].get("resting_heart_rate"),
            "sleep_score": daily_sleep.get("score"),
            "total_sleep": sleep.get("total_sleep_duration", 0) // 60,
            "deep_sleep": sleep.get("deep_sleep_duration", 0) // 60,
            "rem_sleep": sleep.get("rem_sleep_duration", 0) // 60
        }

    except Exception as e:
        print(f"Oura error: {e}")
        return None


# ── Google Calendar ──────────────────────────────────────────────────────────

def get_calendar_events() -> List[Dict[str, Any]]:
    """Fetch today's calendar events"""
    if not CALENDAR_TOKEN_PATH.exists():
        return []

    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build

        # Load credentials
        with open(CALENDAR_TOKEN_PATH, 'rb') as token:
            creds = pickle.load(token)

        # Refresh if needed
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(CALENDAR_TOKEN_PATH, 'wb') as token:
                pickle.dump(creds, token)

        service = build('calendar', 'v3', credentials=creds)

        # Get today's events
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow = today + timedelta(days=1)

        events_result = service.events().list(
            calendarId='primary',
            timeMin=today.isoformat() + 'Z',
            timeMax=tomorrow.isoformat() + 'Z',
            singleEvents=True,
            orderBy='startTime',
            maxResults=50
        ).execute()

        events = []
        for event in events_result.get('items', []):
            start = event.get('start', {})
            end = event.get('end', {})

            if 'dateTime' not in start:
                continue  # Skip all-day events

            start_dt = datetime.fromisoformat(start['dateTime'].replace('Z', '+00:00'))
            end_dt = datetime.fromisoformat(end['dateTime'].replace('Z', '+00:00'))
            duration = int((end_dt - start_dt).total_seconds() / 60)

            events.append({
                'summary': event.get('summary', 'Untitled'),
                'start_time': start_dt.strftime('%I:%M %p'),
                'end_time': end_dt.strftime('%I:%M %p'),
                'duration': duration,
                'attendees': len(event.get('attendees', []))
            })

        return events

    except Exception as e:
        print(f"Calendar error: {e}")
        return []


# ── Weather ──────────────────────────────────────────────────────────────────

def get_weather() -> Optional[Dict[str, Any]]:
    """Fetch current weather + true daily high/low from forecast endpoint.

    The /weather endpoint temp_min/temp_max only reflect the current
    observation period range, not the actual day high/low. We use the
    /forecast endpoint (3-hour slots) to derive a real daily high/low.
    """
    if not WEATHER_API_KEY:
        return None

    try:
        # Current conditions
        current_resp = requests.get(
            "https://api.openweathermap.org/data/2.5/weather",
            params={
                "lat": WEATHER_LAT,
                "lon": WEATHER_LON,
                "appid": WEATHER_API_KEY,
                "units": "imperial"
            },
            timeout=10
        )
        data = current_resp.json()

        # Forecast for true daily high/low (3-hour slots, up to ~48h)
        forecast_resp = requests.get(
            "https://api.openweathermap.org/data/2.5/forecast",
            params={
                "lat": WEATHER_LAT,
                "lon": WEATHER_LON,
                "appid": WEATHER_API_KEY,
                "units": "imperial",
                "cnt": 16
            },
            timeout=10
        )
        forecast_data = forecast_resp.json()

        # forecast dt_txt timestamps are UTC; compare against today UTC
        today_utc = datetime.utcnow().strftime("%Y-%m-%d")
        today_slots = [
            s for s in forecast_data.get("list", [])
            if s["dt_txt"].startswith(today_utc)
        ]

        if today_slots:
            daily_high = int(max(s["main"]["temp_max"] for s in today_slots))
            daily_low = int(min(s["main"]["temp_min"] for s in today_slots))
        else:
            # Fallback: current temp (no forecast slots for today yet)
            daily_high = int(data["main"]["temp"])
            daily_low = int(data["main"]["temp"])

        return {
            "temp": int(data["main"]["temp"]),
            "feels_like": int(data["main"]["feels_like"]),
            "description": data["weather"][0]["description"].title(),
            "high": daily_high,
            "low": daily_low,
            "humidity": data["main"]["humidity"]
        }

    except Exception as e:
        print(f"Weather error: {e}")
        return None


# ── EOD Notes ────────────────────────────────────────────────────────────────

def format_eod_section(eod: dict, calendar: List[Dict] = None) -> str:
    """Format EOD note with AI processing."""
    label = eod['date_label']
    
    # Strip the header lines from the stored file
    content_lines = [l for l in eod['text'].splitlines() if not l.startswith('---')]
    raw_content = '\n'.join(content_lines).strip()
    
    # Process through AI
    use_claude = os.environ.get('USE_CLAUDE_FOR_BRIEF', 'false').lower() == 'true'
    processed = process_eod_with_ai(raw_content, calendar, use_claude=use_claude)
    
    # Format the output  
    header = f"📝 YOUR PLAN FOR TODAY (from {label})"
    formatted = format_processed_eod(processed, raw_content)
    
    return f"{header}\n{formatted}\n"


# ── Brief Generation ─────────────────────────────────────────────────────────

def generate_morning_brief(
    nathan: Optional[Dict],
    nathan_summary: Optional[Dict],
    oura: Optional[Dict],
    calendar: List[Dict],
    weather: Optional[Dict],
    eod: Optional[Dict] = None,
) -> str:
    """Generate formatted morning brief"""

    today = datetime.now().strftime("%A, %B %d, %Y")

    brief = f"🌅 *Good Morning!* - {today}\n\n"

    # EOD Note from last night (shown first — context for the day)
    if eod:
        brief += format_eod_section(eod, calendar)

    # AI News
    if nathan and nathan_summary:
        brief += "🤖 *AI NEWS*\n"
        brief += f"Nathan posted: \"{nathan['title'][:60]}...\"\n"
        brief += f"{nathan_summary['summary']}\n"

        if nathan_summary.get('key_points'):
            for point in nathan_summary['key_points'][:3]:
                brief += f"• {point}\n"

        brief += f"⏱️ Video | Relevance: {nathan_summary.get('relevance', '?')}/10\n"
        brief += f"[Watch Now]({nathan['url']})\n\n"
    else:
        brief += "🤖 *AI NEWS*\nNo new video from Nathan today\n\n"

    # Energy Forecast
    if oura:
        brief += "💪 *ENERGY FORECAST*\n"
        brief += f"Oura Readiness: {oura['score']}/100\n"

        hours = oura['total_sleep'] // 60
        mins = oura['total_sleep'] % 60
        brief += f"• Sleep: {hours}h {mins}m"

        if oura.get('sleep_score'):
            brief += f" ({oura['sleep_score']}/100)\n"
        else:
            brief += "\n"

        if oura.get('deep_sleep'):
            brief += f"• Deep: {oura['deep_sleep']}m | REM: {oura['rem_sleep']}m\n"

        # Interpretation
        if oura['score'] >= 85:
            brief += "→ You're primed for creative work today\n\n"
        elif oura['score'] >= 70:
            brief += "→ Good energy for steady progress\n\n"
        else:
            brief += "→ Take it easy, prioritize recovery\n\n"

    # Calendar
    if calendar:
        brief += "📅 *CALENDAR*\n"
        total_minutes = sum(e['duration'] for e in calendar)
        hours = total_minutes // 60
        mins = total_minutes % 60

        brief += f"{len(calendar)} meeting{'s' if len(calendar) != 1 else ''}"
        brief += f" ({hours}h {mins}m total)\n"

        for event in calendar[:5]:  # Show first 5
            brief += f"• {event['start_time']}-{event['end_time']}: {event['summary']}\n"

        if len(calendar) > 5:
            brief += f"...and {len(calendar) - 5} more\n"

        brief += "\n"
    else:
        brief += "📅 *CALENDAR*\nNo meetings scheduled\n\n"

    # Weather
    if weather:
        brief += "🌤️ *WEATHER*\n"
        brief += f"{weather['temp']}°F, {weather['description']}\n"
        brief += f"High: {weather['high']}°F | Low: {weather['low']}°F\n\n"

    brief += "---\n"
    brief += "✨ Have a great day!\n"

    return brief


# ── Telegram Send ────────────────────────────────────────────────────────────

def send_telegram_message(text: str) -> bool:
    """Send message via Telegram"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_USER_ID:
        print("Missing Telegram credentials")
        return False

    try:
        response = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={
                "chat_id": TELEGRAM_USER_ID,
                "text": text,
                "parse_mode": "Markdown",
                "disable_web_page_preview": True
            },
            timeout=10
        )

        return response.status_code == 200

    except Exception as e:
        print(f"Telegram error: {e}")
        return False


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    """Generate and send morning brief"""

    print("=" * 70)
    print(f"  Morning Brief - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)

    # Gather data
    print("\n📊 Gathering data...")

    print("  🤖 Checking Nathan AI News...")
    nathan = check_nathan_video()
    nathan_summary = None

    if nathan:
        print(f"     Found: {nathan['title'][:50]}...")
        print("     Fetching transcript...")
        transcript = get_video_transcript(nathan['video_id'])
        print("     Generating summary...")
        nathan_summary = summarize_nathan_video(nathan, transcript)
    else:
        print("     No new video")

    print("\n  💪 Fetching Oura data...")
    oura = get_oura_readiness()
    if oura:
        print(f"     Readiness: {oura['score']}/100")
    else:
        print("     No Oura data")

    print("\n  📅 Fetching calendar...")
    calendar = get_calendar_events()
    print(f"     {len(calendar)} events")

    print("\n  🌤️ Fetching weather...")
    weather = get_weather()
    if weather:
        print(f"     {weather['temp']}°F, {weather['description']}")
    else:
        print("     No weather data")

    print("\n  📝 Checking EOD notes...")
    eod = get_last_eod_note()
    if eod:
        print(f"     Found note from {eod['date_label']} ({eod['days_ago']} day(s) ago)")
    else:
        print("     No EOD note found")

    # Generate brief
    print("\n✍️ Generating brief...")
    brief = generate_morning_brief(nathan, nathan_summary, oura, calendar, weather, eod)

    # Send via Telegram
    print("\n📱 Sending to Telegram...")
    success = send_telegram_message(brief)

    if success:
        print("   ✅ Brief sent successfully!")
    else:
        print("   ❌ Failed to send brief")
        print("\n" + brief)

    print("\n" + "=" * 70)

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
