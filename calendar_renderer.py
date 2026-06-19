import os
import datetime
import calendar
import urllib.request
import logging
from PIL import Image, ImageDraw, ImageFont
from icalendar import Calendar
from dateutil import rrule
import pytz

logger = logging.getLogger(__name__)

# Common font paths
FONT_PATHS = [
    "/System/Library/Fonts/Helvetica.ttc",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
]

FONT_BOLD_PATHS = [
    "/System/Library/Fonts/HelveticaNeue.ttc",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
]

def load_font(size, bold=False):
    # Try bundled font first for exact parity between Mac and Pi
    font_name = "Roboto-Bold.ttf" if bold else "Roboto-Regular.ttf"
    bundled_path = os.path.join(os.path.dirname(__file__), "fonts", font_name)
    if os.path.exists(bundled_path):
        try:
            f = ImageFont.truetype(bundled_path, size)
            logger.info(f"Loaded bundled font: {bundled_path} at size {size}")
            return f
        except OSError as e:
            logger.warning(f"Failed to load bundled font {bundled_path}: {e}")

    paths = FONT_BOLD_PATHS if bold else FONT_PATHS
    for path in paths:
        try:
            f = ImageFont.truetype(path, size)
            logger.info(f"Loaded system font fallback: {path} at size {size}")
            return f
        except OSError:
            continue
    logger.warning("All font loading failed, using default PIL font.")
    return ImageFont.load_default()

def draw_sharp_text(img, position, text, font, fill_color):
    """
    Draws text onto a 1-bit mask and pastes it onto the image to completely
    disable anti-aliasing. This ensures razor-sharp text on e-ink screens.
    """
    draw = ImageDraw.Draw(img)
    try:
        # Measure text ink bounds
        bbox = draw.textbbox(position, text, font=font)
        left, top, right, bottom = bbox
        
        # Ink dimensions
        ink_w = right - left
        ink_h = bottom - top
        
        # Mask dimensions (add 10px padding for safety)
        w = max(1, ink_w + 10)
        h = max(1, ink_h + 10)
        
        # Create 1-bit mask
        mask = Image.new("1", (w, h), 0)
        mask_draw = ImageDraw.Draw(mask)
        
        # Draw text in mask so the ink bounds map exactly to (5, 5)
        anchor_offset_x = left - position[0]
        anchor_offset_y = top - position[1]
        mask_draw.text((5 - anchor_offset_x, 5 - anchor_offset_y), text, fill=1, font=font)
        
        # Create color block and paste
        color_img = Image.new("RGB", (w, h), fill_color)
        img.paste(color_img, (left - 5, top - 5), mask=mask)
    except Exception as e:
        logger.debug(f"Sharp text failed, falling back to standard draw: {e}")
        draw.text(position, text, fill=fill_color, font=font)

def fetch_and_parse_events(ics_url, tz, start_date, end_date):
    """
    Fetches the iCal feed from the given URL and parses events
    occurring between `start_date` and `end_date`.
    """
    logger.info(f"Fetching calendar events from {ics_url}...")
    headers = {"User-Agent": "Mozilla/5.0 (InkyCalendar)"}
    req = urllib.request.Request(ics_url, headers=headers)
    
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            ical_data = response.read()
    except Exception as e:
        logger.error(f"Failed to fetch calendar data: {e}")
        return []

    cal = Calendar.from_ical(ical_data)
    
    start_filter = datetime.datetime.combine(start_date, datetime.time.min).replace(tzinfo=tz)
    end_filter = datetime.datetime.combine(end_date, datetime.time.max).replace(tzinfo=tz)
    
    events = []
    
    for component in cal.walk():
        if component.name != "VEVENT":
            continue
            
        summary = str(component.get("summary", "No Title"))
        # Do not modify spelling of Sofia's name per request, keep as is
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
                logger.warning(f"Error parsing recurring event '{summary}': {e}")
        else:
            if start_dt <= end_filter and end_dt >= start_filter:
                events.append({
                    "summary": summary,
                    "start": start_dt,
                    "end": end_dt,
                    "all_day": start_allday
                })
                
    # Sort events by start time
    events.sort(key=lambda x: x["start"])
    
    # Deduplicate events (some calendars return identical events via cal.walk() traversal or spelling duplicates)
    seen = set()
    deduped_events = []
    for ev in events:
        key = (ev["summary"], ev["start"], ev["all_day"])
        if key not in seen:
            seen.add(key)
            deduped_events.append(ev)
            
    return deduped_events

def extract_unique_people(events):
    people = set()
    for ev in events:
        summary = ev.get("summary", "")
        if ":" in summary:
            parts = summary.split(":", 1)
            possible_person = parts[0].strip()
            if possible_person and " " not in possible_person and len(possible_person) < 20:
                people.add(possible_person)
    return sorted(list(people))

def get_person_from_summary(summary, unique_people):
    for person in unique_people:
        if summary.startswith(f"{person}:") or summary.startswith(f"{person} "):
            return person
    return None

# Russian localization dictionaries
RU_DAYS_FULL = {
    0: "ПОНЕДЕЛЬНИК",
    1: "ВТОРНИК",
    2: "СРЕДА",
    3: "ЧЕТВЕРГ",
    4: "ПЯТНИЦА",
    5: "СУББОТА",
    6: "ВОСКРЕСЕНЬЕ"
}

RU_MONTHS = {
    1: "января", 2: "февраля", 3: "марта", 4: "апреля", 5: "мая", 6: "июня",
    7: "июля", 8: "августа", 9: "сентября", 10: "октября", 11: "ноября", 12: "декабря"
}

def format_ru_date(dt):
    return f"{dt.day} {RU_MONTHS[dt.month]}"

