"""Parser utilities for extracting events from general documents (non-syllabi).

This module provides event extraction for general documents like meeting notes,
conference schedules, event descriptions, etc. It uses the Gemini API for better
semantic understanding.
"""
from typing import List, Dict, Optional
from datetime import timedelta, datetime
import dateparser
import os
import json


def extract_events_with_gemini_general(text: str, base_date: Optional[str] = None) -> List[Dict]:
    """Extract events from general documents using Google Gemini API.
    
    This function is optimized for general event extraction (not academic syllabi).
    It uses a different prompt tailored for events, meetings, conferences, etc.
    
    Requires GEMINI_API_KEY environment variable to be set.
    Falls back to dateparser if Gemini API is not available.
    
    Returns events with keys: title, start (datetime), end (datetime), description, location
    """
    api_key = os.environ.get('GEMINI_API_KEY')
    
    if not api_key:
        print("GEMINI_API_KEY not set, falling back to basic date parser")
        return _extract_events_basic(text, base_date)
    
    try:
        import google.generativeai as genai
        
        # Configure API
        genai.configure(api_key=api_key)
        
        # Build the prompt for general events
        current_date = datetime.now().isoformat() if not base_date else base_date
        prompt = f"""You are an expert at extracting events and meetings from general documents.

Extract all events, meetings, deadlines, appointments, and important dates from the following text.

CLASSIFY each item as either an "event" or "task":
- EVENTS: Have specific start and end times (meetings, appointments, conferences, gatherings)
- TASKS: Only have due dates, no specific time needed (to-do items, reminders without times, deadline-only items)

Return a JSON array. Each item should have:
- type: Either "event" or "task"
- title: A short, descriptive title, do not include the date or time
- start_text: The exact start date/time mentioned (keep original format) OR due date for tasks
- end_text: The exact end date/time mentioned, or "1 hour" for events without end time, "0" for tasks
- location: Building name, room number, venue, or "Online" if mentioned (can be empty)
- description: Additional context or category (e.g., "Meeting", "Conference", "Appointment", "Deadline")
- recurring: Boolean indicating if this event/task recurs (e.g., weekly meetings, daily standups, recurring appointments)

Important rules:
1. Use the text's actual date formats (don't convert to ISO unless necessary)
2. For events without time, assume reasonable defaults (morning defaults: 10am, afternoon defaults: 2pm, evening defaults: 6pm)
3. For tasks, use the due date as start_text and set end_text to "0"
4. Return ONLY valid JSON, no markdown formatting
5. Minimum event/task details: name, time, date

Current date context: {current_date}

Text to analyze:
{text}

Return JSON array:"""

        # Call Gemini API (using available models)
        model_names = [
            'models/gemini-2.5-flash',
            'models/gemini-2.0-flash',
            'models/gemini-flash-latest',
            'models/gemini-pro-latest',
            'models/gemini-2.5-pro'
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
                
                # Get recurring flag
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
        print(f"Gemini API error: {e}, falling back to basic date parser")
        return _extract_events_basic(text, base_date)


def _extract_events_basic(text: str, base_date: Optional[str] = None) -> List[Dict]:
    """Basic event extraction using dateparser (fallback)."""
    import dateparser.search
    
    settings = {"PREFER_DATES_FROM": "future"}
    if base_date:
        settings["RELATIVE_BASE"] = base_date

    # search_dates returns tuples (matched_text, datetime)
    found = dateparser.search.search_dates(text, settings=settings, add_detected_language=False)
    events = []
    if not found:
        return events

    # Create an event per match
    for match_text, dt in found:
        start = dt
        end = start + timedelta(hours=1)

        event = {
            "title": match_text or "Event",
            "start": start,
            "end": end,
            "description": match_text,
            "location": None,
            "type": "event",
            "all_day": False,
            "recurring": False
        }
        events.append(event)

    return events


if __name__ == "__main__":
    sample = """
    Let's meet next Tuesday at 3pm to review the proposal.
    John's birthday party on July 10 at 7:30pm at his place.
    Office all-hands Friday 9am.
    """
    evs = _extract_events_basic(sample)
    for e in evs:
        print(e)
