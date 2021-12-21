from errors.error import Error
from utils.range import Range

class TypeError(Error):
    def __init__(self, range: Range, message: str):
        super().__init__(range, 'Type Error', message)