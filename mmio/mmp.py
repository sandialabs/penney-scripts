#! /usr/bin/python3

# A generic memory-mapped peripheral class for controlling any device whose interface is
# based on a collection of memory-mapped registers rather than an elaborate API.
# Assuming device API consists of:
#   Read Register
#   Write Register
#   Other unused/courtesy functions
#   (messaging details are application-specific and should be overridden)
#
# Usage Instructions:
#   1) Create a class which inherits from class phys.PHY
#       a) Override functions with application-specific behavior:
#          openDevice(), transmit(), readResponse(), reset()
#       b) Or select an existing PHY class
#   2) Create a class which inherits from class protocols.Protocol
#       a) Override functions with application-specific behavior:
#          packMessageReadRegister(), packMessageWriteRegister(),
#          unpackResponse(), responseBytes()
#       b) Or select an existing Protocol class
#   3) Create a register map file (currently on JSON format supported)
#      which defines the registers and members according to your
#      device specifications.
#   4) Create a class which inherits from class MMPeriph
#       a) Create an object (instance) of the selected PHY
#       b) Pass the register file name (string), the PHY object (instance),
#          and the Protocol class (NOT instance) to the MMPeriph class
#          via super().__init__()
#   5a) To create an auto-generated GUI, pass an instance of the custom MMPeriph
#      class to mmpgui.makeGUI()
#   5b) Alternatively, create your own GUI with getter/setter functions
#      named according to the auto-association scheme in 
#      MMPeriph.getParentSetter() and MMPeriph.getParentGetter()
#       a) Call MMPeriph.processQueue() and MMPeriph.readAndParseFromDevice()
#          in your main loop.
#       b) Call MMPeriph.setChangesFromUI() and MMPeriph.sendChangesToDevice()
#          whenever you want to update the physical device based on values in
#          the UI.

# TODO:
#   Mask out writes to read-only registers/members?
#   Mask out reads from write-only registers/members?
#   Make a better format for input file (more readable than JSON).

import os
import json
import fifo
import protocols
import phys

