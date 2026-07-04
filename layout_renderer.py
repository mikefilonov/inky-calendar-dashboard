import os
import json
import datetime
import logging
import pytz
from PIL import Image

from list_layout import draw_list_layout
from grid_layout import draw_grid_layout
from renderer_utils import assign_colors_to_people, extract_unique_people

logger = logging.getLogger(__name__)

def load_person_colors():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(base_dir, "config.json")
    if not os.path.exists(config_path):
        config_path = os.path.join(base_dir, "config.json.example")
    if os.path.exists(config_path):
        try:
            with open(config_path, "r") as f:
                config = json.load(f)
                return config.get("person_colors", {})
        except Exception:
            pass
    return {}

def render_layout(spec: dict, resolution: tuple, renderer_type: str = "list", person_colors: dict = None) -> Image.Image:
    """
    Parses the intermediate representation spec and renders it using the requested layout style.
    Input spec format:
    {
        "today_date": "YYYY-MM-DD",
        "events": [
            {
                "summary": "Event summary",
                "start": "ISO8601 string",
                "end": "ISO8601 string",
                "all_day": bool
            },
            ...
        ]
    }
    Returns a PIL.Image.Image.
    """
    today_date_str = spec.get("today_date")
    if not today_date_str:
        logger.warning("No today_date provided in spec. Defaulting to current local date.")
        today_date = datetime.date.today()
    else:
        today_date = datetime.date.fromisoformat(today_date_str)

    events_list = []
    for ev in spec.get("events", []):
        try:
            start_dt = datetime.datetime.fromisoformat(ev["start"])
            end_dt = datetime.datetime.fromisoformat(ev["end"])
            events_list.append({
                "summary": ev["summary"],
                "start": start_dt,
                "end": end_dt,
                "all_day": ev.get("all_day", False)
            })
        except Exception as e:
            logger.error(f"Failed to parse event from spec: {ev}. Error: {e}")

    logger.info(f"Rendering spec containing {len(events_list)} events with layout style '{renderer_type}'")

    if person_colors is None:
        person_colors = load_person_colors()

    # Determine "now" time
    current_time_str = spec.get("current_time")
    if current_time_str:
        now = datetime.datetime.fromisoformat(current_time_str)
    else:
        tz = pytz.utc
        try:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            config_path = os.path.join(base_dir, "config.json")
            if not os.path.exists(config_path):
                config_path = os.path.join(base_dir, "config.json.example")
            if os.path.exists(config_path):
                with open(config_path, "r") as f:
                    cfg = json.load(f)
                    tz = pytz.timezone(cfg.get("timezone", "America/Los_Angeles"))
        except Exception:
            pass
        now = datetime.datetime.now(tz)

    unique_people = extract_unique_people(events_list)
    list_colors, grid_colors = assign_colors_to_people(unique_people, person_colors)
    
    if renderer_type == "grid":
        return draw_grid_layout(resolution, events_list, today_date, grid_colors, now)
    else:
        return draw_list_layout(resolution, events_list, today_date, list_colors, now)
