from Piece_Movement.PieceMovementController import PieceMovementController
from Square import Square
import copy
from Config import Config

def is_white(pieceChar : str):
    return pieceChar.isupper()

def is_black(pieceChar : str):
    return not is_white(pieceChar)

defaultBoardState = [
    [' ', ' ', ' ', ' ', ' ', ' ', ' ', ' '],
    [' ', ' ', ' ', ' ', ' ', ' ', ' ', ' '],
    ['R', 'P', ' ', ' ', ' ', ' ', 'p', 'r'],
    ['N', 'P', ' ', ' ', ' ', ' ', 'p', 'n'],
    ['B', 'P', ' ', ' ', ' ', ' ', 'p', 'b'],
    ['Q', 'P', ' ', ' ', ' ', ' ', 'p', 'q'],
    ['K', 'P', ' ', ' ', ' ', ' ', 'p', 'k'],
    ['B', 'P', ' ', ' ', ' ', ' ', 'p', 'b'],
    ['N', 'P', ' ', ' ', ' ', ' ', 'p', 'n'],
    ['R', 'P', ' ', ' ', ' ', ' ', 'p', 'r'],
    [' ', ' ', ' ', ' ', ' ', ' ', ' ', ' '],
    [' ', ' ', ' ', ' ', ' ', ' ', ' ', ' '],
]

