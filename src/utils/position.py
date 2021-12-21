class Position:
    def __init__(self, ind, line, col, fn, txt):
        self.ind = ind
        self.line = line
        self.col = col
        self.fn = fn
        self.txt = txt
    def advance(self, currentChar=None):
        self.ind+=1
        if(currentChar == '\n'):
            self.line+=1
            self.col = 0
        else:
            self.col+=1
    def copy(self):
        return Position(self.ind, self.line, self.col, self.fn, self.txt)
