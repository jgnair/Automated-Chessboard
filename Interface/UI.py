from svglib.svglib import svg2rlg
from tkinter import *
from PIL import ImageTk, Image
from reportlab.graphics import renderPM
import chess.svg
import Turns
from Config import Config
import queue
import time
import threading


class UI:
    def draw_garages(self):
        self.garage_offset = 20
        self.garage_height = 461.5
        self.garage_width = self.garage_height / 4
        self.square_size = self.garage_width / 2
        garage_dx = 250 + self.garage_offset
        image_x, image_y = self.image_center

        garage_y_top = image_y-self.garage_height/2
        garage_y_bottom = image_y+self.garage_height/2
        left_garage_start = image_x - garage_dx - self.garage_width
        right_garage_start = image_x + garage_dx
        left_garage_end = image_x - garage_dx
        right_garage_end = image_x + garage_dx + self.garage_width

        self.board.create_rectangle(left_garage_start, garage_y_top, left_garage_end, garage_y_bottom, fill='gray', tags=('garage', 'garage_bg'))
        self.board.create_rectangle(right_garage_start, garage_y_top, right_garage_end, garage_y_bottom, fill='gray', tags=('garage', 'garage_bg'))
        
        line_y = garage_y_top + self.square_size
        for line_row in range(7):
            self.board.create_line(left_garage_start, line_y, left_garage_end, line_y, fill='black', tags=('garage', 'garage_line'))
            self.board.create_line(right_garage_start, line_y, right_garage_end, line_y, fill='black', tags=('garage', 'garage_line'))
            line_y += self.square_size
        
        left_vertline_x = left_garage_start + self.square_size
        right_vertline_x = right_garage_start + self.square_size
        self.board.create_line(left_vertline_x, garage_y_top, left_vertline_x, garage_y_bottom, fill='black', tags=('garage', 'garage_line'))
        self.board.create_line(right_vertline_x, garage_y_top, right_vertline_x, garage_y_bottom, fill='black', tags=('garage', 'garage_line'))


    def __init__(self):
        self.root = Tk()
        self.board = Label(self.root, image=None)
        self.board = Canvas(self.root, width=1600, height=500)
        self.image_center = (799, 249)
        self.draw_garages()
        self.board.tag_lower('garage_line')
        self.drawing_sensors = False
        self.stop_flashing = threading.Event()
        self.done_flashing = threading.Event()
        self.done_flashing.set()

        self.board.image = None
        self.buttonFrame = Frame(self.root)
        bf = self.buttonFrame
        self.forfeitButton = Button(bf, text="Forfeit", width=15, height=5, bg='black', fg='white', command=self.player_forfeit)
        self.hintButton = Button(bf, text="Hint", width=15, height = 5, bg='black', fg='white', command=self.player_hint)
        self.resetButton = Button(bf, text="Reset Board", width=15, height = 5, bg='black', fg='white', command=self.player_reset)
        self.root.title("Chess")
        self.message = StringVar()
        self.showInfo = Label(self.root, textvariable=self.message, font=("Courier", 20))
        self.hasConsole = False
        if Config.CONSOLE:
            self.console_label = Label(self.root, text="Console: ")
            self.console = Entry(self.root)
            self.console_cmd_q = queue.Queue()
            def send_console_cmd(event):
                self.console_cmd_q.put(self.console.get())
                self.console.delete(0, END)
            self.console.bind("<Return>", send_console_cmd)
            self.hasConsole = True
        self.alive = True
        self.pack()
        self.reset_cb = lambda: None
        self.forfeit_cb = lambda: None

    def player_forfeit(self):
        print('\nYou lose :(')
        self.message.set("You lose :(")
        self.forfeitButton.config(state='disabled')
        self.root.update()
        self.forfeit_cb()

    def player_hint(self):
        self.message.set("Here's your hint: " + Turns.getStockfishMove(isForHint=True))

    def set_reset_cb(self, cb):
        self.reset_cb = cb

    def player_reset(self):
        self.forfeitButton["state"] = "active"
        self.root.update()
        self.reset_cb()

    def pack(self):
        if not self.alive:
            return 
        self.board.pack(side=TOP, padx=5, pady=5)
        self.hintButton.pack(side = LEFT)
        self.resetButton.pack(side = LEFT)
        self.forfeitButton.pack(side = LEFT)
        self.message.set("Welcome! Make your move.")
        if self.hasConsole:
            self.console.pack(side=BOTTOM, pady=5)
            self.console_label.pack(side=BOTTOM)
        self.buttonFrame.pack(side = BOTTOM, pady=5)
        self.showInfo.pack(side = BOTTOM)

    def draw(self):
        if not self.alive:
            return 
        print('updating board')
        svg = chess.svg.board(chess.Board(Turns.getFenPos()), size=1500)
        with open("Images/svgFile.SVG", "w+") as svgFile:
            svgFile.write(svg)
            drawing = svg2rlg("Images/svgFile.SVG")
            renderPM.drawToFile(drawing, "Images/my.png", fmt="PNG")
        # resize image to fit on screen
        img = Image.open("Images/my.png")
        resized_img = img.resize((500, 500))
        img = ImageTk.PhotoImage(resized_img)
        # update image in Label
        self.board.delete("image")
        self.board.create_image(*self.image_center,image=img, tags=("image"))
        self.board.image = img
        self.board.pack(side=TOP)
    
    def flash_message(self, period=0.2, repeat=6, fg='red', bg='black'):
        self.stop_flashing.set()
        def impl():
            stop = self.stop_flashing
            done = self.done_flashing
            oldFg = self.showInfo.cget('fg')
            oldBg = self.showInfo.cget('bg')
            for _ in range(repeat):
                self.showInfo.config(fg=fg)
                self.showInfo.config(bg=bg)
                if stop.isSet():
                    break
                time.sleep(period)
                self.showInfo.config(fg=oldFg)
                self.showInfo.config(bg=oldBg)
                if stop.isSet():
                    break 
                time.sleep(period)
            self.showInfo.config(fg=oldFg)
            self.showInfo.config(bg=oldBg)
            done.set()

        self.done_flashing.wait(timeout=2)
        self.stop_flashing.clear()
        self.done_flashing.clear()
        threading.Thread(target=impl, daemon=True).start()

    def draw_sensor_diff(self, needs_lift : set, needs_place : set, msg = "Please correct the invalid board state above!"):
        def draw_sensor(pos, color):
            (row,col) = pos
            name = "sensor_{:x}{:x}".format(*pos)
            x_ctr = col - 5.5
            y_ctr = row - 3.5
            x_ctr_abs = abs(x_ctr)
            y_ctr_abs = abs(y_ctr)
            dx_abs = x_ctr_abs*self.square_size
            dy_abs = y_ctr_abs*self.square_size
            if x_ctr_abs > 4:
                board_label_width = 250-4*self.square_size
                dx_abs += self.garage_offset + board_label_width
            
            dx = dx_abs if x_ctr >= 0 else -dx_abs
            dy = dy_abs if y_ctr >= 0 else -dy_abs
            x = self.image_center[0] + dx
            y = self.image_center[1] - dy
            delta = self.square_size/2.3

            self.board.create_rectangle(x-delta, y-delta, x+delta, y+delta, outline=color, width=5, tags=(name, 'sensor'))

        self.message.set(msg)
        self.board.delete('sensor')
        self.board.tag_raise('garage_line')

        for pos in needs_lift:
            draw_sensor(pos, 'green')
        for pos in needs_place:
            draw_sensor(pos, 'red')

        self.flash_message()


    def undraw_sensor_diff(self, msg = "Board state was recovered."):
        self.board.delete('sensor')
        self.board.tag_lower('garage_line')
        self.message.set(msg)

    def mainloop(self):
        self.root.resizable(False, False)
        self.root.mainloop()
        self.alive = False
    
    def is_alive(self):
        return self.alive

    def quit(self):
        print("Quitting UI")
        self.alive = False
        self.root.destroy()

