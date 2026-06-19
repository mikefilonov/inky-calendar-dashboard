import os
import datetime
import calendar
import logging
from PIL import Image, ImageDraw, ImageFont
import pytz

logger = logging.getLogger(__name__)

# Import font and text drawing helpers from calendar_renderer for styling parity
from calendar_renderer import load_font, draw_sharp_text

# Localization dictionaries
RU_DAYS_FULL = {
    0: "Понедельник", 1: "Вторник", 2: "Среда", 3: "Четверг", 4: "Пятница", 5: "Суббота", 6: "Воскресенье"
}

RU_MONTHS_GENITIVE = {
    1: "января", 2: "февраля", 3: "марта", 4: "апреля", 5: "мая", 6: "июня",
    7: "июля", 8: "августа", 9: "сентября", 10: "октября", 11: "ноября", 12: "декабря"
}

def format_ru_date(dt):
    return f"{dt.day} {RU_MONTHS_GENITIVE[dt.month].capitalize()}"

# Let's override font loading to prefer DejaVuSans for crisp 1-bit rendering
def load_crisp_font(size, bold=False):
    # Prefer DejaVuSans for 1-bit non-antialiased screens as it has superior hinting and Cyrillic glyphs
    font_name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    bundled_path = os.path.join(os.path.dirname(__file__), "fonts", font_name)
    if os.path.exists(bundled_path):
        try:
            return ImageFont.truetype(bundled_path, size)
        except OSError:
            pass
    return load_font(size, bold)

def wrap_text(text, font, max_width):
    """Wraps text to fit within max_width pixels using standard font metrics."""
    words = text.split()
    lines = []
    current_line = []
    
    # Dummy image for text length measurements
    img = Image.new("1", (1, 1))
    draw = ImageDraw.Draw(img)
    
    for word in words:
        test_line = " ".join(current_line + [word])
        w = draw.textlength(test_line, font=font)
        if w <= max_width or not current_line:
            current_line.append(word)
        else:
            lines.append(" ".join(current_line))
            current_line = [word]
            
    if current_line:
        lines.append(" ".join(current_line))
        
    return lines

def get_event_colors(summary):
    """Returns (bg_color, text_color) based on the event subject."""
    # Sofia/Sofya -> Burgundy/Dark Purple
    if summary.startswith("Алина"):
        return (50, 15, 45), (255, 255, 255)
    # Misha -> Terracotta/Orange-Brown
    elif summary.startswith("Максим"):
        return (150, 60, 25), (255, 255, 255)
    # Default -> Yellow
    return (240, 195, 30), (0, 0, 0)

def get_event_colors_non_today(summary):
    """Returns (accent_color, text_color) for non-today text layout."""
    # Sofia/Sofya -> Burgundy/Dark Purple
    if summary.startswith("Алина"):
        return (50, 15, 45), (0, 0, 0)
    # Misha -> Terracotta/Orange-Brown
    elif summary.startswith("Максим"):
        return (150, 60, 25), (0, 0, 0)
    # Default -> Yellow/Mustard
    return (210, 170, 20), (0, 0, 0)

def split_summary_by_person(summary):
    """Splits summary into (person, event_title)"""
    for prefix in ["Алина:", "Максим:"]:
        if summary.startswith(prefix):
            return prefix[:-1], summary[len(prefix):].strip()
    return "", summary

