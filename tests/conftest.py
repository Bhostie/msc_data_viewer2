
import pytest
import pandas as pd
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

@pytest.fixture
def mapping():
    return {
        "pk": "rowid",
        "timestamp": "timestamp",
        "key_code": "key_code",
        "key_character": "key_character",
        "text": "current_text",
        "package": "package_name",
        "label": "view_label",
        "action": "key_action",
    }
