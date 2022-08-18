from Serial import ISerial, Serial
from Serial.BoardDelta import BoardDelta
from Serial.Serial import readline


class ArduinoBridge:
    # data members
    ser: Serial.Serial

    def __init__(self, portName = None):
        self.ser = Serial.establishConnection(portName)

    def is_alive(self):
        return self.ser.isOpen()

    def readline(self, timeout=None):
        return readline(self.ser, timeout)

    def read_arduino_delta(self):
        return BoardDelta(self.readline())

    # for simplicity, assumes a move is when there are as many places as lifts, and that first lift goes to first place (capture/garage placed second)
    def read_next_player_move(self):
        num_lift = 0
        num_place = 0
        move_from: BoardDelta
        move_to: BoardDelta

        while True:
            delta = self.read_arduino_delta()
            if delta.lifted:
                if num_lift == 0:
                    move_from = delta
                num_lift += 1
            else:
                if num_place == 0:
                    move_to = delta
                num_place += 1
                if num_place >= num_lift:
                    if num_lift == 0:
                        print("New piece placed at {}".format(delta.pos_str()))
                    else:
                        self.reply_to_move(move_from, move_to)
                        return
                    num_lift = 0
                    num_place = 0

    def send_cmd(self, cmd: str):
        print("Command out: {}".format(cmd))
        self.ser.write(cmd.encode())
