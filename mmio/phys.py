#! /usr/bin/python3

# PHY low-level device control classes for use with mmp.py and mmpgui.py

import serial

class PHY():
    def __init__(self):
        pass

    def openDevice(self):
        """openDevice() should return True if a valid device has been opened
        successfully, otherwise it should return False."""
        print("Please implement openDevice() according to your application.")
        return False

    def transmit(self, msgEncoded):
        """Transmit the encoded message 'msgEncoded' across the implemented
        physical layer.  Return True if successful, False otherwise."""
        print("Please implement transmit() according to your application.")
        return False

    def readResponse(self, nBytes = 1):
        """Poll device for 'nBytes' of response data and return if read.
        May return up to 'nBytes' of encoded data or None if there is no
        data available to read."""

    def reset(self):
        """Reset the low-level device pipe (i.e. flush).  This is used by
        the protocol when message corruption is detected."""
        return

class PHY_USBUART(PHY):
    def __init__(self, port, baudrate=115200, timeout_ms = 1000):
        self.port = port
        self.baudrate = baudrate
        self.timeout_ms = timeout_ms

    def openDevice(self):
        try:
            self.com = serial.Serial(port = self.port, baudrate = self.baudrate, bytesize = 8,\
                                     stopbits = 1, timeout = self.timeout_ms/1000)
        except Exception as e:
            print(e)
            print("Serial ports detected: {}".format(self.listSerialPorts()))
            self.com = None
        return self.com != None

    def readResponse(self, nBytes = 1):
        inBytes = None
        inWaiting = self.com.in_waiting
        #if inWaiting >= nBytes:
        if True:
            try:
                inBytes = self.com.read_all()
                #print("readResponse() read {} bytes".format(len(inBytes)))
            except Exception as e:
                print("readResponse() Err\n" + e)
                return None
        else:
            #print("readResponse() inWaiting = {}".format(inWaiting))
            return None
        return inBytes

    def transmit(self, msg):
        if self.com.out_waiting > 0:
            #print("transmit() out_waiting > 0")
            return False
        try:
            self.com.write(msg)
            #print("transmit() write success")
        except serial.SerialException:
            #print("transmit() SerialException")
            return False
        return True

    def reset(self):
        self.com.flushInput()
        return

    @staticmethod
    def listSerialPorts():
        coms = serial.tools.list_ports.comports()
        return [x.device for x in coms]

