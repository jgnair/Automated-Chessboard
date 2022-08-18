from stockfish import Stockfish
from Config import Config
from Serial.ArduinoBridge import ArduinoBridge
from Board import *
import os
from pathlib import Path
import threading
import queue


sf = None
sf_ready = threading.Event()


class BoardDelta:
    def __init__(self, delta_str: str):
        # These should end up negations of another
        self.lifted = delta_str[0] == '-'
        self.placed = delta_str[0] == '+'
        # row, col comes in in that order in hex
        self.row = int(delta_str[1], 16)
        self.col = int(delta_str[2], 16)
        # chess convenience
        self.rank = 1 + self.row
        self.file = chr(ord('a') + (self.col - 2))

    def pos_str(self):
        return str(self.file) + str(self.rank)

    def is_board_pos(self):
        return self.col >= 2 and self.col <= 9

    def pos(self):
        return (self.row, self.col)

def formatMove(move_from: BoardDelta, move_to: BoardDelta):
    if not move_from.is_board_pos() or not move_to.is_board_pos():
        return None

    return move_from.pos_str() + move_to.pos_str()

def getPlayerMove(readline, gameBoard : Board, sensors_before : set, console_cmd_q = None, checkConnection = lambda: True, do_recover = lambda hint: print("Invalid move ({})".format(hint))):
    wasConsole = False
    garageSquare = None
    sensors_after : set
    def recover(msg):
        do_recover(sensors_after, msg)
    # may be invalid
    def get_move_str():
        nonlocal sensors_after
        nonlocal garageSquare
        nonlocal wasConsole
        if Config.AUTO_PLAY:
            wasConsole = True # autoplay is 'console' if you just run hints
            return getStockfishMove(isForHint=True)
        
        sensors_after = sensors_before.copy()
        whiteLifted = None
        blackLifted = None
        whitePlaced = None
        blackPlaced = None

        while True:
            delta_str = None
            while delta_str is None:
                if not checkConnection():
                    return None
                if readline is not None:
                    delta_str = readline(0.5) # 0.5 second timeout
                    if delta_str == '!': # ignore 'move done' signal (could be cursor pre-position)
                        delta_str = None 
                if console_cmd_q is not None:
                    try:
                        console_cmd = console_cmd_q.get(timeout=0.5)
                        wasConsole = True
                        return console_cmd
                    except queue.Empty:
                        pass
            
            # readline returns empty on pipe break
            if not delta_str:
                return None
            delta = BoardDelta(delta_str)
            pos = delta.pos()
            if delta.lifted:
                assert pos in sensors_after
                sensors_after.remove(pos)
                pieceLifted = gameBoard.getPieceOnSensor(sensor_row=delta.row, sensor_col=delta.col)
                if is_white(pieceLifted):
                    if whiteLifted is None:
                        whiteLifted = delta
                    else:
                        recover("Cannot lift two white pieces!")
                        return None
                # lifted black
                else:
                    if blackLifted is None:
                        blackLifted = delta
                    else:
                        recover("Cannot lift two black pieces!")
                        return None
            # was placed
            else:
                assert pos not in sensors_after
                sensors_after.add(pos)
                if delta.is_board_pos():
                    if whiteLifted is None:
                        recover("You lifted no white piece to place on board!")
                        return None
                    if whitePlaced is None:
                        whitePlaced = delta
                        if whitePlaced.pos() == whiteLifted.pos():
                            whiteLifted = whitePlaced = None
                    else:
                        recover("Cannot place two pieces on the playable board!")
                        return 
                # placed in garage (assume black)
                else:
                    if blackLifted is None:
                        recover("You lifted no black piece to put in garage!")
                        return None
                    if blackPlaced is None:
                        blackPlaced = delta
                        if blackPlaced.pos() == blackLifted.pos():
                            blackLifted = blackPlaced = None
                    else:
                        recover("Cannot place two pieces in the garage!")
                        return

                if whitePlaced is not None:
                    if blackLifted is not None:
                        if blackPlaced is None:
                            continue
                        # black piece lifted and placed
                        elif whitePlaced.pos() != blackLifted.pos():
                            recover("A black piece was lifted that was not then replaced (captured)")
                            return None
                        garageSquare = Square((blackPlaced.col, blackPlaced.row))
                    return formatMove(whiteLifted, whitePlaced)
    moveValid = False
    while not moveValid:
        if not checkConnection():
            return (None, None)
        moveStr = get_move_str()
        if moveStr is None:
            continue
        moveValid = updateStockfish(moveStr)
        if moveStr is not None and not moveValid:
            recover("Not legal chess move in this context")
            return (None, None)
    
    return (moveStr if not wasConsole else 'console: ' + moveStr, garageSquare)

def initStockfish(sf_path, doAsync=True):
    def impl():
        # if sf_path is not None and sf_path.lower().endswith('exe'):
        #     sf_candidates = [sf_path]
        # else:
        #     sf_candidates = [ * Path(sf_path).glob('**/stockfish*.exe') ]
        # if not sf_candidates:
        #     raise RuntimeError('No file matching stockfish*.exe was found in {}'.format(os.path.abspath(sf_path)))
        # if len(sf_candidates) > 1:
        #     raise RuntimeError('Given stockfish path led to multiple potential executables:\n{}'.format('\n'.join(sf_candidates)))
        
        global sf
        sf = Stockfish("D:\Documents\Classes\SrDesign\stockfish_15_win_x64_avx2\stockfish_15_x64_avx2.exe")
        sf_ready.set()
    if doAsync:
        threading.Thread(target=impl, daemon=True).start()
    else:
        impl()
    

def updateStockfish(givenMove):
    sf_ready.wait()
    if sf.is_move_correct(givenMove):
        sf.make_moves_from_current_position([givenMove])
        return True
    else:
        return False


def getStockfishMove(isForHint=False):
    sf_ready.wait()
    bestMove = sf.get_best_move_time(Config.SF_THINK_MILLIS)
    if not isForHint:
        updateStockfish(bestMove)
        print(sf.get_board_visual())
    return bestMove


def getFenPos():
    sf_ready.wait()
    return sf.get_fen_position()


def isGameOver():
    sf_ready.wait()
    return str(sf.get_best_move_time(200)) == "None"


def resetStockFish():
    sf_ready.wait()
    sf.set_position([])