class MMPeriph():
    _CMD_WRITE = 0
    _CMD_READ  = 1
    def __init__(self, memoryMapFilename, protocol, phy, parent = None, queued = True):
        self.parent = parent
        interpreter = None
        registers = []
        self.memoryMapFilename = memoryMapFilename
        if os.path.exists(memoryMapFilename):
            print("{} exists".format(memoryMapFilename))
            root, ext = os.path.splitext(memoryMapFilename)
            if ext.lower() == '.json':
                print("It's a JSON")
                interpreter = JSONRegisterMapReader(memoryMapFilename)
        if interpreter != None:
            registers = interpreter.getRegisters()
        self.queued = True if queued else false
        if self.queued:
            self._cmdQueue = fifo.FIFO(bufferDepth = 10, blockOnFull = True)
        else:
            self._cmdQueue = None
        self.registerMap = RegisterMap(registers)
        self.initUI()
        self.protocol = protocol
        self.phy = phy
        if not hasattr(self.phy, 'openDevice'):
            print("phy object is not compatible. Missing method 'openDevice'")
        else:
            self._ready = self.phy.openDevice()

    def setParent(self, parent):
        self.parent = parent

    def writeRegister(self, regAddr, regValue):
        #print("Please implement writeRegister(regAddr, regValue) according to your application.")
        msgEncoded = self.protocol.packMessageWriteRegister(regAddr, regValue)
        return self.phy.transmit(msgEncoded)

    def readRegister(self, regAddr):
        #print("Please implement readRegister(regAddr) according to your application.")
        msgEncoded = self.protocol.packMessageReadRegister(regAddr)
        #print("readRegister() regAddr {}. Msg = {}".format(regAddr, msgEncoded))
        return self.phy.transmit(msgEncoded)

    def readAndParseFromDevice(self):
        msg = self.phy.readResponse(self.protocol.responseBytes())
        if msg != None and len(msg) > 0:
            regAddr, regVal = self.protocol.unpackResponse(msg)
            #print("readAndParseFromDevice() regAddr {}, regVal {}".format(regAddr, regVal))
            if regAddr != None:
                self.handleReadResponse(regAddr, regVal)
            else:
                # If a message is returned, but not properly parsed, a PHY reset is triggered.
                self.phy.reset()
        else:
            #print("readAndParseFromDevice() msg = None")
            pass

    def processQueue(self):
        """Call this periodically to shift calls through the FIFO (if using)."""
        cmd = self._cmdQueue.load()
        rval = False
        if cmd != None:
            #print("cmd = {}".format(cmd))
            rw, regAddr, regVal = cmd
            if rw == self._CMD_READ:
                rval = self.readRegister(regAddr)
            elif rw == self._CMD_WRITE:
                rval = self.writeRegister(regAddr, regVal)
            if rval:
                # If the command was successful, increment the queue
                self._cmdQueue.inc()

    def addReadToQueue(self, regAddr):
        #print("addReadToQueue({})".format(hex(regAddr)))
        if self.queued:
            self._cmdQueue.add((self._CMD_READ, regAddr, 0))
        else:
            self.readRegister(regAddr)
        return 0

    def addWriteToQueue(self, regAddr, regVal):
        #print("addWriteToQueue({}, {})".format(hex(regAddr), hex(regVal)))
        if self.queued:
            self._cmdQueue.add((self._CMD_WRITE, regAddr, regVal))
        else:
            self.writeRegister(regAddr, regVal)
        return

    def requestNewRegisterValues(self, regAddressList):
        if hasattr(regAddressList, '__len__'):
            for regAddr in regAddressList:
                self.addReadToQueue(regAddr)
        else:
            self.addReadToQueue(regAddressList)

    def handleReadResponse(self, regAddr, regValue):
        """This should be called from the device-specific message reception API
        after the message has been parsed into a register address and value."""
        self.registerMap.setRegisterValue(regAddr, regValue)
        self.handleReadResponseUI(regAddr, regValue)

    def handleReadResponseUI(self, regAddr, regValue):
        """Parse a message into member name, value pairs and call parent callbacks
        if they are registered."""
        #self.distributeToSetters(regAddr, regValue)
        memberDict = self.registerMap.getRegisterValueAsMembers(regAddr)
        if memberDict == None:
            return
        for memberName, value in memberDict.items():
            setter = self.getSetter(regAddr, memberName)
            if setter != None:
                setter(value)

    def initUI(self):
        self.setters = {} # Nested dicts
        self.getters = {} # Nested dicts
        # For each register in the map,
        for regAddr in self.registerMap:
            register = self.registerMap.getRegisterByAddress(regAddr)
            registerName = register.name()
            self.setters[regAddr] = {}
            self.getters[regAddr] = {}
            # For each member in the register
            for member in register.getMembers():
                memberName = register.getName(member)
                setter = self.getParentSetter(regAddr, registerName, memberName)
                if setter != None:
                    self.setters[regAddr][memberName] = setter
                getter = self.getParentGetter(regAddr, registerName, memberName)
                if getter != None:
                    self.getters[regAddr][memberName] = getter

    def registerGetter(self, registerAddrname, memberName, callback):
        """Manually register a getter callback function (rather than doing it with
        auto getter/setter naming protocol.
        'registerAddrname' could be an address (int) or a name (str)."""
        if isinstance(registerAddrname, str):
            regAddr = self.registerMap.getRegisterAddressByName(registerAddrname)
            if regAddr == None:
                return False
        elif isinstance(registerAddrname, int):
            regAddr = registerAddrname
        else:
            return False
        self.getters[regAddr][memberName] = callback
        return True

    def registerSetter(self, registerAddrname, memberName, callback):
        """Manually register a setter callback function (rather than doing it with
        auto getter/setter naming protocol.
        'registerAddrname' could be an address (int) or a name (str)."""
        if isinstance(registerAddrname, str):
            regAddr = self.registerMap.getRegisterAddressByName(registerAddrname)
            if regAddr == None:
                return False
        elif isinstance(registerAddrname, int):
            regAddr = registerAddrname
        else:
            return False
        self.setters[regAddr][memberName] = callback
        return True

    def getParentSetter(self, registerAddress, registerName, memberName):
        """Search for an return if found a setter method for the given member of name
        'memberName' in register at address 'registerAddress' (with name 'registerName')
        according to the auto getter/setter naming protocol."""
        # TODO enable a greater variety of names and CENTRALIZE the naming rule
        if self.parent == None:
            return None
        targetNames = ("set" + registerName + memberName,
                       "setRegister" + str(registerAddress) + memberName)
        for targetName in targetNames:
            target = getattr(self.parent, targetName, None)
            if target != None:
                # TODO - ensure it's callable and can take one arg?
                return target
        return None

    def getParentGetter(self, registerAddress, registerName, memberName):
        """Search for an return if found a setter method for the given member of name
        'memberName' in register at address 'registerAddress' (with name 'registerName')
        according to the auto getter/setter naming protocol."""
        # TODO enable a greater variety of names and CENTRALIZE the naming rule
        if self.parent == None:
            return None
        targetNames = ("get" + registerName + memberName,
                       "getRegister" + str(registerAddress) + memberName)
        for targetName in targetNames:
            target = getattr(self.parent, targetName, None)
            if target != None:
                # TODO - ensure it's callable?
                return target
        return None

    def setChangesFromUI(self):
        """This should be called periodically in a user interface to update the value
        of the register members with getter functions (pre-registered with initUI() or
        with registerGetter())"""
        regDoubleDict = self.getUIValues()
        for regAddr, regDict in regDoubleDict.items():
            #self.registerMap.setRegisterChangeDict(regAddr, regDict)
            self.registerMap.setRegisterIfChanged(regAddr, regDict)

    def getUIValues(self):
        regDict = {} # Nested dicts
        if self.parent == None:
            return regDict
        for regAddr in self.registerMap:
            #register = self.registerMap.getRegisterByAddress(regAddr)
            regDict[regAddr] = {}
            for memberName, getter in self.getters[regAddr].items():
                if getter != None:
                    val = getter()  # Just call the getter for now
                    if val != None:
                        regDict[regAddr][memberName] = val
        return regDict

    def sendChangesToDevice(self, openLoop = False):
        changeDict = self.registerMap.getChangedRegisters()
        for addr, newVal in changeDict.items():
            self.addWriteToQueue(addr, newVal)
        if openLoop:
            self.registerMap.commitChanges()
        else:
            self.requestNewRegisterValues([x for x in changeDict.keys()])

    def getGetter(self, regAddr, memberName):
        """Get a pre-registered getter function by register address 'regAddr' and
        member name 'memberName'."""
        regGetters = self.getters.get(regAddr, None)
        if regGetters != None:
            return regGetters.get(memberName, None)
        return None

    def getSetter(self, regAddr, memberName):
        """Get a pre-registered setter function by register address 'regAddr' and
        member name 'memberName'."""
        regSetters = self.setters.get(regAddr, None)
        if regSetters != None:
            return regSetters.get(memberName, None)
        return None

    def isReady(self):
        return self._ready

    #def distributeToSetters(self, regAddr, regValue):
    #    """A new value 'regValue' for register at address 'regAddr' has been received.
    #    Parse this value into member value and pass them to the UI setters."""

    def printGetters(self):
        print("Getter functions:")
        for regAddr, regDict in self.getters.items():
            for memberName, cb in regDict.items():
                print("Reg {} Member {}".format(regAddr, memberName))
        print()

    def printSetters(self):
        print("Setter functions:")
        for regAddr, regDict in self.setters.items():
            for memberName, cb in regDict.items():
                print("Reg {} Member {}".format(regAddr, memberName))
        print()