def draw_calendar(resolution, events, tz):
    width, height = resolution
    img = Image.new("RGB", (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    
    # Pure colors only (no grays)
    COLOR_BG = (255, 255, 255)
    COLOR_TEXT = (0, 0, 0)
    COLOR_ACCENT = (230, 30, 30) # Red
    COLOR_BLUE = (0, 0, 230)      # Blue
    
    now = datetime.datetime.now(tz)
    today_date = now.date()
    
    # Display 5 days: Today and the next 4 days
    week_dates = [today_date + datetime.timedelta(days=i) for i in range(5)]
    
    # Extract unique people and assign text colors dynamically
    unique_people = extract_unique_people(events)
    # Highlight palette (Blue, Accent/Red, Text/Black)
    COLOR_PALETTE = [COLOR_BLUE, COLOR_ACCENT, COLOR_TEXT]
    person_colors = {}
    for idx, person in enumerate(unique_people):
        color_idx = idx % len(COLOR_PALETTE)
        person_colors[person] = COLOR_PALETTE[color_idx]
        
    # Header area
    font_title = load_font(22, bold=True)
    font_subtitle = load_font(14, bold=True)
    
    title_text = "РАСПИСАНИЕ ЗАНЯТИЙ"
    date_range_text = f"{format_ru_date(today_date)} — {format_ru_date(week_dates[-1])}".upper()
    
    draw_sharp_text(img, (20, 10), title_text, font_title, COLOR_TEXT)
    draw_sharp_text(img, (width - 320, 16), date_range_text, font_subtitle, COLOR_ACCENT)
    
    # Divider under header (using pure black)
    draw.line([(0, 45), (width, 45)], fill=COLOR_TEXT, width=2)
    
    y_cursor = 47
    
    # Group events by date
    events_by_date = {d: [] for d in week_dates}
    for ev in events:
        ev_day = ev["start"].date()
        if ev_day in events_by_date:
            events_by_date[ev_day].append(ev)
            
    # Fonts
    font_day_name = load_font(18, bold=True)
    font_day_date = load_font(12, bold=True)
    
    # Collapsed Day fonts
    font_event_collapsed = load_font(16, bold=True)
    font_no_events = load_font(16)
    
    # Today Expanded fonts
    font_today_time = load_font(20, bold=True)
    font_today_title = load_font(20, bold=False)
    
    # Layout rendering (5 rows: Today expanded, next 4 collapsed)
    for i, day_date in enumerate(week_dates):
        is_today = (i == 0)
        day_events = events_by_date[day_date]
        
        # Today gets 170px height, others get 65px height
        row_height = 170 if is_today else 65
        
        # Draw borders and highlights
        if is_today:
            # Draw a thick Red outline around today's card
            draw.rectangle([(2, y_cursor), (width - 2, y_cursor + row_height)], outline=COLOR_ACCENT, width=4)
            # Divider below today's card
            draw.line([(0, y_cursor + row_height), (width, y_cursor + row_height)], fill=COLOR_TEXT, width=2)
        else:
            # Simple bottom border for other days
            draw.line([(0, y_cursor + row_height), (width, y_cursor + row_height)], fill=COLOR_TEXT, width=1)
            
        # Left side column: Date & Day name (shifted right for padding)
        x_events_start = 200
        
        if is_today:
            draw_sharp_text(img, (20, y_cursor + 55), "СЕГОДНЯ", load_font(26, bold=True), COLOR_ACCENT)
            draw_sharp_text(img, (20, y_cursor + 95), format_ru_date(day_date), font_day_date, COLOR_TEXT)
        else:
            day_label = "ЗАВТРА" if i == 1 else RU_DAYS_FULL[day_date.weekday()]
            draw_sharp_text(img, (20, y_cursor + 12), day_label, font_day_name, COLOR_TEXT)
            draw_sharp_text(img, (20, y_cursor + 38), format_ru_date(day_date), font_day_date, COLOR_TEXT)
            
        # Draw events
        if is_today:
            if not day_events:
                draw_sharp_text(img, (x_events_start, y_cursor + 65), "Нет занятий на сегодня", font_no_events, COLOR_TEXT)
            else:
                # Show up to 4 events stacked
                for idx, ev in enumerate(day_events[:4]):
                    ev_y = y_cursor + 12 + (idx * 38)
                    
                    # 12-hour clock format (e.g. 04:00 PM)
                    time_str = "ВЕСЬ ДЕНЬ" if ev["all_day"] else ev["start"].strftime("%I:%M %p")
                    draw_sharp_text(img, (x_events_start, ev_y), time_str, font_today_time, COLOR_ACCENT)
                    
                    summary = ev["summary"]
                    # Assign custom color highlights dynamically
                    person = get_person_from_summary(summary, unique_people)
                    summary_color = person_colors.get(person, COLOR_TEXT) if person else COLOR_TEXT
                        
                    draw_sharp_text(img, (x_events_start + 110, ev_y), summary, font_today_title, summary_color)
        else:
            if not day_events:
                draw_sharp_text(img, (x_events_start, y_cursor + 20), "Нет занятий", font_no_events, COLOR_TEXT)
            else:
                event_strings = []
                for ev in day_events:
                    # 12-hour clock format (e.g. 04:00 PM)
                    time_str = "Весь день" if ev["all_day"] else ev["start"].strftime("%I:%M %p")
                    event_strings.append(f"{time_str}: {ev['summary']}")
                
                full_line = "   •   ".join(event_strings)
                max_chars = 55
                if len(full_line) > max_chars:
                    full_line = full_line[:max_chars-3] + "..."
                    
                draw_sharp_text(img, (x_events_start, y_cursor + 20), full_line, font_event_collapsed, COLOR_TEXT)
                
        y_cursor += row_height
        
    return img
