import os
import sys
import datetime
import pytz
from PIL import Image

# Add current directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import calendar_renderer

def main():
    # Load configuration if it exists
    import json
    config = {}
    config_path = os.path.join(os.path.dirname(__file__), "config.json")
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            config = json.load(f)
            
    # Determine renderer type: CLI argument takes precedence, then config, then default 'list'
    renderer_type = "list"
    if len(sys.argv) > 1 and sys.argv[1] in ["list", "grid"]:
        renderer_type = sys.argv[1]
    else:
        renderer_type = config.get("renderer", "list")
        
    timezone_name = config.get("timezone", "America/Los_Angeles")
    tz = pytz.timezone(timezone_name)
    
    # 1. Fetch dates (Set to next week's Wednesday, June 24, 2026, for testing)
    today_date = datetime.date(2026, 6, 24)
    start_date = today_date
    end_date = today_date + datetime.timedelta(days=2)
    
    # 2. Get local calendar file path (for fast offline iterations)
    # We can check for live_family.ics first, then family.ics
    ics_path = None
    for filename in ["live_family.ics", "family.ics"]:
        path = os.path.join(os.path.dirname(__file__), filename)
        if os.path.exists(path):
            ics_path = path
            break
            
    if not ics_path:
        print("Error: No local calendar file found. Please download one using curl or deploy the project first.")
        sys.exit(1)
        
    print(f"Reading events from local file: {ics_path}")
    
    # Read iCal data from file
    with open(ics_path, "rb") as f:
        ical_data = f.read()
        
    # We monkeypatch or use a local parser version of calendar_renderer
    # Since fetch_and_parse_events takes a URL and fetches via urllib, let's write a file-based parser
    # that calls the exact same calendar_renderer VEVENT parsing logic.
    from icalendar import Calendar
    from dateutil import rrule
    
    cal = Calendar.from_ical(ical_data)
    start_filter = datetime.datetime.combine(start_date, datetime.time.min).replace(tzinfo=tz)
    end_filter = datetime.datetime.combine(end_date, datetime.time.max).replace(tzinfo=tz)
    
    events = []
    
    for component in cal.walk():
        if component.name != "VEVENT":
            continue
            
        summary = str(component.get("summary", "No Title"))
        dtstart = component.get("dtstart").dt
        dtend = component.get("dtend")
        dtend = dtend.dt if dtend else dtstart
        
        def make_aware(dt, default_tz):
            if isinstance(dt, datetime.date) and not isinstance(dt, datetime.datetime):
                return datetime.datetime.combine(dt, datetime.time.min).replace(tzinfo=default_tz), True
            if dt.tzinfo is None:
                return default_tz.localize(dt), False
            return dt.astimezone(default_tz), False

        start_dt, start_allday = make_aware(dtstart, tz)
        end_dt, end_allday = make_aware(dtend, tz)
        
        rrule_prop = component.get("rrule")
        if rrule_prop:
            try:
                rrule_str = rrule_prop.to_ical().decode("utf-8")
                naive_start = start_dt.astimezone(tz).replace(tzinfo=None)
                rule = rrule.rrulestr(rrule_str, dtstart=naive_start)
                
                occurrences = rule.between(
                    start_filter.replace(tzinfo=None),
                    end_filter.replace(tzinfo=None),
                    inc=True
                )
                
                for occ in occurrences:
                    occ_start = tz.localize(occ)
                    duration = end_dt - start_dt
                    occ_end = occ_start + duration
                    events.append({
                        "summary": summary,
                        "start": occ_start,
                        "end": occ_end,
                        "all_day": start_allday
                    })
            except Exception as e:
                pass
        else:
            if start_dt <= end_filter and end_dt >= start_filter:
                events.append({
                    "summary": summary,
                    "start": start_dt,
                    "end": end_dt,
                    "all_day": start_allday
                })
                
    events.sort(key=lambda x: x["start"])
    
    # Deduplicate events using spelling-independent key (mirroring renderer)
    seen = set()
    deduped_events = []
    for ev in events:
        norm_summary = ev["summary"].replace("Софья", "София")
        key = (norm_summary, ev["start"], ev["all_day"])
        if key not in seen:
            seen.add(key)
            deduped_events.append(ev)
            
    print(f"Loaded {len(deduped_events)} events for the {renderer_type} view.")
    
    # 3. Draw calendar
    resolution = tuple(config.get("resolution", [800, 480]))
    print(f"Rendering layout ({renderer_type}) at resolution {resolution}...")
    
    if renderer_type == "grid":
        import grid_renderer
        img = grid_renderer.draw_calendar(resolution, deduped_events, tz, today_date)
    else:
        # calendar_renderer can also take it or keep standard signature
        try:
            img = calendar_renderer.draw_calendar(resolution, deduped_events, tz, today_date)
        except TypeError:
            img = calendar_renderer.draw_calendar(resolution, deduped_events, tz)
    
    # 4. Save to local calendar.png
    output_path = os.path.join(os.path.dirname(__file__), "calendar.png")
    img.save(output_path)
    print(f"Render complete! View output at: {output_path}")

if __name__ == "__main__":
    main()
