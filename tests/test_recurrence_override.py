import unittest
import datetime
import pytz
from ics_parser import parse_ics_to_spec

class TestRecurrenceOverride(unittest.TestCase):
    def test_recurrence_override_moved_event(self):
        # Raw iCal data simulating:
        # 1. A weekly event on Sundays at 10:00 AM
        # 2. An override for 2026-07-12 (Sunday) moved to 2026-07-13 (Monday) at 10:00 AM
        # 3. An independent event on Sunday 2026-07-12 at 10:00 AM
        ical_str = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Example Corp//Cal//EN
BEGIN:VTIMEZONE
TZID:America/Los_Angeles
BEGIN:DAYLIGHT
TZOFFSETFROM:-0800
TZOFFSETTO:-0700
TZNAME:PDT
DTSTART:19700308T020000
RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=2SU
END:DAYLIGHT
BEGIN:STANDARD
TZOFFSETFROM:-0700
TZOFFSETTO:-0800
TZNAME:PST
DTSTART:19701101T020000
RRULE:FREQ=YEARLY;BYMONTH=11;BYDAY=1SU
END:STANDARD
END:VTIMEZONE
BEGIN:VEVENT
UID:recurring_1
SUMMARY:Софья: Рисование
DTSTART;TZID=America/Los_Angeles:20260621T100000
DTEND;TZID=America/Los_Angeles:20260621T110000
RRULE:FREQ=WEEKLY;BYDAY=SU
END:VEVENT
BEGIN:VEVENT
UID:recurring_1
SUMMARY:Софья: Рисование
RECURRENCE-ID;TZID=America/Los_Angeles:20260712T100000
DTSTART;TZID=America/Los_Angeles:20260713T100000
DTEND;TZID=America/Los_Angeles:20260713T110000
END:VEVENT
BEGIN:VEVENT
UID:single_1
SUMMARY:Миша: математика
DTSTART;TZID=America/Los_Angeles:20260712T100000
DTEND;TZID=America/Los_Angeles:20260712T110000
END:VEVENT
END:VCALENDAR
"""
        ical_data = ical_str.encode("utf-8")
        tz_name = "America/Los_Angeles"
        start_date = datetime.date(2026, 7, 12)
        end_date = datetime.date(2026, 7, 13)

        spec = parse_ics_to_spec(ical_data, tz_name, start_date, end_date)
        events = spec["events"]

        # We expect exactly 2 events in this window:
        # - "Миша: математика" on Sunday 2026-07-12 at 10:00 AM
        # - "Софья: Рисование" on Monday 2026-07-13 at 10:00 AM
        # (The original "Софья: Рисование" on Sunday 2026-07-12 should be overridden and not exist)
        
        self.assertEqual(len(events), 2, f"Expected 2 events, got: {events}")
        
        event_1 = events[0]
        event_2 = events[1]
        
        self.assertEqual(event_1["summary"], "Миша: математика")
        self.assertEqual(event_1["start"], "2026-07-12T10:00:00-07:00")
        
        self.assertEqual(event_2["summary"], "Софья: Рисование")
        self.assertEqual(event_2["start"], "2026-07-13T10:00:00-07:00")

    def test_dtstart_non_matching_rrule_included(self):
        # Raw iCal data simulating:
        # A weekly event repeating on Sundays (BYDAY=SU), but whose DTSTART is on a Monday (2026-07-20).
        # We expect the event to occur on the Monday DTSTART date as the first instance.
        ical_str = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Example Corp//Cal//EN
BEGIN:VTIMEZONE
TZID:America/Los_Angeles
BEGIN:DAYLIGHT
TZOFFSETFROM:-0800
TZOFFSETTO:-0700
TZNAME:PDT
DTSTART:19700308T020000
RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=2SU
END:DAYLIGHT
BEGIN:STANDARD
TZOFFSETFROM:-0700
TZOFFSETTO:-0800
TZNAME:PST
DTSTART:19701101T020000
RRULE:FREQ=YEARLY;BYMONTH=11;BYDAY=1SU
END:STANDARD
END:VTIMEZONE
BEGIN:VEVENT
UID:non_matching_dtstart_1
SUMMARY:Софья: Рисование
DTSTART;TZID=America/Los_Angeles:20260720T100000
DTEND;TZID=America/Los_Angeles:20260720T110000
RRULE:FREQ=WEEKLY;BYDAY=SU
END:VEVENT
END:VCALENDAR
"""
        ical_data = ical_str.encode("utf-8")
        tz_name = "America/Los_Angeles"
        # Check window containing Monday (July 20) and the following Sunday (July 26)
        start_date = datetime.date(2026, 7, 20)
        end_date = datetime.date(2026, 7, 26)

        spec = parse_ics_to_spec(ical_data, tz_name, start_date, end_date)
        events = spec["events"]

        # We expect 2 occurrences:
        # 1. Monday 2026-07-20 (the DTSTART itself)
        # 2. Sunday 2026-07-26 (the next weekly Sunday recurrence)
        self.assertEqual(len(events), 2, f"Expected 2 events, got: {events}")

        self.assertEqual(events[0]["summary"], "Софья: Рисование")
        self.assertEqual(events[0]["start"], "2026-07-20T10:00:00-07:00")

        self.assertEqual(events[1]["summary"], "Софья: Рисование")
        self.assertEqual(events[1]["start"], "2026-07-26T10:00:00-07:00")

if __name__ == "__main__":
    unittest.main()
