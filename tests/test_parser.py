# Agent Instruction Block:
# This script parses an iCal (.ics) file into a clean, intermediate Representation Spec JSON.
# Agents can invoke this script with custom parameters to test different calendar data inputs:
#
# Examples:
#   python tests/test_parser.py -i <path_to_ics> -o <path_to_output_json> -d 2026-07-02
#   python tests/test_parser.py --timezone America/New_York --days 7
#
# Parameters:
#   -i / --input: Path to the calendar .ics source file (e.g. tests/data/test_calendar.ics)
#   -o / --output: Target path where the parsed representation spec JSON should be saved.
#   -t / --timezone: The timezone context to localize recurrences (e.g. America/Los_Angeles)
#   -d / --today: An anchor date (YYYY-MM-DD) to treat as "today" (today's schedule starts on this date).
#   -n / --days: The duration (number of days) to include in the parsed window.

import os
import sys
import json
import datetime
import argparse

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ics_parser import parse_ics_to_spec

def main():
    tests_dir = os.path.dirname(os.path.abspath(__file__))
    default_input = os.path.join(tests_dir, "data", "test_calendar.ics")
    default_output = os.path.join(tests_dir, "specs", "test_calendar_spec.json")

    parser = argparse.ArgumentParser(description="Parse ICS calendar file into Representation Spec JSON.")
    parser.add_argument("-i", "--input", default=default_input, help=f"Path to input .ics file (default: {default_input})")
    parser.add_argument("-o", "--output", default=default_output, help=f"Path to output spec .json file (default: {default_output})")
    parser.add_argument("-t", "--timezone", default="America/Los_Angeles", help="Timezone name (default: America/Los_Angeles)")
    parser.add_argument("-d", "--today", default="2026-06-24", help="Anchor today's date in YYYY-MM-DD format (default: 2026-06-24)")
    parser.add_argument("-n", "--days", type=int, default=4, help="Number of days to parse forward from anchor date (default: 4)")

    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"Error: Input calendar file not found at {args.input}.")
        sys.exit(1)

    print(f"Reading ICS file: {args.input}")
    with open(args.input, "rb") as f:
        ical_data = f.read()

    try:
        today_date = datetime.date.fromisoformat(args.today)
    except ValueError:
        print(f"Error: Invalid date format for --today: {args.today}. Use YYYY-MM-DD.")
        sys.exit(1)

    end_date = today_date + datetime.timedelta(days=args.days)

    print(f"Parsing ICS for date range {today_date} to {end_date} in timezone {args.timezone}...")
    spec = parse_ics_to_spec(ical_data, args.timezone, today_date, end_date)

    # Inject a deterministic current_time (e.g. 18:45:00) on today_date for rendering tests
    import pytz
    try:
        tz = pytz.timezone(args.timezone)
        mock_now = tz.localize(datetime.datetime.combine(today_date, datetime.time(18, 45, 0)))
    except Exception:
        mock_now = datetime.datetime.combine(today_date, datetime.time(18, 45, 0)).replace(tzinfo=datetime.timezone.utc)
    spec["current_time"] = mock_now.isoformat()

    # Ensure output parent directory exists
    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)

    with open(args.output, "w") as f:
        json.dump(spec, f, indent=2, ensure_ascii=False)

    print(f"Success! Generated intermediate Representation Spec at: {args.output}")
    print(f"Parsed {len(spec['events'])} events.")

if __name__ == "__main__":
    main()
