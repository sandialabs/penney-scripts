#! /usr/bin/python3

# Protocol classes for use with mmp.py and mmpgui.py

import re

USE_CRC = False
#USE_CRC = True

if USE_CRC:
    import crcmodel

class Protocol():
    """This class should be inherited with the following methods overloaded
    according to the protocol implemented.
        packMessageReadRegister(addr)
            Compose a bytes-type object observing the implemented protocol
            to perform a "read register" command.  The returned object should
            be formatted to allow direct transfer to the device.
        packMessageWriteRegister(addr, value)
            Compose a bytes-type object observing the implemented protocol
            to perform a "write register" command.  The returned object should
            be formatted to allow direct transfer to the device.
        unpackResponse(response)
            Unpack the raw response from the device into a register address and
            value.  The only response from a memory-mapped peripheral should be
            to a "read register" command.
    """
    @classmethod
    def responseBytes(cls):
        """Return the number of bytes expected in a response message."""
        return 1

    @classmethod
    def packMessageReadRegister(cls, addr):
        """Pack message bytes object for a register write command to be passed
        directly to the low-level PHY class."""
        return None

    @classmethod
    def packMessageWriteRegister(cls, addr, value):
        """Pack message bytes object for a register write command to be passed
        directly to the low-level PHY class."""
        return None

    @classmethod
    def unpackResponse(cls, response):
        """Unpack a response read directly from the low-level PHY class.
        Interpret response into (registerAddress, registerValue) and return."""
        return (None, None)

class ProtocolIPCTRL_ASCII(Protocol):
    """Implements a limited set (just read-reg/write-reg) of the IPCTRL protocol
    with ASCII character encoding."""
    CMD_CHAR_WRITE    = 'a'
    CMD_CHAR_READ     = 'b'
    CMD_CHAR_RESPONSE = 'c'
    TERMINATING_CHAR  = '\n'
    MIN_RESPONSE_LENGTH = 11
    _encoding = 'utf-8'
    # '\A' matches the start of a string
    _matchReadResponse = "\A" + CMD_CHAR_RESPONSE + "([0-9a-fA-F]{2})([0-9a-fA-F]{8})(.*)"
    _reReadResponse = re.compile(_matchReadResponse)
    if USE_CRC:
        _CRCEng = crcmodel.cm_t(width = 16, poly = 0x8005, init = 0, refin = True, refot = True, xorot = 0)
    else:
        _CRCEng = None

    @classmethod
    def responseBytes(cls):
        """Return the number of bytes expected in a response message."""
        return cls.MIN_RESPONSE_LENGTH

    @classmethod
    def _getCRC(cls, msg):
        if cls._CRCEng == None:
            return bytes(cls._hex4(0), cls._encoding)
        cls._CRCEng.cm_ini()
        for b in msg:
            cls._CRCEng.cm_nxt(b)
        crc = cls._CRCEng.cm_crc()
        crc_hex = bytes(cls._hex4(crc), cls._encoding)
        return crc_hex

    @classmethod
    def packMessageReadRegister(cls, addr):
        """Pack message bytes object for a register write command to be passed
        directly to the low-level PHY class."""
        s = cls.CMD_CHAR_READ + cls._hex2(addr) + cls._hex8(0)
        msg = bytes(s, cls._encoding)
        crc = cls._getCRC(msg)
        term = bytes(cls.TERMINATING_CHAR, cls._encoding)
        return msg + crc + term

    @classmethod
    def packMessageWriteRegister(cls, addr, value):
        """Pack message bytes object for a register write command to be passed
        directly to the low-level PHY class."""
        s = cls.CMD_CHAR_WRITE + cls._hex2(addr) + cls._hex8(value)
        msg = bytes(s, cls._encoding)
        crc = cls._getCRC(msg)
        term = bytes(cls.TERMINATING_CHAR, cls._encoding)
        return msg + crc + term

    @classmethod
    def unpackResponse(cls, response):
        """Unpack a response read directly from the low-level PHY class.
        Interpret response into (registerAddress, registerValue) and return."""
        #print("Unpacking {} bytes = {}".format(len(response), response))
        if len(response) < cls.MIN_RESPONSE_LENGTH:
            return (None, None)
        if hasattr(response, 'decode'):
            response = response.decode(cls._encoding)
        match = cls._reReadResponse.match(response)
        if not match:
            return (None, None)
        #nregString = match.group(1)
        #regvalString = match.group(2)
        nreg = cls._fromHex(match.group(1))
        regval = cls._fromHex(match.group(2))
        #print("Parsed: {}, {}".format(nreg, regval))
        return (nreg, regval)

    @classmethod
    def _isTerminated(cls, c):
        try:
            if len(c) == 0:
                return False
            if len(c) == 1:
                return c == cls.TERMINATING_CHAR
            else:
                return cls.TERMINATING_CHAR in c
        except TypeError:           # This will occur if c is None
            return False

    @classmethod
    def _isBufferTerminated(cls, b):
        for i in b:
            if cls.isTerminated(i):
                return True
        return False

    @staticmethod
    def _fromHex(h):
        """Convert a hex string (without the '0x') to a number"""
        return int(h, 16)

    @staticmethod
    def _hex8(b):
        """Returns a string of 8 chars of 'b' in hex-base (0-padded to the left)"""
        return "{:08x}".format(b)

    @staticmethod
    def _hex4(b):
        """Returns a string of 4 chars of 'b' in hex-base (0-padded to the left)"""
        return "{:04x}".format(b)

    @staticmethod
    def _hex2(b):
        """Returns a string of 2 chars of 'b' in hex-base (0-padded to the left)"""
        return "{:02x}".format(b)

    @classmethod
    def testPackMessageReadRegister(cls, argv):
        USAGE = "python3 {} nreg".format(argv[0])
        if len(argv) < 2:
            print(USAGE)
            return False
        nreg = int(argv[1])
        msg = cls.packMessageReadRegister(nreg).decode(cls._encoding)
        print("Read from register {}. Msg = {}".format(nreg, msg))
        return True

    @classmethod
    def testPackMessageWriteRegister(cls, argv):
        USAGE = "python3 {} nreg [regval=0]".format(argv[0])
        if len(argv) < 2:
            print(USAGE)
            return False
        if len(argv) > 2:
            regval = int(argv[2])
        else:
            regval = 0
        nreg = int(argv[1])
        msg = cls.packMessageWriteRegister(nreg, regval).decode(cls._encoding)
        print("Write {} to register {}. Msg = {}".format(regval, nreg, msg))
        return True

    @classmethod
    def testUnpackResponse(cls, argv):
        USAGE = "python3 {} responseString".format(argv[0])
        if len(argv) < 2:
            print(USAGE)
            return False
        nreg, regval = cls.unpackResponse(argv[1])
        print("nreg = {}, regval = {}".format(nreg, regval))
        return True

if __name__ == "__main__":
    import sys
    #ProtocolIPCTRL_ASCII.testUnpackResponse(sys.argv)
    #ProtocolIPCTRL_ASCII.testPackMessageWriteRegister(sys.argv)
    ProtocolIPCTRL_ASCII.testPackMessageReadRegister(sys.argv)
