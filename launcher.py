"""
AWARE Keyboard Viewer - Standalone Launcher

This is the main entry point for the PyInstaller-bundled executable.
It starts the Flask server on a free local port and opens the default browser.
"""

import os
import sys
import socket
import threading
import time
import webbrowser
import signal

def get_free_port():
    """Find a free port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]

def open_browser(url, retries=10, delay=0.5):
    """Open the browser once the server is ready."""
    for i in range(retries):
        try:
            with socket.create_connection(('127.0.0.1', int(url.split(':')[-1].rstrip('/'))), timeout=1):
                webbrowser.open(url)
                return
        except (ConnectionRefusedError, OSError):
            time.sleep(delay)
    # Last resort: open anyway
    webbrowser.open(url)

def main():
    # Ensure src/ is on the Python path so app.py can find its sibling modules
    if getattr(sys, 'frozen', False):
        bundle_dir = sys._MEIPASS  # type: ignore[attr-defined]
    else:
        bundle_dir = os.path.dirname(os.path.abspath(__file__))

    src_dir = os.path.join(bundle_dir, 'src')
    if src_dir not in sys.path:
        sys.path.insert(0, src_dir)

    # Import the Flask app (after path setup)
    # app.py uses bare imports (from database import ...) so src/ must be on sys.path
    from app import app as flask_app  # noqa: E402

    port = int(os.environ.get('PORT', 0)) or get_free_port()
    url = f'http://127.0.0.1:{port}'

    print(f'Starting AWARE Keyboard Viewer at {url}')
    print('Press Ctrl+C to stop the server.\n')

    # Open browser in a background thread
    threading.Thread(target=open_browser, args=(url,), daemon=True).start()

    # Run Flask (production-like, no reloader)
    try:
        flask_app.run(host='127.0.0.1', port=port, debug=False, use_reloader=False)
    except KeyboardInterrupt:
        print('\nShutting down...')
        sys.exit(0)

if __name__ == '__main__':
    main()
