import time
import threading
import queue
import math

import tkinter as tk

class Piece():
  pieceIdCounter = 0
  def __init__(self):
    self.id = Piece.pieceIdCounter
    Piece.pieceIdCounter += 1
    self.name = "piece" + str(self.id)
    self.bg_name = self.name + "_bg"
    self.text_name = self.name + "_text"
    self.lifted = False
    self.pos = None

def trunctate_halfsquare_precision(halfidx, num_digits = 2):
  int_scale = 10**num_digits
  return math.trunc(round(halfidx * int_scale)) / int_scale

class GameBoard(tk.Frame):

  def __init__(self, err_cb=print, out_cb=print, board_rows=8, board_cols=8, garage_cols = 2, garage_gap_halfcols=1, square_size=64, color1="#ebd6ad", color2="#61440a", garage_color='gray'):
    '''square_size is the size of a square, in pixels'''
  
    self.err_cb = err_cb
    self.out_cb = out_cb

    self.square_size = square_size
    self.garage_cols = garage_cols
    self.garage_gap_halfcols = garage_gap_halfcols
    self.garage_color = garage_color

    self.board_rows = board_rows
    self.board_cols = board_cols

    # tracks MOVEABLE (interior) positions
    self.halfcols = 2*(board_cols + 2*(garage_cols)) + 2*garage_gap_halfcols - 1
    self.halfrows = 2*board_rows - 1

    self.color1 = color1
    self.color2 = color2

    self.pieces = {}

    self.sensors = {}
    self.enable_sensors()
    self.enable_sensors_print()
    self.enable_moving_sensors_print()

    self.cursor_pos = (0, 0)
    self.emag_on_color = '#42f2ff'
    self.emag_off_color = '#1d00ba'

    self.emag_on = False

    self.board_events = queue.Queue()
    self.click_lifted_pieces = []
    self.click_handler = None

    def process_moves():
      i = 0
      while True:
        # print("Processing next event...")
        self.board_events.get(block=True)()
        # print("Done with event {}".format(i))
        i += 1
        self.arrange_layers()

    self.move_thread = threading.Thread(target=process_moves, daemon=True)
    self.move_thread.start()

    self.collision_marks = []

  def col_label_height(self):
    return self.square_size/2
  
  def row_label_width(self):
    return self.square_size/2

  def initTk(self, parent):
    tk.Frame.__init__(self, parent)
    # extra square because 'halfcols'/'halfrows' only tracks moveable positions
    self.canvas_width = (self.halfcols+1) * self.square_size / 2 + self.row_label_width() + self.square_size 
    self.canvas_height = (self.halfrows+1) * self.square_size / 2 + self.col_label_height() + self.square_size
    self.needs_redraw = False

    self.canvas = tk.Canvas(self, borderwidth=0, highlightthickness=0,
                width=self.canvas_width, height=self.canvas_height, background="white")
    self.canvas.pack(side="top", fill="both", expand=True, padx=2, pady=2)

    self.canvas.create_oval(0,0,0,0, outline = self.emag_off_color, tags=("cursor"))
    # this binding will cause a refresh if the user interactively
    # changes the window size
    self.canvas.bind("<Configure>", self.refresh)
    self.canvas.bind("<Button-1>", self.handle_click)
    self.canvas.bind("<Button-3>", self.handle_click)
    self.draw()

  def getCanvasCoords(self, row, col):
    half_square = self.square_size/2
    x0 = (col * half_square) + self.row_label_width() + half_square
    y0 = ((self.halfrows - row - 1) * half_square) + self.col_label_height() + half_square
    return (x0, y0)
  
  def posFromCanvasCoords(self, x, y):
    y_halfrow = round((y-self.col_label_height()) / self.square_size * 2)
    y_halfrow = self.halfrows - y_halfrow
    x_halfcol = round((x-self.row_label_width()) / self.square_size * 2) - 1
    return (y_halfrow, x_halfcol)

  def cursor_size(self):
    return self.square_size * 0.8

  def draw_cursor(self):
    (x, y) = self.getCanvasCoords(*self.cursor_pos)
    delta = self.cursor_size() / 4
    self.canvas.itemconfig("cursor", outline=self.emag_on_color if self.emag_on else self.emag_off_color)
    self.canvas.coords("cursor", x-delta, y-delta, x+delta, y+delta)
    self.canvas.itemconfig("cursor", width=self.square_size/20)
    
  def add_piece(self, text, row=0, col=0, white=True, block=True):
    def impl():
      text_color = 'black' if white else 'grey'
      bg_color = 'white' if white else 'black'

      piece = Piece()

      self.canvas.create_oval(0,0,0,0, fill = bg_color, tags=(piece.name, piece.bg_name, "piece", "piece_bg"))
      self.canvas.create_text(0,0, text=text, anchor='c', fill=text_color, tags=(piece.name, piece.text_name, "piece", "piece_text"))
      self.place_piece(piece, row, col)
    
    if block:
      self.board_events.put(impl)
    else:
      impl()

  def sensor_pos(self, row, col):
    garage_halfcols = 2*self.garage_cols
    if row % 2 == 1:
      return None
    sensor_row = int(row / 2)
    # garages are always separated by even number of halfcols, and leftmost is zero, therefore its just even mod2
    if col < garage_halfcols:
      if col % 2 == 0:
        return (sensor_row, int(col / 2))
    elif col > self.halfcols - garage_halfcols:
      if col % 2 == 0:
        return (sensor_row, int(col / 2 - self.garage_gap_halfcols))
    # square is trickier since garage gap changes this
    elif col >= garage_halfcols+self.garage_gap_halfcols and col <= self.halfcols-garage_halfcols-self.garage_gap_halfcols:
      if (col % 2) == (self.garage_gap_halfcols % 2):
        return (sensor_row, int((col - self.garage_gap_halfcols) / 2))
    
    return None
      
  def disable_sensors(self):
    self.sensors_enabled_ = False
  
  def enable_sensors(self):
    self.sensors_enabled_ = True
    
  def disable_sensors_print(self):
    self.do_sensor_print = False
  
  def enable_sensors_print(self):
    self.do_sensor_print = True

  # 'moving' variations determine whether the printing will occur for changes during cursor movement (BUT, can silence user stuff too!)
  def disable_moving_sensors_print(self):
    self.do_moving_sensor_print = False

  def enable_moving_sensors_print(self):
    self.do_moving_sensor_print = True

  def sensors_enabled(self):
    return self.sensors_enabled_

  def sensor_print_enabled(self):
    return self.do_sensor_print

  def output(self, msg : str):
    self.out_cb(msg)

  def send_sensor_turn_on(self, row, col):
    if not self.sensors_enabled_:
      return
    name = "sensor{:x}{:x}".format(row, col)
    self.sensors[(row, col)] = name
    self.canvas.create_rectangle(0,0,0,0, tags=(name, "sensor"))
    self.draw_sensor(row, col)
    if self.do_sensor_print:
      self.output("+{:x}{:x}".format(row, col))

  def send_sensor_turn_off(self, row, col):
    if not self.sensors_enabled_:
      return
    if not (row, col) in self.sensors:
      return

    self.canvas.delete(self.sensors[(row, col)])
    del self.sensors[(row, col)]
    if self.do_sensor_print:
      self.output("-{:x}{:x}".format(row, col))

  def place_piece(self, piece : Piece, row, col):
    if (row, col) in self.pieces:
      cur_piece = self.pieces[(row, col)]
      assert cur_piece.pos == (row, col)
      if cur_piece is piece:
        if not cur_piece.lifted:
          return # do nothing
      else:
        self.remove_piece(row, col, block=False)
    
    if piece.pos is not None:
      del self.pieces[piece.pos] # remove old 
    self.pieces[(row, col)] = piece
    self.pieces[(row, col)].lifted = False
    self.pieces[(row, col)].pos = (row, col)
    sensor_pos = self.sensor_pos(row, col)
    if sensor_pos is not None:
      self.send_sensor_turn_on(*sensor_pos)
    self.draw_piece(row, col)

  def draw_col_labels(self):
    label_spacing = self.square_size/2
    for idx in range(self.halfcols):
      x = label_spacing*(idx+1) + self.row_label_width()
      y = self.col_label_height()/2
      self.canvas.create_text(x, y, text="{:02d}".format(idx), anchor='c', fill='black', tags=("col_labels","labels"))
      self.canvas.itemconfig("col_labels", font=("Arial Bold", int(self.square_size/4.8)))

  def draw_row_labels(self):
    label_spacing = self.square_size/2
    for idx in range(self.halfrows):
      x = self.row_label_width()/2
      y = label_spacing*(self.halfrows - idx) + self.col_label_height()
      self.canvas.create_text(x, y, text="{:02d}".format(idx), anchor='c', fill='black', tags=("col_labels","labels"))
      self.canvas.itemconfig("col_labels", font=("Arial Bold", int(self.square_size/4.8)))
  
  def draw_labels(self):
    self.canvas.delete("labels")
    self.draw_col_labels()
    self.draw_row_labels()

  def width_in_squares(self):
    return self.halfcols/2 + self.row_label_width()/self.square_size

  def height_in_squares(self):
    return self.halfrows/2 + self.col_label_height()/self.square_size

  def draw_game_squares(self):
    self.canvas.delete("square")
    color = self.color2
    for row in range(self.board_rows):
      color = self.color1 if color == self.color2 else self.color2
      for col in range(self.board_cols):
        x1 = ((col + self.garage_cols + self.garage_gap_halfcols/2) * self.square_size) + self.row_label_width()
        y1 = (row * self.square_size) + self.col_label_height()
        x2 = x1 + self.square_size
        y2 = y1 + self.square_size
        self.canvas.create_rectangle(x1, y1, x2, y2, outline="black", fill=color, tags="square")
        color = self.color1 if color == self.color2 else self.color2

  def draw_piece(self, row, col):
    piece = self.pieces[(row, col)]
    (x0, y0) = self.getCanvasCoords(row, col)
    self.canvas.itemconfig(piece.text_name,font=("Arial Bold", int(self.square_size/3)))
    self.canvas.coords(piece.text_name, x0, y0)
    bg_delta = self.square_size/4
    self.canvas.coords(piece.bg_name, x0-bg_delta, y0-bg_delta, x0+bg_delta, y0+bg_delta)

  def redraw_pieces(self):
    for pos in self.pieces:
      self.draw_piece(*pos)

  
  def draw_garages(self):
    self.canvas.delete("garage")
    def do_row_col(row, col, x_offset):
      x1 = (col* self.square_size) + self.row_label_width()+x_offset
      y1 = (row * self.square_size) + self.col_label_height()
      x2 = x1 + self.square_size
      y2 = y1 + self.square_size
      self.canvas.create_rectangle(x1, y1, x2, y2, outline="black", fill=self.garage_color, tags="garage")

    for row in range(self.board_rows):
      for col in range(self.garage_cols):
        do_row_col(row, col, 0)
        do_row_col(row, col, self.square_size*(self.board_cols + self.garage_cols + self.garage_gap_halfcols))


  def draw_collision_marks(self):
    delta = self.square_size / 8
    for (i, mark) in enumerate(self.collision_marks):
      (x, y) = self.getCanvasCoords(*mark)
      self.canvas.coords("collision{}_l1".format(i), x-delta, y+delta, x+delta, y-delta)
      self.canvas.coords("collision{}_l2".format(i), x-delta, y-delta, x+delta, y+delta)
    self.canvas.itemconfig("collision", width=self.square_size/20)

  def draw_sensor(self, row, col):
    delta = self.square_size/2.5
    name = self.sensors[(row, col)]
    y_halfrow = 2*row
    x_halfcol = 2*col
    if x_halfcol >= 2*self.garage_cols:
      x_halfcol += 1
    if x_halfcol >= self.halfcols-2*self.garage_cols:
      x_halfcol += 1
    (x, y) = self.getCanvasCoords(y_halfrow, x_halfcol)
    self.canvas.coords(name, x-delta,y-delta, x+delta, y+delta)
    self.canvas.itemconfig("sensor", width=self.square_size/20, outline='#1ff22a')

  def draw_sensors(self):
    for pos in self.sensors:
      self.draw_sensor(*pos)

  def arrange_layers(self):
    self.canvas.tag_lower("square")
    self.canvas.tag_lower("garage")
    self.canvas.tag_raise("sensor")
    self.canvas.tag_raise("piece")
    self.canvas.tag_raise("piece_text")
    self.canvas.tag_raise("cursor")
    self.canvas.tag_raise("collision")

  def draw(self):
    self.draw_labels()
    self.draw_game_squares()
    self.draw_garages()
    self.redraw_pieces()
    self.draw_sensors()
    self.draw_collision_marks()
    self.draw_cursor()
    self.arrange_layers()
    

  def refresh(self, event):
    '''Redraw the board, possibly in response to window being resized'''
    if self.canvas_width == event.width and self.canvas_height == event.height:
      return

    self.canvas_width = event.width
    self.canvas_height = event.height

    def redraw():
      xsize = int((self.canvas_width-1) / self.width_in_squares())
      ysize = int((self.canvas_height-1) / self.height_in_squares())
      self.square_size = min(xsize, ysize)
      self.draw()
      self.needs_redraw = False
    
    if not self.needs_redraw:
      self.needs_redraw = True
      self.board_events.put(redraw)

  def lift_piece(self, row, col):
    if not (row, col) in self.pieces or self.pieces[(row, col)].lifted:
      return

    sensor_pos = self.sensor_pos(row, col)
    if sensor_pos is not None:
      self.send_sensor_turn_off(*sensor_pos)
    
    self.pieces[(row, col)].lifted = True
    assert self.pieces[(row, col)].pos == (row, col)

  def remove_piece(self, row, col, block=True):
    def impl():
      if (row, col) in self.pieces:
        self.lift_piece(row, col)
        self.canvas.delete(self.pieces[(row, col)].name)
        del self.pieces[(row, col)]
    if block:
      self.board_events.put(impl)
    else:
      impl()
  
  def error(self, msg : str):
    self.err_cb(msg)

  def move_cursor(self, row, col, block=False):
    if row not in range(self.halfrows):
      self.error("Invalid row! (int value {})".format(row))
      return
    if col not in range(self.halfcols):
      self.error("Invalid column! (int value {})".format(col))
      return

    def impl():
      if not self.do_moving_sensor_print:
        print_setting = self.sensor_print_enabled()
        self.disable_sensors_print()
      (from_x, from_y) = self.getCanvasCoords(*self.cursor_pos)
      (to_x, to_y) = self.getCanvasCoords(row, col)
      piece = None
      if self.emag_on:
        if self.cursor_pos in self.pieces:
          piece = self.pieces[self.cursor_pos]
          self.lift_piece(*self.cursor_pos)
        else:
          self.error("Moving cursor with electromagnet on, but it is not under a piece! (from {} {})".format(*self.cursor_pos))

      dx = to_x - from_x
      dy = to_y - from_y
      
      dr = math.sqrt(dx*dx + dy*dy)
      dr_step = self.square_size/10
      steps = dr / dr_step

      dx_canvas = dx/steps if dr > 0 else 0
      dy_canvas = dy/steps if dr > 0 else 0

      x = from_x
      y = from_y

      collisions = set()

      for _ in range(int(steps)):
        x += dx_canvas
        y += dy_canvas
        self.canvas.move("cursor", dx_canvas, dy_canvas)
        if piece is not None:
          self.canvas.move(piece.name, dx_canvas, dy_canvas)
          self.canvas.tag_raise("cursor")

          y_halfrow, x_halfcol = self.posFromCanvasCoords(x, y)
          y_halfrow = trunctate_halfsquare_precision(y_halfrow)
          x_halfcol = trunctate_halfsquare_precision(x_halfcol)
          for round_row in [math.floor(y_halfrow), math.ceil(y_halfrow)]:
            for round_col in [math.floor(x_halfcol), math.ceil(x_halfcol)]:
              round_pos = (round_row, round_col)
              if round_pos not in self.pieces:
                continue
              if not self.pieces[round_pos].lifted and round_pos not in collisions:
                collisions.add(round_pos)
                mid_row = (round_row + y_halfrow) / 2
                mid_col = (round_col + x_halfcol) / 2
                collision_num = len(self.collision_marks)
                self.collision_marks.append((mid_row, mid_col))
                collision_label = "collision{}".format(collision_num)
                self.canvas.create_line(0,0,0,0, fill='red', tags=("collision", collision_label, collision_label+"_l1"))
                self.canvas.create_line(0,0,0,0, fill='red', tags=("collision", collision_label, collision_label+"_l2"))
                self.draw_collision_marks()
                self.error("Collision with another piece already at {} {}! (Cursor was at {:.2f} {:.2f})".format(round_row, round_col, y_halfrow, x_halfcol))

        time.sleep(0.015)

      # animation done
      if piece is not None:
        self.place_piece(piece, row, col)

      if not self.do_moving_sensor_print and print_setting:
        self.enable_sensors_print()

      self.cursor_pos = (row, col)
      self.draw_cursor()

    if block:
      impl()
    else:
      self.board_events.put(impl)

  def move_cursor_by(self, drow, dcol):
    def impl():
      self.move_cursor(self.cursor_pos[0] + drow, self.cursor_pos[1] + dcol, block=True)
    self.board_events.put(impl)

  def set_emag(self, on):
    def impl():
      self.emag_on = on
      self.draw_cursor()
    self.board_events.put(impl)

  def clear_markers(self):
    def impl():
      self.canvas.delete("collision")
      self.collision_marks.clear()
    self.board_events.put(impl)

  def clear_pieces(self):
    def impl():
      self.canvas.delete("piece")
      self.pieces.clear()
    self.board_events.put(impl)
  
  def clear_sensors(self):
    def impl():
      self.canvas.delete("sensor")
      self.sensors.clear()
    self.board_events.put(impl)

  def clear(self):
    self.clear_markers()
    self.clear_pieces()
    self.clear_sensors()
    self.set_emag(False)
  
  def join(self):
    while not self.board_events.empty():
      time.sleep(0.3)
    # this deadlocks becuase python threads are silly
    # self.board_events.join()

  def highlight_piece(self, piece):
    self.canvas.itemconfig(piece.bg_name, outline='#a834eb', width=self.square_size/11)

  def mediumlight_piece(self, piece): # what a name
      self.canvas.itemconfig(piece.bg_name, outline='#5b3b6e', width=self.square_size/11)
  
  def pop_lifted_piece(self):
    piece = self.click_lifted_pieces.pop()
    if self.click_lifted_pieces:
      self.highlight_piece(self.click_lifted_pieces[-1])
    return piece
  
  def push_lifted_piece(self, piece):
    if self.click_lifted_pieces:
      self.mediumlight_piece(self.click_lifted_pieces[-1])

    if piece in self.click_lifted_pieces:
      self.click_lifted_pieces.remove(piece)
      self.click_lifted_pieces.append(piece)
    else:
      self.click_lifted_pieces.append(piece)

    self.lift_piece(*piece.pos)
    self.highlight_piece(piece)

  def handle_click(self, event):
    y_halfrow = round((event.y-self.col_label_height()) / self.square_size * 2)
    y_halfrow = self.halfrows - y_halfrow
    x_halfcol = round((event.x-self.row_label_width()) / self.square_size * 2) - 1

    if y_halfrow not in range(self.halfrows) or x_halfcol not in range(self.halfcols):
      return

    if self.click_handler is not None:
      self.click_handler(y_halfrow, x_halfcol, event)
      return

    pos = (y_halfrow, x_halfcol)

    # right click (3) always lifts
    if event.num == 3 or not self.click_lifted_pieces:
      place=False
    # if clicking on a location with a piece
    elif pos in self.pieces:
      target = self.pieces[pos]
      if self.click_lifted_pieces and self.click_lifted_pieces[-1] is target:
        place=True
      # if there is a different lifted piece at the location, don't allow replacement
      else:
        place = False
    # must be left click with an already lifted piece and an empty square
    else:
      place=True

    if place:
      piece = self.pop_lifted_piece()
      self.place_piece(piece, *pos)
      self.canvas.itemconfig(piece.bg_name, outline='black', width=1)
    else:
      if pos not in self.pieces:
        return
      piece = self.pieces[pos]
      self.push_lifted_piece(piece)
    
    self.arrange_layers()

  def handle_cmd_str(self, cmd : str):
    cmd = cmd.rstrip()
    i = 0
    class NullEx(Exception):
      pass
    def next_char(desc : str):
      nonlocal i
      if i >= len(cmd):
        self.error("Incomplete command! Expected " + desc)
        raise NullEx()
      c = cmd[i]
      i += 1  
      return c
    
    def next_digit(base, desc):
      expected = "{}digit ({})".format("hex " if base == 16 else "", desc)
      c = next_char(expected)
      try:
        return int(c, base)
      except Exception:
        self.error("Invalid character '{}' (i={}). Expected {}".format(c, i-1, expected))
        raise NullEx()

    def next_2digit(desc, base=10):
      res = base*next_digit(base, desc + " 10's digit")
      res += next_digit(base, desc + "1's digit")
      return res

    def next_horz_dir():
      expected = "horizontal direction (l|r)"
      c = next_char(expected)
      if c != 'l' and c != 'r':
        self.error("Invalid character '{}' (i={}). Expected {}".format(c, i-1, expected))
        raise NullEx()
      return c

    try: 
      while i < len(cmd):
        expected = "command neumonic (m|l|r|u|d|Ul|Ur|Dl|Dr|e|E)"
        c = next_char(expected)
        if c == 'E':
          self.set_emag(True)
        elif c == 'e':
          self.set_emag(False)
        elif c == 'm':
          row = next_2digit("row")
          col = next_2digit("col")
          self.move_cursor(row, col)
        elif c == 'l':
          amount = next_2digit("left move amount")
          self.move_cursor_by(0, -amount)
        elif c == 'r':
          amount = next_2digit("right move amount")
          self.move_cursor_by(0, amount)
        elif c == 'u':
          amount = next_2digit("up move amount")
          self.move_cursor_by(amount, 0)
        elif c == 'd':
          amount = next_2digit("down move amount")
          self.move_cursor_by(-amount, 0)
        elif c == 'U':
          hor = next_horz_dir()
          amount = next_2digit("diagonal (U{}) move amount".format(hor))
          self.move_cursor_by(amount, amount if hor == 'r' else -amount)
        elif c == 'D':
          hor = next_horz_dir()
          amount = next_2digit("diagonal (D{}) move amount".format(hor))
          self.move_cursor_by(-amount, amount if hor == 'r' else -amount)
        else:
          self.error("Invalid character '{}' (i={}). Expected {}".format(c, i-1, expected))
          raise NullEx()

      self.board_events.put(lambda: self.output('!'))

    except NullEx:
      return

