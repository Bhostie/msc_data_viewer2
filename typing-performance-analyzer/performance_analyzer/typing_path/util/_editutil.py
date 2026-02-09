from performance_analyzer.spellcheck import SpellChecker
from performance_analyzer.typing_path.enum import EditOperationType, TextChangeType
from performance_analyzer.typing_path.util import CharacterChangeUtil
from performance_analyzer.typing_path.util._wordchangeutil import WordChangeUtil
from performance_analyzer.utils.string import StringUtil

class EditUtil:

    @staticmethod
    def get_edit_correction_status(activity, prev_activity, next_activity) -> EditOperationType | None:
        removed_text = activity.entered
        entered_text = prev_activity.entered

        if EditUtil.is_adjacent_change(removed_text, entered_text):
            return EditOperationType.CORRECTION

        if EditUtil.is_accident_while_shift_error(removed_text, entered_text):
            return EditOperationType.CORRECTION

        if EditUtil.is_transposition_error(removed_text, entered_text):
            return EditOperationType.CORRECTION

        change = CharacterChangeUtil.get_text_change(removed_text.strip(), entered_text.strip())

        if ',' == change.removed.strip() and ('ve' == change.entered.strip() or 'and' == change.entered.strip()):
            return EditOperationType.REVISION

        if StringUtil.remove_punctuation(removed_text) == StringUtil.remove_punctuation(entered_text):
            return EditOperationType.CORRECTION

        if change.entered.lower() == change.removed.lower():
            return EditOperationType.CORRECTION

        if ' ' in removed_text and removed_text.replace(' ', '') in entered_text:
            return EditOperationType.CORRECTION

        if StringUtil.remove_consecutive_repetitions(entered_text).lower() == StringUtil.remove_consecutive_repetitions(removed_text).lower():
            return EditOperationType.CORRECTION

        if len(removed_text) > 3 and len(entered_text) > 3 and len(change.entered) == 1 and change.removed == '':
            return EditOperationType.CORRECTION

        if len(removed_text) > 3 and len(entered_text) > 3 and len(change.removed) == 1 and change.entered == '':
            return EditOperationType.CORRECTION

        if len(removed_text) > 3 and len(entered_text) > 3 and len(change.removed) == 1 and len(change.entered) == 1:
            return EditOperationType.CORRECTION

        edit_state_by_suggestion = EditUtil.get_state_by_suggestion(removed_text, entered_text)
        if edit_state_by_suggestion is not None:
            return edit_state_by_suggestion

        edit_state_by_normalization = EditUtil.get_state_by_normalization(removed_text, entered_text)
        if edit_state_by_normalization is not None:
            return edit_state_by_normalization

        if EditUtil.is_character_order_problem(removed_text, entered_text):
            return EditOperationType.CORRECTION

        if EditUtil.is_first_character_correction(removed_text, entered_text):
            return EditOperationType.CORRECTION

        if EditUtil.is_failed_character_problem(removed_text, entered_text):
            return EditOperationType.CORRECTION

        if EditUtil.is_accidental_character_problem(removed_text, entered_text):
            return EditOperationType.CORRECTION

        if EditUtil.is_same_stem(next_activity, removed_text, entered_text):
            return EditOperationType.CORRECTION

        change_distance = StringUtil.string_distance(removed_text, entered_text)
        if 4 * change_distance > (len(removed_text) + len(entered_text)):
            return EditOperationType.REVISION

        word_change = WordChangeUtil.get_text_change(activity.before, prev_activity.current)
        if word_change.removed.strip() == '' and word_change.entered.strip() != '':
            return EditOperationType.REVISION

        if word_change.entered.strip() == '' and word_change.removed.strip() != '':
            return EditOperationType.REVISION

        word_change_distance = StringUtil.string_distance(word_change.removed, word_change.entered)

        if word_change_distance * 4 > len(word_change.entered) + len(word_change.removed):
            return EditOperationType.REVISION

        if not EditUtil.is_auto_correct(next_activity) and EditUtil.is_correct(word_change.removed):
            return EditOperationType.REVISION

        return EditOperationType.CORRECTION

    @staticmethod
    def is_adjacent_change(removed_text, entered_text) -> bool:
        min_len = min(len(removed_text), len(entered_text))

        if min_len == 0:
            return False

        adjacent_string_distance = StringUtil.adjacent_string_distance(removed_text[:min_len], entered_text[:min_len])
        return adjacent_string_distance == 0

    @staticmethod
    def is_accident_while_shift_error(removed:str, entered:str) -> bool:
        if removed.startswith('z') and entered != '':
            removed = removed[1:]
            entered_initial = entered[0]

            if removed != '':
                removed_initial = removed[0]
                return removed_initial.upper() == entered_initial

            return entered_initial == entered_initial.upper()

        return False

    @staticmethod
    def is_transposition_error(removed:str, entered:str) -> bool:
        if len(removed) > len(entered):
            removed = removed[:len(entered)]

        if len(entered) > len(removed):
            entered = entered[:len(removed)]

        change = CharacterChangeUtil.get_text_change(removed, entered)

        return len(change.entered) == 2 and change.entered.lower() == change.removed.lower()[::-1]

    @staticmethod
    def is_failed_character_problem(removed:str, entered:str) -> bool:
        if removed == '' or entered == '':
            return False

        removed_initial = removed[0]
        entered_initial = entered[0]

        if removed_initial == entered_initial:
            return EditUtil.is_failed_character_problem(removed[1:], entered[1:])

        if len(removed) >= 1 and len(entered) > 1:
            entered = entered[1:]
            return removed.startswith(entered) or (len(entered) >= 2 and entered[:-1].startswith(removed))

        return False

    @staticmethod
    def is_accidental_character_problem(removed:str, entered:str) -> bool:
        if removed == '' or entered == '':
            return False

        removed_initial = removed[0]
        entered_initial = entered[0]

        if removed_initial == entered_initial:
            return EditUtil.is_accidental_character_problem(removed[1:], entered[1:])

        if len(removed) > 1 and len(entered) >= 1:
            removed = removed[1:]
            return entered.startswith(removed) or removed.startswith(entered)

        return False

    @staticmethod
    def is_first_character_correction(removed:str, entered:str) -> bool:
        if len(removed) > 1:
            removed = removed[1:]
            if len(removed) >  len(entered):
                removed = removed[:len(entered)]
            return entered.startswith(removed)
        return False

    @staticmethod
    def is_character_order_problem(removed:str, entered:str) -> bool:
        return ''.join(sorted(removed)).strip() == ''.join(sorted(entered)).strip()

    @staticmethod
    def get_state_by_suggestion(removed:str, entered:str) -> EditOperationType | None:
        if StringUtil.get_word_count(removed) >= 2:
            removed_segments = removed.split()
            entered_segments = entered.split()

            if len(removed_segments) == len(entered_segments):
                if EditUtil.are_segments_in_suggestion(removed_segments, entered_segments):
                    return EditOperationType.CORRECTION
        else:
            suggestions = SpellChecker.suggest(removed)
            if EditUtil.is_in_suggestion(entered, suggestions, True):
                return EditOperationType.CORRECTION

        return None

    @staticmethod
    def are_segments_in_suggestion(removed_segments, entered_segments):
        is_suggestion = True

        for i in range(len(removed_segments)):
            removed_segment = removed_segments[i]
            entered_segment = entered_segments[i]

            if removed_segment != entered_segment:
                suggestions = SpellChecker.suggest(removed_segment)
                if not EditUtil.is_in_suggestion(entered_segment, suggestions, i >= len(removed_segments) - 1):
                    is_suggestion = False
                    break

        return is_suggestion

    @staticmethod
    def is_in_suggestion(entered, suggestions, check_start:bool) -> bool:
        for suggestion in suggestions:
            if suggestion.lower() == entered.lower():
                return True

            if check_start and suggestion.startswith(entered):
                return True

        return False

    @staticmethod
    def get_state_by_normalization(removed_text, entered_text):
        #TODO: implement
        return None

    @staticmethod
    def is_auto_correct(next_activity):
        return next_activity is not None and next_activity.type == TextChangeType.AUTO_CORRECT

    @staticmethod
    def is_same_stem(next_activity, removed_text, entered_text):
        if not EditUtil.is_auto_correct(next_activity):
            return False

        #TODO: implement
        return False

    @staticmethod
    def is_correct(removed_text):
        if len(removed_text) <= 3:
            return False

        words = removed_text.split()
        if len(words) > 1:
            is_correct = True
            for word in words:
                if not SpellChecker.check_spelling(word):
                    is_correct = False
                    break
            return is_correct
        else:
            return SpellChecker.check_spelling(removed_text)