class Board:
    PMController: PieceMovementController
    boardState: []

    def __init__(self):
        self.boardState = copy.deepcopy(defaultBoardState)
        self.PMController = PieceMovementController(self.boardState)

    def updateBoard(self, moveSfFormat, callPM=False, garageSquare = None):
        if moveSfFormat == "0-0":
            print("castling not supported yet")
            return -1

        move = removeLetters(moveSfFormat)
        sourceSquare = Square(move[0:2])
        destSquare = Square(move[2:4])

        if callPM:
            self.PMController.motor.resetCMD()

        dx = sourceSquare.x - destSquare.x
        dy = sourceSquare.y - destSquare.y
        basic_nocheck = dx == 0 or dy == 0 or (abs(dx) == abs(dy) and Config.DIAGONALS)


        # regular move
        if self.getPieceOnSquare(destSquare) == ' ':
            self.movePieceFromTo(sourceSquare, destSquare, callPM, nocheck=basic_nocheck)
        # capture
        else:
            print("Piece has been taken")
            if garageSquare is None: # decide garage square
                garageSquare = self.getGarageLocation(self.getPieceOnSquare(destSquare))
            if callPM and Config.ADVANCED_CAPTURE:
                self.doCapture(source=sourceSquare, dest=destSquare, garage=garageSquare)
            else:
                self.movePieceFromTo(destSquare, garageSquare, callPM)
                self.movePieceFromTo(sourceSquare, destSquare, callPM, nocheck=basic_nocheck)

        if callPM:
            return self.PMController.motor.getCMD()

    def getGarageLocation(self, piece):
        pieceDestination = [-1, -1]
        garagePieceLocations = {
            'R': [11, 0],
            'N': [11, 1],
            'B': [11, 2],
            'Q': [11, 3],
            'K': [11, 4],
            'r': [0, 0],
            'n': [0, 1],
            'b': [0, 2],
            'k': [0, 3],
            'q': [0, 4],
        }

        if piece in garagePieceLocations.keys():
            pieceDestination = Square(garagePieceLocations[piece])
            if not self.getPieceOnSquare(pieceDestination).isspace():
                pieceDestination.y = 7 - pieceDestination.y
        elif piece.lower() == 'p':
            col = 10 if piece.isupper() else 1
            pieceDestination[0] = col
            for row in range(8):
                if self.getPieceOnSquare(Square([col, row])).isspace():
                    pieceDestination = Square([col, row])
                    break
        return pieceDestination

    def getPieceOnSquare(self, square):
        return self.boardState[square.x][square.y]

    def setPieceOnSquare(self, square, val):
        self.boardState[square.x][square.y] = val

    def getPieceOnSensor(self, sensor_row, sensor_col):
        return self.getPieceOnSquare(Square((sensor_col, sensor_row)))

    def movePieceFromTo(self, fromSquare, toSquare, callPM=False, nocheck=False):
        pieceToMove = self.getPieceOnSquare(fromSquare)
        self.setPieceOnSquare(fromSquare, ' ')
        if callPM:
            self.PMController.startMovingPiece(self.boardState, fromSquare, toSquare, nocheck=nocheck)
        self.setPieceOnSquare(toSquare, pieceToMove)

    def moveCursor(self, x, y):
        square = Square((x, y))
        self.PMController.motor.resetCMD()
        self.PMController.moveCursor(square)
        cmd = self.PMController.motor.getCMD()
        return cmd

    def doCapture(self, source : Square, dest : Square, garage : Square):
        source_piece = self.getPieceOnSquare(source)
        dest_piece = self.getPieceOnSquare(dest)
        source_half = source.convToHalfSquares()
        dest_half = dest.convToHalfSquares()
        garage_half = garage.convToHalfSquares()
        assert dest_half.x > 1 and dest_half.x < 24
        dx = dest_half.x - source_half.x
        dy = dest_half.y - source_half.y

        # perfect diagonal, the only captures in chess must be valid even without path checking
        if abs(dx) == abs(dy) and Config.DIAGONALS:
            endHalfSqr = Square((dest_half.x, dest_half.y))
            endHalfSqr.x += -1 if dx > 0 else 1
            endHalfSqr.y += -1 if dy > 0 else 1
            self.setPieceOnSquare(dest, ' ')
            self.PMController.startMovingHalfSquares(self.boardState, startHalfSqr=source_half, endHalfSqr=endHalfSqr, nocheck=True)
            source_half = endHalfSqr
            dx = 1 if dx > 0 else -1
            dy = 1 if dy > 0 else -1

        if dx == 0:
            garage_diff = garage_half.x - dest_half.x
            edge_diff = 1 if garage_diff > 0 else -1
        else:
            edge_diff = 1 if dx > 0 else -1

        source_stash = Square((dest_half.x-edge_diff, dest_half.y))
        self.setPieceOnSquare(source, ' ')
        self.PMController.startMovingHalfSquares(self.boardState, startHalfSqr=source_half, endHalfSqr=source_stash)
        # hacky?
        self.setPieceOnSquare(dest, ' ')
        dest_stash = Square((dest_half.x+edge_diff, dest_half.y))
        self.PMController.startMovingHalfSquares(self.boardState, startHalfSqr=dest_half, endHalfSqr=dest_stash)
        self.PMController.startMovingHalfSquares(self.boardState, startHalfSqr=source_stash, endHalfSqr=dest_half)
        self.setPieceOnSquare(dest, source_piece)
        self.PMController.startMovingHalfSquares(self.boardState, startHalfSqr=dest_stash, endHalfSqr=garage_half)
        self.setPieceOnSquare(garage, dest_piece)

    def reset(self, callPM=False):
        self.PMController.motor.resetCMD()
        open_targets = {}
        out_of_place = set()
        for (x, col) in enumerate(defaultBoardState):
            for (y, default_piece) in enumerate(col):
                actual_piece = self.boardState[x][y]
                if actual_piece != default_piece:
                    if actual_piece == ' ':
                        open_targets.setdefault(default_piece, []).append((x,y))
                    else:
                        out_of_place.add((x,y))
        
        x = self.PMController.motor.x
        y = self.PMController.motor.y
        
        def move_oop(oop_pos, target):
            nonlocal x, y
            (x, y) == target
            self.movePieceFromTo(fromSquare=Square(oop_pos), toSquare=Square(target), callPM=callPM)
            out_of_place.remove(oop_pos)
            default_piece = defaultBoardState[x][y]
            if default_piece != ' ':
                open_targets.setdefault(default_piece, []).append(oop_pos)

        def dist2(pos1, pos2):
            dx = pos2[0] - pos1[0]
            dy = pos2[1] - pos1[1]
            return dx*dx + dy*dy

        while out_of_place:
            progress = False
            oop_sorted = [ piece for piece in out_of_place ]
            oop_sorted.sort(key=lambda piece_pos: dist2(piece_pos, (x, y)))
            for oop_pos in oop_sorted:
                (x, y) = oop_pos
                piece = self.boardState[x][y]
                targets = open_targets.setdefault(piece, [])
                targets.sort(key=lambda target_pos: dist2(target_pos, (x, y)), reverse=True)
                if targets:
                    target = targets.pop()
                    move_oop(oop_pos=oop_pos, target=target)
                    progress = True
                    break
            if progress:
                continue
            # no open targets matching found, hail mary? 
            piece = oop_sorted[0]
            movedTarget = None
            emptySquare = None
            def findTarget():
                nonlocal movedTarget
                nonlocal emptySquare
                for (x, col) in enumerate(defaultBoardState):
                    for (y, default_piece) in enumerate(col):
                        actual_piece = self.boardState[x][y]
                        if default_piece == ' ' and actual_piece == ' ':
                            emptySquare = (x,y)
                            if movedTarget is not None:
                                return
                        elif default_piece == piece and actual_piece != piece and movedTarget is None:
                            movedTarget = (x,y)
                            if emptySquare is not None:
                                return
            findTarget()
            assert movedTarget in out_of_place
            move_oop(oop_pos=movedTarget, target=emptySquare)
        
        if callPM:
            return self.PMController.motor.getCMD()


def removeLetters(piMove):
    # current position
    moveArray = [None] * 4
    moveArray[0] = letterToNumber(piMove[0])
    moveArray[1] = int(piMove[1]) - 1
    # destination
    moveArray[2] = letterToNumber(piMove[2])
    moveArray[3] = int(piMove[3]) - 1
    return moveArray


def letterToNumber(letter):
    asciiVal = ord(letter)
    boardNumVal = asciiVal - 97 + 2  # + 2 for garage places - 97 for ascii value of a
    return boardNumVal
