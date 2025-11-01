"""Calendar helpers: Google Calendar push and .ics export for Apple Calendar import.

Google Calendar uses OAuth2. Place your OAuth client credentials in `credentials.json`
(downloaded from Google Cloud Console) next to this script. The token is saved to `token.json`.

ICS export uses the `icalendar` package and creates a simple calendar file.
"""
from typing import Dict, List, Optional
import os
from datetime import datetime

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
except Exception:
    # Defer import errors until runtime; requirements not installed during static analysis.
    Credentials = None

from icalendar import Calendar, Event

# If modifying these scopes, delete the file token.json.
SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile"
]


def create_google_service_from_credentials(credentials):
    """Create a Google Calendar API service from a credentials object.
    
    Args:
        credentials: google.oauth2.credentials.Credentials object
    
    Returns:
        Google Calendar API service object
    """
    if Credentials is None:
        raise RuntimeError("Google API libraries are not installed. See requirements.txt")
    
    if not credentials:
        raise Exception("Not authenticated. Please sign in with Google first.")
    
    # If credentials are expired, try to refresh
    if credentials.expired and credentials.refresh_token:
        try:
            credentials.refresh(Request())
        except Exception as e:
            print(f"Could not refresh token: {e}")
            raise Exception("Authentication expired. Please sign in again.")
    
    if not credentials.valid:
        raise Exception("Not authenticated. Please sign in with Google first.")
    
    service = build("calendar", "v3", credentials=credentials)
    return service


def create_google_service(credentials_path: str = "credentials.json", token_path: str = "token.json"):
    """Create a Google Calendar API service. Returns the service object.

    Requires `credentials.json` from Google Cloud Console (OAuth Client ID).
    This function will open a browser for the first-time OAuth consent and save `token.json`.
    
    DEPRECATED: Use create_google_service_from_credentials() for session-based auth.
    """
    if Credentials is None:
        raise RuntimeError("Google API libraries are not installed. See requirements.txt")

    creds = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    
    # If there are no (valid) credentials, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            # Refresh the token
            try:
                creds.refresh(Request())
            except Exception as e:
                print(f"Could not refresh token: {e}")
                # If refresh fails, raise an error - user needs to re-authenticate
                raise Exception("Authentication expired. Please sign in again.")
        else:
            # No valid credentials - user needs to authenticate via web OAuth
            raise Exception("Not authenticated. Please sign in with Google first.")

    service = build("calendar", "v3", credentials=creds)
    return service


