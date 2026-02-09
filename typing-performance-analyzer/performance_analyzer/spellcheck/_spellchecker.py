from phunspell import Phunspell

hunspell_tr = Phunspell('tr_TR')

class SpellChecker:

    @staticmethod
    def check_spelling(word:str) -> bool:
        return hunspell_tr.lookup(word)

    @staticmethod
    def suggest(word:str):
        return hunspell_tr.suggest(word)
