from enum import Enum

class EditOperationType(Enum):
    REVISION = 1
    """
    User changed his/her mind and decided to write something else. This is not a performance issue.
    """
    CORRECTION = 2
    """
    User made a typing error (typo), realized it and fixed it.
    """
