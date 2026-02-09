from performance_analyzer.typing_path.enum import TextChangePosition, TextChangeType
from performance_analyzer.typing_path._typingactivity import TypingActivityHelper
from performance_analyzer.typing_path.util import TextChangeCategoryUtil

class TypingPathCalculator:

    def __init__(self, data_list:list):
        self.data_list = data_list
        self._path = self.data_list[0]['before_text']
        self._real_entered_text_length = 0
        self._correction_msd = 0
        self._edit_correction_list = []
        self._auto_completes = []
        self._typing_activity = TypingActivityHelper()

    @property
    def path(self):
        return self._path

    def calculate(self) -> None:
        prev = None
        prev_current_text = None

        for index in range(len(self.data_list)):
            data = self.data_list[index]
            change = TextChangeCategoryUtil.change_type(prev, data)
            current_text = change.current

            if self._typing_activity.is_activity_changed(change):
                self._typing_activity.append_current_activity(change, prev_current_text, index)

            if change.position == TextChangePosition.END:
                if change.type == TextChangeType.INSERT:
                    self._typing_activity.add_to_end_of_current_activity(change.entered)
                elif change.type == TextChangeType.AUTO_COMPLETE:
                    self._typing_activity.add_to_end_of_current_activity(change.entered)
                elif change.type == TextChangeType.DELETE:
                    self._typing_activity.add_to_start_of_current_activity(change.removed)
                elif change.type == TextChangeType.AUTO_CORRECT:
                    self._typing_activity.append_current_activity(change, prev_current_text, index)
                    self._typing_activity.append_current_change(change, index)
            elif change.position == TextChangePosition.INSIDE:
                if change.type == TextChangeType.INSERT:
                    self._typing_activity.add_to_end_of_current_activity(change.entered)
                elif change.type == TextChangeType.AUTO_COMPLETE:
                    self._typing_activity.add_to_end_of_current_activity(change.entered)
                elif change.type == TextChangeType.DELETE:
                    self._typing_activity.add_to_start_of_current_activity(change.removed)
                elif change.type == TextChangeType.AUTO_CORRECT:
                    self._typing_activity.append_current_activity(change, prev_current_text, index)
                    self._typing_activity.append_current_change(change, index)

            self._typing_activity.set_previous_activity_type(change)
            prev_current_text = current_text
            prev = data

        self._typing_activity.append_current_activity(None, prev_current_text, len(self.data_list))

    def detect_edit_operations(self):
        self._typing_activity.detect_edit_operations()

    def print_path(self):
        self._typing_activity.print_activity()
