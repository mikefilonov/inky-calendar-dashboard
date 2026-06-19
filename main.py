import os
import sys
import json
import logging
import datetime
from PIL import Image
import pytz

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("inky-calendar")

# Add current dir to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import calendar_renderer

def load_config():
    config_path = os.path.join(os.path.dirname(__file__), "config.json")
    if not os.path.exists(config_path):
        logger.warning(f"Config file not found at {config_path}. Using config.json.example defaults.")
        config_path = os.path.join(os.path.dirname(__file__), "config.json.example")
        
    with open(config_path, "r") as f:
        return json.load(f)

def update_display(img, dry_run):
    import image_logger
    image_logger.save_and_rotate_image(img, os.path.dirname(__file__))

    if dry_run:
        print("Dry run enabled. Calendar preview saved.")
        return

    try:
        from inky.auto import auto
        logger.info("Initializing Inky display...")
        inky_display = auto(ask_user=False, verbose=True)
        
        # Verify resolution
        display_w, display_h = inky_display.resolution
        img_w, img_h = img.size
        
        if (display_w, display_h) != (img_w, img_h):
            logger.info(f"Resizing rendered image from {img.size} to display resolution {inky_display.resolution}...")
            img = img.resize(inky_display.resolution, Image.Resampling.LANCZOS)
            
        inky_display.set_image(img, saturation=0.5)
        logger.info("Refreshing Inky display...")
        inky_display.show()
        logger.info("Display update complete!")
        
    except ImportError:
        logger.warning("The 'inky' library could not be imported (expected on non-Raspberry Pi environments).")
        print(f"Library fallback: Calendar preview saved to {output_path}")
    except Exception as e:
        logger.error(f"Failed to update Inky display: {e}")
        print(f"Error occurred. Rendered image saved as fallback to {output_path}")

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
    
    # Calculate dates based on selected renderer (both now use rolling 3 days)
    now = datetime.datetime.now(tz)
    today_date = now.date()
    start_date = today_date
    end_date = today_date + datetime.timedelta(days=2)
    
    # Fetch events
    events = calendar_renderer.fetch_and_parse_events(calendar_url, tz, start_date, end_date)
    
    # Calculate state hash for change detection (date + all events)
    state_str = f"Date: {today_date}\nRenderer: {renderer_type}\n"
    for ev in events:
        state_str += f"{ev['summary']}|{ev['start']}|{ev['end']}|{ev['all_day']}\n"
    import hashlib
    current_hash = hashlib.sha256(state_str.encode('utf-8')).hexdigest()
    
    hash_file_path = os.path.join(os.path.dirname(__file__), ".calendar_hash")
    
    previous_hash = None
    if os.path.exists(hash_file_path):
        try:
            with open(hash_file_path, "r") as f:
                previous_hash = f.read().strip()
        except Exception as e:
            logger.warning(f"Failed to read previous hash: {e}")
            
    force_update = "--force" in sys.argv
    
    # Draw calendar
    if renderer_type == "grid":
        import grid_renderer
        img = grid_renderer.draw_calendar(resolution, events, tz)
    else:
        img = calendar_renderer.draw_calendar(resolution, events, tz)
    
    if not dry_run and not force_update and previous_hash == current_hash:
        logger.info("No changes in calendar events or current date. Skipping Inky display refresh to preserve screen life.")
        # Still update the local calendar.png copy
        try:
            output_path = os.path.join(os.path.dirname(__file__), "calendar.png")
            img.save(output_path)
        except Exception:
            pass
        return
    
    # Send to display or file
    update_display(img, dry_run)
    
    # Save the new hash after successful update
    if not dry_run:
        try:
            with open(hash_file_path, "w") as f:
                f.write(current_hash)
            logger.info("Saved new state hash.")
        except Exception as e:
            logger.warning(f"Failed to save new hash: {e}")

if __name__ == "__main__":
    main()
