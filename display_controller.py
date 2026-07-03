import os
import logging
from PIL import Image
import image_logger

logger = logging.getLogger(__name__)

def update_display(img: Image.Image, dry_run: bool):
    """
    Updates the physical Inky display with the provided image (after resizing if needed).
    Also writes/rotates backup copies via `image_logger`.
    """
    # 1. Save local backup and rotation copies
    base_dir = os.path.dirname(os.path.abspath(__file__))
    image_logger.save_and_rotate_image(img, base_dir)

    if dry_run:
        logger.info("Dry run enabled. Calendar preview saved to local history.")
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
        output_path = os.path.join(base_dir, "calendar.png")
        print(f"Library fallback: Calendar preview saved to {output_path}")
    except Exception as e:
        logger.error(f"Failed to update Inky display: {e}")
        output_path = os.path.join(base_dir, "calendar.png")
        print(f"Error occurred. Rendered image saved as fallback to {output_path}")
