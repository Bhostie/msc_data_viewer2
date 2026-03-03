# Copilot Instructions — AWARE Keyboard Viewer

## Architecture Overview

This is a **Flask web app** (`src/app.py`) for viewing, segmenting, and cleaning AWARE Framework keyboard keystroke logs stored in SQLite databases. There is also an independent **typing-performance-analyzer** subproject under `typing-performance-analyzer/` with its own dependencies and test suite — treat it as a separate codebase.

### Core Data Flow
1. User uploads an AWARE SQLite `.db` file → saved to `data/uploads/`
2. `database.py` auto-detects the keyboard table and column mapping (`guess_columns`)
3. Data is loaded into a Pandas DataFrame, then `segmentation.py` groups raw keystrokes into meaningful text segments (messages)
4. Segments are cached as JSON in `data/cache/` (keyed by db path + mtime hash)
5. Users mark segments for deletion → session state tracks `deleted_segment_ids`
6. Filtered database exported to `data/filtered/` with deleted segments removed

### Key Modules (`src/`)
- **`app.py`** — Flask routes, session management, template rendering. All state (settings, mapping, deletions) lives in Flask `session`. The main `index()` route re-runs segmentation on every page load.
- **`segmentation.py`** — The `Segmenter` class implements a multi-method segmentation algorithm. See `algorithm.pseudocode.md` for the full algorithm design.
- **`database.py`** — SQLite introspection helpers (table detection, column guessing, PK detection).
- **`utils.py`** — Timestamp conversion (`ms_to_local_str` with Europe/Istanbul TZ), segment cache I/O.

> **`old_code.py`** is a legacy Streamlit version — ignore it entirely. Do not read, modify, or reference it.

### Frontend
- **Jinja2 templates** (`templates/base.html`, `templates/index.html`) with Bootstrap 5.3 (CDN)
- **Vanilla JS** (`static/js/app.js`) — AJAX calls for keystroke detail loading (`/get_keystrokes/<idx>`) and batch deletion

### Typing Performance Analysis on Deleted Segments
When the user downloads/saves a filtered DB, `analyzer.py` automatically runs `typing-performance-analyzer` on every **deleted** segment's raw keystrokes before they are removed. This preserves typing metrics (WPM, KSPS, KSPC, duration, corrections/revisions) for research even though the actual message text is deleted.

- **`analyzer.py`** — Bridge module. Transforms raw DB rows → analyzer's expected `[{_id, timestamp, before_text, current_text, ...}]` format via `_rows_to_analyzer_sequence()`, then calls `TypingSpeedCalculator`, `ErrorRateCalculator`, and optionally `TypingPathCalculator`.
- Results saved to `data/analysis/typing-analysis.json` and downloadable via `/download_analysis`.
- `phunspell`/`nltk` are optional — if missing, typing path analysis (correction vs revision detection) is skipped gracefully; speed and error-rate metrics still work.

## Segmentation Algorithm (Critical Domain Logic)

The segmentation algorithm in `Segmenter.segment()` uses 4 prioritized methods to detect message boundaries:

1. **`before_text` emptiness** — Primary signal for AWARE data. Empty `before_text` = text field was cleared (message sent). Distinguishes sends from deletions via `_is_deletion_pattern()`.
2. **Text jump detection** — Gap > 30s + completely unrelated text content.
3. **Text discontinuity** — `before_text` doesn't match expected continuation from previous `current_text`.
4. **Gap-based fallback** — Time gap > `gap_seconds` (default 10s). Used when `before_text` column is absent.

**Important edge cases handled:** search box editing (submit but keep text), placeholder text detection (`"Message"`, `"Search…"`), long text mid-edit similarity (>100 chars, checks first/last 50 chars), bracket-wrapped text `[text]` from AWARE logger.

When modifying segmentation logic, always update `algorithm.pseudocode.md` to stay in sync.

## Development

### Setup & Run
```bash
./run.sh                    # Creates .venv, installs deps, runs Flask app
# OR manually:
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cd src && python app.py     # Runs on http://127.0.0.1:5000
```

### Testing
```bash
cd src && python -m pytest ../tests/ -v
```
Tests use `conftest.py` which adds `src/` to `sys.path`. The `mapping` fixture provides a standard AWARE column mapping. Test files import directly from `segmentation` (not `src.segmentation`).

### Deployment (planned)
Not yet deployed. When ready, the simplest options are:
- **Docker** — single `Dockerfile` with `gunicorn` serving the Flask app.
- **PythonAnywhere / Render / Railway** — free-tier hosts that accept Flask apps with minimal config.

The app uses file-system storage (`data/` directories) and Flask sessions — no external DB or message queue needed, so any single-container host works.

### typing-performance-analyzer (Subproject)
Separate Python project with its own `requirements.txt` (nltk, phunspell, coverage). Run independently:
```bash
cd typing-performance-analyzer && python -m performance_analyzer.main
# Tests: coverage run -m unittest discover -s test
```

## Conventions & Patterns

- **Column mapping pattern**: The app never hardcodes column names. All DB access goes through a `mapping` dict (`{"timestamp": "actual_col", "key_code": "actual_col", ...}`) populated by `guess_columns()` and overridable by user in the sidebar.
- **Session-based state**: All user state (settings, deletions, db path) stored in Flask `session`. Segment data is too large for sessions → cached to JSON files in `data/cache/`.
- **Timestamps**: Always in milliseconds (Unix epoch). Convert with `ms_to_local_str()`. Hardcoded to `Europe/Istanbul` timezone.
- **Text cleaning**: Use `Segmenter._clean_text()` for any text comparison — it strips brackets, handles NaN/None, and filters placeholders.
- **SQL safety**: Table/column names are quoted with double quotes in SQL. User inputs use parameterized queries (`?` placeholders).
