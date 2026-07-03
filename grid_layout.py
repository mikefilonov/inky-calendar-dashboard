import datetime
import logging
from PIL import Image, ImageDraw

from renderer_utils import (
    load_crisp_font,
    draw_sharp_text,
    extract_unique_people,
    split_summary_by_person,
    RU_DAYS_CAPITALIZED,
    format_ru_date_grid
)

logger = logging.getLogger(__name__)

# Grid-specific color palettes (Blue, Green, Red, Yellow with White text)
COLOR_PALETTE = [
    ((0, 0, 255), (255, 255, 255)),   # Pure Blue, White text
    ((0, 255, 0), (255, 255, 255)),   # Pure Green, White text
    ((255, 0, 0), (255, 255, 255)),   # Pure Red, White text
    ((255, 255, 0), (255, 255, 255)), # Pure Yellow, White text
]
DEFAULT_COLOR = ((255, 255, 0), (255, 255, 255)) # Pure Yellow, White text

def get_grid_event_colors(summary, unique_people, person_colors):
    """Returns (bg_color, text_color) based on the event subject dynamically."""
    from renderer_utils import get_person_from_summary
    person = get_person_from_summary(summary, unique_people)
    if person:
        return person_colors.get(person, DEFAULT_COLOR)
    return DEFAULT_COLOR

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

def draw_grid_layout(resolution, events, today_date):
    """
    Renders the 2-Column grid layout (3-day view) from the parsed events list.
    `events` should be a list of events with `start` and `end` as datetime objects.
    `today_date` should be a datetime.date object.
    """
    width, height = resolution
    img = Image.new("RGB", (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    
    # Core Colors
    COLOR_GRID = (180, 180, 180)
    COLOR_TEXT = (0, 0, 0)
    COLOR_HEADER_BG = (225, 225, 225)
    
    # 1. Determine Rolling 3-Day window
    week_dates = [today_date + datetime.timedelta(days=i) for i in range(3)]
    
    # Extract unique people and assign colors dynamically
    unique_people = extract_unique_people(events)
    person_colors = {}
    for idx, person in enumerate(unique_people):
        color_idx = idx % len(COLOR_PALETTE)
        person_colors[person] = COLOR_PALETTE[color_idx]
    
    # Group events by date, ignoring all-day events
    events_by_date = {d: [] for d in week_dates}
    for ev in events:
        if ev["all_day"]:
            continue
        ev_day = ev["start"].date()
        if ev_day in events_by_date:
            events_by_date[ev_day].append(ev)
            
    # Fonts
    font_day_header = load_crisp_font(13, bold=True)
    
    font_event_time_today = load_crisp_font(15, bold=False)
    font_event_person_today = load_crisp_font(16, bold=True)
    font_event_title_today = load_crisp_font(26, bold=True)
    
    font_event_person_other = load_crisp_font(12, bold=True)
    font_event_title_other = load_crisp_font(16, bold=True)
    font_event_time_other = load_crisp_font(12, bold=False)
    
    # 3. Dynamic Column Coordinates for 2 Columns
    # Left: Today (480px), Right: Future days collapsed (308px)
    x_hour_col_w = 12
    col_widths = [480, 308]
    col_x_positions = [x_hour_col_w, x_hour_col_w + 480]
        
    y_day_header = 0
    y_day_header_h = 28
    y_grid_start = y_day_header + y_day_header_h
    
    # Draw Background for Column Headers
    draw.rectangle([(0, y_day_header), (width, y_day_header + y_day_header_h)], fill=COLOR_HEADER_BG)
    
    # Draw Borders
    draw.line([(0, y_day_header), (width, y_day_header)], fill=COLOR_TEXT, width=2)
    draw.line([(0, y_grid_start), (width, y_grid_start)], fill=COLOR_TEXT, width=2)
    draw.line([(0, height - 1), (width, height - 1)], fill=COLOR_TEXT, width=1)
    
    # Draw Left Column Header (Today) with full weekday and month
    today_lbl = f"• {RU_DAYS_CAPITALIZED[today_date.weekday()]} {today_date.day} {format_ru_date_grid(today_date).split(' ')[1]} •"
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
        font_event_title_today = load_crisp_font(size_title, bold=False)

        bg_col, text_col = get_grid_event_colors(ev["summary"], unique_people, person_colors)
        
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
        person, title = split_summary_by_person(ev["summary"], unique_people)
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
        day_name = RU_DAYS_CAPITALIZED[day_date.weekday()]
        day_date_str = format_ru_date_grid(day_date)
        sub_hdr_text = f"{day_name} • {day_date_str}"
        draw_sharp_text(img, (col_x_positions[1] + 12, y_seg_start + 8), sub_hdr_text, font_event_person_other, COLOR_TEXT)
        
        # Fetch events for this day
        day_events = sorted(events_by_date[day_date], key=lambda e: e["start"])
        num_day = len(day_events)
        if num_day > 0:
            item_spacing = 2
            item_height = min(18, (192 - (num_day - 1) * item_spacing) // num_day)
            item_height = max(13, item_height)
        else:
            item_height = 16
            item_spacing = 2
            
        for ev_idx, ev in enumerate(day_events):
            y_item_start = y_seg_start + 32 + ev_idx * (item_height + item_spacing)
            if y_item_start + item_height > y_seg_start + segment_height - 2:
                break
                
            # Font size mapping based on item_height
            if item_height >= 18:
                font_size = 11
            elif item_height >= 15:
                font_size = 10
            else:
                font_size = 9

            font_event_other = load_crisp_font(font_size, bold=True)
            bg_col, _ = get_grid_event_colors(ev["summary"], unique_people, person_colors)
            
            # Format display string: Time first, then Person: Title
            start_str = ev["start"].strftime("%I:%M %p").lstrip("0")
            person, title = split_summary_by_person(ev["summary"], unique_people)
            display_text = f"{start_str}  {person}: {title}" if person else f"{start_str}  {title}"
            
            # Truncate text if it exceeds horizontal space (offset is now 26px from the divider to clear the circle)
            max_text_width = width - 12 - 26 - (col_x_positions[1] + 26)
            text_w = draw.textlength(display_text, font=font_event_other)
            if text_w > max_text_width:
                while len(display_text) > 3 and draw.textlength(display_text + "...", font=font_event_other) > max_text_width:
                    display_text = display_text[:-1]
                display_text = display_text + "..."
                
            # Centered text vertical calculation
            bbox = draw.textbbox((0, 0), display_text, font=font_event_other)
            text_h = bbox[3] - bbox[1]
            text_y = y_item_start + (item_height - text_h) // 2 - bbox[1]

            # Calculate precise center of capital letters/digits to align the circle
            cap_bbox = draw.textbbox((0, 0), "H0", font=font_event_other)
            y_center = int(round(text_y + (cap_bbox[1] + cap_bbox[3]) / 2.0))

            # Draw a colored circle (bullet) on the left of the event, aligned with text
            r = 3
            draw.ellipse(
                [(col_x_positions[1] + 12, y_center - r), (col_x_positions[1] + 12 + 2*r, y_center + r)],
                fill=bg_col
            )
            
            draw_sharp_text(img, (col_x_positions[1] + 24, text_y), display_text, font_event_other, COLOR_TEXT)
                
    return img