def draw_calendar(resolution, events, tz, today_date=None):
    width, height = resolution
    img = Image.new("RGB", (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    
    # Core Colors
    COLOR_GRID = (180, 180, 180)
    COLOR_TEXT = (0, 0, 0)
    COLOR_HEADER_BG = (225, 225, 225)
    
    # 1. Determine Rolling 3-Day window
    if today_date is None:
        now = datetime.datetime.now(tz)
        today_date = now.date()
    week_dates = [today_date + datetime.timedelta(days=i) for i in range(3)]
    
    # Group events by date, ignoring all-day events
    events_by_date = {d: [] for d in week_dates}
    for ev in events:
        if ev["all_day"]:
            continue
        ev_day = ev["start"].date()
        if ev_day in events_by_date:
            events_by_date[ev_day].append(ev)
            
    # Fonts (prefer loaded crisp font)
    font_day_header = load_crisp_font(13, bold=True)
    
    font_event_time_today = load_crisp_font(15, bold=False)
    font_event_person_today = load_crisp_font(16, bold=True)
    font_event_title_today = load_crisp_font(26, bold=True)  # Upgraded to size 26 bold!
    
    font_event_person_other = load_crisp_font(12, bold=True)
    font_event_title_other = load_crisp_font(16, bold=True)  # Upgraded to size 16 bold
    font_event_time_other = load_crisp_font(12, bold=False)  # Upgraded to size 12
    
    # 3. Dynamic Column Coordinates for 2 Columns
    # Left: Today (480px), Right: Future days collapsed (308px)
    x_hour_col_w = 12
    col_widths = [480, 308]
    col_x_positions = [x_hour_col_w, x_hour_col_w + 480]
        
    y_day_header = 0  # Reclaimed space from date range header removal
    y_day_header_h = 28
    y_grid_start = y_day_header + y_day_header_h # 28
    
    # Draw Background for Column Headers
    draw.rectangle([(0, y_day_header), (width, y_day_header + y_day_header_h)], fill=COLOR_HEADER_BG)
    
    # Draw Borders
    draw.line([(0, y_day_header), (width, y_day_header)], fill=COLOR_TEXT, width=2)
    draw.line([(0, y_grid_start), (width, y_grid_start)], fill=COLOR_TEXT, width=2)
    draw.line([(0, height - 1), (width, height - 1)], fill=COLOR_TEXT, width=1)
    
    # Draw Left Column Header (Today) with full weekday and month
    today_lbl = f"• {RU_DAYS_FULL[today_date.weekday()]} {today_date.day} {RU_MONTHS_GENITIVE[today_date.month].capitalize()} •"
    draw.rectangle([(col_x_positions[0] + 1, y_day_header + 1), (col_x_positions[0] + col_widths[0] - 1, y_day_header + y_day_header_h - 1)], outline=(200, 30, 30), width=2)
    text_w = draw.textlength(today_lbl, font=font_day_header)
    draw_sharp_text(img, (col_x_positions[0] + (col_widths[0] - text_w) // 2, y_day_header + 6), today_lbl, font_day_header, COLOR_TEXT)
    
    # Draw Right Column Header (Future Days)
    future_lbl = "ПРЕДСТОЯЩИЕ ДНИ"
    text_w = draw.textlength(future_lbl, font=font_day_header)
    draw_sharp_text(img, (col_x_positions[1] + (col_widths[1] - text_w) // 2, y_day_header + 6), future_lbl, font_day_header, COLOR_TEXT)
    
    # Vertical divider line separating the two main columns
    draw.line([(col_x_positions[1], y_day_header), (col_x_positions[1], height)], fill=COLOR_TEXT, width=2)
    
    # 4. Draw Today's Column (Left Column)
    today_events = sorted(events_by_date[today_date], key=lambda e: e["start"])
    card_height = 112  # Reclaimed space allows larger card height (was 96)
    card_spacing = 14
    for ev_idx, ev in enumerate(today_events):
        y_start = y_grid_start + 12 + ev_idx * (card_height + card_spacing)
        if y_start + card_height > height - 4:
            break
            
        bg_col, text_col = get_event_colors(ev["summary"])
        
        # Draw Event Card Background & Border (thick black border)
        draw.rectangle(
            [(col_x_positions[0] + 10, y_start), (col_x_positions[0] + col_widths[0] - 10, y_start + card_height)],
            fill=bg_col,
            outline=COLOR_TEXT,
            width=2
        )
        
        # Format time range
        start_str = ev["start"].strftime("%I:%M %p").lstrip("0")
        end_str = ev["end"].strftime("%I:%M %p").lstrip("0")
        time_str = f"{start_str} - {end_str}"
        
        # Time label at top-left
        draw_sharp_text(img, (col_x_positions[0] + 24, y_start + 8), time_str, font_event_time_today, text_col)
        
        # Split prefix
        person, title = split_summary_by_person(ev["summary"])
        if person:
            person_lbl = f"[{person.upper()}]"
            lbl_w = draw.textlength(person_lbl, font=font_event_person_today)
            draw_sharp_text(img, (col_x_positions[0] + col_widths[0] - 24 - lbl_w, y_start + 7), person_lbl, font_event_person_today, text_col)
            
        # Wrap and draw title (plenty of horizontal space: 480 - 48 = 432px!)
        padded_width = col_widths[0] - 48
        wrapped_lines = wrap_text(title, font_event_title_today, padded_width)
        
        curr_y = y_start + 36
        for line in wrapped_lines:
            if curr_y + 28 > y_start + card_height - 2:
                break
            draw_sharp_text(img, (col_x_positions[0] + 24, curr_y), line, font_event_title_today, text_col)
            curr_y += 28
            
    # 5. Draw Future Days Column (Right Column, split vertically for Tomorrow and Day-After-Tomorrow)
    y_cursor = y_grid_start
    future_days = week_dates[1:]
    
    # Heights: divide the column vertically (approx 220px each)
    segment_height = (height - y_grid_start) // 2
    
    for f_idx, day_date in enumerate(future_days):
        y_seg_start = y_cursor + f_idx * segment_height
        
        # Draw sub-header divider for the second segment
        if f_idx > 0:
            draw.line([(col_x_positions[1], y_seg_start), (width, y_seg_start)], fill=COLOR_GRID, width=1)
            
        # Draw sub-header day name
        day_name = RU_DAYS_FULL[day_date.weekday()]
        day_date_str = f"{day_date.day} {RU_MONTHS_GENITIVE[day_date.month].capitalize()}"
        sub_hdr_text = f"{day_name} • {day_date_str}"
        draw_sharp_text(img, (col_x_positions[1] + 12, y_seg_start + 8), sub_hdr_text, font_event_person_other, COLOR_TEXT)
        
        # Fetch events for this day
        day_events = sorted(events_by_date[day_date], key=lambda e: e["start"])
        
        item_height = 62  # Reclaimed space allows larger list item height
        item_spacing = 10
        for ev_idx, ev in enumerate(day_events):
            y_item_start = y_seg_start + 32 + ev_idx * (item_height + item_spacing)
            
            # Check segment overflow
            if y_item_start + item_height > y_seg_start + segment_height - 2:
                break
                
            accent_col, text_col = get_event_colors_non_today(ev["summary"])
            
            # Left accent stripe
            draw.rectangle(
                [(col_x_positions[1] + 12, y_item_start + 3), (col_x_positions[1] + 17, y_item_start + item_height - 3)],
                fill=accent_col
            )
            
            # Start time
            start_str = ev["start"].strftime("%I:%M %p").lstrip("0")
            draw_sharp_text(img, (col_x_positions[1] + 26, y_item_start + 2), start_str, font_event_time_other, accent_col)
            
            # Split summary
            person, title = split_summary_by_person(ev["summary"])
            full_display_str = f"[{person}] {title}" if person else title
            
            # Wrap and draw title
            padded_width = col_widths[1] - 38
            wrapped_lines = wrap_text(full_display_str, font_event_title_other, padded_width)
            
            curr_y = y_item_start + 20
            for line in wrapped_lines:
                if curr_y + 18 > y_item_start + item_height:
                    break
                draw_sharp_text(img, (col_x_positions[1] + 26, curr_y), line, font_event_title_other, text_col)
                curr_y += 18
                
    return img
