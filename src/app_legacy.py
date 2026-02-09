"""
AWARE Keyboard Viewer - Flask Edition
A web application to view, segment, and clean keyboard keystroke logs from AWARE.

To run this app:
    flask run
    or
    python app.py
"""

import os
import sqlite3
import shutil
import json
import hashlib
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from typing import Dict, List, Optional
import pandas as pd
import numpy as np
from flask import Flask, render_template, request, redirect, url_for, flash, send_file, jsonify, session
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['UPLOAD_FOLDER'] = 'data/uploads'
app.config['FILTERED_FOLDER'] = 'data/filtered'
app.config['CACHE_FOLDER'] = 'data/cache'
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max file size

# Ensure directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['FILTERED_FOLDER'], exist_ok=True)
os.makedirs(app.config['CACHE_FOLDER'], exist_ok=True)

ISTANBUL_TZ = ZoneInfo("Europe/Istanbul")

# -------- Database Helper Functions --------

def list_tables(conn: sqlite3.Connection) -> List[str]:
    """List all tables in the database."""
    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    return [r[0] for r in cur.fetchall()]

def table_columns(conn: sqlite3.Connection, table: str) -> List[str]:
    """Get column names for a table."""
    cur = conn.execute(f"PRAGMA table_info('{table}')")
    return [r[1] for r in cur.fetchall()]

def detect_keyboard_table(conn: sqlite3.Connection) -> Optional[str]:
    """Detect the most likely keyboard data table."""
    candidates = list_tables(conn)
    # Common AWARE plugin names
    preferred = [
        "plugin_keyboard",
        "keyboard",
        "aware_keyboard",
        "applications_keyboard",
    ]
    for p in preferred:
        if p in candidates:
            return p
    # Fallback: pick any table that has likely keyboard columns
    for t in candidates:
        cols = set(table_columns(conn, t))
        if {"timestamp"}.intersection(cols) and {"key_code", "key_character", "text"}.intersection(cols):
            return t
    return candidates[0] if candidates else None

def detect_pk_column(conn: sqlite3.Connection, table: str) -> str:
    """Detect the primary key column."""
    cols = set(table_columns(conn, table))
    for c in ["_id", "id", "ID"]:
        if c in cols:
            return c
    return "rowid"

def guess_columns(cols: List[str]) -> Dict[str, Optional[str]]:
    """Attempt to map standard column names to found columns."""
    lower = {c.lower(): c for c in cols}
    
    def pick(*names):
        for n in names:
            if n in lower:
                return lower[n]
        return None
    
    mapping = {
        "timestamp": pick("timestamp", "time", "ts"),
        "key_code": pick("key_code", "code", "keycode"),
        "key_character": pick("key_character", "character", "char", "key_char", "unicode"),
        "text": pick("text", "current_text", "message", "content", "field_text"),
        "package": pick("package_name", "package", "app", "application", "app_package"),
        "label": pick("label", "field", "hint", "view_label"),
        "action": pick("key_action", "action", "event"),
    }
    return mapping

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

# -------- Cache Helper Functions --------

def get_cache_key():
    """Generate a cache key for the current database."""
    db_path = get_db_path()
    if not db_path:
        return None
    # Use db path + modification time as key
    try:
        mtime = os.path.getmtime(db_path)
        key_str = f"{db_path}:{mtime}"
        return hashlib.md5(key_str.encode()).hexdigest()
    except Exception:
        return None

def save_segments_cache(segments):
    """Save segments to a file instead of session."""
    cache_key = get_cache_key()
    if not cache_key:
        return
    cache_file = os.path.join(app.config['CACHE_FOLDER'], f"{cache_key}.json")
    try:
        with open(cache_file, 'w') as f:
            json.dump(segments, f)
        session['segments_cache_key'] = cache_key
    except Exception as e:
        print(f"Error saving segments cache: {e}")

