import os
import sys
import json
import logging

# Add parent directory to path to allow importing modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from calendar_fetcher import fetch_ics

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_fetcher")

def main():
    config_path = os.path.join(os.path.dirname(__file__), "..", "config.json")
    if not os.path.exists(config_path):
        config_path = os.path.join(os.path.dirname(__file__), "..", "config.json.example")

    with open(config_path, "r") as f:
        config = json.load(f)

    url = config.get("calendar_url")
    if not url:
        logger.error("No calendar_url found in config.json or config.json.example")
        sys.exit(1)

    print(f"Testing calendar fetch from: {url}")
    try:
        data = fetch_ics(url)
        print(f"Success! Fetched {len(data)} bytes of ICS data.")
    except Exception as e:
        print(f"Failed to fetch calendar: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
