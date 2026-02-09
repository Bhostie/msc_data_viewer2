import json

class JsonUtil:

    @staticmethod
    def get_sample_data(file_name:str) -> list:
        data = []
        with open(file_name, 'r', encoding='utf-8') as file:
            data = json.load(file)
        return data

    @staticmethod
    def read_file(file_name:str) -> dict[str, list[str]]:
        data = {}
        with open(file_name, 'r', encoding='utf-8') as file:
            data = json.load(file)
        return data
