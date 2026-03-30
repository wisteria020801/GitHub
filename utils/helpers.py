import re
import time
import functools
from datetime import datetime, timedelta
from typing import Tuple, Optional, Callable, Any


def clean_text(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def extract_github_info(url: str) -> Tuple[Optional[str], Optional[str]]:
    pattern = r'github\.com/([^/]+)/([^/]+)/?'
    match = re.search(pattern, url)
    if match:
        return match.group(1), match.group(2)
    return None, None


def format_number(num: int) -> str:
    if num >= 1_000_000:
        return f"{num / 1_000_000:.1f}M"
    elif num >= 1_000:
        return f"{num / 1_000:.1f}K"
    return str(num)


def get_date_range(days: int = 7) -> Tuple[str, str]:
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    return start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")


def get_github_search_date(days: int = 7) -> str:
    date = datetime.now() - timedelta(days=days)
    return date.strftime("%Y-%m-%d")


def retry_on_failure(
    max_retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,)
) -> Callable:
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            current_delay = delay

            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        time.sleep(current_delay)
                        current_delay *= backoff

            raise last_exception
        return wrapper
    return decorator


def truncate_text(text: str, max_length: int = 500) -> str:
    if not text:
        return ""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."


def parse_github_date(date_str: str) -> Optional[datetime]:
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        try:
            return datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            return None
