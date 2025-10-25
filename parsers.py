"""Simple NLP/parser utilities to extract event-like mentions from free text.

This is intentionally lightweight for a demo: it uses dateparser.search.search_dates
to locate date/time mentions and then builds simple event dicts (title, start, end,
description, location).

Improve by using an NLP model or rule engine for production.
"""
from typing import List, Dict, Optional
import dateparser.search
from dateparser import parse as parse_date
from datetime import timedelta


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


if __name__ == "__main__":
    sample = """
    Let's meet next Tuesday at 3pm to review the proposal.
    John's birthday party on July 10 at 7:30pm at his place.
    Office all-hands Friday 9am.
    """
    evs = extract_events_from_text(sample)
    for e in evs:
        print(e)
