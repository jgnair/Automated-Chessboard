from serial import Serial  # if this fails you need: pip install pyserial (for me, pip is python 3.8, so I also have to use python 3.8 in vscode)serial.Serial
import serial.tools.list_ports
import sys
from Serial import ISerial
import time


def find_arduino_port():
    arduinos = list(serial.tools.list_ports.grep("."))
    if len(arduinos) == 0:
        raise RuntimeError("Found no arduinos!")
    if len(arduinos) > 1:
        raise RuntimeError("Found multiple arduinos!")
    return arduinos[0]


def establishConnection(portName = None):
    if len(sys.argv) > 1 and sys.argv[1] == 'stdin':
        serial = sys.stdin
    else:
        if portName is not None:
            serial = open_serial_port(portName)
        else:
            serial = open_serial_port(find_arduino_port().device)
    return serial


def get_timeout(ser) -> float:
    if hasattr(ser, 'timeout'):
        return ser.timeout

def set_timeout(ser, val: float) -> None:
    if hasattr(ser, 'timeout'):
        ser.timeout = val

# built-in serial function is kind of dumb because it doesn't allow keyboard interrupt
# also, removes the newline crap
def readline(ser: ISerial, timeout=None):
    line = str()
    if get_timeout(ser) == None:
        set_timeout(ser, 0.5)
    start_time = time.time()
    while not line or not line.endswith('\n'):
        line += str(ser.readline())
        if time.time() - start_time >= timeout:
          return None

    return line.encode().decode("utf-8").rstrip()


def open_serial_port(port):
    ser = Serial()
    # self.ser.timeout = 0.5
    ser.port = port
    ser.baudrate = 115200
    ser.open()
    if not ser.is_open:
        raise RuntimeError("Couldn't open {}".format(port))
    
    return ser
