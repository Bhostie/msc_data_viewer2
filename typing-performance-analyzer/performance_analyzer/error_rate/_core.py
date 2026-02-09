from performance_analyzer.utils.string import StringUtil

class ErrorRateCalculator:
    """
    A class to calculate error rate metrics
    """

    def __init__(self, data_list:list):
        self.data_list = data_list
        self.initial_text = self._get_initial_text()
        self.final_text = self._get_final_text()

    def kspc(self, additional_characters:int = 0) -> float:
        """
        KSPC (keystrokes per character) is the ratio of the total entered character count
        to the length of the transcribed string.

        :param additional_characters: additional characters deleted by user due to changing mind
        :return: calculated kspc value
        """
        session_size = len(self.data_list)
        transcribed_text_length = (len(self.final_text) - len(self.initial_text)) + additional_characters

        if transcribed_text_length == 0:
            return 0
        else:
            return session_size / transcribed_text_length

    def get_final_text(self):
        return self.final_text

    def _get_final_text(self) -> str:
        current_text = self.data_list[len(self.data_list) - 1]['current_text']
        return StringUtil.remove_braces(current_text)

    def _get_initial_text(self) -> str:
        return self.data_list[0]['before_text']

