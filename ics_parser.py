import datetime
import logging
import pytz
from icalendar import Calendar
from dateutil import rrule

logger = logging.getLogger(__name__)

def parse_ics_to_spec(ical_data: bytes, tz_name: str, start_date: datetime.date, end_date: datetime.date) -> dict:
    """
    Parses the raw ICS data, applies timezone localization, recurrences (rrule),
    exclusion dates (exdates), deduplicates and returns a JSON-serializable representation spec.
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

    events = []
    overrides = {}
    components_to_process = []

    # First Pass: collect all overrides and prepare list of components to process
    for component in cal.walk():
        if component.name != "VEVENT":
            continue

        uid = str(component.get("uid", ""))
        summary = str(component.get("summary", "No Title"))
        dtstart_prop = component.get("dtstart")
        if not dtstart_prop:
            continue
        dtstart = dtstart_prop.dt
        dtend = component.get("dtend")
        dtend = dtend.dt if dtend else dtstart

        start_dt, start_allday = make_aware(dtstart, tz)
        end_dt, end_allday = make_aware(dtend, tz)
        status = str(component.get("status", "")).upper()

        rec_id_prop = component.get("recurrence-id")
        if rec_id_prop:
            rec_id_dt, _ = make_aware(rec_id_prop.dt, tz)
            overrides[(uid, rec_id_dt)] = {
                "start_dt": start_dt,
                "end_dt": end_dt,
                "summary": summary,
                "all_day": start_allday,
                "cancelled": status == "CANCELLED"
            }
        else:
            components_to_process.append((component, uid, summary, start_dt, end_dt, start_allday, status))

    # Second Pass: process all components that are NOT overrides
    for component, uid, summary, start_dt, end_dt, start_allday, status in components_to_process:
        rrule_prop = component.get("rrule")
        if rrule_prop:
            try:
                # Parse exclusions (EXDATE)
                exdates = []
                exdate_prop = component.get("exdate")
                if exdate_prop:
                    if not isinstance(exdate_prop, list):
                        exdate_prop = [exdate_prop]
                    for ex_list in exdate_prop:
                        if hasattr(ex_list, "dts"):
                            for ex_item in ex_list.dts:
                                ex_dt, _ = make_aware(ex_item.dt, tz)
                                exdates.append(ex_dt)
                        else:
                            ex_dt, _ = make_aware(ex_list, tz)
                            exdates.append(ex_dt)

                rrule_str = rrule_prop.to_ical().decode("utf-8")
                naive_start = start_dt.astimezone(tz).replace(tzinfo=None)
                rule = rrule.rrulestr(rrule_str, dtstart=naive_start, ignoretz=True)

                occurrences = rule.between(
                    start_filter.replace(tzinfo=None),
                    end_filter.replace(tzinfo=None),
                    inc=True
                )

                if naive_start not in occurrences:
                    if start_filter.replace(tzinfo=None) <= naive_start <= end_filter.replace(tzinfo=None):
                        occurrences.append(naive_start)

                for occ in occurrences:
                    occ_start = tz.localize(occ)
                    if any(occ_start == ex_dt for ex_dt in exdates):
                        continue
                    if (uid, occ_start) in overrides:
                        continue
                    duration = end_dt - start_dt
                    occ_end = occ_start + duration
                    events.append({
                        "summary": summary,
                        "start": occ_start,
                        "end": occ_end,
                        "all_day": start_allday
                    })
            except Exception as e:
                logger.warning(f"Error parsing recurring event '{summary}': {e}")
        else:
            if status != "CANCELLED":
                if start_dt <= end_filter and end_dt >= start_filter:
                    events.append({
                        "summary": summary,
                        "start": start_dt,
                        "end": end_dt,
                        "all_day": start_allday
                    })

    # Add active overrides that fall in the window
    for override in overrides.values():
        if not override["cancelled"]:
            start_dt = override["start_dt"]
            end_dt = override["end_dt"]
            if start_dt <= end_filter and end_dt >= start_filter:
                events.append({
                    "summary": override["summary"],
                    "start": start_dt,
                    "end": end_dt,
                    "all_day": override["all_day"]
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
