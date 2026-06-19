import os
import glob
import datetime
import logging
from PIL import Image

logger = logging.getLogger("inky-calendar.image_logger")

HISTORY_DIR_NAME = "history"
MAX_HISTORY_FILES = 100

def save_and_rotate_image(img, base_dir):
    """
    Saves the rendered image with a timestamp into a 'history' subfolder.
    Maintains a maximum of 100 images, deleting the oldest ones.
    Also updates a static 'calendar.png' in the root directory for easy fetching.
    """
    # 1. Create history directory if it doesn't exist
    history_dir = os.path.join(base_dir, HISTORY_DIR_NAME)
    if not os.path.exists(history_dir):
        try:
            os.makedirs(history_dir)
            logger.info(f"Created history directory at {history_dir}")
        except Exception as e:
            logger.error(f"Failed to create history directory: {e}")
            return

    # 2. Save timestamped copy in history folder
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    history_filename = f"calendar_{timestamp}.png"
    history_path = os.path.join(history_dir, history_filename)
    
    try:
        img.save(history_path)
        logger.info(f"Saved historical image to {history_path}")
    except Exception as e:
        logger.error(f"Failed to save historical image: {e}")

    # 3. Save a static 'calendar.png' copy in the root folder for easy fetching
    root_path = os.path.join(base_dir, "calendar.png")
    try:
        img.save(root_path)
        logger.info(f"Updated static root copy at {root_path}")
    except Exception as e:
        logger.error(f"Failed to update root image copy: {e}")

    # 4. Clean up old files to keep only the last 100
    try:
        # Find all calendar_*.png files in the history folder
        search_pattern = os.path.join(history_dir, "calendar_*.png")
        history_files = sorted(glob.glob(search_pattern))
        
        if len(history_files) > MAX_HISTORY_FILES:
            files_to_delete = history_files[:-MAX_HISTORY_FILES]
            for file_path in files_to_delete:
                os.remove(file_path)
                logger.info(f"Deleted old historical log: {file_path}")
    except Exception as e:
        logger.error(f"Failed to rotate historical files: {e}")
