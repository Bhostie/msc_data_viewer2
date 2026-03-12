"""
Bridge module between the AWARE Keyboard Viewer and typing-performance-analyzer.

Transforms raw DB keystroke rows into the format expected by the analyzer,
runs the calculators, and returns structured results.
"""

import os
import sys
import sqlite3
import json
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from typing import List, Dict, Any, Optional

# Add the typing-performance-analyzer to sys.path so its packages are importable
if getattr(sys, 'frozen', False):
    _BUNDLE_DIR = sys._MEIPASS  # type: ignore[attr-defined]
else:
    _BUNDLE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

_ANALYZER_ROOT = os.path.join(_BUNDLE_DIR, 'typing-performance-analyzer', 'performance_analyzer')
if _ANALYZER_ROOT not in sys.path:
    sys.path.insert(0, _ANALYZER_ROOT)
# Also add the parent so "from performance_analyzer..." works
_ANALYZER_PARENT = os.path.join(_BUNDLE_DIR, 'typing-performance-analyzer')
if _ANALYZER_PARENT not in sys.path:
    sys.path.insert(0, _ANALYZER_PARENT)

ISTANBUL_TZ = ZoneInfo("Europe/Istanbul")


def _censor_text(text: str) -> str:
    """Replace text content with asterisks of the same length, preserving privacy."""
    if not text:
        return ''
    return '*' * len(text)


def _rows_to_analyzer_sequence(rows: List[Dict[str, Any]], mapping: Dict[str, Optional[str]]) -> List[Dict[str, Any]]:
    """
    Transform raw DB rows (list of dicts with actual column names) into the
    format expected by typing-performance-analyzer.

    Expected output format per entry:
        {
            "_id": int,
            "timestamp": str (ms epoch),
            "package_name": str,
            "before_text": str (no brackets),
            "current_text": str (may have [brackets]),
            "is_password": 0
        }
    """
    pk_col = mapping.get('pk') or 'rowid'
    ts_col = mapping.get('timestamp') or pk_col
    text_col = mapping.get('text')
    pkg_col = mapping.get('package')

    # Detect before_text column: prefer mapping, fall back to sniffing row keys
    before_text_col = mapping.get('before_text')
    if not before_text_col and rows:
        for col_name in ['before_text', 'before', 'previous_text']:
            if col_name in rows[0]:
                before_text_col = col_name
                break

    sequence = []
    for row in rows:
        _id = row.get(pk_col, 0)
        # Timestamps may come as float (e.g. 1760445945533.0) from SQLite/Pandas.
        # The analyzer does int(timestamp) so we must provide a clean integer string.
        raw_ts = row.get(ts_col, 0)
        try:
            timestamp = str(int(float(raw_ts)))
        except (ValueError, TypeError):
            timestamp = str(raw_ts)
        package_name = str(row.get(pkg_col, '')) if pkg_col and pkg_col in row else ''

        # current_text: keep as-is (analyzer handles brackets internally)
        current_text = ''
        if text_col and text_col in row:
            val = row[text_col]
            if val is not None:
                current_text = str(val)

        # before_text: the analyzer expects it WITHOUT brackets
        before_text = ''
        if before_text_col and before_text_col in row:
            val = row[before_text_col]
            if val is not None:
                before_text = str(val)

        sequence.append({
            '_id': _id,
            'timestamp': timestamp,
            'package_name': package_name,
            'before_text': before_text,
            'current_text': current_text,
            'is_password': int(row.get('is_password', 0)) if 'is_password' in row else 0,
        })

    return sequence


