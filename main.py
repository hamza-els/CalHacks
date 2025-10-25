"""CLI entrypoint for the Event extractor and calendar uploader.

Usage examples:
  python main.py --input examples/sample_input.txt --ics out.ics
  python main.py --input examples/sample_input.txt --google --calendar-id primary

Before using --google, follow README to create `credentials.json` and enable Calendar API.
"""
import argparse
from pprint import pprint
from pathlib import Path
import sys

from parsers import extract_events_from_text

try:
	from calendar_utils import create_google_service, create_google_event, export_events_to_ics
except Exception:
	# We'll only error if the user tries to push or export; keep imports lazy.
	create_google_service = None
	create_google_event = None
	export_events_to_ics = None


def read_input_text(path: str) -> str:
	if path == "-":
		return sys.stdin.read()
	p = Path(path)
	if not p.exists():
		raise FileNotFoundError(f"Input file not found: {path}")
	return p.read_text(encoding="utf-8")


def main():
	parser = argparse.ArgumentParser(description="Extract events from text and create calendar events or export .ics")
	parser.add_argument("--input", "-i", required=True, help="Input text file path or '-' to read stdin")
	parser.add_argument("--google", action="store_true", help="Push extracted events to Google Calendar (requires credentials.json)")
	parser.add_argument("--calendar-id", default="primary", help="Google Calendar ID, default 'primary'")
	parser.add_argument("--ics", help="Write extracted events to an .ics file (Apple Calendar import)")
	parser.add_argument("--dry-run", action="store_true", help="Don't create events; just show parsed results")
	args = parser.parse_args()

	text = read_input_text(args.input)
	events = extract_events_from_text(text)

	if not events:
		print("No event-like dates found in input.")
		return

	print(f"Found {len(events)} events:")
	for i, e in enumerate(events, 1):
		print(f"[{i}] {e['title']}")
		print(f"    start: {e['start']}")
		print(f"    end:   {e['end']}")

	if args.ics:
		if export_events_to_ics is None:
			print("ICS export not available: missing dependencies. Install requirements.txt")
		else:
			out = export_events_to_ics(events, args.ics)
			print(f"Wrote ICS to: {out}")

	if args.google:
		if create_google_service is None:
			print("Google Calendar push not available: missing google client libraries. Install requirements.txt")
			return
		if args.dry_run:
			print("Dry run: skipping Google Calendar push")
			return
		# Create service and push events
		service = create_google_service()
		created = []
		for e in events:
			res = create_google_event(service, e, calendar_id=args.calendar_id)
			created.append(res.get("htmlLink"))
			print("Created:", res.get("htmlLink"))


if __name__ == "__main__":
	main()