def load_segments_cache():
    """Load segments from file instead of session."""
    cache_key = session.get('segments_cache_key')
    if not cache_key:
        return None
    cache_file = os.path.join(app.config['CACHE_FOLDER'], f"{cache_key}.json")
    if not os.path.exists(cache_file):
        return None
    try:
        with open(cache_file, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading segments cache: {e}")
        return None

# -------- Segmentation Logic --------

def segment_keystrokes(df: pd.DataFrame, cfg, *,
                       enter_codes={66}, backspace_codes={67},
                       use_ime_actions=True, ime_submit={2,3,4,6},
                       finalize_on_context_change=True, gap_seconds=10):
    """Segment keystrokes into meaningful text messages."""
    ts_col = cfg.get("timestamp")
    code_col = cfg.get("key_code") if cfg.get("key_code") in df.columns else None
    char_col = cfg.get("key_character") if cfg.get("key_character") in df.columns else None
    text_col = cfg.get("text") if cfg.get("text") in df.columns else None
    pkg_col = cfg.get("package") if cfg.get("package") in df.columns else None
    lbl_col = cfg.get("label") if cfg.get("label") in df.columns else None
    act_col = cfg.get("action") if cfg.get("action") in df.columns else None
    pk_col = cfg.get("pk", "rowid")

    if not ts_col or ts_col not in df.columns:
        ts_col = pk_col

    # Sort stable by (timestamp, pk)
    df = df.sort_values([ts_col, pk_col]).reset_index(drop=True)

    segments = []
    buf_chars = []
    last_text_snapshot = ""
    current_rows = []
    seg_start_ts = None
    last_pkg = None
    last_lbl = None
    last_ts_val = None

    def end_segment(end_ts):
        nonlocal buf_chars, last_text_snapshot, current_rows, seg_start_ts
        if not current_rows:
            buf_chars.clear()
            last_text_snapshot = ""
            seg_start_ts = None
            return
        
        # Prefer text snapshot if meaningful
        final_txt = (last_text_snapshot or "").strip()
        if not final_txt:
            final_txt = "".join(buf_chars).strip()
        
        if final_txt:
            # Determine package/label from the segment's rows (use the last row's context)
            seg_pkg = None
            seg_lbl = None
            if current_rows:
                last_row = current_rows[-1]
                if pkg_col: seg_pkg = last_row.get(pkg_col)
                if lbl_col: seg_lbl = last_row.get(lbl_col)

            segments.append({
                "text": final_txt,
                "start_ts": seg_start_ts if seg_start_ts is not None else current_rows[0][ts_col],
                "end_ts": end_ts,
                "row_ids": [r[pk_col] for _, r in pd.DataFrame(current_rows).iterrows()],
                "package": seg_pkg,
                "label": seg_lbl,
                "time_str": ms_to_local_str(int(end_ts)) if isinstance(end_ts, (int, float, np.integer)) else str(end_ts)
            })
        
        # reset
        buf_chars.clear()
        last_text_snapshot = ""
        current_rows = []
        seg_start_ts = None

    def to_int_or_none(x):
        try:
            return int(x)
        except Exception:
            return None

    for _, row in df.iterrows():
        cur_ts = row[ts_col]
        
        # --- 1. Check Start-of-Segment Triggers (Gap, Context Change, Text Jump) ---
        should_split_before = False
        
        # Gap Check
        if gap_seconds and last_ts_val is not None:
            try:
                dt_ms = float(cur_ts) - float(last_ts_val)
                if dt_ms > gap_seconds * 1000:
                    should_split_before = True
            except Exception:
                pass
        
        # Context Change Check
        if finalize_on_context_change:
            if pkg_col and last_pkg is not None and row[pkg_col] != last_pkg:
                should_split_before = True
            if lbl_col and last_lbl is not None and row[lbl_col] != last_lbl:
                should_split_before = True

        # Text Jump Check (Heuristic for missing Enter/Clear)
        if text_col and isinstance(row[text_col], str):
            curr_txt = row[text_col].strip()
            prev_txt = (last_text_snapshot or "").strip()
            # If text goes from long (>2 chars) to 1 char, and that 1 char is NOT the start of prev text
            if len(prev_txt) > 2 and len(curr_txt) == 1 and not prev_txt.startswith(curr_txt):
                should_split_before = True

        if should_split_before and (buf_chars or (last_text_snapshot and last_text_snapshot.strip())):
             end_segment(last_ts_val)

        # --- 2. Add Row to Current Segment ---
        if seg_start_ts is None:
            seg_start_ts = cur_ts
        current_rows.append(row)
        
        # Update trackers
        last_ts_val = cur_ts
        if pkg_col: last_pkg = row[pkg_col]
        if lbl_col: last_lbl = row[lbl_col]

        # --- 3. Update Content State ---
        prev_text_snapshot = last_text_snapshot
        if text_col and isinstance(row[text_col], str):
            last_text_snapshot = row[text_col]
        
        if char_col and isinstance(row[char_col], str) and len(row[char_col]) == 1:
            ch = row[char_col]
            if ch not in ["\n", "\r"]:
                buf_chars.append(ch)

        if code_col:
            code = to_int_or_none(row[code_col])
            if code in backspace_codes and buf_chars:
                buf_chars.pop()

        # --- 4. Check End-of-Segment Triggers (Enter, IME, Text Cleared) ---
        should_split_after = False
        
        # Enter Key
        if code_col:
            code = to_int_or_none(row[code_col])
            if code in enter_codes:
                should_split_after = True
        
        # Newline char
        if char_col and isinstance(row[char_col], str) and row[char_col] in ["\n", "\r"]:
            should_split_after = True

        # IME actions
        if use_ime_actions and act_col:
            act = to_int_or_none(row[act_col])
            if act in ime_submit:
                should_split_after = True
        
        # Text Cleared Heuristic (Explicit clear)
        if prev_text_snapshot and prev_text_snapshot.strip() and not (last_text_snapshot and last_text_snapshot.strip()):
            should_split_after = True

        if should_split_after:
            end_segment(cur_ts)

    # finalize trailing buffer
    if current_rows and (buf_chars or (last_text_snapshot and last_text_snapshot.strip())):
        end_segment(current_rows[-1][ts_col])

    return segments

# -------- Session Helper Functions --------

def get_db_path():
    """Get the current database path from session."""
    return session.get('db_path')

def get_settings():
    """Get current settings from session with defaults."""
    return {
        'limit': session.get('limit', 0),
        'use_ime_actions': session.get('use_ime_actions', True),
        'ime_action_delims': session.get('ime_action_delims', [2, 3, 4, 6]),
        'finalize_on_context_change': session.get('finalize_on_context_change', True),
        'gap_seconds': session.get('gap_seconds', 10),
        'enter_keycodes': session.get('enter_keycodes', '66'),
        'segments_per_page': session.get('segments_per_page', 50),
        'mapping': session.get('mapping', {})
    }

def save_settings(settings):
    """Save settings to session."""
    for key, value in settings.items():
        session[key] = value

# -------- Routes --------

@app.route('/')
def index():
    """Main page - show upload form or segments viewer."""
    db_path = get_db_path()
    
    if not db_path or not os.path.exists(db_path):
        return render_template('index.html', no_db=True)
    
    try:
        conn = sqlite3.connect(db_path)
        table = detect_keyboard_table(conn)
        
        if not table:
            flash('No tables found in the database.', 'error')
            conn.close()
            return render_template('index.html', no_db=True)
        
        # Store table info in session
        session['table'] = table
        
        # Get columns and mapping
        cols = table_columns(conn, table)
        pk_col = detect_pk_column(conn, table)
        
        # Initialize mapping if not exists
        if 'mapping' not in session:
            mapping = guess_columns(cols)
            mapping['pk'] = pk_col
            session['mapping'] = mapping
        
        settings = get_settings()
        mapping = settings['mapping']
        
        # Get total row count
        total_rows = conn.execute(f"SELECT COUNT(*) FROM '{table}'").fetchone()[0]
        
        # Load data
        limit = settings['limit']
        pk = mapping.get('pk', pk_col)
        ts_col = mapping.get('timestamp', pk)
        
        if pk == "rowid":
            sql = f"SELECT rowid as rowid, * FROM '{table}' ORDER BY {ts_col} ASC"
        else:
            sql = f"SELECT * FROM '{table}' ORDER BY {ts_col} ASC"
        
        if limit and limit > 0:
            sql += f" LIMIT {int(limit)}"
        
        df = pd.read_sql_query(sql, conn)
        loaded_rows = len(df)
        
        # Segment the data
        enter_codes = {int(x.strip()) for x in settings['enter_keycodes'].split(",") if x.strip().isdigit()}
        
        segments = segment_keystrokes(
            df, mapping,
            enter_codes=enter_codes,
            use_ime_actions=settings['use_ime_actions'],
            ime_submit=set(settings['ime_action_delims']),
            finalize_on_context_change=settings['finalize_on_context_change'],
            gap_seconds=int(settings['gap_seconds'])
        )
        
        # Store segments in cache file instead of session
        save_segments_cache(segments)
        session['total_rows'] = total_rows
        session['loaded_rows'] = loaded_rows
        
        # Get filter query
        query = request.args.get('q', '')
        
        # Add original indices to ALL segments first
        for i, s in enumerate(segments):
            s['original_idx'] = i
        
        # Filter segments (preserving original_idx)
        if query:
            q_low = query.lower()
            segments_view = []
            for s in segments:
                if q_low in s["text"].lower():
                    segments_view.append(s)
        else:
            segments_view = segments
        
        # Get deleted segments
        deleted_ids = set(session.get('deleted_segment_ids', []))
        
        # Pagination
        page = int(request.args.get('page', 1))
        per_page = settings['segments_per_page']
        total_pages = max(1, (len(segments_view) + per_page - 1) // per_page)
        
        # Ensure page is within bounds
        page = max(1, min(page, total_pages))
        
        start_idx = (page - 1) * per_page
        end_idx = min(start_idx + per_page, len(segments_view))
        segments_page = segments_view[start_idx:end_idx]
        
        conn.close()
        
        return render_template('index.html',
                             no_db=False,
                             table=table,
                             columns=cols,
                             mapping=mapping,
                             total_rows=total_rows,
                             loaded_rows=loaded_rows,
                             segments=segments_page,
                             total_segments=len(segments),
                             filtered_segments=len(segments_view),
                             deleted_count=len(deleted_ids),
                             page=page,
                             total_pages=total_pages,
                             per_page=per_page,
                             query=query,
                             start_idx=start_idx,
                             settings=settings,
                             db_filename=os.path.basename(db_path))
    
    except Exception as e:
        flash(f'Error processing database: {str(e)}', 'error')
        return render_template('index.html', no_db=True)

@app.route('/upload', methods=['POST']) # type: ignore
def upload_file():
    """Handle database file upload."""
    if 'database' not in request.files:
        flash('No file selected', 'error')
        return redirect(url_for('index'))
    
    file = request.files['database']
    
    if file.filename == '':
        flash('No file selected', 'error')
        return redirect(url_for('index'))
    
    if file:
        filename = secure_filename(file.filename) # type: ignore
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Clear previous session data
        session.clear()
        session['db_path'] = filepath
        
        flash(f'Successfully loaded: {filename}', 'success')
        return redirect(url_for('index'))

@app.route('/settings', methods=['POST'])
def update_settings():
    """Update application settings."""
    settings = get_settings()
    
    # Update settings from form
    settings['limit'] = int(request.form.get('limit', 0))
    settings['use_ime_actions'] = 'use_ime_actions' in request.form
    settings['finalize_on_context_change'] = 'finalize_on_context_change' in request.form
    settings['gap_seconds'] = int(request.form.get('gap_seconds', 10))
    settings['enter_keycodes'] = request.form.get('enter_keycodes', '66')
    settings['segments_per_page'] = int(request.form.get('segments_per_page', 50))
    
    # Update IME action delimiters
    ime_actions = []
    for action in [2, 3, 4, 6]:
        if f'ime_action_{action}' in request.form:
            ime_actions.append(action)
    settings['ime_action_delims'] = ime_actions
    
    # Update column mapping
    mapping = settings.get('mapping', {})
    for key in ['timestamp', 'key_code', 'key_character', 'text', 'package', 'label', 'action']:
        value = request.form.get(f'col_{key}')
        mapping[key] = value if value != '(none)' else None
    settings['mapping'] = mapping
    
    save_settings(settings)
    flash('Settings updated successfully', 'success')
    
    return redirect(url_for('index'))

@app.route('/delete_segment/<int:idx>', methods=['POST'])
def delete_segment(idx):
    """Mark a segment for deletion."""
    deleted_ids = set(session.get('deleted_segment_ids', []))
    deleted_ids.add(idx)
    session['deleted_segment_ids'] = list(deleted_ids)
    
    return jsonify({'success': True, 'deleted_count': len(deleted_ids)})

@app.route('/undelete_segment/<int:idx>', methods=['POST'])
def undelete_segment(idx):
    """Unmark a segment for deletion."""
    deleted_ids = set(session.get('deleted_segment_ids', []))
    deleted_ids.discard(idx)
    session['deleted_segment_ids'] = list(deleted_ids)
    
    return jsonify({'success': True, 'deleted_count': len(deleted_ids)})

@app.route('/delete_all_visible', methods=['POST'])
def delete_all_visible():
    """Mark all visible segments for deletion."""
    segments = load_segments_cache() or []
    query = request.form.get('query', '')
    
    # Filter segments same way as index route
    if query:
        q_low = query.lower()
        segments_to_delete = [i for i, s in enumerate(segments) if q_low in s["text"].lower()]
    else:
        segments_to_delete = list(range(len(segments)))
    
    deleted_ids = set(session.get('deleted_segment_ids', []))
    deleted_ids.update(segments_to_delete)
    session['deleted_segment_ids'] = list(deleted_ids)
    
    flash(f'Marked {len(segments_to_delete)} segments for deletion', 'success')
    return redirect(url_for('index', q=query))

@app.route('/clear_deletions', methods=['POST'])
def clear_deletions():
    """Clear all deletion marks."""
    session['deleted_segment_ids'] = []
    
    # Check if it's an AJAX request
    if request.headers.get('Content-Type') == 'application/json':
        return jsonify({'success': True, 'deleted_count': 0})
    
    # Otherwise redirect (for backward compatibility)
    flash('Cleared all deletion marks', 'success')
    return redirect(url_for('index', q=request.form.get('query', '')))

@app.route('/clear_all_data', methods=['POST'])
def clear_all_data():
    """Clear all uploaded data and reset session - for multi-user privacy."""
    try:
        # Clear session
        session.clear()
        
        # Clear uploaded files (optional - keeps backups)
        # Uncomment if you want to delete uploaded files too
        # for f in os.listdir(app.config['UPLOAD_FOLDER']):
        #     os.remove(os.path.join(app.config['UPLOAD_FOLDER'], f))
        
        # Clear cache files
        for f in os.listdir(app.config['CACHE_FOLDER']):
            try:
                os.remove(os.path.join(app.config['CACHE_FOLDER'], f))
            except:
                pass
        
        # Clear filtered files
        for f in os.listdir(app.config['FILTERED_FOLDER']):
            try:
                os.remove(os.path.join(app.config['FILTERED_FOLDER'], f))
            except:
                pass
        
        flash('All data cleared successfully. Ready for next user.', 'success')
    except Exception as e:
        flash(f'Error clearing data: {str(e)}', 'error')
    
    return redirect(url_for('index'))

@app.route('/download_filtered_db', methods=['POST'])
def download_filtered_db():
    """Create and immediately download the filtered database."""
    db_path = get_db_path()
    
    if not db_path or not os.path.exists(db_path):
        flash('No database loaded', 'error')
        return redirect(url_for('index'))
    
    segments = load_segments_cache() or []
    deleted_ids = set(session.get('deleted_segment_ids', []))
    mapping = session.get('mapping', {})
    table = session.get('table')
    
    # Collect row IDs to keep
    keep_row_ids = set()
    for i, s in enumerate(segments):
        if i not in deleted_ids:
            keep_row_ids.update(s["row_ids"])
    
    if not keep_row_ids:
        flash('No segments to save (all segments marked for deletion)', 'warning')
        return redirect(url_for('index'))
    
    # Create filtered database
    filtered_db_path = os.path.join(app.config['FILTERED_FOLDER'], 'keyboard-filtered.db')
    
    if os.path.exists(filtered_db_path):
        os.remove(filtered_db_path)
    
    try:
        with sqlite3.connect(db_path) as src_conn:
            with sqlite3.connect(filtered_db_path) as dst_conn:
                # Copy schema
                tables_to_copy = [t for t in list_tables(src_conn) if not t.startswith('sqlite_')]
                
                for tbl in tables_to_copy:
                    # Get CREATE TABLE statement
                    schema_query = f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{tbl}'"
                    schema = src_conn.execute(schema_query).fetchone()
                    if schema and schema[0]:
                        dst_conn.execute(schema[0])
                
                # Copy indices
                indices = src_conn.execute("SELECT sql FROM sqlite_master WHERE type='index' AND sql IS NOT NULL").fetchall()
                for idx in indices:
                    if idx[0]:
                        try:
                            dst_conn.execute(idx[0])
                        except sqlite3.OperationalError:
                            pass
                
                # Copy filtered data from keyboard table
                pk = mapping.get('pk', 'rowid')
                columns = table_columns(src_conn, table) # type: ignore
                col_list = ", ".join(f'"{c}"' for c in columns)
                
                placeholders = ",".join("?" for _ in keep_row_ids)
                select_query = f'SELECT {col_list} FROM "{table}" WHERE {pk} IN ({placeholders})'
                rows_to_copy = src_conn.execute(select_query, list(keep_row_ids)).fetchall()
                
                question_marks = ",".join("?" for _ in columns)
                insert_query = f'INSERT INTO "{table}" ({col_list}) VALUES ({question_marks})'
                dst_conn.executemany(insert_query, rows_to_copy)
                
                # Copy other tables completely
                for tbl in tables_to_copy:
                    if tbl != table:
                        cols_other = table_columns(src_conn, tbl)
                        col_list_other = ", ".join(f'"{c}"' for c in cols_other)
                        rows_other = src_conn.execute(f'SELECT {col_list_other} FROM "{tbl}"').fetchall()
                        if rows_other:
                            qmarks = ",".join("?" for _ in cols_other)
                            dst_conn.executemany(f'INSERT INTO "{tbl}" ({col_list_other}) VALUES ({qmarks})', rows_other)
                
                dst_conn.commit()
        
        kept_segments = len(segments) - len(deleted_ids)
        # Return the file for download
        return send_file(filtered_db_path, as_attachment=True, download_name='keyboard-filtered.db')
        
    except Exception as e:
        flash(f'Error creating filtered database: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/save_filtered', methods=['POST'])
def save_filtered():
    """Save a filtered database with deleted segments removed."""
    db_path = get_db_path()
    
    if not db_path or not os.path.exists(db_path):
        flash('No database loaded', 'error')
        return redirect(url_for('index'))
    
    segments = load_segments_cache() or []
    deleted_ids = set(session.get('deleted_segment_ids', []))
    mapping = session.get('mapping', {})
    table = session.get('table')
    
    # Collect row IDs to keep
    keep_row_ids = set()
    for i, s in enumerate(segments):
        if i not in deleted_ids:
            keep_row_ids.update(s["row_ids"])
    
    if not keep_row_ids:
        flash('No segments to save (all segments marked for deletion)', 'warning')
        return redirect(url_for('index'))
    
    # Create filtered database
    filtered_db_path = os.path.join(app.config['FILTERED_FOLDER'], 'keyboard-filtered.db')
    
    if os.path.exists(filtered_db_path):
        os.remove(filtered_db_path)
    
    try:
        with sqlite3.connect(db_path) as src_conn:
            with sqlite3.connect(filtered_db_path) as dst_conn:
                # Copy schema
                tables_to_copy = [t for t in list_tables(src_conn) if not t.startswith('sqlite_')]
                
                for tbl in tables_to_copy:
                    # Get CREATE TABLE statement
                    schema_query = f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{tbl}'"
                    schema = src_conn.execute(schema_query).fetchone()
                    if schema and schema[0]:
                        dst_conn.execute(schema[0])
                
                # Copy indices
                indices = src_conn.execute("SELECT sql FROM sqlite_master WHERE type='index' AND sql IS NOT NULL").fetchall()
                for idx in indices:
                    if idx[0]:
                        try:
                            dst_conn.execute(idx[0])
                        except sqlite3.OperationalError:
                            pass
                
                # Copy filtered data from keyboard table
                pk = mapping.get('pk', 'rowid')
                columns = table_columns(src_conn, table) # type: ignore
                col_list = ", ".join(f'"{c}"' for c in columns)
                
                placeholders = ",".join("?" for _ in keep_row_ids)
                select_query = f'SELECT {col_list} FROM "{table}" WHERE {pk} IN ({placeholders})'
                rows_to_copy = src_conn.execute(select_query, list(keep_row_ids)).fetchall()
                
                question_marks = ",".join("?" for _ in columns)
                insert_query = f'INSERT INTO "{table}" ({col_list}) VALUES ({question_marks})'
                dst_conn.executemany(insert_query, rows_to_copy)
                
                # Copy other tables completely
                for tbl in tables_to_copy:
                    if tbl != table:
                        cols_other = table_columns(src_conn, tbl)
                        col_list_other = ", ".join(f'"{c}"' for c in cols_other)
                        rows_other = src_conn.execute(f'SELECT {col_list_other} FROM "{tbl}"').fetchall()
                        if rows_other:
                            qmarks = ",".join("?" for _ in cols_other)
                            dst_conn.executemany(f'INSERT INTO "{tbl}" ({col_list_other}) VALUES ({qmarks})', rows_other)
                
                dst_conn.commit()
        
        kept_segments = len(segments) - len(deleted_ids)
        flash(f'Successfully saved filtered database with {kept_segments} segments ({len(keep_row_ids)} rows)', 'success')
        session['filtered_db_path'] = filtered_db_path
        
    except Exception as e:
        flash(f'Error creating filtered database: {str(e)}', 'error')
    
    return redirect(url_for('index'))

@app.route('/download_filtered')
def download_filtered():
    """Download the filtered database."""
    filtered_path = session.get('filtered_db_path')
    
    if not filtered_path or not os.path.exists(filtered_path):
        flash('No filtered database available. Please save a filtered database first.', 'error')
        return redirect(url_for('index'))
    
    return send_file(filtered_path, as_attachment=True, download_name='keyboard-filtered.db')

@app.route('/get_keystrokes/<int:segment_idx>')
def get_keystrokes(segment_idx):
    """Get detailed keystrokes for a segment (AJAX endpoint)."""
    try:
        db_path = get_db_path()
        if not db_path:
             return jsonify({'error': 'No database loaded'}), 400
        segments = load_segments_cache() or []
        mapping = session.get('mapping', {})
        table = session.get('table')
        
        print(f"DEBUG: Getting keystrokes for segment {segment_idx}, total segments: {len(segments)}")
        
        if not segments:
            return jsonify({'error': 'No segments loaded'}), 404
        
        if segment_idx >= len(segments):
            return jsonify({'error': f'Segment index {segment_idx} out of range (max: {len(segments)-1})'}), 404
        
        segment = segments[segment_idx]
        row_ids = segment.get('row_ids', [])
        
        if not row_ids:
            return jsonify({'error': 'No row IDs found for this segment'}), 404
        
        print(f"DEBUG: Segment has {len(row_ids)} row_ids")
        
        conn = sqlite3.connect(db_path) # type: ignore
        pk = mapping.get('pk', 'rowid')
        ts_col = mapping.get('timestamp', pk)
        
        placeholders = ",".join("?" for _ in row_ids)
        query = f'SELECT * FROM "{table}" WHERE {pk} IN ({placeholders}) ORDER BY {ts_col}'
        cursor = conn.execute(query, row_ids)
        
        col_names = [description[0] for description in cursor.description]
        rows = cursor.fetchall()
        conn.close()
        
        # Convert to list of dicts
        data = []
        for row in rows:
            row_dict = dict(zip(col_names, row))
            # Convert timestamp to readable format
            if mapping.get('timestamp') and mapping['timestamp'] in row_dict:
                ts_value = row_dict[mapping['timestamp']]
                if ts_value:
                    row_dict['time_str'] = ms_to_local_str(int(ts_value))
            data.append(row_dict)
        
        print(f"DEBUG: Returning {len(data)} rows")
        
        return jsonify({
            'success': True,
            'columns': col_names,
            'rows': data,
            'count': len(data)
        })
    
    except Exception as e:
        print(f"ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)