def analyze_segment(rows: List[Dict[str, Any]], mapping: Dict[str, Optional[str]]) -> Dict[str, Any]:
    """
    Run typing-performance-analyzer on a single segment's raw keystroke rows.

    Returns a dict with metrics. Gracefully handles import failures for
    optional dependencies (phunspell, nltk) — typing path analysis will
    be skipped if they're unavailable.
    """
    sequence = _rows_to_analyzer_sequence(rows, mapping)

    if len(sequence) < 2:
        return {
            'keystroke_count': len(sequence),
            'error': 'Too few keystrokes for analysis (need >= 2)',
        }

    result: Dict[str, Any] = {
        'keystroke_count': len(sequence),
    }

    # --- Typing Speed ---
    try:
        from performance_analyzer.typing_speed import TypingSpeedCalculator
        speed_calc = TypingSpeedCalculator(sequence)
        result['wpm'] = round(speed_calc.wpm(interrupted_time=0), 2)
        result['ksps'] = round(speed_calc.ksps(interrupted_time=0), 2)
        result['duration_seconds'] = round(speed_calc.get_duration(), 2)
        # Store only the length — not the actual text (deleted for privacy)
        result['final_text_length'] = len(speed_calc.get_final_text())
    except Exception as e:
        result['speed_error'] = str(e)

    # --- Error Rate ---
    try:
        from performance_analyzer.error_rate import ErrorRateCalculator
        error_calc = ErrorRateCalculator(sequence)
        result['kspc'] = round(error_calc.kspc(additional_characters=0), 2)
    except Exception as e:
        result['error_rate_error'] = str(e)

    # --- Typing Path (optional — needs phunspell/nltk) ---
    try:
        from performance_analyzer.typing_path import TypingPathCalculator
        path_calc = TypingPathCalculator(sequence)
        path_calc.calculate()
        path_calc.detect_edit_operations()

        # Extract activity summary from internal state
        activities = []
        for act in path_calc._typing_activity._activity_list:
            activity_info = {
                'type': act.type.name if act.type else None,
                'position': act.position.name if act.position else None,
                'entered': _censor_text(act.entered) if act.entered else '',
                'removed': _censor_text(act.removed) if act.removed else '',
            }
            if act.edit_correction is not None:
                activity_info['edit_operation'] = act.edit_correction.name
            activities.append(activity_info)

        # Count corrections vs revisions
        corrections = sum(1 for a in activities if a.get('edit_operation') == 'CORRECTION')
        revisions = sum(1 for a in activities if a.get('edit_operation') == 'REVISION')

        result['typing_path'] = {
            'total_activities': len(activities),
            'corrections': corrections,
            'revisions': revisions,
            'activities': activities,
        }
    except ImportError:
        result['typing_path_note'] = 'Skipped (phunspell/nltk not installed)'
    except Exception as e:
        result['typing_path_error'] = str(e)

    return result


def analyze_deleted_segments(
    db_path: str,
    table: str,
    mapping: Dict[str, Optional[str]],
    segments: List[Dict[str, Any]],
    deleted_ids: set,
) -> Dict[str, Any]:
    """
    Run typing performance analysis on all deleted segments.

    Fetches raw keystrokes from the DB for each deleted segment,
    runs the analyzer, and returns a JSON-serializable report.
    """
    pk_col = mapping.get('pk', 'rowid')
    ts_col = mapping.get('timestamp', pk_col)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # access columns by name

    segment_results = []

    for seg_idx in sorted(deleted_ids):
        if seg_idx >= len(segments):
            continue

        segment = segments[seg_idx]
        row_ids = segment.get('row_ids', [])

        if not row_ids:
            continue

        # Fetch raw rows for this segment
        placeholders = ",".join("?" for _ in row_ids)
        query = f'SELECT * FROM "{table}" WHERE "{pk_col}" IN ({placeholders}) ORDER BY "{ts_col}"'
        cursor = conn.execute(query, row_ids)
        col_names = [desc[0] for desc in cursor.description]
        raw_rows = [dict(zip(col_names, row)) for row in cursor.fetchall()]

        if not raw_rows:
            continue

        # Run analysis
        metrics = analyze_segment(raw_rows, mapping)

        # Build per-segment result (without the actual message text — that's the point)
        segment_result = {
            'segment_index': seg_idx,
            'start_time': segment.get('time_str', ''),
            'package': segment.get('package', ''),
            'label': segment.get('label', ''),
            'char_count': len(segment.get('text', '')),
            'word_count': len(segment.get('text', '').split()) if segment.get('text') else 0,
            'metrics': metrics,
        }
        segment_results.append(segment_result)

    conn.close()

    # Aggregate summary
    valid = [r for r in segment_results if 'error' not in r['metrics']]
    summary: Dict[str, Any] = {
        'total_deleted_segments': len(deleted_ids),
        'analyzed_segments': len(segment_results),
        'segments_with_metrics': len(valid),
    }

    if valid:
        wpms = [r['metrics']['wpm'] for r in valid if 'wpm' in r['metrics']]
        ksps_list = [r['metrics']['ksps'] for r in valid if 'ksps' in r['metrics']]
        kspcs = [r['metrics']['kspc'] for r in valid if 'kspc' in r['metrics']]
        durations = [r['metrics']['duration_seconds'] for r in valid if 'duration_seconds' in r['metrics']]

        if wpms:
            summary['avg_wpm'] = round(sum(wpms) / len(wpms), 2)
            summary['min_wpm'] = round(min(wpms), 2)
            summary['max_wpm'] = round(max(wpms), 2)
        if ksps_list:
            summary['avg_ksps'] = round(sum(ksps_list) / len(ksps_list), 2)
        if kspcs:
            summary['avg_kspc'] = round(sum(kspcs) / len(kspcs), 2)
        if durations:
            summary['total_duration_seconds'] = round(sum(durations), 2)

        # Typing path aggregate (if available)
        corrections = sum(r['metrics'].get('typing_path', {}).get('corrections', 0) for r in valid)
        revisions = sum(r['metrics'].get('typing_path', {}).get('revisions', 0) for r in valid)
        if corrections > 0 or revisions > 0:
            summary['total_corrections'] = corrections
            summary['total_revisions'] = revisions

    now = datetime.now(tz=ISTANBUL_TZ)
    report = {
        'generated_at': now.strftime('%Y-%m-%d %H:%M:%S'),
        'database': os.path.basename(db_path),
        'summary': summary,
        'segments': segment_results,
    }

    return report


