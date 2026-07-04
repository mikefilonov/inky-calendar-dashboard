import datetime
import logging
from PIL import Image, ImageDraw

from renderer_utils import (
    load_crisp_font,
    draw_sharp_text,
    extract_unique_people,
    split_summary_by_person,
    RU_DAYS_CAPITALIZED,
    format_ru_date_grid,
    get_person_from_summary
)

logger = logging.getLogger(__name__)

# Grid-specific color palettes (Blue, Green, Red, Yellow with White/Black text)
COLOR_PALETTE = [
    ((0, 0, 255), (255, 255, 255)),   # Pure Blue, White text
    ((0, 255, 0), (255, 255, 255)),   # Pure Green, White text
    ((255, 0, 0), (255, 255, 255)),   # Pure Red, White text
    ((255, 255, 0), (0, 0, 0)),       # Pure Yellow, Black text
]
DEFAULT_COLOR = ((255, 255, 0), (0, 0, 0)) # Pure Yellow, Black text

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

def draw_grid_layout(resolution, events, today_date, person_colors=None, now=None):
    """
    Renders the 2-Column grid layout (3-day view) from the parsed events list.
    `events` should be a list of events with `start` and `end` as datetime objects.
    `today_date` should be a datetime.date object.
    """
    if person_colors is None:
        person_colors = {}
    if now is None:
        now = datetime.datetime.now(datetime.timezone.utc)
        
    width, height = resolution
    img = Image.new("RGB", (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    
    # Core Colors (pure black/white for high-contrast e-ink, no grays)
    COLOR_GRID = (0, 0, 0)
    COLOR_TEXT = (0, 0, 0)
    COLOR_HEADER_BG = (255, 255, 255)
    
    # 1. Determine Rolling 3-Day window
    week_dates = [today_date + datetime.timedelta(days=i) for i in range(3)]
    
    unique_people = list(person_colors.keys())
    
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
    
    # Draw Borders (using soft COLOR_GRID)
    draw.line([(0, y_day_header), (width, y_day_header)], fill=COLOR_GRID, width=1)
    draw.line([(0, y_grid_start), (width, y_grid_start)], fill=COLOR_GRID, width=1)
    draw.line([(0, height - 1), (width, height - 1)], fill=COLOR_GRID, width=1)
    
    # Draw Left Column Header (Today) as a clean red pill tag
    today_lbl = f" {RU_DAYS_CAPITALIZED[today_date.weekday()]} {today_date.day} {format_ru_date_grid(today_date).split(' ')[1]} ".upper()
    text_w = draw.textlength(today_lbl, font=font_day_header)
    pill_w = text_w + 16
    pill_x0 = col_x_positions[0] + (col_widths[0] - pill_w) // 2
    pill_x1 = pill_x0 + pill_w
    pill_y0 = y_day_header + 4
    pill_y1 = y_day_header + y_day_header_h - 4
    draw.rounded_rectangle([(pill_x0, pill_y0), (pill_x1, pill_y1)], radius=6, fill=(200, 30, 30))
    draw_sharp_text(img, (pill_x0 + 8, y_day_header + 5), today_lbl, font_day_header, (255, 255, 255))
    
    # Draw Right Column Header (Future Days)
    future_lbl = "ПРЕДСТОЯЩИЕ ДНИ"
    text_w = draw.textlength(future_lbl, font=font_day_header)
    draw_sharp_text(img, (col_x_positions[1] + (col_widths[1] - text_w) // 2, y_day_header + 6), future_lbl, font_day_header, COLOR_TEXT)
    
    # Vertical divider line separating the two main columns (using soft COLOR_GRID)
    draw.line([(col_x_positions[1], y_day_header), (col_x_positions[1], height)], fill=COLOR_GRID, width=1)
    
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
            size_title, size_person = 26, 16
            size_start_time, size_end_time = 18, 12
            time_y_offset = 6
            person_y_offset = 7
            title_start_y = 36
            line_height = 28
        elif card_height >= 75:
            size_title, size_person = 20, 14
            size_start_time, size_end_time = 16, 11
            time_y_offset = 5
            person_y_offset = 5
            title_start_y = 28
            line_height = 22
        elif card_height >= 52:
            size_title, size_person = 16, 12
            size_start_time, size_end_time = 13, 9
            time_y_offset = 3
            person_y_offset = 3
            title_start_y = 20
            line_height = 18
        else:
            size_title, size_person = 13, 10
            size_start_time, size_end_time = 11, 8
            time_y_offset = 1
            person_y_offset = 2
            title_start_y = 14
            line_height = 13

        font_event_start_today = load_crisp_font(size_start_time, bold=True)
        font_event_end_today = load_crisp_font(size_end_time, bold=False)
        font_event_person_today = load_crisp_font(size_person, bold=True)
        font_event_title_today = load_crisp_font(size_title, bold=False)

        # Determine event status
        is_soon = False
        if not ev["all_day"] and now is not None:
            ev_start = ev["start"]
            ev_start_utc = ev_start.astimezone(datetime.timezone.utc) if ev_start.tzinfo else ev_start.replace(tzinfo=datetime.timezone.utc)
            now_utc = now.astimezone(datetime.timezone.utc) if now.tzinfo else now.replace(tzinfo=datetime.timezone.utc)
            time_diff = (ev_start_utc - now_utc).total_seconds()
            is_soon = (0 <= time_diff <= 3600)
            
        person = get_person_from_summary(ev["summary"], unique_people)
        if person:
            person_bg, person_fg = person_colors.get(person, DEFAULT_COLOR)
        else:
            person_bg, person_fg = DEFAULT_COLOR
            
        if is_soon:
            # Filled Card
            bg_col = person_bg
            outline_col = person_bg
            text_col = person_fg
            
            # Draw Rounded Event Card
            draw.rounded_rectangle(
                [(col_x_positions[0] + 10, y_start), (col_x_positions[0] + col_widths[0] - 10, y_start + card_height)],
                radius=6,
                fill=bg_col,
                outline=outline_col,
                width=2
            )
        else:
            # Option 1: 1px black border + rounded color bar on the left (pure white card background)
            bg_col = (255, 255, 255)
            text_col = COLOR_TEXT
            
            draw.rounded_rectangle(
                [(col_x_positions[0] + 10, y_start), (col_x_positions[0] + col_widths[0] - 10, y_start + card_height)],
                radius=6,
                fill=bg_col,
                outline=(0, 0, 0),
                width=1
            )
            draw.rounded_rectangle(
                [(col_x_positions[0] + 12, y_start + 2), (col_x_positions[0] + 20, y_start + card_height - 2)],
                radius=3,
                fill=person_bg
            )
        
        # Format time range
        start_str = ev["start"].strftime("%I:%M %p").lstrip("0")
        end_str = ev["end"].strftime("%I:%M %p").lstrip("0")
        
        # Time label at top-left
        start_x = col_x_positions[0] + 24
        start_y = y_start + time_y_offset
        draw_sharp_text(img, (start_x, start_y), start_str, font_event_start_today, text_col)
        
        # Draw end time next to it in smaller font
        start_w = draw.textlength(start_str, font=font_event_start_today)
        draw_sharp_text(img, (start_x + start_w + 5, start_y + (size_start_time - size_end_time) // 2), f"- {end_str}", font_event_end_today, text_col)
        
        # Split prefix
        person, title = split_summary_by_person(ev["summary"], unique_people)
        if person:
            # Draw solid rounded tag instead of plain text brackets
            person_lbl = person.upper()
            lbl_w = draw.textlength(person_lbl, font=font_event_person_today)
            tag_h = size_person + 4
            tag_x1 = col_x_positions[0] + col_widths[0] - 24
            tag_x0 = tag_x1 - lbl_w - 10
            tag_y0 = y_start + person_y_offset - 2
            tag_y1 = tag_y0 + tag_h
            
            tag_bg = person_bg
            tag_fg = person_fg
            
            draw.rounded_rectangle([(tag_x0, tag_y0), (tag_x1, tag_y1)], radius=4, fill=tag_bg)
            draw_sharp_text(img, (tag_x0 + 5, tag_y0 + 2), person_lbl, font_event_person_today, tag_fg)
            
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

            font_time = load_crisp_font(font_size, bold=False)
            font_title = load_crisp_font(font_size, bold=True)
            font_tag = load_crisp_font(font_size - 1, bold=True)
            
            # Format display string
            start_str = ev["start"].strftime("%I:%M %p").lstrip("0")
            person, title = split_summary_by_person(ev["summary"], unique_people)
            
            # Centered text vertical calculation
            bbox = draw.textbbox((0, 0), "H0", font=font_time)
            text_h = bbox[3] - bbox[1]
            text_y = y_item_start + (item_height - text_h) // 2 - bbox[1]
            
            # 1. Draw start time
            x_cursor = col_x_positions[1] + 12
            draw_sharp_text(img, (x_cursor, text_y), start_str, font_time, COLOR_TEXT)
            x_cursor += draw.textlength(start_str, font=font_time) + 6
            
            # 2. Draw Pill Tag (if person exists)
            if person:
                bg_col, fg_col = person_colors.get(person, DEFAULT_COLOR)
                tag_lbl = person.upper()
                tag_text_w = draw.textlength(tag_lbl, font=font_tag)
                tag_w = tag_text_w + 8
                tag_h = font_size + 2
                
                tx0 = x_cursor
                tx1 = tx0 + tag_w
                ty0 = text_y - 1
                ty1 = ty0 + tag_h
                
                draw.rounded_rectangle([(tx0, ty0), (tx1, ty1)], radius=3, fill=bg_col)
                draw_sharp_text(img, (tx0 + 4, ty0 + 1), tag_lbl, font_tag, fg_col)
                x_cursor += tag_w + 6
                
            # 3. Draw Event Title (truncated to fit)
            max_w = width - 12 - x_cursor
            title_text = title
            title_w = draw.textlength(title_text, font=font_title)
            if title_w > max_w:
                while len(title_text) > 3 and draw.textlength(title_text + "...", font=font_title) > max_w:
                    title_text = title_text[:-1]
                title_text = title_text + "..."
                
            draw_sharp_text(img, (x_cursor, text_y), title_text, font_title, COLOR_TEXT)
                
    return img
