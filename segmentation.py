import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Set, Any
from dataclasses import dataclass, field
from utils import ms_to_local_str

@dataclass
class SegmentationConfig:
    """Configuration for the segmentation algorithm."""
    enter_codes: Set[int] = field(default_factory=lambda: {66})
    backspace_codes: Set[int] = field(default_factory=lambda: {67})
    use_ime_actions: bool = True
    ime_submit: Set[int] = field(default_factory=lambda: {2, 3, 4, 6})
    finalize_on_context_change: bool = True
    gap_seconds: float = 10.0
    min_text_drop_len: int = 2  # Minimum chars dropped to consider a "bulk delete"
    max_bulk_delete_gap: float = 0.5  # Max seconds for a bulk delete to happen

class Segmenter:
    def __init__(self, df: pd.DataFrame, mapping: Dict[str, Optional[str]], config: SegmentationConfig):
        self.df = df
        self.mapping = mapping
        self.cfg = config
        
        # Column mapping
        # Ensure pk_col is a string
        pk = mapping.get("pk")
        self.pk_col: str = pk if pk else "rowid"

        # Ensure ts_col is a string
        ts = mapping.get("timestamp")
        if ts and ts in df.columns:
            self.ts_col: str = ts
        else:
            self.ts_col: str = self.pk_col

        self.code_col = mapping.get("key_code") if mapping.get("key_code") in df.columns else None
        self.char_col = mapping.get("key_character") if mapping.get("key_character") in df.columns else None
        self.text_col = mapping.get("text") if mapping.get("text") in df.columns else None
        self.pkg_col = mapping.get("package") if mapping.get("package") in df.columns else None
        self.lbl_col = mapping.get("label") if mapping.get("label") in df.columns else None
        self.act_col = mapping.get("action") if mapping.get("action") in df.columns else None
        
        # Detect before_text column (AWARE format) - critical for segmentation
        self.before_text_col: Optional[str] = None
        for col_name in ['before_text', 'before', 'previous_text']:
            if col_name in df.columns:
                self.before_text_col = col_name
                break
        
        # Also detect current_text if text column not found
        if not self.text_col:
            for col_name in ['current_text', 'text', 'after_text']:
                if col_name in df.columns:
                    self.text_col = col_name
                    break

    def _is_empty_or_placeholder(self, val: Any) -> bool:
        """Check if a value is empty, None, NaN, or a placeholder text."""
        if val is None:
            return True
        if isinstance(val, float) and np.isnan(val):
            return True
        if isinstance(val, str):
            s = val.strip()
            if s == '':
                return True
            # Common placeholder texts that indicate empty field
            placeholders = ['message', 'search…', 'search...', 'type a message', 'type message']
            if s.lower() in placeholders:
                return True
        return False

    def _clean_text(self, val: Any) -> str:
        """Clean text value, removing brackets if present."""
        if val is None:
            return ""
        if isinstance(val, float) and np.isnan(val):
            return ""
        s = str(val).strip()
        # Remove surrounding brackets like [text]
        if s.startswith('[') and s.endswith(']'):
            s = s[1:-1]
        # Return empty if it's a placeholder
        placeholders = ['message', 'search…', 'search...', 'type a message', 'type message']
        if s.lower() in placeholders:
            return ""
        return s

    def segment(self) -> List[Dict[str, Any]]:
        """Run the segmentation algorithm."""
        # Sort stable by (timestamp, pk)
        df = self.df.sort_values([self.ts_col, self.pk_col]).reset_index(drop=True)

        segments: List[Dict[str, Any]] = []
        current_rows: List[Any] = []
        seg_start_ts: Any = None
        last_pkg: Any = None
        last_lbl: Any = None
        last_ts_val: Any = None
        last_text: str = ""

        def end_segment(end_ts: Any, final_text: str):
            nonlocal current_rows, seg_start_ts
            if not current_rows:
                seg_start_ts = None
                return
            
            final_txt = self._clean_text(final_text)
            
            if final_txt:
                # Determine package/label from the segment's rows (use the last row's context)
                seg_pkg = None
                seg_lbl = None
                if current_rows:
                    last_row = current_rows[-1]
                    if self.pkg_col: 
                        seg_pkg = last_row[self.pkg_col] if self.pkg_col in last_row.index else None
                    if self.lbl_col: 
                        seg_lbl = last_row[self.lbl_col] if self.lbl_col in last_row.index else None

                segments.append({
                    "text": final_txt,
                    "start_ts": seg_start_ts if seg_start_ts is not None else current_rows[0][self.ts_col],
                    "end_ts": end_ts,
                    "row_ids": [r[self.pk_col] for r in current_rows],
                    "package": seg_pkg,
                    "label": seg_lbl,
                    "time_str": ms_to_local_str(int(end_ts)) if isinstance(end_ts, (int, float, np.integer)) else str(end_ts)
                })
            
            # reset
            current_rows = []
            seg_start_ts = None

        def to_int_or_none(x: Any) -> Optional[int]:
            try:
                return int(x)
            except Exception:
                return None

        for _, row in df.iterrows():
            cur_ts = row[self.ts_col]
            
            # Get current text value (cumulative message)
            curr_text = ""
            if self.text_col and self.text_col in row.index:
                curr_text = self._clean_text(row[self.text_col])
            
            # --- PRIMARY SEGMENTATION: Check if this is a NEW MESSAGE ---
            should_split_before = False
            
            # METHOD 1: Use before_text column (most reliable for AWARE data)
            # A new message starts when before_text is EMPTY (meaning text field was cleared/sent)
            if self.before_text_col and self.before_text_col in row.index:
                before_val = row[self.before_text_col]
                if self._is_empty_or_placeholder(before_val) and current_rows and last_text:
                    should_split_before = True
            
            # METHOD 2: Fallback - Gap-based splitting
            if not self.before_text_col:
                if last_ts_val is not None and self.cfg.gap_seconds:
                    try:
                        time_diff = (float(cur_ts) - float(last_ts_val)) / 1000.0  # seconds
                        if time_diff > self.cfg.gap_seconds:
                            should_split_before = True
                    except Exception:
                        pass
            
            # Context Change Check (app/label change)
            if self.cfg.finalize_on_context_change:
                if self.pkg_col and self.pkg_col in row.index and last_pkg is not None:
                    if row[self.pkg_col] != last_pkg:
                        should_split_before = True
                if self.lbl_col and self.lbl_col in row.index and last_lbl is not None:
                    if row[self.lbl_col] != last_lbl:
                        should_split_before = True

            # Execute split if needed
            if should_split_before and current_rows:
                end_segment(last_ts_val, last_text)
                last_text = ""

            # --- Add Row to Current Segment ---
            if seg_start_ts is None:
                seg_start_ts = cur_ts
            current_rows.append(row)
            
            # Update trackers
            last_ts_val = cur_ts
            if self.pkg_col and self.pkg_col in row.index: 
                last_pkg = row[self.pkg_col]
            if self.lbl_col and self.lbl_col in row.index: 
                last_lbl = row[self.lbl_col]

            # Update text snapshot (current_text contains the cumulative message)
            if curr_text:
                last_text = curr_text

            # --- Check End-of-Segment Triggers (Enter, IME) ---
            should_split_after = False
            
            # Enter Key
            if self.code_col and self.code_col in row.index:
                code = to_int_or_none(row[self.code_col])
                if code in self.cfg.enter_codes:
                    should_split_after = True
            
            # Newline char
            if self.char_col and self.char_col in row.index:
                char_val = row[self.char_col]
                if isinstance(char_val, str) and char_val in ["\n", "\r"]:
                    should_split_after = True

            # IME actions
            if self.cfg.use_ime_actions and self.act_col and self.act_col in row.index:
                act = to_int_or_none(row[self.act_col])
                if act in self.cfg.ime_submit:
                    should_split_after = True

            if should_split_after and current_rows:
                end_segment(cur_ts, last_text)
                last_text = ""

        # Finalize trailing segment
        if current_rows and last_text:
            end_segment(current_rows[-1][self.ts_col], last_text)

        return segments

def segment_keystrokes(df: pd.DataFrame, mapping: Dict[str, Optional[str]], **kwargs) -> List[Dict[str, Any]]:
    """Wrapper for backward compatibility."""
    cfg = SegmentationConfig(
        enter_codes=kwargs.get('enter_codes', {66}),
        backspace_codes=kwargs.get('backspace_codes', {67}),
        use_ime_actions=kwargs.get('use_ime_actions', True),
        ime_submit=kwargs.get('ime_submit', {2, 3, 4, 6}),
        finalize_on_context_change=kwargs.get('finalize_on_context_change', True),
        gap_seconds=kwargs.get('gap_seconds', 10.0)
    )
    segmenter = Segmenter(df, mapping, cfg)
    return segmenter.segment()
