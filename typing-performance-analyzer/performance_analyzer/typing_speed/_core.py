from performance_analyzer.utils.string import StringUtil

MILLISECONDS = 1000.0
WORD_PER_MINUTE = 12

class TypingSpeedCalculator:
    """
    A class to calculate typing speed metrics
    """

    def __init__(self, data_list:list):
        self.data_list = data_list
        self.initial_text = self._get_initial_text()
        self.final_text = self._get_final_text()
        self.duration = self._calculate_duration()

    def wpm(self, interrupted_time:int = 0) -> float:
        """
        WPM (words per minute) considers only the length of transcribed text and how long it takes
        to produce it. It considers a word every five characters entered and measures the number
        of words typed in a minute.

        :param interrupted_time: any interrupted time during the session (received calls or switching to another app)
        :return: calculated wpm value
        """
        final_character_count = len(self.final_text) - len(self.initial_text)
        duration = self.duration - (interrupted_time / MILLISECONDS)

        if duration <= 0:
            return 0

        return (final_character_count - 1) / duration * WORD_PER_MINUTE

    def ksps(self, interrupted_time:int = 0) -> float:
        """
        KSPS (keystrokes per second) is the number of keystrokes made in a second.
        It is useful when taking error corrections into account.

        :param interrupted_time: any interrupted time during the session (received calls or switching to another app)
        :return: calculated ksps value
        """
        duration = self.duration - (interrupted_time / MILLISECONDS)

        if duration <= 0:
            return 0

        return (len(self.data_list) - 1) / duration

    def get_duration(self):
        """

        :return: session duration in seconds
        """
        return self.duration

    def get_final_text(self):
        return self.final_text

    def _get_final_text(self) -> str:
        current_text = self.data_list[len(self.data_list) - 1]['current_text']
        return StringUtil.remove_braces(current_text)

    def _get_initial_text(self) -> str:
        return self.data_list[0]['before_text']

    def _calculate_duration(self) -> float:
        start = int(self.data_list[0]['timestamp'])
        end = int(self.data_list[len(self.data_list) - 1]['timestamp'])
        return (end - start) / MILLISECONDS
