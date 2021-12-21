from utils.position import Position
from utils.range import Range

class Error():
    def __init__(self, range: Range, name: str, msg: str):
        self.range = range
        self.name = name or 'Error'
        self.msg = msg
    def message(self):
        return f'{self.name}: {self.msg}\nFile "{self.range.start.fn}", line {self.range.start.line+1}\n{string_with_arrows(self.range.start.txt, self.range.start, self.range.end)}'

def string_with_arrows(text, pos_start: Position, pos_end: Position):
    result = ''
    # Calculate indices
    idx_start = max(text.rfind('\n', 0, pos_start.ind), 0)
    idx_end = text.find('\n', idx_start + 1)
    if idx_end < 0: idx_end = len(text)
    
    # Generate each line
    line_count = pos_end.line - pos_start.line + 1
    for i in range(line_count):
        # Calculate line columns
        line = text[idx_start:idx_end]
        col_start = pos_start.col if i == 0 else 0
        col_end = pos_end.col if i == line_count - 1 else len(line) - 1

        # Append to result
        result += line + '\n'
        result += ' ' * col_start + '^' * (col_end - col_start)

        # Re-calculate indices
        idx_start = idx_end
        idx_end = text.find('\n', idx_start + 1)
        if idx_end < 0: idx_end = len(text)

    return result.replace('\t', '')