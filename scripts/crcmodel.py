#!/usr/bin/python3

# Safe data packet transmission over UART using Forward Error Correction via CRC16
# To be used with any server which calculates an identical CRC16
# Using CRC-16-IBM (USB-type)

#   Name   : "CRC-16"
#   Width  : 16
#   Poly   : 8005
#   Init   : 0000
#   RefIn  : True
#   RefOut : True
#   XorOut : 0000
#   Check  : BB3D

def _bin8(h):
    return "{:08b}".format(h)

class cm_t():
    def __init__(self, width = None, poly = None, init = None, refin = False, refot = False, xorot = False):
        self.width = width
        self.poly = poly
        self.init = init
        self.refin = refin
        self.refot = refot
        self.xorot = xorot
        self.reg = 0
        self._ready = False
        if self._check():
            self._ready = True
            self.cm_ini()
        else:
            print("cm_t not initialized!")

    def _check(self):
        if self.width is None:
            return False
        if self.poly is None:
            return False
        if self.init is None:
            return False
        if self.refin is None:
            return False
        if self.refot is None:
            return False
        if self.xorot is None:
            return False
        return True

    def initialize(self, width = None, poly = None, init = None, refin = False, refot = False, xorot = False):
        if width is not None:
            self.width = width
        if poly is not None:
            self.poly = poly
        if init is not None:
            self.init = init
        if refin is not None:
            self.refin = refin
        if refot is not None:
            self.refot = refot
        if xorot is not None:
            self.xorot = xorot
        return

    def cm_ini(self):
        self.reg = self.init

    def cm_nxt(self, ch):
        if self._ready:
            topbit = (1 << (self.width - 1))    # Bitmask of top bit of poly width
            if self.refin:
                ch = self._reflect(ch, 8)
            self.reg ^= (ch << (self.width - 8))
            for i in range(8):
                if (self.reg & topbit):         # If the MSbit of the register is '1'
                    self.reg = (self.reg << 1) ^ self.poly
                else:
                    self.reg <<= 1
                self.reg &= self._widmask()
        return

    def cm_crc(self):
        if self._ready:
            if self.refot:
                return self.xorot ^ self._reflect(self.reg, self.width)
            else:
                return self.xorot ^ self.reg
        else:
            print("cm_crc - not initialized!")

    def cm_blk(self, blk):
        if self._ready:
            for b in blk:
                self.cm_nxt(b)
        else:
            print("cm_blk - not initialized!")

    @staticmethod
    def _reflect(val, bottom):
        """Returns the value 'val' with the bottom 'bottom' = [0-32] bits reflected"""
        t = val
        for i in range(bottom):
            if (t & 1):
                val |= (1 << (bottom - 1 - i))
            else:
                val &= ~(1 << (bottom - 1 - i))
            t >>= 1
        return val

    def _widmask(self):
        return (((1 << (self.width - 1)) - 1) << 1) | 1

class cm_tab():
    def __init__(self, cm):
        self.cm = cm
        if cm._ready:
            self.width = cm.width
            self.poly = cm.poly
            self.init = cm.init
            self.refin = cm.refin
            self.refot = cm.refot
            self.xorot = cm.xorot
        else:
            print("cm not initialized")

    def calc(self, index):
        topbit = (1 << (self.width - 1))    # Bitmask of top bit of poly width
        if self.refin:
            index = cm_t._reflect(index, 8)
        r = index << (self.width - 8)
        for i in range(8):
            if (r & topbit):
                r = (r << 1) ^ self.poly
            else:
                r <<= 1
        if self.refin:
            r = cm_t._reflect(r, self.width)
        return r & self.cm._widmask()

def main():
    cm16 = cm_t(
        width = 16,
        poly = 0x8005,
        init = 0,
        refin = True,
        refot = True,
        xorot = 0
        )

    msg = bytes("123456789", "ASCII")
    for b in msg:
        cm16.cm_nxt(b)
    crc = cm16.cm_crc()
    print("msg = {}".format(msg.decode('ASCII')))
    print("CRC = {:04x}".format(crc))

if __name__ == "__main__":
    main()