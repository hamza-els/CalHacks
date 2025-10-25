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
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile"
]


def create_google_service(credentials_path: str = "credentials.json", token_path: str = "token.json"):
    """Create a Google Calendar API service. Returns the service object.

    Requires `credentials.json` from Google Cloud Console (OAuth Client ID).
    This function will open a browser for the first-time OAuth consent and save `token.json`.
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


def create_google_event(service, event: Dict, calendar_id: str = "primary", timezone: str = "America/Los_Angeles") -> Dict:
    """Create an event in Google Calendar.

    event: dict with keys title, start (datetime), end (datetime), description, location, all_day (bool)
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
