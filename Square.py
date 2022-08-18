class Square:
    x: int
    y: int

    def __init__(self, coords):
        self.x = coords[0]
        self.y = coords[1]

    def convToHalfSquares(self):
        newX = self.x * 2
        if self.x >= 2:
            newX += 1
            if self.x >= 10:
                newX += 1
        return Square([newX, self.y * 2])

    def convXHalfSqrToLeftSqrIndex(self):
        if self.x < 0:
            return 0
        if self.x <= 3:
            return self.x // 2
        elif self.x <= 20:
            return (self.x - 1) // 2
        else:
            return (self.x - 2) // 2

    def convXHalfSqrToRightSqrIndex(self):
        if self.x <= 3:
            return (self.x + 1) // 2
        elif self.x <= 20:
            return self.x // 2
        elif self.x <= 24:
            return (self.x - 1) // 2
        else:
            return 11

    def xIsOnSquare(self):
        if self.x >= 4 and self.x <= 20:
            return self.x % 2 == 1
        else:
            return self.x % 2 == 0

    def yIsOnSquare(self):
        return self.y % 2 == 0

    def convYHalfSqrToUpSqrIndex(self):
        if self.y < 0:
            return 0
        elif self.y <= 14:
            return (self.y + 1) // 2
        else:
            return 7

    def convYHalfSqrToDownSqrIndex(self):
        if self.y < 0:
            return 0
        elif self.y <= 14:
            return self.y // 2
        else:
            return 7
