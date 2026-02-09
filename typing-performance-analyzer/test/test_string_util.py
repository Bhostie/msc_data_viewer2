import unittest

from performance_analyzer.utils.string import StringUtil


class TestStringUtil(unittest.TestCase):

    def test_remove_braces(self):
        self.assertEqual('test', StringUtil.remove_braces('[test]'))
        self.assertEqual('test', StringUtil.remove_braces('[test'))
        self.assertEqual('test', StringUtil.remove_braces('test]'))
        self.assertEqual('test', StringUtil.remove_braces('test'))
        self.assertEqual('te]st', StringUtil.remove_braces('te]st'))
        self.assertEqual(']test[', StringUtil.remove_braces(']test['))

    def test_remove_recurring_spaces(self):
        self.assertEqual('test', StringUtil.remove_recurring_spaces('test'))
        self.assertEqual('This is a test sentence.', StringUtil.remove_recurring_spaces('This is a test sentence.'))
        self.assertEqual('This is a test sentence.', StringUtil.remove_recurring_spaces('This is a test  sentence.'))
        self.assertEqual('This is a test sentence.', StringUtil.remove_recurring_spaces('This is a test   sentence.'))

    def test_remove_first_word(self):
        self.assertEqual('', StringUtil.remove_first_word('test'))
        self.assertEqual('is a test sentence.', StringUtil.remove_first_word('This is a test sentence.'))

    def test_remove_last_word(self):
        self.assertEqual('', StringUtil.remove_last_word('test'))
        self.assertEqual('This is a test', StringUtil.remove_last_word('This is a test sentence.'))

    def test_equals(self):
        self.assertTrue(StringUtil.equals('', ''))
        self.assertTrue(StringUtil.equals('Test', 'Test'))
        self.assertTrue(StringUtil.equals('Test\'', 'Test'))
        self.assertTrue(StringUtil.equals('Test', 'Test\''))
        self.assertTrue(StringUtil.equals('\'Test', 'Test'))
        self.assertTrue(StringUtil.equals('Test', '\'Test'))
        self.assertTrue(StringUtil.equals('Test', 'test'))
        self.assertTrue(StringUtil.equals('çşğüöıÇŞĞÜÖİ', 'csguoiCSGUOI'))
        self.assertFalse(StringUtil.equals('Test', 'Text'))

    def test_equals_in_same_length(self):
        self.assertTrue(StringUtil.equals_in_same_length('Test', 'Testing'))
        self.assertTrue(StringUtil.equals_in_same_length('Test', 'Test'))
        self.assertFalse(StringUtil.equals_in_same_length('Test', 'Texting'))
        self.assertFalse(StringUtil.equals_in_same_length('Test', 'Text'))

    def test_remove_initial_space(self):
        self.assertEqual('', StringUtil.remove_initial_space(''))
        self.assertEqual('Test', StringUtil.remove_initial_space('Test'))
        self.assertEqual('Test', StringUtil.remove_initial_space(' Test'))
        self.assertEqual(' Test', StringUtil.remove_initial_space('  Test'))

    def test_get_word_count(self):
        self.assertEqual(0, StringUtil.get_word_count(''))
        self.assertEqual(1, StringUtil.get_word_count('Test'))
        self.assertEqual(5, StringUtil.get_word_count('This is a test sentence.'))

    def test_text_in_equal_length(self):
        self.assertEqual('', StringUtil.text_in_equal_length('', ''))
        self.assertEqual('', StringUtil.text_in_equal_length('Test', 'Testing'))
        self.assertEqual('Test', StringUtil.text_in_equal_length('Testing', 'Test'))
        self.assertEqual('Test', StringUtil.text_in_equal_length('Testing', 'Text'))

    def test_string_distance(self):
        self.assertEqual(0, StringUtil.string_distance('Test', 'Test'))
        self.assertEqual(0, StringUtil.string_distance('Test', 'Teşt'))
        self.assertEqual(1, StringUtil.string_distance('Test', 'Text'))
        self.assertEqual(4, StringUtil.string_distance('Test', 'Texting'))
        self.assertEqual(1, StringUtil.string_distance('Test', 'Text'))
        self.assertEqual(0, StringUtil.string_distance('', ''))
        self.assertEqual(5, StringUtil.string_distance('', 'Hello'))
        self.assertEqual(3, StringUtil.string_distance('kitten', 'sitting'))
        self.assertEqual(1, StringUtil.string_distance('abc', 'ab'))
        self.assertEqual(1, StringUtil.string_distance('abc', 'adc'))
        self.assertEqual(2, StringUtil.string_distance('flaw', 'lawn'))
        self.assertEqual(1, StringUtil.string_distance('a', 'b'))
        self.assertEqual(3, StringUtil.string_distance('Saturday', 'Sunday'))
        self.assertEqual(3, StringUtil.string_distance('abcdef', 'azced'))

    def test_adjacent_string_distance(self):
        self.assertEqual(0, StringUtil.adjacent_string_distance('Test', 'Test'))
        self.assertEqual(0, StringUtil.adjacent_string_distance('Test', 'Teşt'))
        self.assertEqual(0, StringUtil.adjacent_string_distance('Test', 'Text'))
        self.assertEqual(3, StringUtil.adjacent_string_distance('Test', 'Texting'))
        self.assertEqual(0, StringUtil.adjacent_string_distance('', ''))
        self.assertEqual(5, StringUtil.adjacent_string_distance('', 'Hello'))
        self.assertEqual(3, StringUtil.adjacent_string_distance('kitten', 'sitting'))
        self.assertEqual(1, StringUtil.adjacent_string_distance('abc', 'ab'))
        self.assertEqual(1, StringUtil.adjacent_string_distance('abc', 'adc'))
        self.assertEqual(2, StringUtil.adjacent_string_distance('flaw', 'lawn'))
        self.assertEqual(1, StringUtil.adjacent_string_distance('a', 'b'))
        self.assertEqual(3, StringUtil.adjacent_string_distance('Saturday', 'Sunday'))
        self.assertEqual(2, StringUtil.adjacent_string_distance('abcdef', 'azced'))

    def test_is_adjacent(self):
        self.assertTrue(StringUtil.is_adjacent('a', 's'))
        self.assertTrue(StringUtil.is_adjacent('q', 'w'))
        self.assertFalse(StringUtil.is_adjacent('q', 'f'))
        self.assertFalse(StringUtil.is_adjacent('Z', 'U'))

    def test_remove_punctuation(self):
        self.assertEqual('Sample text', StringUtil.remove_punctuation('Sample text'))
        self.assertEqual('123456789', StringUtil.remove_punctuation('123456789'))
        self.assertEqual('Sample text', StringUtil.remove_punctuation('Sample text!'))
        self.assertEqual('Sample text', StringUtil.remove_punctuation('Sample text.'))
        self.assertEqual('Sample text', StringUtil.remove_punctuation('Sample text...'))
        self.assertEqual('Sample text', StringUtil.remove_punctuation('Sample text,'))
        self.assertEqual('Sample text', StringUtil.remove_punctuation('Sample text?'))
        self.assertEqual('Sample text', StringUtil.remove_punctuation('Sample text*'))
        self.assertEqual('Sample text', StringUtil.remove_punctuation('Sample text&'))
        self.assertEqual('Sample text', StringUtil.remove_punctuation('Sample text|'))
        self.assertEqual('Sample text', StringUtil.remove_punctuation('Sample text>'))
        self.assertEqual('Sample text', StringUtil.remove_punctuation('Sample text<'))
        self.assertEqual('Sample text', StringUtil.remove_punctuation('Sample text^'))
        self.assertEqual('1234', StringUtil.remove_punctuation('12.34'))
        self.assertEqual('1234', StringUtil.remove_punctuation('12,34'))

    def test_remove_consecutive_repetitions(self):
        self.assertEqual('Sample text', StringUtil.remove_consecutive_repetitions('Sample text'))
        self.assertEqual('Sample text', StringUtil.remove_consecutive_repetitions('Sampleeeee text'))
        self.assertEqual('Sample text', StringUtil.remove_consecutive_repetitions('Sample texttttttt'))
        self.assertEqual('Sample text', StringUtil.remove_consecutive_repetitions('SSSSSSSample text'))
        self.assertEqual('Samplele text', StringUtil.remove_consecutive_repetitions('Samplele text'))

if __name__ == '__main__':
    unittest.main()
