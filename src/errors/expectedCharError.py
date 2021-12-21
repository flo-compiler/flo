from errors.error import Error
from utils.range import Range

class ExpectedCharError(Error):
    def __init__(self, range: Range, msg: str):
        super().__init__(range, 'Expected character', msg)