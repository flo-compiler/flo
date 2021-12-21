from errors.error import Error
from utils.range import Range

class SyntaxError(Error):
    def __init__(self, range: Range, char: str):
        super().__init__(range, 'Syntax Error', char)