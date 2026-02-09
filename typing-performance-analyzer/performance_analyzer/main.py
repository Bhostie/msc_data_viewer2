from performance_analyzer.error_rate import ErrorRateCalculator
from performance_analyzer.typing_path import TypingPathCalculator
from performance_analyzer.typing_speed import TypingSpeedCalculator
from utils.json import JsonUtil
import json

def main():
    base = 'samples/'
    keyboards = ['gboard', 'swiftkey', 'samsung']
    cases = [
        'normal',
        'normal_2',
        'autocorrect',
        'prediction',
        'typo',
        'change',
        'word_delete',
        'delete_end',
        'insert_middle',
        'typo_middle',
        'change_middle',
        'gesture'
    ]

    for case in cases:
        for keyboard in keyboards:
            sample_data = JsonUtil.get_sample_data(base + keyboard + '/' + case + '.json')

            if len(sample_data) > 0:
                print(base + keyboard + '_' + case + '.json')
                calculate_metrics(sample_data)
                print('')

def calculate_metrics(sequence:list):
    typing_speed_calculator = TypingSpeedCalculator(sequence)
    error_rate_calculator = ErrorRateCalculator(sequence)
    typing_path_calculator = TypingPathCalculator(sequence)
    typing_path_calculator.calculate()

    print('WPM: ', typing_speed_calculator.wpm(interrupted_time=0))
    print('KSPS:', typing_speed_calculator.ksps(interrupted_time=0))
    print('KSPC:', error_rate_calculator.kspc(additional_characters=0))
    print('Duration:', typing_speed_calculator.get_duration(), 'seconds')
    print('Path:')
    typing_path_calculator.detect_edit_operations()
    typing_path_calculator.print_path()
    print('Final:\n' + typing_speed_calculator.get_final_text())

if __name__ == "__main__":
    main()
