class BoardDelta:
    def __init__(self, delta_str: str):
        # These should end up negations of another
        self.lifted = delta_str[0] == '-'
        self.placed = delta_str[0] == '+'
        # row, col comes in in that order in hex
        self.row = int(delta_str[1], 16)
        self.col = int(delta_str[2], 16)
        # chess convenience
        self.rank = 8 - self.row
        self.file = chr(ord('a') + (self.col - 2))

    def pos_str(self):
        return str(self.file) + str(self.rank)
