from utils.position import Position


class Range:
    def __init__(self, start: Position, end: Position=None):
        self.start = start.copy()
        if end is None:
            end = self.start.copy()
            end.advance()
            self.end = end
        else:
            self.end = end.copy()

    @staticmethod
    def merge(r1, r2):
        return Range(r1.start, r2.end)