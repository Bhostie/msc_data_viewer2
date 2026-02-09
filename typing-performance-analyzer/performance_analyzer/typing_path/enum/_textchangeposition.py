from enum import Enum

class TextChangePosition(Enum):
    END = 1
    """
    The change is at the end of the sequence.
    """
    INSIDE = 2
    """
    The change is inside the text. Some part of the text previously writen may come after this change in the final text.
    """
