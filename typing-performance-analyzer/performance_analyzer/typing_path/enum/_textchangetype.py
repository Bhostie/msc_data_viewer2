from enum import Enum

class TextChangeType(Enum):
    INSERT = 1
    """
    The user entered one or more characters without deleting any character from the previous text.
    """
    DELETE = 2
    """
    The user removed one or more characters without inserting any character to the previous text.
    """
    AUTO_CORRECT = 3
    """
    The user replaced one or more characters with another set of characters.
    """
    AUTO_COMPLETE = 4
    """
    The user entered multiple characters without deleting any character from the previous text.
    """
    NO_CHANGE = 5
    """
    The previous text and the current text are exactly the same.
    """
