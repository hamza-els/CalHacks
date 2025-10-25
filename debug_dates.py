#!/usr/bin/env python3
"""Debug what dates are being found by dateparser."""

import dateparser.search
from datetime import datetime

def debug_dates():
    with open('examples/math55_syllabus.txt', 'r', encoding='utf-8') as f:
        text = f.read()
    
    current_year = datetime.now().year
    settings = {
        "PREFER_DATES_FROM": "current_period",
        "RELATIVE_BASE": datetime(current_year, 1, 1)
    }
    
    found = dateparser.search.search_dates(text, settings=settings, add_detected_language=False)
    
    print(f"Found {len(found)} date matches:")
    for i, (match_text, dt) in enumerate(found[:20]):  # Show first 20
        print(f"{i+1}. Text: '{match_text}' -> Date: {dt}")
    
    # Look specifically for "Wed Sep 3, 2025"
    print("\nLooking for 'Wed Sep 3, 2025' matches:")
    for i, (match_text, dt) in enumerate(found):
        if "Wed Sep 3, 2025" in match_text or "Sep 3" in match_text:
            print(f"  Match {i+1}: '{match_text}' -> {dt}")

if __name__ == "__main__":
    debug_dates()
