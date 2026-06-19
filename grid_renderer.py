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
    # Sofya/Sofia -> Burgundy/Dark Purple
    if summary.startswith("София") or summary.startswith("Софья"):
        return (50, 15, 45), (255, 255, 255)
    # Misha -> Terracotta/Orange-Brown
    elif summary.startswith("Миша"):
        return (150, 60, 25), (255, 255, 255)
    # Default -> Yellow
    return (240, 195, 30), (0, 0, 0)

def get_event_colors_non_today(summary):
    """Returns (accent_color, text_color) for non-today text layout."""
    # Sofya/Sofia -> Burgundy/Dark Purple
    if summary.startswith("София") or summary.startswith("Софья"):
        return (50, 15, 45), (0, 0, 0)
    # Misha -> Terracotta/Orange-Brown
    elif summary.startswith("Миша"):
        return (150, 60, 25), (0, 0, 0)
    # Default -> Yellow/Mustard
    return (210, 170, 20), (0, 0, 0)

def split_summary_by_person(summary):
    """Splits summary into (person, event_title)"""
    for prefix in ["София:", "Софья:", "Миша:"]:
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
    num_today = len(today_events)
    if num_today > 0:
        card_spacing = 10
        # Total height space available: 436px (from y_grid_start + 12 to height - 4)
        card_height = min(112, (436 - (num_today - 1) * card_spacing) // num_today)
        card_height = max(36, card_height)
    else:
        card_height = 112
        card_spacing = 14

    for ev_idx, ev in enumerate(today_events):
        y_start = y_grid_start + 12 + ev_idx * (card_height + card_spacing)
        if y_start + card_height > height - 2:
            break
            
        # Determine sizes dynamically based on card_height to ensure text fits
        if card_height >= 95:
            size_title, size_time, size_person = 26, 15, 16
            time_y_offset = 8
            person_y_offset = 7
            title_start_y = 36
            line_height = 28
        elif card_height >= 75:
            size_title, size_time, size_person = 20, 13, 14
            time_y_offset = 6
            person_y_offset = 5
            title_start_y = 28
            line_height = 22
        elif card_height >= 52:
            size_title, size_time, size_person = 16, 11, 12
            time_y_offset = 4
            person_y_offset = 3
            title_start_y = 20
            line_height = 18
        else:
            size_title, size_time, size_person = 13, 10, 10
            time_y_offset = 2
            person_y_offset = 2
            title_start_y = 14
            line_height = 13

        font_event_time_today = load_crisp_font(size_time, bold=False)
        font_event_person_today = load_crisp_font(size_person, bold=True)
        font_event_title_today = load_crisp_font(size_title, bold=True)

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
        draw_sharp_text(img, (col_x_positions[0] + 24, y_start + time_y_offset), time_str, font_event_time_today, text_col)
        
        # Split prefix
        person, title = split_summary_by_person(ev["summary"])
        if person:
            person_lbl = f"[{person.upper()}]"
            lbl_w = draw.textlength(person_lbl, font=font_event_person_today)
            draw_sharp_text(img, (col_x_positions[0] + col_widths[0] - 24 - lbl_w, y_start + person_y_offset), person_lbl, font_event_person_today, text_col)
            
        # Wrap and draw title
        padded_width = col_widths[0] - 48
        wrapped_lines = wrap_text(title, font_event_title_today, padded_width)
        
        curr_y = y_start + title_start_y
        for line in wrapped_lines:
            if curr_y + line_height > y_start + card_height - 2:
                break
            draw_sharp_text(img, (col_x_positions[0] + 24, curr_y), line, font_event_title_today, text_col)
            curr_y += line_height
            
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
        num_day = len(day_events)
        if num_day > 0:
            item_spacing = 6
            # Total height space available: 192px (from y_seg_start + 32 to y_seg_start + segment_height - 2)
            item_height = min(46, (192 - (num_day - 1) * item_spacing) // num_day)
            item_height = max(26, item_height)
        else:
            item_height = 42
            item_spacing = 6
            
        for ev_idx, ev in enumerate(day_events):
            y_item_start = y_seg_start + 32 + ev_idx * (item_height + item_spacing)
            if y_item_start + item_height > y_seg_start + segment_height - 2:
                break
                
            # Font size mapping based on item_height
            if item_height >= 40:
                font_size = 12
            elif item_height >= 32:
                font_size = 11
            else:
                font_size = 10

            font_event_other = load_crisp_font(font_size, bold=True)
            bg_col, text_col = get_event_colors(ev["summary"])
            
            # Draw rounded pill capsule
            draw.rounded_rectangle(
                [(col_x_positions[1] + 12, y_item_start), (width - 12, y_item_start + item_height)],
                radius=4,
                fill=bg_col
            )
            
            # Format display string: Time first, then Person: Title
            start_str = ev["start"].strftime("%I:%M %p").lstrip("0")
            person, title = split_summary_by_person(ev["summary"])
            display_text = f"{start_str}  {person}: {title}" if person else f"{start_str}  {title}"
            
            # Truncate text if it exceeds horizontal space inside the pill
            max_text_width = width - 12 - 20 - (col_x_positions[1] + 20)  # ~276px
            text_w = draw.textlength(display_text, font=font_event_other)
            if text_w > max_text_width:
                while len(display_text) > 3 and draw.textlength(display_text + "...", font=font_event_other) > max_text_width:
                    display_text = display_text[:-1]
                display_text = display_text + "..."
                
            # Centered text vertical calculation
            bbox = draw.textbbox((0, 0), display_text, font=font_event_other)
            text_h = bbox[3] - bbox[1]
            text_y = y_item_start + (item_height - text_h) // 2 - bbox[1]
            
            draw_sharp_text(img, (col_x_positions[1] + 20, text_y), display_text, font_event_other, text_col)
                
    return img