def save_analysis_report(report: Dict[str, Any], output_folder: str) -> str:
    """Save the analysis report as a JSON file with a unique name. Returns the file path."""
    os.makedirs(output_folder, exist_ok=True)
    # Include database name and timestamp to avoid overwriting previous reports
    db_name = report.get('database', 'unknown').replace('.db', '')
    now = datetime.now(tz=ISTANBUL_TZ)
    timestamp_str = now.strftime('%Y%m%d_%H%M%S')
    filename = f'typing-analysis_{db_name}_{timestamp_str}.json'
    filepath = os.path.join(output_folder, filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    return filepath


def save_analysis_to_db(report: Dict[str, Any], filtered_db_path: str) -> None:
    """
    Write the deleted-segment analysis into the filtered .db as two tables:
      - deleted_segment_analysis          (one row per deleted segment)
      - deleted_segment_analysis_summary  (single summary row)

    All message text is already censored upstream; only metrics are stored.
    """
    conn = sqlite3.connect(filtered_db_path)

    # --- per-segment table ---
    conn.execute("""
        CREATE TABLE IF NOT EXISTS deleted_segment_analysis (
            segment_index       INTEGER,
            start_time          TEXT,
            package             TEXT,
            label               TEXT,
            char_count          INTEGER,
            word_count          INTEGER,
            keystroke_count     INTEGER,
            wpm                 REAL,
            ksps                REAL,
            duration_seconds    REAL,
            final_text_length   INTEGER,
            kspc                REAL,
            total_activities    INTEGER,
            corrections         INTEGER,
            revisions           INTEGER,
            typing_path_json    TEXT
        )
    """)

    for seg in report.get('segments', []):
        metrics = seg.get('metrics', {})
        tp = metrics.get('typing_path', {})
        conn.execute(
            """INSERT INTO deleted_segment_analysis
               (segment_index, start_time, package, label, char_count, word_count,
                keystroke_count, wpm, ksps, duration_seconds, final_text_length,
                kspc, total_activities, corrections, revisions, typing_path_json)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                seg.get('segment_index'),
                seg.get('start_time', ''),
                seg.get('package', ''),
                seg.get('label', ''),
                seg.get('char_count', 0),
                seg.get('word_count', 0),
                metrics.get('keystroke_count', 0),
                metrics.get('wpm'),
                metrics.get('ksps'),
                metrics.get('duration_seconds'),
                metrics.get('final_text_length'),
                metrics.get('kspc'),
                tp.get('total_activities'),
                tp.get('corrections'),
                tp.get('revisions'),
                json.dumps(tp.get('activities', []), ensure_ascii=False) if tp.get('activities') else None,
            ),
        )

    # --- summary table ---
    conn.execute("""
        CREATE TABLE IF NOT EXISTS deleted_segment_analysis_summary (
            generated_at            TEXT,
            database_name           TEXT,
            total_deleted_segments  INTEGER,
            analyzed_segments       INTEGER,
            segments_with_metrics   INTEGER,
            avg_wpm                 REAL,
            min_wpm                 REAL,
            max_wpm                 REAL,
            avg_ksps                REAL,
            avg_kspc                REAL,
            total_duration_seconds  REAL,
            total_corrections       INTEGER,
            total_revisions         INTEGER
        )
    """)

    summary = report.get('summary', {})
    conn.execute(
        """INSERT INTO deleted_segment_analysis_summary
           (generated_at, database_name, total_deleted_segments, analyzed_segments,
            segments_with_metrics, avg_wpm, min_wpm, max_wpm, avg_ksps, avg_kspc,
            total_duration_seconds, total_corrections, total_revisions)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            report.get('generated_at', ''),
            report.get('database', ''),
            summary.get('total_deleted_segments', 0),
            summary.get('analyzed_segments', 0),
            summary.get('segments_with_metrics', 0),
            summary.get('avg_wpm'),
            summary.get('min_wpm'),
            summary.get('max_wpm'),
            summary.get('avg_ksps'),
            summary.get('avg_kspc'),
            summary.get('total_duration_seconds'),
            summary.get('total_corrections'),
            summary.get('total_revisions'),
        ),
    )

    conn.commit()
    conn.close()