class RegisterMap():
    """Use with a memory-mapped peripheral for register access.
    To update a device after changes from the user, use:
        changeDict = self.getChangedRegisters()
        for addr, newVal in changeDict.items():
            device.writeRegister(addr, newVal)
        self.clearChanges()
    
    If you are not doing the writing (above) on a tight loop, you can
    skip 'self.clearChanges()' and allow a subsequent read to confirm
    that the value has been updated.
    WARNING! This is tricky with registers that are not R/W in nature."""
    def __init__(self, registerList):
        self.regDict = {}
        self.registerWidth = 0
        print("RegisterMap got a list of {} registers".format(len(registerList)))
        for register in registerList:
            # Make a dict of addr : register object pairs
            if not hasattr(register, 'addr'):
                print("No 'addr' method")
                continue
            addr = register.addr()
            size = register.size()
            self.registerWidth = max(self.registerWidth, size)
            if addr in self.regDict.keys():
                existingRegister = self.regDict.get(addr)
                existingRegisterName = existingRegister.name()
                thisRegisterName = register.name()
                print("WARNING! Overwriting register {} at addres {} with {}!".format(
                    existingRegisterName, addr, thisRegisterName))
            self.regDict[addr] = register
        print("Parsed {} registers".format(len(self.regDict)))

    def getWidth(self):
        return self.registerWidth

    def __len__(self):
        return len(self.regDict)

    def __iter__(self):
        return iter(self.regDict)

    def __next__(self):
        return next(self.regDict)

    def getRegisters(self):
        return self.regDict.items()

    def getRegisterByAddress(self, addr):
        return self.regDict.get(addr, None)

    def getRegisterAddressByName(self, regName):
        for addr, register in self.regDict.items():
            if regName == register.name():
                return addr
        return None

    def getRegValueDict(self):
        valDict = {}
        for addr, register in self.regDict.items():
            value = register.value()
            valDict[addr] = value
        return valDict

    def getChangedRegisters(self, autoClear = False):
        valDict = {}
        for addr, register in self.regDict.items():
            if register.isChanged():
                nextVal = register.nextValue()
                valDict[addr] = nextVal
                if autoClear:
                    register.resetChanges()
        return valDict

    def clearChanges(self):
        for addr, register in self.regDict.items():
            register.resetChanges()
        return

    def commitChanges(self):
        for addr, register in self.regDict.items():
            register.commitChanges()
        return

    def __str__(self):
        s = []
        for addr, register in self.regDict.items():
            s.append(str(register))
        return '\n'.join(s)

    def setRegisterValue(self, regAddr, regValue):
        """Immediately set the value of the local copy of register at address 'regAddr'
        to value 'regValue'. This function should be used when a read response message
        has arrived from the device, NOT when the user wants to make a register change
        (use self.setRegisterChange() for that)."""
        register = self.regDict.get(regAddr, None)
        if register == None:
            print("setRegisterChange() Unknown register referenced: {}".format(regAddr))
            return
        register.set(regValue)

    def setRegisterChangeDict(self, regAddr, regDict):
        """Post changes from the members of the local copy of register at address 'regAddr'
        with {memberName: value} pairs in 'regDict'. This function should be used when
        the value of individual members within registers have changed and the changes are
        posted to the register to eventually update the device."""
        register = self.regDict.get(regAddr, None)
        if register == None:
            print("setRegisterChangeDict() Unknown register referenced: {}".format(regAddr))
            return
        register.setChangeDict(regDict)

    def setRegisterIfChanged(self, regAddr, regDict):
        """Set the change dict for register at 'regAddr' if the resulting value is different
        than the previously stored value."""
        register = self.regDict.get(regAddr, None)
        if register == None:
            print("setRegisterIfChanged() Unknown register referenced: {}".format(regAddr))
            return
        register.setChangeDictIfChanged(regDict)

    def setRegisterChange(self, regAddr, newRegisterValue):
        """If a whole register value has been changed (i.e. by the user), the change can
        be set in the register by address via this function.  The change will be stored
        for later use by a device updater function with self.getChangedRegisters()"""
        register = self.regDict.get(regAddr, None)
        if register == None:
            print("setRegisterChange() Unknown register referenced: {}".format(regAddr))
            return
        register.setChange(newRegisterValue)

    def setRegisterMemberChange(self, regAddr, memberName, newMemberValue):
        """This function can be used to post a change to a single member (by name 'memberName')
        inside register at address 'regAddr'.  The change will be stored for later use
        by a device updater function with self.getChangedRegisters()"""
        register = self.regDict.get(regAddr, None)
        if register == None:
            print("setRegisterMemberChange() Unknown register referenced: {}".format(regAddr))
            return
        register.setChangeByName(memberName, newMemberValue)

    def getRegisterValueAsMembers(self, regAddr):
        """Return a dict of {memberName : memberValue} pairs from register at address 'regAddr'."""
        register = self.regDict.get(regAddr, None)
        if register == None:
            print("getRegisterValueAsMembers() Unknown register referenced: {}".format(regAddr))
            return None
        members = register.getMembers()
        memberDict = {}
        for member in members:
            name = register.getName(member)
            value = register.getValue(member)
            memberDict[name] = value
        return memberDict

