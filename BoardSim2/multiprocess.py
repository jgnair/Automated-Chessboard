from BoardSim2 import sim
import threading
import multiprocessing as mp
from multiprocessing.connection import Connection
import time

class Pipe:
  def __init__(self, connection : Connection):
    self.connection = connection
    self.buf = str()
    self.name = "Stockfish Pipe"
    self.closed = False

  def readline(self, timeout=None) -> str:
    try:
      line = ''
      start_time = time.time()
      elapsed_time = 0
      while not line: # could maybe be while True but ....
        split_res = self.buf.split('\n', 1)
        if len(split_res) == 2:
          (line, self.buf) = split_res
          return line

        if self.closed:
          return ''
        try:
          if not self.connection.poll(timeout=None if timeout is None else timeout-elapsed_time):
            return None
        except BrokenPipeError:
          return ''
        elapsed_time = time.time() - start_time
        if timeout is not None and elapsed_time >= timeout:
          return None

        self.buf += self.connection.recv()
    except EOFError:
      return ''
    return line

  def write(self, text):
    try: 
      self.connection.send(text)
    except BrokenPipeError:
      pass

  def clear_input_buf(self):
    self.buf = str()

  def close(self):
    self.closed = True
    self.connection.close()

def run_sim(pipe, startup=sim.setup_board):
  board = sim.GameBoard()
  sim.launch_tk(board=board, file_in=pipe, file_out=pipe, after_arg=lambda: startup(board))
  print("Simulator closed!")

# needed to auto close pipes for some strange reason
def start_child_proc_from_pipe(target, pipe, daemon=False, launch_args=(), launch_kwargs = {}, terminate_cb = lambda: None, terminate_args = (), terminate_kwargs = {}):
  child = mp.Process(target = target, args=launch_args, kwargs=launch_kwargs, daemon=daemon)
  def watch_child():
    while child.exitcode is None:
      child.join(timeout=1)
    pipe.close()
    terminate_cb(*terminate_args, **terminate_kwargs)
  child.start()
  threading.Thread(target=watch_child, daemon=True).start()
  return child

class SimulatorProcess:
  def __init__(self):
    parent_conn, sim_conn = mp.Pipe()
    self.parent_pipe = Pipe(parent_conn)
    self.sim_pipe = Pipe(sim_conn)
    self.terminate_cb = lambda: None
    self.terminate_args = ()
    self.terminate_kwargs = {}
  
  def on_terminate(self, cb, *args, **kwargs):
    self.terminate_cb = cb
    self.terminate_args = args
    self.terminate_kwargs = kwargs

  def start(self, target = run_sim, *args, **kwargs):
    if target is run_sim and not args and not kwargs:
      kwargs = { 'pipe': self.sim_pipe, 'startup': None }
    self.sim_proc = start_child_proc_from_pipe(target=target, pipe=self.sim_pipe, launch_args=args, launch_kwargs=kwargs,
      terminate_cb=self.terminate_cb, terminate_args=self.terminate_args, terminate_kwargs=self.terminate_kwargs)

  def write(self, text):
    self.parent_pipe.write(text)

  def readline(self, timeout=None):
    return self.parent_pipe.readline(timeout)
  
  def is_alive(self):
    return self.sim_proc.is_alive()

  def destroy(self):
    print("Destroying simulator process!")
    self.parent_pipe.close()
    self.sim_pipe.close()
    self.sim_proc.terminate()
    self.sim_proc.join()