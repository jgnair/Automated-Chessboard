# Movement - each motor will always get the same number of steps, we will adjust the speed
# Right: both motors clockwise
# Left: both motors counter-clockwise
# Up: right clockwise, left counter
# Down: right counter, left clockwise
# Diagonal: one motor full speed other motor half speed - use up or down motor directions?

# I drew it out on the whiteboard and i think perfect diagonal is one moving and one stopped, see below - Nathan
#   for constant velocity factor 'v' and desired motion dx/dy, L/R motor speeds vl/vr (positive is clockwise) are
#       dx=0 (vertical): 
#           vr = -vl = dy * v; vl = -vr = -dy * v
#       dy=0 (horizontal):
#           vr = vl = dx * v
#       dx=dy='d' (diag down right): 
#           vl = 0 ; vr = -d * sqrt(2) * v
#       dx=-dy (diag up right): 
#           vl = dx * sqrt(2) * v = -dy * sqrt(2) * v ; vr = 0


####NEW MOVEMENT FORMAT######
# m: movement (step-number possibly 4 digits)  FOR ease of code writing on the number of sterps will always be four digits
# L: Left Motor Direction (0 - counter-clockwise, 1 - clockwise)
# R: Right Motor Direction (0 - counter-clockwise, 1 - clockwise)
# l: Left Motor Speed (0 - half speed, 1 - full speed) 
# r: right Motor speed 0 - half speed, 1 - full speed)

#######EXAMPLE Move Right 100#######
# m1000L1l1R1r1

#####Using electromagnet####### 
# 1000 steps right, EM on, 1000 steps off, EM off, end#####
# m1000L1l1R1r1Em1000L0l1R1r1e\n

import math
from Config import Config

global steps_per_half_sq
steps_per_half_sq = 100

class Motion:
    def __init__(self, dx, dy):
        self.dx = dx
        self.dy = dy
    
    def isLeft(self, perfect = True):
        return self.dx < 0 and (not perfect or self.dy == 0)
    
    def isRight(self, perfect = True):
        return self.dx > 0 and (not perfect or self.dy == 0)
    
    def isUp(self, perfect = True):
        return self.dy > 0 and (not perfect or self.dx == 0)

    def isDown(self, perfect = True):
        return self.dy < 0 and (not perfect or self.dx == 0)

    def isUpLeft(self):
        return self.isUp(perfect=False) and self.isLeft(perfect=False)
    
    def isUpRight(self):
        return self.isUp(perfect=False) and self.isRight(perfect=False)
    
    def isDownLeft(self):
        return self.isDown(perfect=False) and self.isLeft(perfect=False)

    def isDownRight(self):
        return self.isUp(perfect=False) and self.isRight(perfect=False)
    
    def to_str(self):
        if self.isUp(perfect=False):
            if self.isRight(perfect=False):
                assert self.dx == self.dy
                return "Ur{:02d}".format(self.dy)
            elif self.isLeft(perfect=False):
                assert -self.dx == self.dy
                return "Ul{:02d}".format(self.dy)
            else:
                return "u{:02d}".format(self.dy)
        elif self.isDown(perfect=False):
            if self.isRight(perfect=False):
                assert -self.dx == self.dy
                return "Dr{:02d}".format(-self.dy)
            elif self.isLeft(perfect=False):
                assert self.dx == self.dy
                return "Dl{:02d}".format(-self.dy)
            else:
                return "d{:02d}".format(-self.dy)
        else:
            if self.isRight(perfect=False):
                return "r{:02d}".format(self.dx)
            else:
                assert self.isLeft(perfect=False)
                return "l{:02d}".format(-self.dx)

def is_motion(cmd):
    return isinstance(cmd, Motion)

class EmagCtl:
    def __init__(self, emag):
        self.emag = emag
    
    def to_str(self):
        return 'E' if self.emag else 'e'

def is_emag(cmd):
    return isinstance(cmd, EmagCtl)

