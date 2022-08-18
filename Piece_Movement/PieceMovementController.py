from Square import Square
from Motor import Motor


class PieceMovementController:
    motor: Motor
    
    curHalfSqr: Square

    boardState: []

    def __init__(self, boardState):
        self.boardState = boardState
        self.motor = Motor(0, 0)
        self.curHalfSqr = Square([0, 0])

    def startMovingPiece(self, boardState, startSquare: Square, endSquare: Square, nocheck=False):
        self.boardState = boardState
        startHalfSqr = startSquare.convToHalfSquares()
        endHalfSqr = endSquare.convToHalfSquares()
        self.startMovingHalfSquares(boardState, startHalfSqr=startHalfSqr, endHalfSqr=endHalfSqr, nocheck=nocheck)
    
    def startMovingHalfSquares(self, boardstate, startHalfSqr, endHalfSqr, nocheck=False):
        self.totalMoveDx = endHalfSqr.x - startHalfSqr.x
        self.totalMoveDy = endHalfSqr.y - startHalfSqr.y

        self.moveCursor(startHalfSqr)
        self.motor.turnOnElecMag()
        if nocheck:
            self.motor.addMotion(self.totalMoveDx, self.totalMoveDy)
            self.curHalfSqr.x = endHalfSqr.x
            self.curHalfSqr.y = endHalfSqr.y
        else:
            self.movePiece(startHalfSqr, endHalfSqr)
        self.motor.turnOffElecMag()

    def movePiece(self, startHalfSqr, endHalfSqr):
        # TODO
        if isDiagonal(startHalfSqr, endHalfSqr) and False:
            return self.startDiagMovement(startHalfSqr, endHalfSqr)
        else:
            return self.startLateralMovement(endHalfSqr)

    def moveCursor(self, halfSquare):
        self.motor.turnOffElecMag() # redundant, but should ease post processing by establishing magnet is off (allowing rerouting)
        xdiff = halfSquare.x - self.curHalfSqr.x
        ydiff = halfSquare.y - self.curHalfSqr.y

        self.motor.addMotion(dx=xdiff, dy=ydiff) 
        
        # implicit reference semantics are the devil
        self.curHalfSqr.x = halfSquare.x
        self.curHalfSqr.y = halfSquare.y

    def startHorzMovement(self, endHalfSqr):
        steps = 0
        while self.curHalfSqr.x != endHalfSqr.x:
            potentialPiece = not self.curHalfSqr.xIsOnSquare() and self.curHalfSqr.yIsOnSquare()
            if self.curHalfSqr.x - endHalfSqr.x < 0:  # Move Right
                if potentialPiece and self.boardState[self.curHalfSqr.convXHalfSqrToRightSqrIndex()][self.curHalfSqr.convYHalfSqrToUpSqrIndex()] != ' ':
                    self.motor.addRightMove(steps)
                    steps = 0
                    if abs(self.curHalfSqr.x - endHalfSqr.x) == 1:
                        return
                    self.avoidPieceHorz(True, endHalfSqr)
                else:
                    self.curHalfSqr.x += 1
                    steps += 1
            else:  # Move Left
                if potentialPiece and self.boardState[self.curHalfSqr.convXHalfSqrToLeftSqrIndex()][self.curHalfSqr.convYHalfSqrToUpSqrIndex()] != ' ':
                    self.motor.addLeftMove(abs(steps))
                    steps = 0
                    if abs(self.curHalfSqr.x - endHalfSqr.x) == 1:
                        return
                    self.avoidPieceHorz(False, endHalfSqr)
                else:
                    self.curHalfSqr.x -= 1
                    steps -= 1

        if steps > 0:
            self.motor.addRightMove(steps)
        else:
            self.motor.addLeftMove(abs(steps))

    def startDiagMovement(self, startHalfSqr, endHalfSqr):
        pass

    def startVertMovement(self, endHalfSqr):
        steps = 0
        while self.curHalfSqr.y != endHalfSqr.y:
            potentialPiece = self.curHalfSqr.xIsOnSquare() and not self.curHalfSqr.yIsOnSquare()
            if self.curHalfSqr.y - endHalfSqr.y < 0:  # Move Up
                if potentialPiece and self.boardState[self.curHalfSqr.convXHalfSqrToRightSqrIndex()][self.curHalfSqr.convYHalfSqrToUpSqrIndex()] != ' ':
                    self.motor.addUpMove(steps)
                    steps = 0
                    if abs(self.curHalfSqr.y - endHalfSqr.y) == 1:
                        return
                    self.avoidPieceVert(True, endHalfSqr)
                else:
                    self.curHalfSqr.y += 1
                    steps += 1
            else:  # Move Down
                if potentialPiece and self.boardState[self.curHalfSqr.convXHalfSqrToRightSqrIndex()][self.curHalfSqr.convYHalfSqrToDownSqrIndex()] != ' ':
                    self.motor.addDownMove(abs(steps))
                    steps = 0
                    if abs(self.curHalfSqr.y - endHalfSqr.y) == 1:
                        return
                    self.avoidPieceVert(False, endHalfSqr)
                else:
                    self.curHalfSqr.y -= 1
                    steps -= 1
        if steps > 0:
            self.motor.addUpMove(steps)
        else:
            self.motor.addDownMove(abs(steps))

    def startLateralMovement(self, endHalfSqr):
        while self.curHalfSqr.x != endHalfSqr.x or self.curHalfSqr.y != endHalfSqr.y:
            if self.curHalfSqr.x != endHalfSqr.x:
                self.startHorzMovement(endHalfSqr)
            if self.curHalfSqr.y != endHalfSqr.y:
                self.startVertMovement(endHalfSqr)

    def avoidPieceHorz(self, rightMove, finalSpot): # True to move right, False to move left
        def up():
            self.motor.addUpMove(1)
            self.curHalfSqr.y += 1
        def down():
            self.motor.addDownMove(1)
            self.curHalfSqr.y -= 1

        diffY = finalSpot.y - self.curHalfSqr.y
        if diffY == 0:
            #if we already have been moving up, backtrack down
            if self.totalMoveDy > 0: 
                down()
            # if have been moving down, backtrack up
            elif self.totalMoveDy < 0:
                up()
            # else only concern is boundaries
            else:
                up() if finalSpot.y == 0 else down()
        else:
            up() if diffY > 0 else down()

    def avoidPieceVert(self, upMove, finalSpot): # True to move up, False to move down
        def left():
            self.motor.addLeftMove(1)
            self.curHalfSqr.x -= 1
        def right():
            self.motor.addRightMove(1)
            self.curHalfSqr.x += 1

        diffX = finalSpot.x - self.curHalfSqr.x
        if diffX == 0:
            # if we already HAVE been moving right, backtrack to improve postprocessing
            if self.totalMoveDx > 0: 
                left()
            # if have been moving left, backtrack right
            elif self.totalMoveDx < 0:
                right()
            # else only concern is boundaries
            else:
                right() if finalSpot.x == 0 else left()
        else:
            right() if diffX > 0 else left()

    def avoidPieceDiag(self):
        pass


def isHorizontal(startSquare, endSquare):
    return startSquare.x == endSquare.x


def isVertical(startSquare, endSquare):
    return startSquare.y == endSquare.y


def isDiagonal(startSquare, endSquare):
    xDiff = abs(endSquare.x - startSquare.x)
    yDiff = abs(endSquare.y - startSquare.y)
    return xDiff == yDiff
