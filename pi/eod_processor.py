#!/usr/bin/env python3
"""
EOD Note Processor — AI-powered analysis of end-of-day notes
Uses Ollama or Claude to transform raw notes into actionable insights
"""

import os
import requests
from typing import Dict, List, Any, Optional


def process_eod_with_ai(
    eod_text: str,
    calendar_events: List[Dict] = None,
    use_claude: bool = False
) -> Dict[str, Any]:
    """
    Process EOD note through AI to extract structure and insights.
    
    Returns dict with:
    - priorities: List of high-priority items
    - tasks: Structured task list with time estimates
    - blockers: Dependencies or blockers mentioned
    - suggestions: AI recommendations for task order
    - warnings: Potential conflicts with calendar
    """
    
    # Build context
    calendar_context = ""
    if calendar_events:
        calendar_context = "\n\nToday's Calendar:\n"
        for event in calendar_events[:5]:
            calendar_context += f"- {event['start_time']}: {event['summary']} ({event['duration']}m)\n"
    
    prompt = f"""Analyze this end-of-day note and help prioritize the work for today.

EOD Note:
{eod_text}
{calendar_context}

Please provide:
1. **Top 3 Priorities** - Most important/urgent items from the note
2. **Task Breakdown** - All tasks extracted, with rough time estimates
3. **Dependencies** - What needs to happen before what
4. **Suggested Order** - Best sequence to tackle these tasks
5. **Calendar Conflicts** - Any tasks that conflict with scheduled meetings
6. **Quick Wins** - Fast tasks that can be done early for momentum

Format as JSON:
{{
  "priorities": ["task 1", "task 2", "task 3"],
  "tasks": [
    {{"task": "Send WRR", "estimate_mins": 15, "urgency": "high"}},
    {{"task": "Get Krishna feedback", "estimate_mins": 30, "urgency": "medium"}}
  ],
  "dependencies": ["Need Krishna feedback before updating doc"],
  "suggested_order": ["Quick wins first: send WRR", "Then tackle Krishna meeting"],
  "calendar_conflicts": ["Haircut at 4:15 blocks afternoon deep work"],
  "quick_wins": ["Send WRR (15m)", "Ride bike (30m)"]
}}

Be concise and actionable."""

    if use_claude:
        return _process_with_claude(prompt)
    else:
        return _process_with_ollama(prompt)


def _process_with_ollama(prompt: str) -> Dict[str, Any]:
    """Process with local Ollama."""
    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "llama3.2:3b",
                "prompt": prompt,
                "stream": False
            },
            timeout=60
        )
        
        result = response.json()['response']
        
        # Extract JSON from response
        import json
        if '```json' in result:
            result = result.split('```json')[1].split('```')[0].strip()
        elif '```' in result:
            result = result.split('```')[1].split('```')[0].strip()
        elif '{' in result:
            # Find first { and last }
            start = result.find('{')
            end = result.rfind('}') + 1
            result = result[start:end]
        
        return json.loads(result)
        
    except Exception as e:
        print(f"Ollama processing error: {e}")
        return _fallback_processing()


def _process_with_claude(prompt: str) -> Dict[str, Any]:
    """Process with Claude API."""
    try:
        claude_key = os.environ.get("CLAUDE_API_KEY")
        if not claude_key:
            return _process_with_ollama(prompt)
        
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": claude_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            },
            json={
                "model": "claude-sonnet-4-5-20250929",
                "max_tokens": 1500,
                "messages": [{"role": "user", "content": prompt}]
            },
            timeout=30
        )
        
        result = response.json()['content'][0]['text']
        
        # Extract JSON
        import json
        if '```json' in result:
            result = result.split('```json')[1].split('```')[0].strip()
        elif '```' in result:
            result = result.split('```')[1].split('```')[0].strip()
        elif '{' in result:
            start = result.find('{')
            end = result.rfind('}') + 1
            result = result[start:end]
        
        return json.loads(result)
        
    except Exception as e:
        print(f"Claude processing error: {e}")
        return _process_with_ollama(prompt)


def _fallback_processing() -> Dict[str, Any]:
    """Fallback if AI processing fails - return empty structure."""
    return {
        "priorities": [],
        "tasks": [],
        "dependencies": [],
        "suggested_order": [],
        "calendar_conflicts": [],
        "quick_wins": []
    }


def format_processed_eod(processed: Dict[str, Any], raw_note: str = None) -> str:
    """Format processed EOD into readable brief section."""
    
    sections = []
    
    # Top Priorities
    if processed.get('priorities'):
        sections.append("🎯 *TOP PRIORITIES*")
        for i, priority in enumerate(processed['priorities'][:3], 1):
            sections.append(f"{i}. {priority}")
        sections.append("")
    
    # Quick Wins
    if processed.get('quick_wins'):
        sections.append("⚡ *QUICK WINS*")
        for win in processed['quick_wins'][:3]:
            sections.append(f"• {win}")
        sections.append("")
    
    # All Tasks
    if processed.get('tasks'):
        total_time = sum(t.get('estimate_mins', 0) for t in processed['tasks'])
        sections.append(f"📋 *ALL TASKS* (~{total_time}min total)")
        for task in processed['tasks']:
            time_str = f" ({task['estimate_mins']}m)" if task.get('estimate_mins') else ""
            urgency = task.get('urgency', '')
            marker = "🔴" if urgency == "high" else "🟡" if urgency == "medium" else "🟢"
            sections.append(f"{marker} {task['task']}{time_str}")
        sections.append("")
    
    # Suggested Order
    if processed.get('suggested_order'):
        sections.append("💡 *SUGGESTED ORDER*")
        for suggestion in processed['suggested_order']:
            sections.append(f"→ {suggestion}")
        sections.append("")
    
    # Dependencies & Blockers
    if processed.get('dependencies'):
        sections.append("⚠️ *DEPENDENCIES*")
        for dep in processed['dependencies']:
            sections.append(f"• {dep}")
        sections.append("")
    
    # Calendar Conflicts
    if processed.get('calendar_conflicts'):
        sections.append("📅 *CALENDAR NOTES*")
        for conflict in processed['calendar_conflicts']:
            sections.append(f"• {conflict}")
        sections.append("")
    
    return '\n'.join(sections)
