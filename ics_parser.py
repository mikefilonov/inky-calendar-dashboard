import datetime
import logging
import pytz
from icalendar import Calendar
import recurring_ical_events

logger = logging.getLogger(__name__)

def parse_ics_to_spec(ical_data: bytes, tz_name: str, start_date: datetime.date, end_date: datetime.date) -> dict:
    """
    Parses the raw ICS data, applies timezone localization, recurrences,
    exclusions, overrides, deduplicates and returns a JSON-serializable representation spec.
    """
    try:
        tz = pytz.timezone(tz_name)
    except Exception as e:
        logger.warning(f"Invalid timezone '{tz_name}', falling back to UTC. Error: {e}")
        tz = pytz.utc

    try:
        cal = Calendar.from_ical(ical_data)
    except Exception as e:
        logger.error(f"Failed to parse ICS data: {e}")
        return {"today_date": start_date.isoformat(), "events": []}

    start_filter = datetime.datetime.combine(start_date, datetime.time.min).replace(tzinfo=tz)
    end_filter = datetime.datetime.combine(end_date, datetime.time.max).replace(tzinfo=tz)

    def make_aware(dt, default_tz):
        if isinstance(dt, datetime.date) and not isinstance(dt, datetime.datetime):
            return datetime.datetime.combine(dt, datetime.time.min).replace(tzinfo=default_tz), True
        if dt.tzinfo is None:
            return default_tz.localize(dt), False
        return dt.astimezone(default_tz), False

    # Fetch recurring and non-recurring events with all rules applied automatically
    try:
        raw_events = recurring_ical_events.of(cal).between(start_filter, end_filter)
    except Exception as e:
        logger.error(f"Failed to calculate occurrences: {e}")
        return {"today_date": start_date.isoformat(), "events": []}

    events = []
    for event in raw_events:
        dtstart = event.get("dtstart").dt
        dtend = event.get("dtend")
        dtend = dtend.dt if dtend else dtstart

        start_dt, start_allday = make_aware(dtstart, tz)
        end_dt, end_allday = make_aware(dtend, tz)

        events.append({
            "summary": str(event.get("summary", "No Title")),
            "start": start_dt,
            "end": end_dt,
            "all_day": start_allday
        })

    # Sort events by start time, end time, and summary for stable deterministic ordering
    events.sort(key=lambda x: (x["start"], x["end"], x["summary"]))

    # Deduplicate events
    seen = set()
    deduped_events = []
    for ev in events:
        key = (ev["summary"], ev["start"], ev["all_day"])
        if key not in seen:
            seen.add(key)
            deduped_events.append(ev)

    # Convert to JSON-serializable Spec representation
    spec_events = []
    for ev in deduped_events:
        spec_events.append({
            "summary": ev["summary"],
            "start": ev["start"].isoformat(),
            "end": ev["end"].isoformat(),
            "all_day": ev["all_day"]
        })

    return {
        "today_date": start_date.isoformat(),
        "events": spec_events
    }

