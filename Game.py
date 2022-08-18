import asyncio
import Turns
from Board import Board
from Serial.ArduinoBridge import ArduinoBridge
from Config import Config
from Interface.UI import UI
from BoardSim2 import sim
from BoardSim2 import multiprocess as smp
import os
import threading
import queue
import sys
import time

isInit = False
def init():
    global isInit
    if isInit:
        return
    
    sf_path = os.getenv('SF_PATH')
    if sf_path is None:
        sf_path = '../../stockfish'
    Turns.initStockfish(sf_path=sf_path, doAsync=True)
    isInit = True

# return (row, col) in ARDUINO/SIMULATOR coordinate
def get_sensor_set(gameBoard : Board):
    res = set()
    state = gameBoard.boardState
    for col_idx in range(len(state)):
        col = state[col_idx]
        for row_idx in range(len(col)):
            if col[row_idx] != ' ':
                res.add((row_idx, col_idx))
    return res

# gets the 'immediate' sensor diff (assumes any diff-correction communication will happen within short time)
def get_sensor_diff(before : set, after : set, readline, checkConnection, board_idle):
    # cannot validate sensors without them lol
    if readline is None:
        return None
    
    sensors_lifted = before.difference(after)
    sensors_placed = after.difference(before)


    while checkConnection() and not board_idle():
        line = readline(timeout=None) 
        if line == '!':
            continue
        delta = Turns.BoardDelta(line)
        pos = delta.pos()
        if delta.lifted:
            if pos in sensors_lifted:
                sensors_lifted.remove(pos)
            else:
                sensors_placed.add(pos)
        else: # placed
            if pos in sensors_placed:
                sensors_placed.remove(pos)
            else:
                sensors_lifted.add(pos)
    
    if not sensors_lifted and not sensors_placed: 
        return None
    else:
        return (sensors_lifted, sensors_placed)

def wait_for_board_completion(readline, n=1):
    while n > 0:
        line = readline(timeout=None)
        if not line:
            return 
        if line == '!':
            n -= 1


# returns whether to restart
def startGame(gameBoard : Board, ui: UI, readline=lambda: input("Players turn: "), write=lambda text: print(text, end=''), checkConnection=lambda: True, board_idle=lambda: True):
    def center_cursor():
        write(gameBoard.moveCursor(12, 7))

    def resolve_board_diff(sensors_before : set, custom_msg = None, sensors_after = None):
        if sensors_after is None:
            sensors_after = get_sensor_set(gameBoard)
        diff = get_sensor_diff(before=sensors_before, after=sensors_after, readline=readline, checkConnection=checkConnection, board_idle=board_idle)
        if diff is None:
            return
        
        (needs_lift, needs_place) = diff
        while checkConnection() and (needs_lift or needs_place):
            print("Please lift {} and place {}".format(needs_lift, needs_place))
            if custom_msg is None:
                ui.draw_sensor_diff(needs_lift=needs_lift, needs_place=needs_place)
            else:
                ui.draw_sensor_diff(needs_lift=needs_lift, needs_place=needs_place, msg=custom_msg)

            line = None
            while line is None or line == '!':
                line = readline(timeout=None)
            if not line:
                return 
            delta = Turns.BoardDelta(line)
            pos = delta.pos()
            if delta.lifted:
                if pos in needs_lift:
                    needs_lift.remove(pos)
                else:
                    needs_place.add(pos)
            else: # placed
                if pos in needs_place:
                    needs_place.remove(pos)
                else:
                    needs_lift.add(pos)
            (needs_lift, needs_place) = diff

        ui.undraw_sensor_diff()


    def boardUpdateCommandAndVerify(playerMove):
        sensors_before = get_sensor_set(gameBoard)
        cmd = gameBoard.updateBoard(playerMove, callPM=True)
        write(cmd)
        resolve_board_diff(sensors_before)
        center_cursor()
        

    curTurn = "white"
    sensors_before = get_sensor_set(gameBoard)
    cmd = gameBoard.reset(callPM=True)
    if cmd:
        write(cmd)
    resolve_board_diff(sensors_before)
    center_cursor() # do this before resolve_board_diff
    ui.draw()

    ui_reset = threading.Event()
    ui.set_reset_cb(ui_reset.set)
    oldCheckConnection = checkConnection
    checkConnection = lambda: not ui_reset.isSet() and oldCheckConnection()

    while checkConnection() and not Turns.isGameOver():
        if curTurn == "white":
            playerMove = None
            sensors_before_move = get_sensor_set(gameBoard)
            resolve_bad_move = lambda bad_sensors, hint = None: (
                ui.message.set("Invalid move!{}".format("" if hint is None else " ({})".format(hint))),
                ui.flash_message(),
                resolve_board_diff(sensors_before=bad_sensors, sensors_after=sensors_before_move, 
                    custom_msg="Invalid move, revert the invalid board state above!{}".format("" if hint is None else " ({})".format(hint)))
            )

            while playerMove is None:
                if not checkConnection():
                    return ui_reset.isSet()
                (playerMove, garageSquare) = Turns.getPlayerMove(readline, gameBoard, sensors_before=sensors_before_move,
                    console_cmd_q=ui.console_cmd_q if ui.hasConsole else None, 
                    checkConnection=checkConnection, do_recover=resolve_bad_move)

            moveWasConsole = playerMove.startswith('console: ')
            playerMove = playerMove.replace('console: ', '')
            ui.draw()
            # need to update physical/sim board if from console
            if moveWasConsole:
                boardUpdateCommandAndVerify(playerMove)
            else:
                gameBoard.updateBoard(playerMove, callPM=False, garageSquare=garageSquare)
            curTurn = "black"
            print(playerMove)
        else:
            move = Turns.getStockfishMove(isForHint=False)
            ui.draw()
            print(move)
            curTurn = "white"
            boardUpdateCommandAndVerify(move)

    if not checkConnection():
        return ui_reset.isSet()
    if curTurn == "white":
        ui.message.set("Black wins")
    else:
        ui.message.set("White wins")

    ui.flash_message()
    time.sleep(5)
    return True


