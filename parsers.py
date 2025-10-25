"""Simple NLP/parser utilities to extract event-like mentions from free text.

This is intentionally lightweight for a demo: it uses dateparser.search.search_dates
to locate date/time mentions and then builds simple event dicts (title, start, end,
description, location).

Improve by using an NLP model or rule engine for production.
"""
from typing import List, Dict, Optional
import dateparser.search
from dateparser import parse as parse_date
from datetime import timedelta, datetime
import os
import json


def _extract_sentence(text: str, start_idx: int, end_idx: int) -> str:
    # Return the sentence containing the matched span (approximate).
    # Split on line breaks or punctuation to keep it simple.
    left = text.rfind("\n", 0, start_idx)
    if left == -1:
        left = 0
    else:
        left += 1
    right = text.find("\n", end_idx)
    if right == -1:
        right = len(text)
    return text[left:right].strip()


def extract_events_from_text(text: str, base_date: Optional[str] = None) -> List[Dict]:
    """Extract a list of event dicts from free text.

    Returns events with keys: title, start (datetime), end (datetime), description, location

    base_date: optional reference date for relative date parsing (ISO string) — passed to dateparser.
    """
    settings = {"PREFER_DATES_FROM": "future"}
    if base_date:
        settings["RELATIVE_BASE"] = base_date

    # search_dates returns tuples (matched_text, datetime)
    found = dateparser.search.search_dates(text, settings=settings, add_detected_language=False)
    events = []
    if not found:
        return events

    # To avoid duplicating overlapping matches, we'll iterate and create an event per match.
    for match_text, dt in found:
        # find indices to extract context
        idx = text.find(match_text)
        if idx == -1:
            title = match_text
        else:
            title = _extract_sentence(text, idx, idx + len(match_text))

        # Heuristic: if title is long, clip to first clause
        if len(title) > 140:
            title = title.split(".")[0]

        start = dt
        # If no explicit end time, default to 1 hour event
        end = start + timedelta(hours=1)

        event = {
            "title": title or match_text,
            "start": start,
            "end": end,
            "description": title,
            "location": None,
        }
        events.append(event)

    return events