def try_set_entry_hint(entry : tk.Entry, hint : str, color='gray'):
  if not entry.get():
    entry.delete(0, tk.END)
    entry.config(fg=color)
    entry.insert(0, hint)

def remove_entry_hint(entry : tk.Entry, color='black'):
  if entry.cget('fg') != color:
    entry.delete(0, tk.END)
    entry.config(fg=color)

def add_entry_hint(entry : tk.Entry, hint : str, hint_color='gray'):
  regular_color = entry.cget('fg')
  try_set = lambda event: try_set_entry_hint(entry, hint, hint_color)
  remove = lambda event: remove_entry_hint(entry, regular_color)
  try_set(None)
  entry.bind("<FocusIn>", remove)
  entry.bind("<FocusOut>", try_set)

def tee_cb(cb_1, cb_2):
  return lambda *args: (cb_1(*args), cb_2(*args))

def launch_tk(board : GameBoard, file_in=None, file_out = None, after_arg=None):
  root = tk.Tk()
  root.title("Insane Chess Board Simulator")

  board_frame = tk.Frame(root)
  board_frame.pack(fill="both", expand="true", side="left")
  board.initTk(board_frame)
  board.pack(side="top", fill="both", expand="true", padx=4, pady=4)

  control_frame = tk.Frame(root)
  control_frame.pack(fill="x", expand="true", side="right")

  piece_ctl_frame = tk.Frame(control_frame)
  piece_ctl_frame.pack(fill="x", expand="true", side="top")

  default_instructions = "Left-Click to Select+Lift or Place Selected Piece (if valid).\nRight-Click to Select+Lift (without placing; allows multiple lifts)\n"
  add_piece_instructions = default_instructions + "Click board location to place the new piece!"
  instruction_text = tk.StringVar(value=default_instructions)
  instruction_label = tk.Label(piece_ctl_frame, textvariable=instruction_text, anchor='w', justify='left')
  instruction_label.pack(side="top", fill="x", expand="true", pady=7)

  piece_add_frame = tk.Frame(piece_ctl_frame)
  piece_add_frame.pack(fill="x", expand="true", side="top")
  add_piece_btn_text = tk.StringVar(value="Add New Piece")
  add_piece_btn = tk.Button(piece_add_frame, textvariable=add_piece_btn_text)
  piece_label_entry = tk.Entry(piece_add_frame, text="<piece label>")

  add_piece_color_val = tk.StringVar(value='white')
  piece_color_radio_white = tk.Radiobutton(piece_add_frame, text="White", variable=add_piece_color_val, value='white')
  piece_color_radio_black = tk.Radiobutton(piece_add_frame, text="Black", variable=add_piece_color_val, value='black')
  
  for e in [add_piece_btn, piece_label_entry, piece_color_radio_white, piece_color_radio_black]:
    e.pack(side="left", padx=4)

  add_entry_hint(piece_label_entry, "Piece Label")

  adding_piece = False
  def set_add_piece_click_handler():
    nonlocal adding_piece
    def cancel():
      nonlocal adding_piece
      instruction_text.set(default_instructions)
      add_piece_btn_text.set("Add New Piece")
      board.click_handler = None
      adding_piece = False
    if adding_piece:
      cancel() # toggles
    else:
      instruction_text.set(add_piece_instructions)
      add_piece_btn_text.set("Cancel")
      entry_fg = piece_label_entry.cget("fg")
      board.click_handler = lambda row, col, event: \
        (
          board.add_piece(
            text="?" if piece_label_entry.cget("fg") == 'gray' else piece_label_entry.get(),
            row=row, col=col, white=add_piece_color_val.get()=='white', block=False),
          cancel()
        )
      adding_piece = True
  add_piece_btn.config(command=set_add_piece_click_handler)
  
  rm_piece_frame = tk.Frame(piece_ctl_frame)
  rm_piece_frame.pack(fill="x", expand="true", side="top", pady=6)
  def try_remove_lifted_piece():
    if board.click_lifted_pieces:
      board.remove_piece(*board.pop_lifted_piece().pos, block=False)
  rm_piece_btn = tk.Button(rm_piece_frame, text="Remove Lifted Piece", command=try_remove_lifted_piece)
  rm_piece_btn.pack(side="left", padx=4)


  err_frame = tk.Frame(control_frame)
  err_frame.pack(fill="x", expand="true", side="top", pady=10)
  err_out_label = tk.Label(err_frame, text="Error Messages:", anchor="w")
  err_out_label.pack(side="top", fill="x", expand="yes")
  err_out_scroll = tk.Scrollbar(err_frame)
  err_out_scroll.pack(side="right", fill="y")
  err_out = tk.Text(err_frame, width=50, height=10, yscrollcommand=err_out_scroll.set, state="disabled")
  err_out.pack(side="left", expand="true", fill="both")
  err_out_scroll.config(command=err_out.yview)

  def write_err(msg : str):
    err_out.config(state='normal')
    err_out.insert(tk.END, msg + "\n")
    err_out.config(state='disabled')
    err_out.yview_pickplace(tk.END)

  board.err_cb = write_err

  button_frame = tk.Frame(control_frame)
  button_frame.pack(fill="x", expand="true", side="top", pady=6)
  clear_marker_btn = tk.Button(button_frame, text="Clear Collision Markers", command=board.clear_markers)
  clear_marker_btn.pack(side="left")

  if file_in is None:
    pipein_frame = tk.Frame(control_frame)
    pipein_frame.pack(fill="x", expand="true", side="top", pady=6)
    pipein_label = tk.Label(pipein_frame, text="Board Input:", anchor="w")
    pipein_label.pack(side="top", fill="x", expand="yes")
    pipein = tk.Entry(pipein_frame)
    pipein.pack(side="top", fill="x", expand="true")

    def send_pipein(event=None):
      cmd = pipein.get()
      if cmd:
        write_pipeout("<{}>".format(pipein.get()))
        board.handle_cmd_str(cmd)
        pipein.delete(0, tk.END)

    pipein.bind("<Return>", send_pipein)
    pipein_button = tk.Button(pipein_frame, text="Send", command=send_pipein)
    pipein_button.pack(side="bottom", expand="true")

  else: # infile is not none
    halt = False
    halt_cv = threading.Condition()
    filename_hint = " '{}'".format(file_in.name) if hasattr(file_in, 'name') else ""
    running_text = "(Running file{})".format(filename_hint)
    resume_text = "Continue File '{}'".format(filename_hint)
    continue_btn = tk.Button(control_frame, text=running_text, state='disabled')
    def continue_file():
      nonlocal halt
      halt_cv.acquire()
      halt = False
      continue_btn.config(text=running_text, state='disabled')
      halt_cv.notify()
      halt_cv.release()
    continue_btn.config(command=continue_file)
    continue_btn.pack(side="top")

    def file_listener():
      time.sleep(0.2)
      line : str = file_in.readline()
      while line:
        nonlocal halt
        halt_cv.acquire()
        while not halt_cv.wait_for(lambda: not halt):
          pass
        halt_cv.release()
        if line == 'halt':
          halt = True
          continue_btn.config(text=resume_text)
          continue_btn.config(state='normal')
        else:
          write_pipeout("<{}>".format(line.rstrip()))
          board.handle_cmd_str(line)
        line = file_in.readline()
      write_pipeout("<EOF>")
    listener_thread = threading.Thread(target=file_listener, daemon=True)
    listener_thread.start()

  pipeout_frame = tk.Frame(control_frame, pady=6)
  pipeout_frame.pack(fill="x", expand="true", side="bottom")

  pipeout_label = tk.Label(pipeout_frame, text="Board Output:", anchor="w")
  pipeout_label.pack(side="top", fill="x", expand="yes")
  pipeout_scroll = tk.Scrollbar(pipeout_frame)
  pipeout_scroll.pack(side="right", fill="y")
  pipeout = tk.Text(pipeout_frame, width=20, height=8, yscrollcommand=pipeout_scroll.set, state="disabled")
  pipeout.pack(side="left", expand="true", fill="both")
  pipeout_scroll.config(command=pipeout.yview)

  def write_pipeout(msg : str):
    pipeout.config(state='normal')
    pipeout.insert(tk.END, msg + "\n")
    pipeout.config(state='disabled')
    pipeout.yview_pickplace(tk.END)

  board.out_cb = write_pipeout

  if file_out is not None:
    board.out_cb = tee_cb(board.out_cb, lambda str: file_out.write(str + '\n'))

  if after_arg is not None:
    root.after(100, after_arg)
  root.mainloop()

def setup_board(board : GameBoard):
  board.join()
  board.clear()
  do_sensor_print = board.sensor_print_enabled()
  if do_sensor_print:
    board.board_events.put(board.disable_sensors_print)
  board_rows = {
    14: "rnbqkbnr",
    12: "pppppppp",

    2: "PPPPPPPP",
    0: "RNBQKBNR"
  }
  for row in board_rows:
    col = 5
    for piece in board_rows[row]:
      board.add_piece(piece.upper(), row=row, col=col, white=piece.isupper())
      col += 2
  
  if do_sensor_print:
    board.board_events.put(board.enable_sensors_print)

def launch_appthread(board : GameBoard):
  board.enable_sensors()
  board.enable_sensors_print()
  board.join()
  setup_board(board)

def main():
  board = GameBoard()
  launch_tk(board, after_arg=lambda: launch_appthread(board))

if __name__ == "__main__":
  main()