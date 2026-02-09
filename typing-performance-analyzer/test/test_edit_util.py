import unittest

from performance_analyzer.typing_path import TypingActivity
from performance_analyzer.typing_path.enum import EditOperationType
from performance_analyzer.typing_path.util import EditUtil


class TestEditUtil(unittest.TestCase):

    def test_is_character_order_problem(self):
        self.assertTrue(EditUtil.is_character_order_problem('test', 'estt'))
        self.assertFalse(EditUtil.is_character_order_problem('test', 'tost'))

    def test_is_first_character_correction(self):
        self.assertFalse(EditUtil.is_first_character_correction('', 'test'))
        self.assertTrue(EditUtil.is_first_character_correction('rtest', 'testing'))
        self.assertFalse(EditUtil.is_first_character_correction('rtest', 'texting'))
        self.assertTrue(EditUtil.is_first_character_correction('rtest', 'tes'))
        self.assertFalse(EditUtil.is_first_character_correction('rtest', 'tex'))

    def test_is_accidental_character_problem(self):
        self.assertFalse(EditUtil.is_accidental_character_problem('', 'test'))
        self.assertFalse(EditUtil.is_accidental_character_problem('test', ''))
        self.assertFalse(EditUtil.is_accidental_character_problem('', ''))
        self.assertTrue(EditUtil.is_accidental_character_problem('sampler text', 'sample text'))
        self.assertFalse(EditUtil.is_accidental_character_problem('sample text', 'simple text'))
        self.assertFalse(EditUtil.is_accidental_character_problem('t', 'simple text'))

    def test_is_failed_character_problem(self):
        self.assertFalse(EditUtil.is_failed_character_problem('', 'test'))
        self.assertFalse(EditUtil.is_failed_character_problem('test', ''))
        self.assertFalse(EditUtil.is_failed_character_problem('', ''))
        self.assertTrue(EditUtil.is_failed_character_problem('sampl text', 'sample text'))
        self.assertFalse(EditUtil.is_failed_character_problem('sample text', 'simple text'))
        self.assertFalse(EditUtil.is_failed_character_problem('t', 'simple text'))
        self.assertFalse(EditUtil.is_failed_character_problem('simple text', 't'))

    def test_is_adjacent_change(self):
        self.assertFalse(EditUtil.is_adjacent_change('', 'test'))
        self.assertFalse(EditUtil.is_adjacent_change('west', 'test'))
        self.assertTrue(EditUtil.is_adjacent_change('test', 'text'))
        self.assertTrue(EditUtil.is_adjacent_change('tester', 'text'))
        self.assertTrue(EditUtil.is_adjacent_change('test', 'texting'))
        self.assertFalse(EditUtil.is_adjacent_change('tester', 'texting'))

    def test_is_accident_while_shift_error(self):
        self.assertFalse(EditUtil.is_accident_while_shift_error('one', 'two'))
        self.assertFalse(EditUtil.is_accident_while_shift_error('twe', 'two'))
        self.assertFalse(EditUtil.is_accident_while_shift_error('zoo', ''))
        self.assertTrue(EditUtil.is_accident_while_shift_error('zshift', 'Shift'))
        self.assertFalse(EditUtil.is_accident_while_shift_error('z', 'shift'))
        self.assertTrue(EditUtil.is_accident_while_shift_error('z', 'Shift'))

    def test_is_transposition_error(self):
        self.assertFalse(EditUtil.is_transposition_error('one', 'two'))
        self.assertFalse(EditUtil.is_transposition_error('', 'two'))
        self.assertFalse(EditUtil.is_transposition_error('one', ''))
        self.assertTrue(EditUtil.is_transposition_error('oen', 'one'))
        self.assertTrue(EditUtil.is_transposition_error('noe', 'one'))

    def _get_activity(self, text:str) -> TypingActivity:
        return TypingActivity(0, '', text)

    def test_get_edit_correction_status(self):
        self.assertEqual(EditOperationType.CORRECTION, EditUtil.get_edit_correction_status(self._get_activity('Dinlerimbirazdan'), self._get_activity('Dinlerim birazdan'), None))
        self.assertEqual(EditOperationType.CORRECTION, EditUtil.get_edit_correction_status(self._get_activity('doktoryn'), self._get_activity('doktorun'), None))
        self.assertEqual(EditOperationType.CORRECTION, EditUtil.get_edit_correction_status(self._get_activity('zmiddle East'), self._get_activity('Middle East'), None))
        self.assertEqual(EditOperationType.CORRECTION, EditUtil.get_edit_correction_status(self._get_activity('Zaten'), self._get_activity('Zatn'), None))
        self.assertEqual(EditOperationType.CORRECTION, EditUtil.get_edit_correction_status(self._get_activity('Ameriakya'), self._get_activity('Amerikaya '), None))
        self.assertEqual(EditOperationType.REVISION, EditUtil.get_edit_correction_status(self._get_activity('kedi, köpek'), self._get_activity('kedi ve köpek '), None))
        self.assertEqual(EditOperationType.REVISION, EditUtil.get_edit_correction_status(self._get_activity('cat, dog'), self._get_activity('cat and dog '), None))
        self.assertEqual(EditOperationType.CORRECTION, EditUtil.get_edit_correction_status(self._get_activity('okula.gittim'), self._get_activity('okula gittim'), None))
        self.assertEqual(EditOperationType.CORRECTION, EditUtil.get_edit_correction_status(self._get_activity('mountins'), self._get_activity('mountains'), None))

if __name__ == '__main__':
    unittest.main()
