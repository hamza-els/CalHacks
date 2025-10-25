#!/usr/bin/env python3
"""Test the parser deduplication with the math55_syllabus.txt file."""

from parsers import extract_events_from_text

def test_dedup():
    with open('examples/math55_syllabus.txt', 'r', encoding='utf-8') as f:
        text = f.read()
    
    events = extract_events_from_text(text)
    print(f'Found {len(events)} events (should be fewer due to deduplication):')
    
    # Group by title to see duplicates
    title_counts = {}
    for event in events:
        title = event["title"]
        title_counts[title] = title_counts.get(title, 0) + 1
    
    print(f'\nUnique titles: {len(title_counts)}')
    print('\nEvents with duplicates:')
    for title, count in title_counts.items():
        if count > 1:
            print(f'  "{title[:60]}..." appears {count} times')
    
    print('\nFirst 10 events:')
    for i, event in enumerate(events[:10]):
        print(f'{i+1}. {event["title"][:60]}...')
        print(f'   Date: {event["start"].strftime("%Y-%m-%d %H:%M")}')
        print()

if __name__ == "__main__":
    test_dedup()
