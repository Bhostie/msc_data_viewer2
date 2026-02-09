from performance_analyzer.typing_path.util._textchange import TextChangeResult
from performance_analyzer.utils.string import StringUtil

class WordChangeUtil:

    @staticmethod
    def get_text_change(before_text:str, current_text:str) -> TextChangeResult:
        """
        Calculates the change in text between two texts in word level.

        :param before_text: the text before the change.
        :param current_text: the text after the change.
        :return: change between the two texts.
        """
        return WordChangeUtil._get_text_change(0,
                                               StringUtil.remove_recurring_spaces(before_text),
                                               StringUtil.remove_recurring_spaces(current_text))

    @staticmethod
    def _get_text_change(index: int, before_text:str, current_text:str) -> TextChangeResult:
        if before_text == '' or current_text == '':
            return TextChangeResult(index, before_text, current_text)

        before_text_split = before_text.split()
        current_text_split = current_text.split()

        if len(before_text_split) <= 1 and len(current_text_split) <= 1:
            return TextChangeResult(index, before_text, current_text)

        before_first_word = before_text_split[0]
        current_first_word = current_text_split[0]

        if StringUtil.equals(before_first_word, current_first_word):
            return WordChangeUtil._get_text_change(index + len(before_first_word),
                                                   StringUtil.remove_first_word(before_text),
                                                   StringUtil.remove_first_word(current_text))

        before_last_word = before_text_split[-1]
        current_last_word = current_text_split[-1]

        if StringUtil.equals(before_last_word, current_last_word):
            return WordChangeUtil._get_text_change(index,
                                                   StringUtil.remove_last_word(before_text),
                                                   StringUtil.remove_last_word(current_text))

        return TextChangeResult(index, before_text, current_text)