class Motor:
    def __init__(self, x, y):
        # blank command to start
        self.cmd_list = []
        self.cmd = ""
        # current x using half squares
        self.x = x
        # current y using half square
        self.y = y

    def addMotion(self, dx, dy):
        self.cmd_list.append(Motion(dx=dx, dy=dy))
        self.x += dx
        self.y += dy
        return self

    def addLeftMove(self, halfSquares):
        if halfSquares > 0:
            return self.addMotion(dx=-halfSquares, dy=0)

    def addRightMove(self, halfSquares):
        if halfSquares > 0:
            return self.addMotion(dx=halfSquares, dy=0)

    def addUpMove(self, halfSquares):
        if halfSquares > 0:
            return self.addMotion(dx=0, dy=halfSquares)

    def addDownMove(self, halfSquares):
        if halfSquares > 0:
            return self.addMotion(dx=0, dy=-halfSquares)

    def addUpLeftMove(self, halfSquares):
        # Might be wrong command we will have to check these
        if halfSquares > 0:
            return self.addMotion(dx=-halfSquares, dy=halfSquares)

    def addUpRightMove(self, halfSquares):
        # Might be wrong command we will have to check these
        if halfSquares > 0:
            return self.addMotion(dx=halfSquares, dy=halfSquares)

    def addDownLeftMove(self, halfSquares):
        # Might be wrong command we will have to check these
        if halfSquares > 0:
            return self.addMotion(dx=-halfSquares, dy=-halfSquares)

    def addDownRightMove(self, halfSquares):
        # Might be wrong command we will have to check these
        if halfSquares > 0:
            return self.addMotion(dx=halfSquares, dy=-halfSquares)

    def turnOnElecMag(self):
        self.cmd_list.append(EmagCtl(emag=True))
        return self

    def turnOffElecMag(self):
        self.cmd_list.append(EmagCtl(emag=False))
        return self

    def resetCMD(self):
        self.cmd = ""
        return self

    def getCMD(self):
        if not self.cmd:
            postprocessed = self.postprocessCMD(self.cmd_list)
            for cmd in postprocessed:
                self.cmd += cmd.to_str()
            self.cmd_list.clear()
            if self.cmd:
                self.cmd += "\n"
        return self.cmd
    
    def optimizeEmagMotion(self, cmd_sub):
        result = []
        dirs = []
        def get_dir(cmd : Motion):
            assert cur.dx == 0 or cmd.dy == 0 or abs(cmd.dx) == abs(cmd.dy)
            # put everything in quadrants 1/2
            dir_dx, dir_dy = (cmd.dx, cmd.dy)
            if cmd.dy < 0:
                dir_dx = -dir_dx
                dir_dx = -dir_dy
            if cmd.dy == 0:
                dir_dx = abs(dir_dx)

            return round(100*math.atan2(dir_dy, dir_dx))

        for cur in cmd_sub:
            cur : Motion 
            assert is_motion(cur)
            cur_dir = get_dir(cur)

            if result:
                prev : Motion = result[-1]
                prev_dir = dirs[-1]
                if prev_dir == cur_dir:
                    combined = Motion(dx=cur.dx+prev.dx, dy=cur.dy+prev.dy)
                    if combined.dx == 0 and combined.dy == 0:
                        result.pop()
                        dirs.pop()
                    else:
                        result[-1] = combined
                        # dir is already in
                    continue
            
            result.append(cur)
            dirs.append(cur_dir)
                
        return result

    def optimizeNonEmagMotion(self, cmd_sub):
        xdiff = 0
        ydiff = 0
        for cmd in cmd_sub:
            assert is_motion(cmd)
            xdiff += cmd.dx
            ydiff += cmd.dy

        result = []

        if Config.DIAGONALS:
            diff_common = min(abs(xdiff), abs(ydiff))
            if diff_common > 0:
                diag_diffx = diff_common if xdiff >= 0 else -diff_common
                diag_diffy = diff_common if ydiff >= 0 else -diff_common
                result.append(Motion(dx=diag_diffx, dy=diag_diffy))
                xdiff -= diag_diffx
                ydiff -= diag_diffy

        if xdiff != 0:
            result.append(Motion(dx=xdiff, dy=0))
        if ydiff != 0:
            result.append(Motion(dx=0, dy=ydiff))

        return result


    def postprocessCMD(self, cmd_list):
        emag = True
        emag_chunk = []
        result = []
        def optimize_chunk(new_emag):
            nonlocal emag
            nonlocal result
            assert new_emag != emag
            emag = new_emag
            if not emag_chunk:
                return
            if not new_emag:
                optimized = self.optimizeEmagMotion(emag_chunk)
            else:
                optimized = self.optimizeNonEmagMotion(emag_chunk)
            emag_chunk.clear()
            if optimized:
                result += optimized

        for cmd in cmd_list:
            if is_emag(cmd):
                # if its the different from our current recollection
                if cmd.emag != emag:
                    optimize_chunk(cmd.emag)
                    result.append(cmd)
            # non emag
            else:
                emag_chunk.append(cmd)
        
        #trailing chunk
        optimize_chunk(not emag)
        return result

    def MoveToCoordinate(self, newX, newY):
        hori = self.x - newX
        vert = self.y - newY
        if (hori < 0):
            self.addLeftMove(abs(hori) * 2)
        else:
            self.addRightMove(hori * 2)
        if (vert < 0):
            self.addUpMove(abs(vert) * 2)
        else:
            self.addDownMove(vert * 2)
        return self

    def MoveDiagonal(self, newX, newY):
        hori = self.x - newX
        vert = self.y - newY
        if (hori < 0 and vert < 0):
            self.addUpLeftMove(abs(hori) * 2)
        elif (hori < 0 and vert > 0):
            self.addUpRight(abs(hori) * 2)
        elif (hori > 0 and vert < 0):
            self.addDownLeft(hori * 2)
        else:
            self.addDownRight(hori * 2)
        return self
