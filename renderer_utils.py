import os
import logging
from PIL import Image, ImageDraw, ImageFont

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

def split_summary_by_person(summary, unique_people):
    """Splits summary into (person, event_title)"""
    person = get_person_from_summary(summary, unique_people)
    if person:
        prefix_len = len(person) + (2 if summary.startswith(f"{person}:") else 1)
        return person, summary[prefix_len:].strip()
    return "", summary

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

RU_DAYS_CAPITALIZED = {
    0: "Понедельник",
    1: "Вторник",
    2: "Среда",
    3: "Четверг",
    4: "Пятница",
    5: "Суббота",
    6: "Воскресенье"
}

RU_MONTHS = {
    1: "января", 2: "февраля", 3: "марта", 4: "апреля", 5: "мая", 6: "июня",
    7: "июля", 8: "августа", 9: "сентября", 10: "октября", 11: "ноября", 12: "декабря"
}

def format_ru_date_list(dt):
    return f"{dt.day} {RU_MONTHS[dt.month]}"

def format_ru_date_grid(dt):
    return f"{dt.day} {RU_MONTHS[dt.month].capitalize()}"

def assign_colors_to_people(unique_people, config_colors):
    """
    Assigns colors to names from config_colors (if specified) or dynamic defaults.
    Ensures defined names always use the same color, and unknown names use unused palette colors.
    Returns:
        (dict, dict): (assigned_list_colors, assigned_grid_colors)
        - list: mapping of person -> RGB tuple
        - grid: mapping of person -> (bg_RGB_tuple, fg_RGB_tuple)
    """
    standard_palette = ["blue", "red", "green", "yellow", "orange"]
    
    grid_colors = {
        "blue": ((0, 0, 255), (255, 255, 255)),
        "red": ((255, 0, 0), (255, 255, 255)),
        "green": ((0, 255, 0), (255, 255, 255)),
        "yellow": ((255, 255, 0), (0, 0, 0)),
        "orange": ((255, 165, 0), (255, 255, 255)),
        "black": ((0, 0, 0), (255, 255, 255)),
        "white": ((255, 255, 255), (0, 0, 0))
    }
    
    list_colors = {
        "blue": (0, 0, 230),
        "red": (230, 30, 30),
        "green": (0, 150, 0),
        "yellow": (200, 160, 0),
        "orange": (230, 100, 0),
        "black": (0, 0, 0),
        "white": (180, 180, 180)
    }
    
    def parse_color(c):
        if isinstance(c, str):
            c_lower = c.lower()
            if c_lower in grid_colors:
                return c_lower, grid_colors[c_lower][0], grid_colors[c_lower][1], list_colors[c_lower]
            if c.startswith("#"):
                try:
                    r = int(c[1:3], 16)
                    g = int(c[3:5], 16)
                    b = int(c[5:7], 16)
                    rgb = (r, g, b)
                    lum = 0.299 * r + 0.587 * g + 0.114 * b
                    text_color = (0, 0, 0) if lum > 128 else (255, 255, 255)
                    return c, rgb, text_color, rgb
                except Exception:
                    pass
        elif isinstance(c, (list, tuple)) and len(c) == 3:
            rgb = tuple(c)
            lum = 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]
            text_color = (0, 0, 0) if lum > 128 else (255, 255, 255)
            return tuple(c), rgb, text_color, rgb
        return "red", grid_colors["red"][0], grid_colors["red"][1], list_colors["red"]
        
    assigned_list_colors = {}
    assigned_grid_colors = {}
    
    used_palette_names = set()
    
    # 1. Assign configuration colors first
    if config_colors:
        for person in unique_people:
            if person in config_colors:
                color_val = config_colors[person]
                name_or_val, grid_bg, grid_fg, list_c = parse_color(color_val)
                assigned_grid_colors[person] = (grid_bg, grid_fg)
                assigned_list_colors[person] = list_c
                if isinstance(name_or_val, str) and name_or_val in standard_palette:
                    used_palette_names.add(name_or_val)
                    
    # 2. Assign unused standard palette colors to the rest
    unused_palette_names = [c for c in standard_palette if c not in used_palette_names]
    
    unused_idx = 0
    for person in unique_people:
        if person not in assigned_grid_colors:
            if unused_idx < len(unused_palette_names):
                color_name = unused_palette_names[unused_idx]
                unused_idx += 1
            else:
                color_name = standard_palette[unused_idx % len(standard_palette)]
                unused_idx += 1
                
            assigned_grid_colors[person] = grid_colors[color_name]
            assigned_list_colors[person] = list_colors[color_name]
            
    return assigned_list_colors, assigned_grid_colors
