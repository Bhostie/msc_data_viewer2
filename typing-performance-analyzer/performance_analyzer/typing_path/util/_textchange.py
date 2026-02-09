class TextChangeResult:

    def __init__(self, index:int, removed:str, entered:str):
        self._index = index
        self._removed = removed
        self._entered = entered
        self._before = None
        self._current = None
        self._type = None
        self._position = None

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
