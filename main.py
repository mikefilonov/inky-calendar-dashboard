import os
import sys
import json
import logging
import datetime
import pytz
import hashlib

# Add current dir to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import calendar_fetcher
import ics_parser
import layout_renderer
import display_controller

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("inky-calendar")

def load_config():
    config_path = os.path.join(os.path.dirname(__file__), "config.json")
    if not os.path.exists(config_path):
        logger.warning(f"Config file not found at {config_path}. Using config.json.example defaults.")
        config_path = os.path.join(os.path.dirname(__file__), "config.json.example")
        
    with open(config_path, "r") as f:
        return json.load(f)

def main():
    try:
        config = load_config()
    except Exception as e:
        logger.critical(f"Failed to load configuration: {e}")
        sys.exit(1)
        
    calendar_url = config.get("calendar_url")
    if not calendar_url:
        logger.error("No calendar_url specified in configuration.")
        sys.exit(1)
        
    timezone_name = config.get("timezone", "America/Los_Angeles")
    try:
        tz = pytz.timezone(timezone_name)
    except Exception as e:
        logger.warning(f"Invalid timezone '{timezone_name}', falling back to UTC. Error: {e}")
        tz = pytz.utc
        
    resolution = tuple(config.get("resolution", [800, 480]))
    dry_run = config.get("dry_run", True)
    renderer_type = config.get("renderer", "list")
    
    # Calculate dates based on selected renderer:
    # list layout displays 5 days (today + next 4 days)
    # grid layout displays 3 days (today + next 2 days)
    now = datetime.datetime.now(tz)
    today_date = now.date()
    start_date = today_date
    
    if renderer_type == "grid":
        end_date = today_date + datetime.timedelta(days=2)
    else:
        end_date = today_date + datetime.timedelta(days=4)
    
    # 1. Fetch raw ICS calendar data
    try:
        ical_data = calendar_fetcher.fetch_ics(calendar_url)
    except Exception as e:
        logger.error(f"Failed to fetch calendar: {e}")
        sys.exit(1)
        
    # 2. Parse ICS to representation spec
    spec = ics_parser.parse_ics_to_spec(ical_data, timezone_name, start_date, end_date)
    spec["current_time"] = now.isoformat()
    
    person_colors = config.get("person_colors", {})
    
    # 3. Render spec to PIL Image
    img = layout_renderer.render_layout(spec, resolution, renderer_type, person_colors)
    
    # 4. Calculate state hash based on PIL Image pixels for change detection
    image_bytes = img.tobytes()
    current_hash = hashlib.sha256(image_bytes).hexdigest()
    
    hash_file_path = os.path.join(os.path.dirname(__file__), ".calendar_hash")
    previous_hash = None
    if os.path.exists(hash_file_path):
        try:
            with open(hash_file_path, "r") as f:
                previous_hash = f.read().strip()
        except Exception as e:
            logger.warning(f"Failed to read previous hash: {e}")
            
    force_update = "--force" in sys.argv
    
    # 5. Check if we can skip screen refresh (preserves e-ink life)
    if not dry_run and not force_update and previous_hash == current_hash:
        logger.info("No changes in calendar layout rendering or current date. Skipping Inky display refresh to preserve screen life.")
        # Still update the local calendar.png copy
        try:
            output_path = os.path.join(os.path.dirname(__file__), "calendar.png")
            img.save(output_path)
        except Exception:
            pass
        return
    
    # 6. Update physical display
    display_controller.update_display(img, dry_run)
    
    # 7. Save the new hash after successful update
    if not dry_run:
        try:
            with open(hash_file_path, "w") as f:
                f.write(current_hash)
            logger.info("Saved new state hash.")
        except Exception as e:
            logger.warning(f"Failed to save new hash: {e}")

if __name__ == "__main__":
    main()
