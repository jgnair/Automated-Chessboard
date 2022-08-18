import sim
import threading
import tkinter as tk
import multiprocessing as mp
import time

class Pipe:
  def __init__(self, connection):
    self.connection = connection
    self.buf = str()
    self.name = "Stockfish Pipe"

  def readline(self) -> str:
    line = str()
    try:
      while not line:
        self.buf += self.connection.recv()
        split_res = self.buf.split('\n', 1)
        if len(split_res) == 2:
          (line, self.buf) = split_res
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

def sim_setup(board):
  sim.setup_board(board)
  board.move_cursor(3, 6)
  board.set_emag(True)
  board.move_cursor(8, 8)
  board.set_emag(False)
  board.move_cursor(3, 8)
  board.set_emag(True)
  board.remove_piece(3, 12)
  board.move_cursor(10, 9)
  board.set_emag(False)
  board.move_cursor(1, 10)
  board.set_emag(True)
  board.move_cursor(5, 6)
  board.set_emag(False)
  board.move_cursor(1, 16)
  board.set_emag(True)
  board.move_cursor(5, 14)
  board.set_emag(False)

def run_sim(conn):
  board = sim.GameBoard()
  pipe = Pipe(conn)
  sim.launch_tk(board=board, file_in=pipe, file_out=pipe, after_arg=lambda: sim_setup(board))
  print("Simulator closed!")
  conn.close()

# needed to auto close pipes for some strange reason
def start_child_proc_from_conn(target, conn, daemon=False):
  child = mp.Process(target = target, args=(conn,), daemon=daemon)
  def watch_child():
    while child.join(timeout=1) is not None:
      pass
    conn.close()
  child.start()
  conn.close() # this isn't the same instance that the child process has
  threading.Thread(target=watch_child, daemon=True).start()
  return child

def main():
  this_conn, sim_conn = mp.Pipe()

  sim_proc = start_child_proc_from_conn(target=run_sim, conn=sim_conn)

  pipe = Pipe(this_conn)
  # we can launch another tk!
  root = tk.Tk()
  root.title("Insert Stockfish Application Below")
  sim_out = tk.Text(root)
  sim_out.pack()

  cmd_label = tk.Label(root, text="Simluator input command (e.g. 'md10Emb10e' to move f3 or whatever the chess notation is):")
  cmd_label.pack()
  sim_cmd_entry = tk.Entry(root)
  sim_cmd_entry.bind("<Return>", lambda event: (pipe.write(sim_cmd_entry.get() + '\n'), sim_cmd_entry.delete(0, tk.END)))
  sim_cmd_entry.pack()

  tk_running = True
  def listener():
    def write(msg):
      if tk_running:
        sim_out.config(state='normal')
        sim_out.insert(tk.END, msg)
        sim_out.yview(tk.END)
        sim_out.config(state='disabled')
    line = pipe.readline()
    while line and tk_running:
      write("Got '{}' from the simulator process!\n".format(line.rstrip()))
      line = pipe.readline()
    print("Listener readline interrupted")
    if tk_running:
      write("Connection closed! Terminating in 5 seconds")
      sim_cmd_entry.config(state='disabled')
      for _ in range(5):
        if tk_running:
          time.sleep(1)
          write('.')
      if tk_running:
        root.quit()
    print("Listener exiting")


  listener_thread = threading.Thread(target=listener)
  listener_thread.start()

  root.mainloop()
  tk_running = False
  # reduce risk of slight
  # sim_cmd_entry = None
  # cmd_label = None
  # sim_out = None
  # root = None
  this_conn.close()
  sim_proc.terminate()
  print("Joining simulator")
  sim_proc.join(timeout=2)
  print("Joining listener")
  if listener_thread.is_alive():
     listener_thread.join(timeout=2)
  print("Done")
  time.sleep(0.5) # helps thread cleanup

if __name__ == '__main__':
  main()