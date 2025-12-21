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
        # Strip whitespace AFTER removing brackets (spaces inside brackets)
        s = s.strip()
        # Return empty if it's a placeholder
        placeholders = ['message', 'search…', 'search...', 'type a message', 'type message']
        if s.lower() in placeholders:
            return ""
        return s

    def _is_deletion_pattern(self, prev_text: str, curr_before: Any) -> bool:
        """
        Check if this empty before_text is due to user deleting text (not sending).
        
        When user SENDS: previous current_text has the complete message (non-empty)
        When user DELETES: previous current_text is empty/[] because they deleted everything
        
        If the previous text was already empty, this is a continuation (delete & retype),
        not a new message send.
        
        NOTE: If prev_text was a PLACEHOLDER (like "Message" or "Search…"), that doesn't
        count as deletion - it means the field was showing a placeholder before user typed.
        """
        # Check if prev_text is a raw placeholder (before cleaning)
        if prev_text:
            raw = str(prev_text).strip()
            if raw.startswith('[') and raw.endswith(']'):
                raw = raw[1:-1]
            placeholders = ['message', 'search…', 'search...', 'type a message', 'type message']
            if raw.lower() in placeholders:
                # Previous was a placeholder, so this is NOT a deletion pattern
                # It's a new message in a fresh input field
                return False
        
        # Clean the previous text
        prev_clean = self._clean_text(prev_text)
        
        # If previous text was empty (user deleted everything), 
        # this is a continuation (delete & retype), not a new message send
        if prev_clean == "" or prev_clean == "[]":
            return True
        
        return False
    
    def _is_continuous_edit(self, prev_current: str, curr_current: str) -> bool:
        """
        Check if the current row is a continuation of editing the previous text.
        
        This handles cases like search boxes where:
        - User types "watch", submits search (before_text becomes empty)
        - But current_text still shows "watch" or modified version
        - User then continues editing/deleting from that text
        
        If the current_text is same as or derived from prev_current, 
        it's a continuation, not a new message.
        
        CRITICAL: If current text is very short (1-3 chars) and previous was much longer,
        this is likely a NEW message starting, not continuous editing.
        """
        prev = self._clean_text(prev_current)
        curr = self._clean_text(curr_current)
        
        if not prev or not curr:
            return False
        
        # If current text is very short and previous was much longer,
        # this is likely a NEW message (user just typed first character)
        # NOT continuous editing
        if len(curr) <= 3 and len(prev) > len(curr) * 3:
            return False
        
        # If current text is same as previous - editing continues
        if curr == prev:
            return True
        
        # If current is a prefix/suffix of previous (user is deleting)
        # But only if the length difference is reasonable (not too drastic)
        if prev.startswith(curr) and len(prev) - len(curr) <= 5:
            return True
        if curr.startswith(prev) and len(curr) - len(prev) <= 5:
            return True
        
        # For long texts (>100 chars), check if they're mostly the same
        # This handles editing in the middle of long messages (e.g., adding emoji bullets)
        if len(prev) > 100 and len(curr) > 100:
            len_ratio = min(len(prev), len(curr)) / max(len(prev), len(curr))
            if len_ratio > 0.90:  # Lengths within 10%
                # Check if beginning and end match (edit was in middle)
                check_len = min(50, len(prev) // 4, len(curr) // 4)
                first_match = prev[:check_len] == curr[:check_len]
                last_match = prev[-check_len:] == curr[-check_len:]
                if first_match and last_match:
                    return True
                # Even if just one end matches with very high similarity, consider it continuous
                if (first_match or last_match) and len_ratio > 0.95:
                    return True
        
        return False

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
        prev_current_text: str = ""  # Track previous row's current_text for deletion detection

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
            
            # First, check time gap (strong indicator regardless of text patterns)
            time_gap_seconds = 0.0
            if last_ts_val is not None:
                try:
                    time_gap_seconds = (float(cur_ts) - float(last_ts_val)) / 1000.0
                except Exception:
                    pass
            
            # METHOD 1: Use before_text column (most reliable for AWARE data)
            # A new message starts when:
            #   - before_text is EMPTY (text field was cleared)
            #   - AND the previous current_text was NOT empty (meaning message was sent, not deleted)
            #   - AND the current text is NOT a continuation of editing previous text
            #   - OR there's a significant time gap (user moved on)
            if self.before_text_col and self.before_text_col in row.index:
                before_val = row[self.before_text_col]
                if self._is_empty_or_placeholder(before_val) and current_rows:
                    # Large time gap = definitely new message
                    if time_gap_seconds > 60.0:  # More than 1 minute
                        should_split_before = True
                    # Check if this is a real send or just user deleting & retyping
                    elif not self._is_deletion_pattern(prev_current_text, before_val):
                        # Check if user is continuing to edit (e.g., search box scenario)
                        raw_curr = str(row[self.text_col]) if self.text_col and self.text_col in row.index else ""
                        # Only consider continuous edit if gap is short (< 30 seconds)
                        if time_gap_seconds > 30.0 or not self._is_continuous_edit(prev_current_text, raw_curr):
                            # Previous text was substantial and not continuing edit - new message
                            should_split_before = True
                    # else: User deleted everything and is retyping - don't split
            
            # METHOD 2: Detect "text jump" - significant gap + completely different text
            # This catches cases where before_text isn't empty but user switched context
            # (e.g., row 95->96 in segment 5: gap=537s, text jumps from long message to "ek")
            if not should_split_before and current_rows and time_gap_seconds > 30.0:
                # Check if text completely changed (not a continuation)
                prev_clean = self._clean_text(prev_current_text)
                curr_clean = self._clean_text(curr_text) if curr_text else ""
                
                if prev_clean and curr_clean:
                    # If texts have no relationship and there's a big gap, split
                    has_overlap = (
                        prev_clean.startswith(curr_clean) or 
                        curr_clean.startswith(prev_clean) or
                        prev_clean in curr_clean or 
                        curr_clean in prev_clean
                    )
                    
                    # For long texts, check if they're "mostly the same" (editing in middle)
                    if not has_overlap and len(prev_clean) > 100 and len(curr_clean) > 100:
                        len_ratio = min(len(prev_clean), len(curr_clean)) / max(len(prev_clean), len(curr_clean))
                        if len_ratio > 0.90:  # Lengths within 10%
                            # Check if beginning or end matches
                            check_len = min(50, len(prev_clean) // 4, len(curr_clean) // 4)
                            first_match = prev_clean[:check_len] == curr_clean[:check_len]
                            last_match = prev_clean[-check_len:] == curr_clean[-check_len:]
                            if first_match or last_match:
                                has_overlap = True  # It's the same long text being edited
                    
                    if not has_overlap:
                        should_split_before = True
            
            # METHOD 3: Detect "text discontinuity" - before_text doesn't match previous current_text
            # This catches cases where the user's text field was completely replaced
            # (e.g., switching chat windows, autocomplete replacement, etc.)
            # 
            # EXCEPTION: For very long texts, the user might be editing in the middle,
            # which causes before_text to not exactly match prev_current_text.
            # In this case, check if they're "mostly the same" (high similarity).
            if not should_split_before and current_rows and self.before_text_col:
                before_val = row[self.before_text_col] if self.before_text_col in row.index else None
                if before_val is not None and not self._is_empty_or_placeholder(before_val):
                    before_clean = self._clean_text(before_val)
                    prev_clean = self._clean_text(prev_current_text)
                    
                    # If before_text exists but doesn't match what we expect from previous current_text
                    # (before should be a prefix/suffix or similar to prev_current)
                    if prev_clean and before_clean and len(prev_clean) > 3:
                        # Check if before_text is related to previous current_text
                        is_related = (
                            prev_clean.startswith(before_clean) or
                            before_clean.startswith(prev_clean) or
                            prev_clean == before_clean or
                            # Allow for minor edits (within 3 chars)
                            (len(before_clean) > 0 and abs(len(prev_clean) - len(before_clean)) <= 3 and 
                             (prev_clean[:min(len(prev_clean), len(before_clean))] == before_clean[:min(len(prev_clean), len(before_clean))]))
                        )
                        
                        # For long texts (>100 chars), check if they're mostly the same
                        # This handles the case of editing in the middle of a long message
                        if not is_related and len(prev_clean) > 100 and len(before_clean) > 100:
                            # Check if lengths are similar (within 10%)
                            len_ratio = min(len(prev_clean), len(before_clean)) / max(len(prev_clean), len(before_clean))
                            if len_ratio > 0.85:  # Relaxed from 0.95 to handle AWARE logger quirks
                                # Check if first 50 and last 50 chars match (editing in middle)
                                first_match = prev_clean[:50] == before_clean[:50]
                                last_match = prev_clean[-50:] == before_clean[-50:]
                                # If BOTH match, very likely same text
                                if first_match and last_match:
                                    is_related = True
                                # If only one matches and ratio is very high, also consider related
                                elif (first_match or last_match) and len_ratio > 0.92:
                                    is_related = True
                        
                        if not is_related:
                            should_split_before = True
            
            # METHOD 4: Fallback - Gap-based splitting (for non-AWARE data)
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
            
            # Track raw current_text for deletion detection (before cleaning)
            if self.text_col and self.text_col in row.index:
                raw_val = row[self.text_col]
                prev_current_text = str(raw_val) if raw_val is not None and not (isinstance(raw_val, float) and np.isnan(raw_val)) else ""
            else:
                prev_current_text = ""

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
