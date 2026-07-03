import urllib.request
import logging

logger = logging.getLogger(__name__)

def fetch_ics(url: str, timeout: int = 15) -> bytes:
    """
    Fetches the raw iCal feed bytes from the given URL.
    Raises an exception if the fetch fails.
    """
    logger.info(f"Fetching calendar events from {url}...")
    headers = {"User-Agent": "Mozilla/5.0 (InkyCalendar)"}
    req = urllib.request.Request(url, headers=headers)
    
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.read()
    except Exception as e:
        logger.error(f"Failed to fetch calendar data from {url}: {e}")
        raise e
