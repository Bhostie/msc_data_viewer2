import os
import hashlib
import json
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from flask import session

ISTANBUL_TZ = ZoneInfo("Europe/Istanbul")

def ms_to_local_str(ms: int, tz=ISTANBUL_TZ) -> str:
    """Convert millisecond timestamp to local time string."""
    try:
        dt = datetime.fromtimestamp(ms/1000.0, tz=timezone.utc).astimezone(tz)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        # maybe already in seconds
        try:
            dt = datetime.fromtimestamp(int(ms), tz=timezone.utc).astimezone(tz)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            return str(ms)

def get_cache_key(db_path: str):
    """Generate a cache key for the current database."""
    if not db_path:
        return None
    # Use db path + modification time as key
    try:
        mtime = os.path.getmtime(db_path)
        key_str = f"{db_path}:{mtime}"
        return hashlib.md5(key_str.encode()).hexdigest()
    except Exception:
        return None

def save_segments_cache(segments, cache_folder: str, db_path: str):
    """Save segments to a file instead of session."""
    cache_key = get_cache_key(db_path)
    if not cache_key:
        return
    cache_file = os.path.join(cache_folder, f"{cache_key}.json")
    try:
        with open(cache_file, 'w') as f:
            json.dump(segments, f)
        session['segments_cache_key'] = cache_key
    except Exception as e:
        print(f"Error saving segments cache: {e}")

def load_segments_cache(cache_folder: str):
    """Load segments from file instead of session."""
    cache_key = session.get('segments_cache_key')
    if not cache_key:
        return None
    cache_file = os.path.join(cache_folder, f"{cache_key}.json")
    if not os.path.exists(cache_file):
        return None
    try:
        with open(cache_file, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading segments cache: {e}")
        return None
