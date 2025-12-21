ALGORITHM: Chat Message Segmentation for Keystroke Log Data
INPUT: DataFrame D with columns: timestamp, before_text, current_text, package_name
OUTPUT: List of segments, each containing: text, row_ids, start_time, end_time

CONSTANTS:
    PLACEHOLDERS = {"Message", "Search…", "Type a message", ...}
    LARGE_GAP_THRESHOLD = 60 seconds
    MEDIUM_GAP_THRESHOLD = 30 seconds

FUNCTIONS:

    FUNCTION is_empty_or_placeholder(text):
        RETURN text is NULL OR text is empty OR text ∈ PLACEHOLDERS

    FUNCTION clean_text(text):
        Remove surrounding brackets [text] → text
        IF text ∈ PLACEHOLDERS THEN RETURN ""
        RETURN text

    FUNCTION is_deletion_pattern(prev_current_text):
        // User deleted all text (not sent message) if previous current was empty
        IF prev_current_text was a PLACEHOLDER THEN RETURN FALSE
        IF clean_text(prev_current_text) is empty THEN RETURN TRUE
        RETURN FALSE

    FUNCTION is_continuous_edit(prev_text, curr_text):
        // Detects if current keystroke is editing previous text
        prev ← clean_text(prev_text)
        curr ← clean_text(curr_text)
        
        // New message starting with same letter is NOT continuous
        IF length(curr) ≤ 3 AND length(prev) > length(curr) × 3 THEN
            RETURN FALSE
        
        // Identical or minor prefix/suffix change
        IF curr = prev THEN RETURN TRUE
        IF prev starts with curr AND length(prev) - length(curr) ≤ 5 THEN RETURN TRUE
        IF curr starts with prev AND length(curr) - length(prev) ≤ 5 THEN RETURN TRUE
        
        // Long text similarity check (handles mid-text editing)
        IF length(prev) > 100 AND length(curr) > 100 THEN
            len_ratio ← min(length(prev), length(curr)) / max(length(prev), length(curr))
            IF len_ratio > 0.90 THEN
                first_match ← prev[0:50] = curr[0:50]
                last_match ← prev[-50:] = curr[-50:]
                IF first_match AND last_match THEN RETURN TRUE
                IF (first_match OR last_match) AND len_ratio > 0.95 THEN RETURN TRUE
        
        RETURN FALSE

    FUNCTION has_text_overlap(text1, text2):
        // For short texts: prefix/suffix or containment
        IF text1 starts with text2 OR text2 starts with text1 THEN RETURN TRUE
        IF text1 contains text2 OR text2 contains text1 THEN RETURN TRUE
        
        // For long texts: check similarity
        IF length(text1) > 100 AND length(text2) > 100 THEN
            len_ratio ← min(length(text1), length(text2)) / max(length(text1), length(text2))
            IF len_ratio > 0.90 THEN
                first_match ← text1[0:50] = text2[0:50]
                last_match ← text1[-50:] = text2[-50:]
                IF first_match AND last_match THEN RETURN TRUE
                IF (first_match OR last_match) AND len_ratio > 0.92 THEN RETURN TRUE
        
        RETURN FALSE

MAIN ALGORITHM:

    Sort D by (timestamp, row_id)
    segments ← empty list
    current_segment_rows ← empty list
    prev_current_text ← ""
    prev_timestamp ← NULL

    FOR EACH row IN D:
        time_gap ← (row.timestamp - prev_timestamp) / 1000  // seconds
        should_split ← FALSE

        // ─────────────────────────────────────────────────────────
        // METHOD 1: Empty before_text detection (primary signal)
        // Empty before_text indicates text field was cleared (message sent)
        // ─────────────────────────────────────────────────────────
        IF is_empty_or_placeholder(row.before_text) AND current_segment_rows ≠ empty:
            
            IF time_gap > LARGE_GAP_THRESHOLD THEN
                // But check if it's the same long text being edited
                IF NOT is_continuous_edit(prev_current_text, row.current_text) THEN
                    should_split ← TRUE
            
            ELSE IF NOT is_deletion_pattern(prev_current_text) THEN
                IF time_gap > MEDIUM_GAP_THRESHOLD THEN
                    IF NOT is_continuous_edit(prev_current_text, row.current_text) THEN
                        should_split ← TRUE
                ELSE IF NOT is_continuous_edit(prev_current_text, row.current_text) THEN
                    should_split ← TRUE

        // ─────────────────────────────────────────────────────────
        // METHOD 2: Text jump detection
        // Large time gap with completely unrelated text
        // ─────────────────────────────────────────────────────────
        IF NOT should_split AND time_gap > MEDIUM_GAP_THRESHOLD:
            IF NOT has_text_overlap(prev_current_text, row.current_text) THEN
                should_split ← TRUE

        // ─────────────────────────────────────────────────────────
        // METHOD 3: Text discontinuity detection  
        // before_text doesn't match expected continuation from prev_current
        // ─────────────────────────────────────────────────────────
        IF NOT should_split AND NOT is_empty_or_placeholder(row.before_text):
            IF length(prev_current_text) > 3 THEN
                IF NOT has_text_overlap(prev_current_text, row.before_text) THEN
                    should_split ← TRUE

        // ─────────────────────────────────────────────────────────
        // METHOD 4: Context change detection
        // ─────────────────────────────────────────────────────────
        IF row.package_name ≠ prev_package_name THEN
            should_split ← TRUE

        // Execute split if needed
        IF should_split AND current_segment_rows ≠ empty THEN
            final_text ← clean_text(prev_current_text)
            IF final_text ≠ "" THEN
                CREATE segment with current_segment_rows and final_text
                APPEND segment to segments
            current_segment_rows ← empty list

        // Add current row to segment
        APPEND row to current_segment_rows
        prev_current_text ← row.current_text
        prev_timestamp ← row.timestamp

    // Finalize last segment
    IF current_segment_rows ≠ empty AND clean_text(prev_current_text) ≠ "" THEN
        CREATE segment with current_segment_rows

    RETURN segments

NOTES:
- Rows with empty final text are excluded (~0.3% of data)
- Long text similarity check handles mid-text editing (e.g., adding emoji bullets)
- AWARE keyboard logger may cache before_text; algorithm compensates for this