import re
import os
import string

from performance_analyzer.utils.json import JsonUtil

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_RE_COMBINE_WHITESPACE = re.compile(r"\s+")
KEYBOARD_MAP = JsonUtil.read_file(os.path.join(BASE_DIR, "keyboard.json"))

class StringUtil:

    @staticmethod
    def remove_braces(text:str) -> str:
        """
        Removes the braces ([ and ]) around the text.

        It only changes the text if the first character is [ or the last character is ].

        :param text:
        :return:
        """
        if text.startswith('['):
            text = text[1:]

        if text.endswith(']'):
            text = text[:-1]

        return text

    @staticmethod
    def remove_recurring_spaces(text:str) -> str:
        """
        Removes the recurring spaces inside the text with a single space.

        :param text:
        :return:
        """
        return _RE_COMBINE_WHITESPACE.sub(" ", text).strip()

    @staticmethod
    def remove_first_word(text:str) -> str:
        return ' '.join(text.split(' ')[1:])

    @staticmethod
    def remove_last_word(text:str) -> str:
        return ' '.join(text.split(' ')[:-1])

    @staticmethod
    def equals(original:str, suggestion:str) -> bool:
        if original == suggestion:
            return True
        elif original == '':
            return suggestion.replace("'", '') == ''
        elif suggestion == '':
            return original.replace("'", '') == ''

        c1 = original[0]
        c2 = suggestion[0]

        original_remaining = original[1:]
        suggestion_remaining = suggestion[1:]

        if c1 == "'":
            return StringUtil.equals(original_remaining, suggestion)
        elif c2 == "'":
            return StringUtil.equals(original, suggestion_remaining)
        elif c1 == c2 or c1.lower() == c2.lower():
            return StringUtil.equals(original_remaining, suggestion_remaining)
        elif (c1 == 'i' or c1 == 'ı' or c1 == 'İ' or c1 == 'I') and (c2 == 'i' or c2 == 'ı' or c2 == 'İ' or c2 == 'I'):
            return StringUtil.equals(original_remaining, suggestion_remaining)
        elif (c1 == 'ç' or c1 == 'c' or c1 == 'Ç' or c1 == 'C') and (c2 == 'ç' or c2 == 'c' or c2 == 'Ç' or c2 == 'C'):
            return StringUtil.equals(original_remaining, suggestion_remaining)
        elif (c1 == 'ş' or c1 == 's' or c1 == 'Ş' or c1 == 'S') and (c2 == 'ş' or c2 == 's' or c2 == 'Ş' or c2 == 'S'):
            return StringUtil.equals(original_remaining, suggestion_remaining)
        elif (c1 == 'ğ' or c1 == 'g' or c1 == 'Ğ' or c1 == 'G') and (c2 == 'ğ' or c2 == 'g' or c2 == 'Ğ' or c2 == 'G'):
            return StringUtil.equals(original_remaining, suggestion_remaining)
        elif (c1 == 'ö' or c1 == 'o' or c1 == 'Ö' or c1 == 'O') and (c2 == 'ö' or c2 == 'o' or c2 == 'Ö' or c2 == 'O'):
            return StringUtil.equals(original_remaining, suggestion_remaining)
        elif (c1 == 'ü' or c1 == 'u' or c1 == 'Ü' or c1 == 'U') and (c2 == 'ü' or c2 == 'u' or c2 == 'Ü' or c2 == 'U'):
            return StringUtil.equals(original_remaining, suggestion_remaining)

        return False

    @staticmethod
    def equals_in_same_length(removed:str, reentered:str) -> bool:
        if len(removed) < len(reentered):
            return StringUtil.equals(removed, reentered[:len(removed)])
        return StringUtil.equals(removed, reentered)

    @staticmethod
    def remove_initial_space(text:str) -> str:
        if text.startswith(' '):
            return text[1:]
        return text

    @staticmethod
    def get_word_count(text:str) -> int:
        return len(text.split())

    @staticmethod
    def text_in_equal_length(target_text:str, reference_text:str) -> str:
        if len(reference_text) >= len(target_text):
            return ''

        return StringUtil.remove_initial_space(target_text[:len(reference_text)])

    @staticmethod
    def _string_distance(x:str, y:str, cost_func) -> int:
        # Initialize DP table
        dp = [[0] * (len(y) + 1) for _ in range(len(x) + 1)]

        for i in range(len(x) + 1):
            for j in range(len(y) + 1):
                if i == 0:
                    dp[i][j] = j
                elif j == 0:
                    dp[i][j] = i
                else:
                    dp[i][j] = min(
                        dp[i - 1][j - 1] + cost_func(x[i - 1], y[j - 1]),
                        dp[i - 1][j] + 1,
                        dp[i][j - 1] + 1
                    )

        return dp[len(x)][len(y)]

    @staticmethod
    def string_distance(x:str, y:str) -> int:
        return StringUtil._string_distance(x, y, StringUtil._cost_of_substitution)

    @staticmethod
    def adjacent_string_distance(x:str, y:str) -> int:
        return StringUtil._string_distance(x, y, StringUtil._cost_of_adjacent_substitution)

    @staticmethod
    def is_adjacent(a: str, b: str) -> bool:
        characters = KEYBOARD_MAP.get(a)
        if characters is not None and b in characters:
            return True
        characters = KEYBOARD_MAP.get(b)
        return characters is not None and a in characters

    @staticmethod
    def _cost_of_substitution(a: str, b: str) -> int:
        return 0 if StringUtil.equals(a, b) else 1

    @staticmethod
    def _cost_of_adjacent_substitution(a: str, b: str) -> int:
        return 0 if StringUtil.equals(a, b) or StringUtil.is_adjacent(a, b) else 1

    @staticmethod
    def remove_punctuation(text:str) -> str:
        return text.translate(str.maketrans("", "", string.punctuation))

    @staticmethod
    def remove_consecutive_repetitions(text:str) -> str:
        if len(text) < 2:
            return text
        if text[0] != text[1]:
            return text[0] + StringUtil.remove_consecutive_repetitions(text[1:])
        return StringUtil.remove_consecutive_repetitions(text[1:])
