#!/usr/bin/env python3
"""Debug specific duplicate issue."""

import dateparser.search
from datetime import datetime

def debug_specific():
    with open('examples/math55_syllabus.txt', 'r', encoding='utf-8') as f:
        text = f.read()
    
    current_year = datetime.now().year
    settings = {
        "PREFER_DATES_FROM": "current_period",
        "RELATIVE_BASE": datetime(current_year, 1, 1)
    }
    
    found = dateparser.search.search_dates(text, settings=settings, add_detected_language=False)
    
    # Find the line with "Wed Sep 3, 2025"
    lines = text.split('\n')
    target_line = None
    for i, line in enumerate(lines):
        if "Wed Sep 3, 2025" in line:
            target_line = i
            print(f"Found target line {i}: {line}")
            break
    
    if target_line is not None:
        print(f"\nAll date matches in that line:")
        for i, (match_text, dt) in enumerate(found):
            # Check if this match is in the target line
            if match_text in lines[target_line]:
                print(f"  {i+1}. '{match_text}' -> {dt}")
                
                # Extract sentence context
                idx = text.find(match_text)
                if idx != -1:
                    left = text.rfind("\n", 0, idx)
                    if left == -1:
                        left = 0
                    else:
                        left += 1
                    right = text.find("\n", idx)
                    if right == -1:
                        right = len(text)
                    sentence = text[left:right].strip()
                    print(f"     Context: '{sentence}'")

if __name__ == "__main__":
    debug_specific()
