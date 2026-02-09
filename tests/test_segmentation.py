
import pytest
import pandas as pd
from segmentation import Segmenter, SegmentationConfig

class TestSegmenter:
    
    def test_basic_segmentation_gap(self, mapping):
        """Test segmentation by time gap."""
        data = [
            {"rowid": 1, "timestamp": 1000, "current_text": "h", "key_character": "h"},
            {"rowid": 2, "timestamp": 1100, "current_text": "hi", "key_character": "i"},
            # > 10s gap
            {"rowid": 3, "timestamp": 20000, "current_text": "w", "key_character": "w"},
            {"rowid": 4, "timestamp": 20100, "current_text": "wo", "key_character": "o"},
        ]
        df = pd.DataFrame(data)
        cfg = SegmentationConfig(gap_seconds=10.0)
        segmenter = Segmenter(df, mapping, cfg)
        segments = segmenter.segment()
        
        assert len(segments) == 2
        assert segments[0]["text"] == "hi"
        assert segments[1]["text"] == "wo"

    def test_segmentation_enter_key(self, mapping):
        """Test segmentation by Enter key."""
        data = [
            {"rowid": 1, "timestamp": 1000, "current_text": "hello", "key_character": "o", "key_code": 33},
            {"rowid": 2, "timestamp": 1100, "current_text": "hello", "key_character": "\n", "key_code": 66}, # Enter
            {"rowid": 3, "timestamp": 1200, "current_text": "world", "key_character": "w", "key_code": 44},
        ]
        df = pd.DataFrame(data)
        cfg = SegmentationConfig(enter_codes={66})
        segmenter = Segmenter(df, mapping, cfg)
        segments = segmenter.segment()
        
        assert len(segments) == 2
        assert segments[0]["text"] == "hello"
        assert segments[1]["text"] == "world"

    def test_segmentation_context_change(self, mapping):
        """Test segmentation by app/package change."""
        data = [
            {"rowid": 1, "timestamp": 1000, "current_text": "msg1", "package_name": "com.whatsapp"},
            {"rowid": 2, "timestamp": 1100, "current_text": "msg1", "package_name": "com.whatsapp"},
            # App switch
            {"rowid": 3, "timestamp": 1200, "current_text": "search", "package_name": "com.google.android.googlequicksearchbox"},
        ]
        df = pd.DataFrame(data)
        cfg = SegmentationConfig(finalize_on_context_change=True)
        segmenter = Segmenter(df, mapping, cfg)
        segments = segmenter.segment()
        
        assert len(segments) == 2
        assert segments[0]["text"] == "msg1"
        assert segments[0]["package"] == "com.whatsapp"
        assert segments[1]["text"] == "search"
        assert segments[1]["package"] == "com.google.android.googlequicksearchbox"

    def test_segmentation_before_text_empty(self, mapping):
        """Test segmentation when before_text becomes empty (message sent)."""
        data = [
            # User typing "hi"
            {"rowid": 1, "timestamp": 1000, "current_text": "h", "before_text": ""},
            {"rowid": 2, "timestamp": 1100, "current_text": "hi", "before_text": "h"},
            # Message sent, field cleared. Next key sets before_text=""
            {"rowid": 3, "timestamp": 1500, "current_text": "y", "before_text": ""},
            {"rowid": 4, "timestamp": 1600, "current_text": "yo", "before_text": "y"},
        ]
        df = pd.DataFrame(data)
        cfg = SegmentationConfig()
        segmenter = Segmenter(df, mapping, cfg)
        segments = segmenter.segment()
        
        assert len(segments) == 2
        assert segments[0]["text"] == "hi"
        assert segments[1]["text"] == "yo"

    def test_continuous_editing_search_box(self, mapping):
        """Test that search box editing (submit but keep text) is NOT segmented."""
        data = [
            # Typing "test"
            {"rowid": 1, "timestamp": 1000, "current_text": "test", "before_text": "tes"},
            # Search submitted, input might clear or stay, but user keeps typing "testing"
            # Here, imagine the logger sees before_text="" but the text is still "test"
            # This is the tricky case the algorithm handles
            {"rowid": 2, "timestamp": 2000, "current_text": "testi", "before_text": "test"},
            {"rowid": 3, "timestamp": 2100, "current_text": "testing", "before_text": "testi"},
        ]
        df = pd.DataFrame(data)
        cfg = SegmentationConfig()
        segmenter = Segmenter(df, mapping, cfg)
        segments = segmenter.segment()
        
        # Should be ONE segment because "testing" contains "test"
        assert len(segments) == 1
        assert segments[0]["text"] == "testing"

