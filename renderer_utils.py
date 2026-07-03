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