def create_calendar(service, file_content=None, filename=None) -> tuple:
    """Create a new calendar for syllabus events. ALWAYS creates a new calendar.
    
    service: Google Calendar API service object
    file_content: the actual text content of the uploaded file (optional)
    filename: name of the uploaded file (optional)
    Returns a tuple of (calendar_id, calendar_name).
    """
    calendar_name = "Syllabus Events"
    
    # Log which file we're using
    print(f"DEBUG [CALENDAR UTILS]: Creating calendar with filename: {filename}")
    print(f"DEBUG [CALENDAR UTILS]: file_content length: {len(file_content) if file_content else 0}")
    
    # Generate dynamic calendar name using file content
    if file_content and len(file_content.strip()) > 0:
        try:
            import google.generativeai as genai
            import os
            
            api_key = os.environ.get('GEMINI_API_KEY')
            if api_key:
                genai.configure(api_key=api_key)
                
                # Use first 1300 characters of file content (typically first page)
                content_snippet = file_content[:1300]
                
                print(f"DEBUG [CALENDAR UTILS]: Sending content snippet to Gemini for calendar naming:")
                print(f"DEBUG [CALENDAR UTILS]: Content snippet (first 500 chars): {content_snippet[:500]}")
                print(f"DEBUG [CALENDAR UTILS]: Content snippet length: {len(content_snippet)}")
                
                prompt = f"""Extract the course code and number from this syllabus. This is VERY IMPORTANT.

PRIORITY 1 (HIGHEST PRIORITY): Look for course codes with format [Department][Number]
Examples: "CS 61A", "CS 101", "Math 55", "MATH 1B", "ENG 125", "EECS 16A", "CHEM 1C"
Format is typically: [2-4 letter department code] [number][optional letter]

PRIORITY 2: If no course code is found, extract the course title/topic
Examples: "Discrete Mathematics", "Introduction to Algorithms", "Calculus I"

DO NOT return generic terms like "Math", "Computer Science", "English", "Physics", etc.
DO NOT return the word "syllabus", "course", "class", or "schedule".
DO NOT use cached or remembered information from previous requests.

READ THE SYLLABUS CONTENT BELOW CAREFULLY and extract the specific course information:

Syllabus content:
{content_snippet}

Return ONLY the course code or title from the content above (max 30 characters), nothing else:"""
                for model_name in ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.0-flash"]:
                    try:
                        model = genai.GenerativeModel(model_name)
                        response = model.generate_content(prompt)
                        suggested_name = response.text.strip().replace('"', '').replace("'", "")
                        
                        # Validate the name (remove any extra text, limit length)
                        if suggested_name and len(suggested_name) <= 30 and suggested_name.lower() not in ["syllabus", "course", "class", "schedule"]:
                            calendar_name = suggested_name
                            print(f"Generated calendar name: {calendar_name}")
                            break
                    except Exception as e:
                        print(f"Model {model_name} failed: {e}, trying next model")
                        continue
        except Exception as e:
            print(f"Gemini API not available for naming: {e}, using default")
    
    # Always create a new calendar
    description = 'Events extracted from academic syllabi'
    calendar_body = {
        'summary': calendar_name,
        'description': description,
        'timeZone': 'America/Los_Angeles'
    }
    
    created_calendar = service.calendars().insert(body=calendar_body).execute()
    calendar_id = created_calendar['id']
    print(f"Created new calendar: {calendar_id} with name: {calendar_name}")
    
    return calendar_id, calendar_name