def tee_readline(readline1, readline2):
    if readline1 is None:
        return readline2
    if readline2 is None:
        return readline1

    def run2(timeout=None):
        q = queue.Queue()
        threading.Thread(target=lambda: q.put(readline1, timeout), daemon=True).start()
        threading.Thread(target=lambda: q.put(readline2, timeout), daemon=True).start()
        num_running = 2
        while num_running != 0:
            line = q.get()
            if line is None: # timeout
                return None
            if line: 
                return line
            else: # EOF
                num_running -= 1
    
    return run2

def tee_write(write1, write2):
    if write1 is None:
        return write2
    if write2 is None:
        return write1
    return lambda text: (write1(text), write2(text))

def tee_is_alive(isalive1, isalive2):
    if isalive1 is None:
        return isalive2
    if isalive2 is None:
        return isalive1
    return lambda: isalive1() and isalive2()

def run_logic(ui : UI):
    readline = None
    write = None
    is_alive = ui.is_alive
    board_idle = lambda: True
    if Config.SIM:
        sim_proc = smp.SimulatorProcess()
        sim_proc.on_terminate(ui.quit)
        sim_proc.start(target=smp.run_sim, pipe=sim_proc.sim_pipe, startup=sim.setup_board)
        if Config.HALL_EFFECT:
            readline = tee_readline(readline, sim_proc.readline)
        write = tee_write(write, sim_proc.write)
        is_alive = tee_is_alive(is_alive, sim_proc.is_alive)
    if Config.ARDUINO:
        arduino = ArduinoBridge("COM3")
        if Config.HALL_EFFECT:
            readline = tee_readline(readline, arduino.readline)
        write = tee_write(write, arduino.send_cmd)
        is_alive = tee_is_alive(is_alive, arduino.is_alive)
    
    if readline is not None and write is not None:
        numOutstandingCmds = 0
        old_write = write
        def writeIntercept(text):
            nonlocal numOutstandingCmds
            numOutstandingCmds += text.count('\n')
            old_write(text)

        old_readline = readline
        def readlineIntercept(timeout=None):
            line = old_readline(timeout=timeout)
            if line == '!':
                nonlocal numOutstandingCmds
                numOutstandingCmds -= 1
            return line

        readline = readlineIntercept
        write = writeIntercept
        board_idle = lambda: numOutstandingCmds == 0
        
    restart = True
    gameBoard = Board()
    while restart:
        Turns.resetStockFish()
        ui.pack()
        ui.draw()
        restart = startGame(gameBoard, ui, readline=readline, write=write, checkConnection=is_alive, board_idle=board_idle)

    if Config.SIM:
        sim_proc.destroy()

def set_config():
    if sys.argv.count('sim') != 0:
        Config.SIM = True
    if sys.argv.count('arduino') != 0:
        Config.ARDUINO = True
    if sys.argv.count('nohall') != 0:
        Config.HALL_EFFECT = False
        Config.CONSOLE = True
    if sys.argv.count('console') != 0:
        Config.CONSOLE = True
    if sys.argv.count('nodiag') != 0:
        Config.DIAGONALS = False
    if sys.argv.count('simplecapture') != 0:
        Config.ADVANCED_CAPTURE = False
    if sys.argv.count('autoplay') != 0:
        Config.AUTO_PLAY = True

async def main():
    set_config()
    init()
    ui = UI()
    logic_thread = threading.Thread(target=lambda: run_logic(ui))
    logic_thread.start()
    ui.mainloop()
    logic_thread.join()

if __name__ == "__main__":
    asyncio.run(main())