class Register():
    """Pythonic representation of an N-bit register which contains
    various data types of differing widths, offsets, and permissions.
    The members of the struct are stored in order in self.members
    and should be accessed by either self.getMembers() to get the
    full list or self.getMemberByName(nameString) to get a member
    object associated with the given nameString.

    For a peripheral whose interface is based on a collection of 
    memory-mapped registers, the flow should be the following:
        If user makes change to member in register, use:
            Register.setChangeByName(name, newValue)
        On a periodic (i.e. main) loop, look for changes to the
        register with:
            Register.isChanged()
        If a change has occurred, get the intended next value of
        the register (incorporating the changes) with:
            val = Register.nextValue()
        Then send the new register value to the peripheral with
        the application-specific register write function.
            addr = Register.addr()
            devWriteReg(addr, val)
        Once a change has been confirmed (successful write), you
        can use the following to set the register as up-to-date:
            Register.resetChanges()
        Or you can wait until the next register value is received
        with Register.set(), Register.setValue(), or
        Register.setMemberValueByName().  The value is checked against
        the change dict.  If the values are equal, the entry is
        removed from the change dict.

    The member objects themselves are simple dicts but to access
    their attributes, you should use the class APIs:
        self.getName(member)
        self.getWidth(member)
        self.getOffset(member)
    """
    _RESERVED_PREFIXES = ("RESERVED", "_")
    _sNAME = "name"
    _sWIDTH = "width"
    _sOFFSET = "offset"
    _sPERMISSIONS = "permissions"
    _sVALUE = "value"
    _sDESC = "desc"

    _bmREAD = 1
    _bmWRITE = 2
    _aPERMISSIONS = {
        "r" : _bmREAD,
        "w" : _bmWRITE
        }
    def __init__(self, name, addr, size, memberList, permissionString = None):
        self._name = name
        self._addr = _int(addr)
        self._size = _int(size)
        self._32bitmask = True
        self._readMemberList = memberList
        self.permissions = self._parsePermissionString(permissionString)
        self._readable = self._permissionsIsRead(self.permissions)
        self._writeable = self._permissionsIsWrite(self.permissions)
        # Each member will be a dict of attributes 'name', 'size', 'order', and 'offset'
        # Order and offset are sort of redundant, but it's nice to have both pre-calculated
        self.members = []
        self.changeDict = {}
        self._lock = False
        for member in self._readMemberList:
            name = member.get(self._sNAME, None)
            desc = member.get(self._sDESC, None)
            offset = member.get(self._sOFFSET, None)
            width = member.get(self._sWIDTH, None)
            rpermissions = member.get(self._sPERMISSIONS, None)
            if rpermissions == None:     # Inherit from register permissions if not set individually
                rpermissions = permissionString
            rpermissions = self._parsePermissionString(rpermissions)
            value = member.get(self._sVALUE, None)
            self._addMember(name, offset, width, permissions = rpermissions, value = value, description = desc)
        # Ensure the members list is sorted by the order in which they are read - this should be redundant but safe
        #print("Register {} has {} members".format(self._name, len(self.members)))
        self.members.sort(key = lambda x: x[self._sOFFSET])
        self.checkValidity()
        self.reserveBits()
        self.sortMembers()
        self._lock = True

    @classmethod
    def _parsePermissionString(cls, pString):
        permissions = 0
        if not hasattr(pString, "__len__"):
            return pString
        for c in pString:
            p = cls._aPERMISSIONS.get(c.lower(), None)
            if p != None:
                permissions |= int(p)
        return permissions

    @classmethod
    def _permissionsIsRead(cls, permissions):
        if permissions & cls._bmREAD:
            return True
        return False

    @classmethod
    def _permissionsIsWrite(cls, permissions):
        if permissions & cls._bmWRITE:
            return True
        return False

    @classmethod
    def _permissionsIsReadWrite(cls, permissions):
        bm = cls._bmWRITE | cls._bmREAD
        if (permissions & bm) == bm:
            return True
        return False

    def checkValidity(self):
        """Check for valid register description including the following potential errors:
        1. Bit fields that overlap or reference the same bit for different members.
        2. Bits that extend beyond the length of the containing register.
        Returns True if neither of the above occur; returns False otherwise."""
        # Logically OR all the masks, then count the number of ones in the resulting mask
        # This should be exactly the sum of member lengths
        bits = 0
        bm = 0
        for member in self.members:
            bm |= self.getMask(member)
            bits += self.getWidth(member)
        if bm > ((1 << self._size) - 1):
            print("Invalid register definition {}: Bits are defined beyond the size of the register!".format(self._name))
            return False
        bmOnes = self._binOnes(bm, self._size)
        if bmOnes != bits:
            print("Invalid register definition {}: potentially overlapping bits!".format(self._name))
            return False
        return True

    def reserveBits(self):
        inReserved = False
        rstart = 0
        nBit = 0
        for nbit in range(self._size):
            nBit = nbit
            # If nbit is in use
            if self._isBitUsed(nbit):
                if inReserved:
                    # If inReserved, button up the reserved member
                    self._addReservedMember(rstart, nbit)
                    inReserved = False
            else:
                if not inReserved:
                    rstart = nbit
                    inReserved = True
        if inReserved:
            self._addReservedMember(rstart, nBit+1)
        return

    def sortMembers(self):
        self.members.sort(key = lambda x : x[self._sOFFSET])
        return

    def _isBitUsed(self, nBit):
        for member in self.getMembers():
            bm = self.getMask(member)
            name = self.getName(member)
            if bm & (1 << nBit):
                return True
        return False

    def _addReservedMember(self, nBitStart, nBitEnd):
        self.members.append(
            {self._sNAME : self._RESERVED_PREFIXES[0],
            self._sOFFSET : nBitStart,
            self._sWIDTH : nBitEnd - nBitStart,
            self._sPERMISSIONS : 0,
            self._sVALUE : 0,
            self._sDESC : ""}
            )

    @staticmethod
    def _binOnes(n, nbits = 32):
        """Return the number of set bits (ones) in number 'n'"""
        x = 0
        for nbit in range(nbits):
            if n & (1 << nbit):
                x += 1
        return x

    def __len__(self):
        return self._size

    def _addMember(self, name, offset, width, permissions = None, value = 0, description = None):
        if self._lock:
            # Prevent adding members after the class has been locked
            return
        if width == None:
            width = 1   # default to 1 bit assumed width
        else:
            width = _int(width)
        if offset == None:
            offset = 0  # default to offset of 0
        else:
            offset = _int(offset)
        if name == None:
            name = "R{:04x}".format(offset)     # Default name is e.g. "R000F" for register 15
        else:
            name = str(name)    # Input sanitization
        value = _int(value)
        if value == None:
            value = 0
        #permissions = self._parsePermissionString(permissionString)
        # If any member is readable, the register is readable
        isReadable = self._permissionsIsRead(permissions)
        isWriteable = self._permissionsIsWrite(permissions)
        if isReadable:
            self._readable = True
        if isWriteable:
            self._writeable = True
        self.members.append(
            {self._sNAME : name,
            self._sOFFSET : offset,
            self._sWIDTH : width,
            self._sPERMISSIONS : permissions,
            self._sVALUE : value,
            self._sDESC : description}
            )
        return

    def _isReserved(self, name):
        for prefix in self._RESERVED_PREFIXES:
            if name.startswith(prefix):
                return True
        return False

    def _bm(self, member):
        """Return a bitmask for the given member in the register."""
        offset = self.getOffset(member)
        width = self.getWidth(member)
        if (offset == None) or (width == None):
            return None
        return ((1 << width) - 1) << offset

    def _bmString(self, member):
        bm = self._bm(member)
        nhalfwords = (self._size // 4) + ((self._size % 4) + 3) // 4
        fs = "{:0" + str(nhalfwords) + "x}"
        return fs.format(bm)

    def __setitem__(self, key, value):
        """Redirect register[key] = value to char.key = value"""
        self.__setattr__(key, value)

    def __repr__(self):
        members = self.getMembers() # BUTTERFLY
        #members = self.getAllMembers()
        s = ["Register {}".format(self.name())]
        for member in members:
            width = self.getWidth(member)
            offset = self.getOffset(member)
            if width == 1:
                bitString = "[{}]".format(offset)
            else:
                bitString = "[{}:{}]".format(offset + width - 1, offset)
            s.append("  {} : {}".format(bitString, self.getName(member)))
        return "\n".join(s)

    def __str__(self):
        return self.__repr__()

    def isReserved(self, member):
        name = self.getName(member)
        return self._isReserved(name)

    def isReadable(self):
        return self._readable

    def isWriteable(self):
        return self._writeable

    def printAll(self):
        members = self.getAllMembers()
        s = ["Register {}".format(self.name())]
        for member in members:
            width = self.getWidth(member)
            offset = self.getOffset(member)
            if width == 1:
                bitString = "[{}]".format(offset)
            else:
                bitString = "[{}:{}]".format(offset + width - 1, offset)
            s.append("  {} : {}".format(bitString, self.getName(member)))
        print("\n".join(s))
        return

    def getMembers(self):
        members = []
        for member in self.members:
            name = self.getName(member)
            if not self._isReserved(name):
                members.append(member)
        return members

    def getAllMembers(self):
        members = self.members.copy()
        return members

    def getAllMembersBigEndian(self):
        members = self.members.copy()
        members.reverse()
        return members

    def getMemberByName(self, name):
        for member in self.members:
            if name == member.get(self._sNAME, None):
                return member
        return None

    def getName(self, member):
        return member.get(self._sNAME, None)

    def getWidthByName(self, name):
        member = self.getMemberByName(name)
        if member != None:
            return member.get(self._sWIDTH, None)
        return None

    def getWidth(self, member):
        return member.get(self._sWIDTH, None)

    def getOffsetByName(self, name):
        member = self.getMemberByName(name)
        if member != None:
            return member.get(self._sOFFSET, None)
        return None

    def getOffset(self, member):
        return member.get(self._sOFFSET, None)

    def getValueByName(self, name):
        member = self.getMemberByName(name)
        if member != None:
            return member.get(self._sVALUE, None)
        return None

    def getValue(self, member):
        return member.get(self._sVALUE, None)

    def getPermissionsByName(self, name):
        member = self.getMemberByName(name)
        if member != None:
            return member.get(self._sPERMISSIONS, None)
        return None

    def getPermissions(self, member):
        return member.get(self._sPERMISSIONS, None)

    def isMemberReadable(self, member):
        permissions = self.getPermissions(member)
        return self._permissionsIsRead(permissions)

    def isMemberWriteable(self, member):
        permissions = self.getPermissions(member)
        return self._permissionsIsWrite(permissions)

    def getDescriptionByName(self, name):
        member = self.getMemberByName(name)
        if member != None:
            return member.get(self._sDESC, None)
        return None

    def getDescription(self, member):
        return member.get(self._sDESC, None)

    def setMemberValue(self, member, value):
        name = self.getName(member)
        if name != None:
            # This member is in fact one of ours
            self.setMemberValueByName(name, value)

    def setMemberValueByName(self, name, value):
        """Set the value of a member by name (string)."""
        # We have to do this carefully because we need to modify the stored dict, not a shallow copy
        for n in range(len(self.members)):
            memberName = self.getName(self.members[n])
            if name == memberName:
                self.members[n][self._sVALUE] = value
        # Check and clear the change dict if up-to-date
        member = self.getMemberByName(name)
        changeVal = self.changeDict.get(memberName, None)
        if changeVal != None:
            if value == changeVal:
                # If the values are equal, remove the entry from the change dict
                self.changeDict.pop(member)

    def getMask(self, member):
        return self._bm(member)

    def getMaskByName(self, name):
        member = self.getMemberByName(name)
        if member != None:
            return self._bm(member)
        return None

    def get(self, s, fallback = None):
        if s == self._sOFFSET:
            return 0
        elif s == self._sWIDTH:
            return self.__len__()
        elif s == self._sNAME:
            return self._name
        elif s == self._sVALUE:
            return 0

    def isMember(self, name):
        for member in self.getMembers():
            memberName = self.getName(member)
            if name == memberName:
                return True
        return False

    def set(self, regValue):
        """Receive a new register value (most likely from the device itself) and parse
        into member values."""
        for member in self.getMembers():
            mask = self.getMask(member)
            offset = self.getOffset(member)
            newval = (regValue & mask) >> offset
            self.setMemberValue(member, newval)
        self.resetChanges()

    def setChange(self, regValue):
        """Set a new register value as a change (to be written to the device) and parse
        into the change dict."""
        for member in self.getMembers():
            name = self.getName(member)
            mask = self.getMask(member)
            offset = self.getOffset(member)
            newval = (regValue & mask) >> offset
            self.changeDict[name] = newval

    def setChangeDict(self, regDict):
        for memberName, value in regDict.items():
            member = self.getMemberByName(memberName)
            if member != None:
                self.changeDict[memberName] = value

    def setChangeDictIfChanged(self, regDict):
        currentValue = self.value()
        newValue = 0
        regAddr = self.addr()
        for memberName, value in regDict.items():
            member = self.getMemberByName(memberName)
            mask = self.getMask(member)
            offset = self.getOffset(member)
            newValue |= (value << offset) & mask
        if currentValue != newValue:
            print("Setting change value for register {} to value {}".format(regAddr, newValue))
            self.setChangeDict(regDict)
        else:
            #print("Register {} up to date".format(regAddr))
            pass

    def setByMembers(self, valDict):
        """Set register member values by a dict of {name : value} pairs."""
        for name, val in valDict.items():
            if self.isMember(name):
                self.setMemberValueByName(name, val)

    def setChangeByName(self, name, newValue):
        members = self.getMembers()
        member = members.get(name, None)
        if member != None:
            width = self.getWidth(member)
            newValue = min(_int(newValue), (1 << width) - 1)    # Ensure newValue fits in the width
            self.changeDict[member] = _int(newValue)

    def isChanged(self):
        if len(self.changeDict) > 0:
            return True
        return False

    def resetChanges(self):
        """Use this once a register value has been updated by a read from the device; it will
        forget all desired user-changes (the user interface must reflect the actual value read
        from the device to prevent confusion)."""
        self.changeDict = {}

    def commitChanges(self):
        """Use this instead of 'resetChanges' if you are working 'open loop' (i.e. assuming all
        writes take effect, not waiting for a subsequent read to confirm)."""
        self.set(self.nextValue())
        self.resetChanges()

    def nextValue(self):
        """Get the next value of the register (reflecting unsent member value changes)"""
        regVal = 0
        for member in self.members: # Remember to get ALL the members, even the reserved ones
            mask = self.getMask(member)
            name = self.getName(member)
            val = self.changeDict.get(name, None) # If the member is in the change dict, use that value
            if val == None:
                val = self.getValue(member)         # Otherwise use the last value
            offset = self.getOffset(member)
            regVal |= (val << offset) & mask
        return regVal

    def value(self):
        """Get the current value of the register as a whole."""
        regVal = 0
        for member in self.members: # Remember to get ALL the members, even the reserved ones
            mask = self.getMask(member)
            val = self.getValue(member)
            offset = self.getOffset(member)
            regVal |= (val << offset) & mask
        return regVal

    def addr(self):
        return self._addr

    def size(self):
        return self._size

    def name(self):
        return self._name

class JSONRegisterMapReader():
    _sSIZE = "size"
    _sADDR = "addr"
    _sPERMISSIONS = "permissions"
    _sMAP = "map"
    def __init__(self, jsonFilename):
        self.filename = jsonFilename
        self.registers = []
        self._locked = False
        self.jsondict = {}
        self.load()
        self.interpret()

    def load(self):
        if self._locked:
            return
        if self.filename == None:
            print("No filename provided")
            return False
        if not os.path.exists(self.filename):
            print("File {} does not seem to exist.".format(self.filename))
            return False
        with open(self.filename, 'r') as fd:
            self._jsonhack = JSONHack(self.filename)
            self.jsondict = self._jsonhack.load()
            print("Loaded {}".format(self.filename))

    def interpret(self):
        if self._locked:
            return
        for key, val in self.jsondict.items():
            self.registers.append(self.parseRegister(key, val))
        print("Found {} registers.".format(len(self.registers)))
        self._locked = True

    def parseRegister(self, regName, valdict):
        name = regName
        size = 0
        addr = 0
        permissions = 0
        rmap = []
        for key, val in valdict.items():
            key = key.lower()
            if key == self._sSIZE:
                size = val
            elif key == self._sADDR:
                addr = val
            elif key == self._sPERMISSIONS:
                permissions = val
            elif key == self._sMAP:
                rmap = val
        return self.makeRegister(name, addr, size, permissions, rmap)

    def makeRegister(self, name, addr, size, permissions, rmap):
        #print("Making register with name = {}, addr = {}, size = {}, permissions = {}".format(name, addr, size, permissions))
        return Register(name, addr, size, memberList = rmap, permissionString = permissions)

    def getRegisters(self):
        return self.registers

class JSONHack():
    """A hack to allow an arbitrary number of comment lines at the top of an otherwise JSON-compliant file.
    The comments are ignored before the remainder of the file is passed to the JSON interpreter."""
    _commentChar = "#"
    def __init__(self, filename = None):
        if filename == None:
            filename = "default.json"
        self.filename = filename
        if not os.path.exists(self.filename):
            print("File {} doesn't appear to exist".format(self.filename))

    def load(self):
        if not os.path.exists(self.filename):
            print("Cannot load. File {} doesn't appear to exist".format(self.filename))
            return {}
        s = []
        with open(self.filename, 'r') as fd:
            line = True
            while line:
                #line = fd.readline().strip("\n") # severely undercounts lines...
                line = fd.readline()
                if line.strip().startswith(self._commentChar):
                    # Skip any lines that begin with the comment char
                    s.append("") # Append a blank line to ensure accurate line count on error
                    continue
                if len(line.strip('\n').replace('\r', '')) > 0:
                    #print("len({}) = {}".format(line, len(line)))
                    s.append(line.strip('\n'))
                else:
                    s.append("") # Append a blank line to ensure accurate line count on error
        try:
            o = json.loads('\n'.join(s))
        except json.decoder.JSONDecodeError as jerr:
            # This line number is not correct. Why?
            print("JSON Decoder Error:\n{}".format(jerr))
            o = {}
        return o

def _int(s):
    """Do a better job at int() by allowing hex and binary strings."""
    # Pass ints right through
    if isinstance(s, int):
        return s
    if not hasattr(s, '__len__'):
        return s
    base = 10
    if 'x' in s:
        base = 16
    elif 'b' in s:
        base = 2
    try:
        n = int(s, base)
    except:
        return None
    return n

def readAndParseMemoryMap(argv):
    USAGE = "python3 {} memoryMapFileName".format(argv[0])
    if len(argv) < 2:
        print(USAGE)
        return False
    filename = argv[1]
    mmp = MMPeriph(filename, protocols.Protocol, phys.PHY)
    mmp.registerMap.printAll()
    #for regaddr in mmp.registerMap:
    #    print("register {}".format(regaddr))
    return True

if __name__ == "__main__":
    import sys
    readAndParseMemoryMap(sys.argv)