def extract_events_with_gemini(text: str, base_date: Optional[str] = None) -> List[Dict]:
    """Extract events using Google Gemini API for better semantic understanding.
    
    Requires GEMINI_API_KEY environment variable to be set.
    Falls back to dateparser if Gemini API is not available.
    
    Returns events with keys: title, start (datetime), end (datetime), description, location
    """
    api_key = os.environ.get('GEMINI_API_KEY')
    
    if not api_key:
        print("GEMINI_API_KEY not set, falling back to dateparser")
        return extract_events_from_text(text, base_date)
    
    try:
        import google.generativeai as genai
        
        # Configure API - use stable v1 API instead of v1beta
        genai.configure(api_key=api_key)
        
        # List available models to debug
        try:
            available_models = [m.name for m in genai.list_models()]
            print(f"Available models: {available_models}")
        except Exception as e:
            print(f"Could not list models: {e}")
        
        # Build the prompt
        current_date = datetime.now().isoformat() if not base_date else base_date
        prompt = f"""You are an expert at extracting calendar events from academic syllabi and course schedules.

Extract all events, deadlines, exams, lectures, and important dates from the following text. The same event can be referenced in various parts of the text, each with some context. Make sure to group these events if you are sure they are the same

STEPS
- SCAN: Initially go through the text and note important names that refer to events or tasks, make sure to get anything accademically related
- COLLECT: Collect info about events, grouping them by their names (make sure to distinguish seperate midterms)
- COLLECT A SECOND TIME QUICKLY: make sure to not make duplicates
- OUPUT: Output the events with enough info about them to be able to create a simple google calendar event

CLASSIFY each item as either an "event" or "task":
- EVENTS: Have specific start and end times (lectures, labs, discussions, exams, meetings, office hours)
- TASKS: Only have due dates, no specific time needed (assignments, projects, homework, papers)

Return a JSON array. Each item should have:
- type: Either "event" or "task"
- title: A short, descriptive title, do not include the date or time
- start_text: The exact start date/time mentioned (keep original format) OR due date for tasks
- end_text: The exact end date/time mentioned, or "1 hour" for events, "0" for tasks
- location: Building name, room number, or "Online" if mentioned (usually empty for tasks)
- description: For recurring events/tasks, include days of week (e.g., "Lecture MWF", "Lab TTH", "Assignment Monday"). For non-recurring: Category like "Lecture", "Lab", "Exam", "Discussion", "Assignment", "Project"
- recurring: Boolean indicating if this event/task recurs (e.g., weekly lectures, weekly assignments, recurring meetings). Events/tasks for which there is not specified date but there is a day of the week (or multiple ex: M W (Every Monday and Wednesday)) are likely to be recurring

Important rules:
1. Use the text's actual date formats (don't convert to ISO unless necessary)
2. For events without time, assume reasonable defaults (10am for classes, 3pm for exams)
3. For tasks, use the due date as start_text and set end_text to "0"
4. For recurring events or tasks, include days in description (e.g., "MWF", "TTH", "Monday Wednesday Friday", "Assignment Monday") so the recurrence pattern can be determined
5. Return ONLY valid JSON, no markdown formatting
6. Minimum event/task details: name, time, date

Current date context: {current_date}

Text to analyze:
{text}

Return JSON array:"""

        # Call Gemini API (using available models - free tier)
        # Using models from the available list
        model_names = [
            'models/gemini-2.5-flash',  # Latest flash model
            'models/gemini-2.0-flash',   # Stable flash model
            'models/gemini-flash-latest', # Compatible version
            'models/gemini-pro-latest',   # Pro version
            'models/gemini-2.5-pro'       # Latest pro model
        ]
        
        response = None
        for model_name in model_names:
            try:
                print(f"Trying model: {model_name}")
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(prompt)
                print(f"Successfully used {model_name}")
                break
            except Exception as model_error:
                print(f"Model {model_name} failed: {model_error}")
                continue
        
        if response is None:
            raise Exception("All Gemini models failed")
        
        # Extract JSON from response
        response_text = response.text
        
        # Clean up the response (remove markdown code blocks if present)
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0]
        
        # Parse JSON
        events_raw = json.loads(response_text.strip())
        
        # Convert to our format with proper datetime objects
        events = []
        for event_raw in events_raw:
            try:
                event_type = event_raw.get('type', 'event')
                
                # Parse start time
                start_text = event_raw.get('start_text', '')
                start_dt = dateparser.parse(start_text, settings={"PREFER_DATES_FROM": "future"})
                
                if not start_dt:
                    continue  # Skip if we can't parse the date
                
                # Handle events vs tasks differently
                if event_type == 'task':
                    # Tasks are all-day events
                    end_dt = start_dt
                else:
                    # Parse end time for events
                    end_text = event_raw.get('end_text', '1 hour')
                    if end_text == '0' or end_text.lower() == 'none':
                        end_dt = start_dt  # All-day event
                    elif 'hour' in end_text.lower() or 'hr' in end_text.lower():
                        # Extract number of hours
                        try:
                            hours = float(''.join(filter(str.isdigit, end_text.split()[0])))
                            end_dt = start_dt + timedelta(hours=hours)
                        except:
                            end_dt = start_dt + timedelta(hours=1)
                    else:
                        end_dt = dateparser.parse(end_text, settings={"PREFER_DATES_FROM": "future"})
                        if not end_dt:
                            end_dt = start_dt + timedelta(hours=1)
                
                # Get recurring flag (can be True for both events and tasks)
                recurring = event_raw.get('recurring', False)
                
                event = {
                    "title": event_raw.get('title', 'Event'),
                    "start": start_dt,
                    "end": end_dt,
                    "description": event_raw.get('description', ''),
                    "location": event_raw.get('location'),
                    "type": event_type,
                    "all_day": (event_type == 'task' or end_dt == start_dt),
                    "recurring": recurring
                }
                events.append(event)
            except Exception as e:
                print(f"Error parsing event: {e}")
                continue
        
        return events
        
    except Exception as e:
        print(f"Gemini API error: {e}, falling back to dateparser")
        return extract_events_from_text(text, base_date)


if __name__ == "__main__":
    sample = """
    Let's meet next Tuesday at 3pm to review the proposal.
    John's birthday party on July 10 at 7:30pm at his place.
    Office all-hands Friday 9am.
    """
    evs = extract_events_from_text(sample)
    for e in evs:
        print(e)