def create_google_event(service, event: Dict, calendar_id: str = "primary", timezone: str = "America/Los_Angeles") -> Dict:
    """Create an event in Google Calendar.

    event: dict with keys title, start (datetime), end (datetime), description, location, all_day (bool), recurring (bool)
    timezone: IANA timezone string (default: America/Los_Angeles)
    Returns the created event resource.
    """
    # Validate required fields
    if not event.get("title"):
        raise ValueError("Event title is required")
    
    start_dt = event.get("start")
    end_dt = event.get("end")
    
    if not start_dt or not end_dt:
        raise ValueError("Event start and end times are required")
    
    # Check if this is an all-day event
    is_all_day = event.get("all_day", False)
    is_recurring = event.get("recurring", False)
    
    # Handle all-day events vs timed events
    if is_all_day:
        # For all-day events, use date field (no time component)
        # Ensure we have valid dates
        if not hasattr(start_dt, 'strftime') or not hasattr(end_dt, 'strftime'):
            raise ValueError("Invalid datetime objects for all-day event")
            
        body = {
            "summary": event.get("title"),
            "description": event.get("description"),
            "location": event.get("location"),
            "start": {
                "date": start_dt.strftime("%Y-%m-%d")
            },
            "end": {
                "date": end_dt.strftime("%Y-%m-%d")
            },
        }
    else:
        # For timed events, use dateTime with timezone
        # Validate datetime objects
        if not hasattr(start_dt, 'strftime') or not hasattr(end_dt, 'strftime'):
            raise ValueError("Invalid datetime objects for timed event")
        
        # Format datetime without timezone if naive
        if start_dt.tzinfo is None:
            start_str = start_dt.strftime("%Y-%m-%dT%H:%M:%S")
        else:
            start_str = start_dt.isoformat()
            
        if end_dt.tzinfo is None:
            end_str = end_dt.strftime("%Y-%m-%dT%H:%M:%S")
        else:
            end_str = end_dt.isoformat()
        
        # Validate that start is before end
        if start_dt >= end_dt:
            raise ValueError(f"Start time ({start_dt}) must be before end time ({end_dt})")
        
        body = {
            "summary": event.get("title"),
            "description": event.get("description"),
            "location": event.get("location"),
            "start": {
                "dateTime": start_str,
                "timeZone": timezone
            },
            "end": {
                "dateTime": end_str,
                "timeZone": timezone
            },
        }
    
    # Add recurrence rule if this is a recurring event (events or tasks)
    if is_recurring:
        from datetime import timedelta
        
        # Try to get the days of week from the event description or location
        # Common patterns: "MWF" (Monday, Wednesday, Friday), "TTH" (Tuesday, Thursday), etc.
        days_str = event.get("description", "").upper()
        
        # Map day abbreviations to Google Calendar format
        day_patterns = {
            'M': 'MO', 'MON': 'MO', 'MONDAY': 'MO',
            'T': 'TU', 'TUE': 'TU', 'TUES': 'TU', 'TUESDAY': 'TU',
            'W': 'WE', 'WED': 'WE', 'WEDNESDAY': 'WE',
            'R': 'TH', 'TH': 'TH', 'THUR': 'TH', 'THURS': 'TH', 'THURSDAY': 'TH',
            'F': 'FR', 'FRI': 'FR', 'FRIDAY': 'FR',
            'SA': 'SA', 'SAT': 'SA', 'SATURDAY': 'SA',
            'SU': 'SU', 'SUN': 'SU', 'SUNDAY': 'SU'
        }
        
        # Try to find day patterns in the description
        # Look for patterns like "MWF", "TTH", "M W F", "Mon Wed Fri", etc.
        found_days = []
        
        # First, check for abbreviated patterns like "MWF", "TTH"
        if len(days_str) <= 5 and all(c in 'MTWRF' for c in days_str):
            # Pattern like "MWF" or "TTH"
            for char in days_str:
                if char in day_patterns:
                    day_code = day_patterns[char]
                    if day_code not in found_days:
                        found_days.append(day_code)
        
        # Check for word patterns in description
        if not found_days:
            import re
            # Look for day names in the description
            for pattern, day_code in day_patterns.items():
                if len(pattern) > 2 and pattern in days_str:
                    if day_code not in found_days:
                        found_days.append(day_code)
        
        # Fallback: use the start date's day if no pattern found
        if not found_days:
            weekday = start_dt.weekday()
            days_map = ["MO", "TU", "WE", "TH", "FR", "SA", "SU"]
            found_days = [days_map[weekday]]
        
        # Create recurrence rule with BYDAY parameter
        byday_str = ','.join(found_days)
        end_date = start_dt + timedelta(weeks=16)
        
        # For all-day events (tasks), use date format in UNTIL
        if is_all_day:
            until_date = end_date.strftime('%Y%m%d')
            body["recurrence"] = [
                f"RRULE:FREQ=WEEKLY;BYDAY={byday_str};UNTIL={until_date}"
            ]
        else:
            until_datetime = end_date.strftime('%Y%m%dT%H%M%SZ')
            body["recurrence"] = [
                f"RRULE:FREQ=WEEKLY;BYDAY={byday_str};UNTIL={until_datetime}"
            ]
    
    created = service.events().insert(calendarId=calendar_id, body=body).execute()
    return created


def export_events_to_ics(events: List[Dict], path: str = "events.ics") -> str:
    """Write events to an .ics file. Returns the path written.

    Each event requires start and end datetimes and summary.
    """
    cal = Calendar()
    cal.add("prodid", "-//CalHacks Event Export//mxm.dk//")
    cal.add("version", "2.0")

    for ev in events:
        ical_ev = Event()
        ical_ev.add("summary", ev.get("title"))
        ical_ev.add("description", ev.get("description"))
        if ev.get("location"):
            ical_ev.add("location", ev.get("location"))
        # Use dateTime with timezone-aware datetimes if available; here we assume naive -> treat as local
        ical_ev.add("dtstart", ev["start"])
        ical_ev.add("dtend", ev["end"])
        cal.add_component(ical_ev)

    with open(path, "wb") as f:
        f.write(cal.to_ical())
    return path


if __name__ == "__main__":
    print("calendar_utils module: provide create_google_service, create_google_event, export_events_to_ics")
