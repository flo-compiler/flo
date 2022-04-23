from termcolor import colored

class Position:
    def __init__(self, ind, line, col, fn, txt):
        self.ind = ind
        self.line = line
        self.col = col
        self.fn = fn
        self.txt = txt

    def advance(self, currentChar=None):
        self.ind += 1
        if currentChar == "\n":
            self.line += 1
            self.col = 0
        else:
            self.col += 1

    def copy(self):
        return Position(self.ind, self.line, self.col, self.fn, self.txt)


class Range:
    def __init__(self, start: Position, end: Position = None):
        self.start = start.copy()
        if end is None:
            end = self.start.copy()
            end.advance()
            self.end = end
        else:
            self.end = end.copy()

    def copy(self):
        return Range(self.start, self.end)

    @staticmethod
    def merge(r1, r2):
        return Range(r1.start, r2.end)


class Error:
    def __init__(self, range: Range, name: str, msg: str):
        self.range = range
        self.name = name
        self.msg = msg

    def message(self):
        name = colored(f"[{self.name}]: ", "red", attrs=["bold"])
        msg = colored(f"{self.msg}\n", attrs=["bold"])
        trace = (
            f'File "{self.range.start.fn}", line {self.range.start.line+1}\n{string_with_arrows(self.range.start.txt, self.range.start, self.range.end)}'
            if self.range
            else ""
        )
        return name + msg + trace

    def throw(self):
        print(self.message())
        exit(1)


class ExpectedCharError(Error):
    def __init__(self, range: Range, msg: str):
        super().__init__(range, "Expected character", msg)


class IllegalCharacterError(Error):
    def __init__(self, range: Range, char: str):
        super().__init__(range, "Illegal character", f"'{char}'")


class RTError(Error):
    def __init__(self, range: Range, msg: str):
        super().__init__(range, "Runtime Error", msg)


class SyntaxError(Error):
    def __init__(self, range: Range, char: str):
        super().__init__(range, "Syntax Error", char)


class TypeError(Error):
    def __init__(self, range: Range, message: str):
        super().__init__(range, "Type Error", message)


class GeneralError(Error):
    def __init__(self, range: Range, message: str):
        super().__init__(range, "Error", message)


class IOError(Error):
    def __init__(self, range: Range, message: str):
        super().__init__(range, "IO Error", message)


class NameError(Error):
    def __init__(self, range: Range, message: str):
        super().__init__(range, "Name Error", message)


class CompileError(Error):
    def __init__(self, message):
        super().__init__(None, "Compile Error", message)


def string_with_arrows(text, pos_start: Position, pos_end: Position):
    result = ""
    # Calculate indices
    idx_start = max(text.rfind("\n", 0, pos_start.ind), 0)
    idx_end = text.find("\n", idx_start + 1)
    if idx_end < 0:
        idx_end = len(text)

    # Generate each line
    line_count = pos_end.line - pos_start.line + 1
    for i in range(line_count):
        # Calculate line columns
        line = text[idx_start:idx_end]
        col_start = pos_start.col if i == 0 else 0
        col_end = pos_end.col if i == line_count - 1 else len(line) - 1

        # Append to result
        result += line + "\n"
        result += colored(
            " " * col_start + "^" * (col_end - col_start), "red", attrs=["bold"]
        )

        # Re-calculate indices
        idx_start = idx_end
        idx_end = text.find("\n", idx_start + 1)
        if idx_end < 0:
            idx_end = len(text)

    return result.replace("\t", "")
