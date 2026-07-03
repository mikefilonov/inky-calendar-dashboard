import datetime
import logging
from PIL import Image

from list_layout import draw_list_layout
from grid_layout import draw_grid_layout

logger = logging.getLogger(__name__)

def render_layout(spec: dict, resolution: tuple, renderer_type: str = "list") -> Image.Image:
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
    
    if renderer_type == "grid":
        return draw_grid_layout(resolution, events_list, today_date)
    else:
        return draw_list_layout(resolution, events_list, today_date)
