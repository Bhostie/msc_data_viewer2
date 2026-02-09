from performance_analyzer.typing_path.enum import TextChangePosition, TextChangeType, EditOperationType
from performance_analyzer.typing_path.util import EditUtil


class TypingActivity:

    def __init__(self, index:int, removed:str, entered:str):
        self._index = index
        self._removed = removed
        self._entered = entered
        self._before = None
        self._current = None
        self._type = None
        self._position = None
        self._start_index = None
        self._end_index = None
        self._edit_correction = None

    @property
    def index(self):
        return self._index

    @property
    def removed(self):
        return self._removed

    @property
    def entered(self):
        return self._entered

    @property
    def before(self):
        return self._before

    @before.setter
    def before(self, before: int):
        self._before = before

    @property
    def current(self):
        return self._current

    @current.setter
    def current(self, current: int):
        self._current = current

    @property
    def type(self):
        return self._type

    @type.setter
    def type(self, change_type):
        self._type = change_type

    @property
    def position(self):
        return self._position

    @position.setter
    def position(self, position):
        self._position = position

    @property
    def end_index(self):
        return self._end_index

    @end_index.setter
    def end_index(self, end_index):
        self._end_index = end_index

    @property
    def start_index(self):
        return self._start_index

    @start_index.setter
    def start_index(self, start_index):
        self._start_index = start_index

    @property
    def edit_correction(self) -> EditOperationType:
        return self._edit_correction

    @edit_correction.setter
    def edit_correction(self, edit_correction: EditOperationType):
        self._edit_correction = edit_correction

class TypingActivityHelper:

    def __init__(self):
        self._activity_list = []
        self._current_activity = ''
        self._current_activity_start_index = 0
        self._current_activity_end_index = 0
        self._prev_change_type = TextChangeType.INSERT
        self._prev_change_position = TextChangePosition.END
        self._initial_text = ''
        self._initial_index = 0

    def append_current_change(self, change, index:int):
        activity = TypingActivity(change.index, change.removed, change.entered)
        activity.type = change.type
        activity.position = change.position
        activity.before = change.before
        activity.current = change.current
        activity.start_index = index
        activity.end_index = index
        self._activity_list.append(activity)
        self._current_activity = ''
        self._current_activity_start_index = change.index
        self._initial_text = change.current

    def append_current_activity(self, change, current_text:str, index:int):
        if self._current_activity != '':
            activity = TypingActivity(self._current_activity_start_index, '', self._current_activity)
            activity.type = self._prev_change_type
            activity.position = self._prev_change_position
            activity.before = self._initial_text
            activity.current = current_text
            activity.start_index = self._initial_index
            activity.end_index = index
            self._activity_list.append(activity)
            self._current_activity = ''
            if change is not None:
                self._current_activity_start_index = change.index
            self._initial_text = current_text
            self._initial_index = index

    def is_activity_changed(self, change):
        return ((change.type != self._prev_change_type or change.position != self._prev_change_position)
                and change.type != TextChangeType.NO_CHANGE)

    def set_previous_activity_type(self, change):
        if change.type != TextChangeType.NO_CHANGE:
            self._prev_change_type = change.type
            self._prev_change_position = change.position

    def print_activity(self):
        size = 0

        for activity in self._activity_list:
            position = size
            if activity.position == TextChangePosition.INSIDE:
                position = activity.index
                if activity.entered.startswith(' '):
                    position -= 1
                if activity.type == TextChangeType.DELETE:
                    position -= len(activity.entered) - 1
                    if activity.entered.endswith(' '):
                        position -= 1
            else:
                if activity.type == TextChangeType.DELETE:
                    position -= len(activity.entered)

            if activity.type == TextChangeType.DELETE:
                size -= len(activity.entered)
                print((' ' * position) + self._visualize_space(activity.entered) + ' < ' + activity.type.name + self._get_edit_operation_name(activity))
            elif activity.type == TextChangeType.AUTO_CORRECT:
                size -= len(activity.removed)
                print((' ' * position) + self._visualize_space(activity.removed) + ' <<>>')
                print((' ' * position) + self._visualize_space(activity.entered.strip()) + ' <<>> ' + activity.type.name + self._get_edit_operation_name(activity))
            elif activity.type == TextChangeType.AUTO_COMPLETE:
                print((' ' * position) + self._visualize_space(activity.entered) + ' >>>> ' + activity.type.name + self._get_edit_operation_name(activity))
            else:
                print((' ' * position) + self._visualize_space(activity.entered) + ' > ' + activity.type.name + self._get_edit_operation_name(activity))

            #print(self._get_activity_details(activity))

            if activity.type != TextChangeType.DELETE or activity.position != TextChangePosition.END:
                size += len(activity.entered)

    def _get_edit_operation_name(self, activity):
        if activity is None or activity.edit_correction is None:
            return ''
        return ' (' + activity.edit_correction.name.lower() + ')'

    def detect_edit_operations(self):
        prev_activity = None
        reversed_activity_list = self._activity_list[::-1]
        for i in range(len(reversed_activity_list) - 1):
            activity = reversed_activity_list[i]
            next_activity = reversed_activity_list[i + 1]

            if activity.type == TextChangeType.DELETE:
                if prev_activity is None:
                    activity.edit_correction = EditOperationType.REVISION
                else:
                    activity.edit_correction = EditUtil.get_edit_correction_status(activity, prev_activity, next_activity)

            elif activity.type == TextChangeType.AUTO_CORRECT:
                activity.edit_correction = EditOperationType.CORRECTION

            prev_activity = activity



    @staticmethod
    def _get_activity_details(activity) -> str:
        value = '\n' + str(activity.start_index) + ' -> ' + str(activity.end_index) + '\n'

        if activity.before is not None:
            value += TypingActivityHelper._visualize_space(activity.before) + ' <---- Initial'
        else:
            value += 'None'
        value += '\n'
        if activity.current is not None:
            value += TypingActivityHelper._visualize_space(activity.current) + ' <---- Final'
        else:
            value += 'None'
        value += '\n'

        return value

    @staticmethod
    def _visualize_space(text:str):
        if text == ' ':
            return '_'
        if text.endswith(' '):
            return text[:-1] + '_'
        return text

    def add_to_end_of_current_activity(self, text):
        self._current_activity += text

    def add_to_start_of_current_activity(self, text):
        self._current_activity = text + self._current_activity

