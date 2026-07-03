import datetime
import logging
from PIL import Image, ImageDraw

from renderer_utils import (
    load_font,
    draw_sharp_text,
    extract_unique_people,
    get_person_from_summary,
    RU_DAYS_FULL,
    format_ru_date_list
)

logger = logging.getLogger(__name__)

def draw_list_layout(resolution, events, today_date):
    """
    Renders the chronological list layout (5-day view) from the parsed events list.
    `events` should be a list of events with `start` and `end` as datetime objects.
    `today_date` should be a datetime.date object.
    """
    width, height = resolution
    img = Image.new("RGB", (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    
    # Pure colors only (no grays)
    COLOR_BG = (255, 255, 255)
    COLOR_TEXT = (0, 0, 0)
    COLOR_ACCENT = (230, 30, 30) # Red
    COLOR_BLUE = (0, 0, 230)      # Blue
    
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
    date_range_text = f"{format_ru_date_list(today_date)} — {format_ru_date_list(week_dates[-1])}".upper()
    
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
            draw_sharp_text(img, (20, y_cursor + 95), format_ru_date_list(day_date), font_day_date, COLOR_TEXT)
        else:
            day_label = "ЗАВТРА" if i == 1 else RU_DAYS_FULL[day_date.weekday()]
            draw_sharp_text(img, (20, y_cursor + 12), day_label, font_day_name, COLOR_TEXT)
            draw_sharp_text(img, (20, y_cursor + 38), format_ru_date_list(day_date), font_day_date, COLOR_TEXT)
            
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
