#! /usr/bin/python3

from PyQt5 import QtCore as qtc
from PyQt5 import QtWidgets as qtw
from PyQt5 import QtGui as qtg

import mmp

# PyQt5 / PySide2 compatibility def
qtc.Signal = qtc.pyqtSignal

# TODO:
#   I am currently only getting updates from one register at a time.
#       This could be the fault of the poor IPCTRL firmware clobbering messages.

# Next steps:
#   Add grid lines (boxes around each gui widget)
#   Create an "update" button
#   Figure out how to have a "global" keyboard binding (works regardless of field focus)
#   Try with an actual device

MAIN_TIMER_PERIOD = 0 # ms
UPDATE_TIMER_PERIOD = 100 # ms

class QtGUIRegMap(qtw.QMainWindow):
    def __init__(self, mmPeriph, mainTimerPeriod = MAIN_TIMER_PERIOD,
                 updateTimerPeriod = UPDATE_TIMER_PERIOD, parent = None):
        super().__init__(parent)
        self._mainTimerPeriod = mainTimerPeriod
        self._updateTimerPeriod = updateTimerPeriod
        self.mmPeriph = mmPeriph
        self.mmPeriph.setParent(self)
        rmap = self.mmPeriph.registerMap
        #self.mmPeriph.printGetters()
        #self.mmPeriph.printSetters()
        self._widgets = {}  # A permanent reference to widgets
        self.initUpdateRequests()
        self.initUI(rmap)
        self.initTimers()
        self.show()

    def initUI(self, registerMap):
        mainPanel = qtw.QWidget()
        gridLayout = self.buildFromRegMap(registerMap)
        self.bindKeyboard()
        mainPanel.setLayout(gridLayout)
        self.setCentralWidget(mainPanel)

    def bindKeyboard(self):
        shortcut = qtw.QShortcut(qtg.QKeySequence("u"), self)         # 'u' key
        shortcut.activated.connect(self.onKeyboardUpdateOpenLoop)
        shortcut = qtw.QShortcut(qtg.QKeySequence.MoveToPreviousLine, self)         # Up key
        shortcut.activated.connect(self.onKeyboardUpdateClosedLoop)

    def initTimers(self):
        self.timerMain = qtc.QTimer()
        self.timerMain.timeout.connect(self.onTimerMain)
        self.timerMain.start(self._mainTimerPeriod)
        self.timerUpdate = qtc.QTimer()
        self.timerUpdate.timeout.connect(self.onTimerUpdate)
        self.timerUpdate.start(self._updateTimerPeriod)

    def onTimerMain(self):
        self.mmPeriph.processQueue()
        self.mmPeriph.readAndParseFromDevice()

    def onTimerUpdate(self):
        self.processUpdateRequests()

    def initUpdateRequests(self):
        self._updateRequestList = []

    def addUpdateRequest(self, regAddr):
        """Add an update request for a particular register address."""
        # Search for the address in the list
        for lRegAddr in self._updateRequestList:
            if regAddr == lRegAddr:
                return  # If the address is already in the list, early return
        # If we get here, we didn't find it in the list. Append it.
        self._updateRequestList.append(regAddr)

    def removeUpdateRequest(self, regAddr):
        """Remove an update request for a particular register address."""
        # Search for the request in the list
        for n in range(len(self._updateRequestList)):
            lRegAddr = self._updateRequestList[n]
            if regAddr == lRegAddr:
                del self._updateRequestList[n] # If the request is found in the list, delete it
                return # and early return

    def onKeyboardUpdateOpenLoop(self):
        print("Open Loop")
        self.mmPeriph.setChangesFromUI()
        self.mmPeriph.sendChangesToDevice(openLoop = True)

    def onKeyboardUpdateClosedLoop(self):
        print("Closed Loop")
        self.mmPeriph.setChangesFromUI()
        self.mmPeriph.sendChangesToDevice(openLoop = False)

    def buildFromRegMap(self, registerMap):
        gridLayout = qtw.QGridLayout()
        gridWidth = registerMap.getWidth() + 3 # addr + checkbox + (contents) + label
        row = 0
        for addr, register in registerMap.getRegisters():
            self.addRegister(gridLayout, row, register, gridWidth)
            row += 1
        return gridLayout

    def addRegister(self, gridLayout, row, register, gridWidth):
        addr = register.addr()
        self._widgets[addr] = []
        labelAddr = qtw.QLabel(hex(addr))
        gridLayout.addWidget(labelAddr, row, 0)       # First add the label
        if register.isReadable():
            checkBox = QtGUIRegisterCheckBox(addr)
            gridLayout.addWidget(checkBox, row, 1)    # Then add the check box if readable
            checkBox.toggled.connect(self.onRegisterChecked)
        for member in register.getAllMembersBigEndian():
            width = register.getWidth(member)
            offset = register.getOffset(member)
            name = register.getName(member)
            permissions = register.getPermissions(member)
            value = register.getValue(member)
            description = register.getDescription(member)
            if register.isReserved(member):
                widget = QtGUIWidgetReserved(width, offset)
            else:
                if width == 1:
                    widget = QtGUIWidgetBit(addr, name, width, offset, permissions, value, description = description)
                else:
                    widget = QtGUIWidgetInt(addr, name, width, offset, permissions, value, description = description)
                # Only keep a reference to non-reserved widgets
                self._widgets[addr].append(widget)
                # Connect to widgets 'checked' signal for auto-updates  # CHANGE! Moving check boxes to register
                #widget.checked.connect(self.onRegisterChecked)
                if register.isMemberReadable(member):
                    # If readable, register a SETTER
                    self.mmPeriph.registerSetter(addr, name, widget.setValue)
                if register.isMemberWriteable(member):
                    # If writeable, register a GETTER
                    self.mmPeriph.registerGetter(addr, name, widget.getValue)
            column = gridWidth - (offset + width) - 1
            span = width
            gridLayout.addWidget(widget, row, column, 1, span)  # Row span = 0
        registerLabel = qtw.QLabel(register.name())
        gridLayout.addWidget(registerLabel, row, gridWidth - 1) # Row span = column span = 0

    def onRegisterChecked(self, info):
        regAddr, isChecked = info
        if isChecked:
            print("Reg {} is checked".format(regAddr))
            self.addUpdateRequest(regAddr)
        else:
            print("Reg {} is un-checked".format(regAddr))
            self.removeUpdateRequest(regAddr)

    def processUpdateRequests(self):
        for regAddr in self._updateRequestList:
            self.mmPeriph.addReadToQueue(regAddr)
        #self.collectUpdateRequests()   # Only use this if the 'onWidgetChecked' signal method doesn't work

    def isAddressInUpdateList(self, regAddr):
        if regAddr in self._updateRequestList:
            return True
        else:
            return False

    def collectUpdateRequests(self):
        """Iterate through the gui widgets and add any 'checked' items to the list of registers
        to update."""
        self.initUpdateRequests()
        for addr, widgetlist in self._widgets.items():
            for widget in widgetlist:
                if widget.isAutoUpdate():
                    self.addUpdateRequest(addr)
                    break

class QtGUIWidgetReserved(qtw.QWidget):
    _colorGray = "#AAAAAA"
    _bgColorGray = "#777777"
    def __init__(self, width, offset):
        super().__init__()
        if width == 1:
            bitString = "[{}]".format(offset)
        else:
            bitString = "[{}:{}]".format(offset + width - 1, offset)
        self.regAddr = None
        self.name = None
        label = qtw.QLabel("{} Reserved".format(bitString))
        #self.setStyleSheet("background-color: {}".format(self._bgColorGray))
        self.setStyleSheet("color: {}".format(self._colorGray))
        hbox = qtw.QHBoxLayout()
        hbox.setAlignment(qtc.Qt.AlignCenter)
        hbox.addWidget(label)
        self.setLayout(hbox)

    def isAutoUpdate(self):
        return False

    def isReserved(self):
        return True

class QtGUIRegisterCheckBox(qtw.QCheckBox):
    toggled = qtc.Signal(tuple)
    def __init__(self, regAddr):
        self.regAddr = regAddr
        super().__init__('')
        self.stateChanged.connect(self.onToggled)

    def onToggled(self):
        isChecked = self.isChecked()
        self.toggled.emit((self.regAddr, isChecked))

class QtGUIWidget(qtw.QWidget):
    checked = qtc.Signal(tuple)
    def __init__(self, regAddr, name, width, offset, permissions, value = None, parent = None, description = None):
        super().__init__(parent)
        self.parent = parent
        self.regAddr = regAddr
        self.name = name
        self.width = width
        self.offset = offset
        self.spanLabel = self._getSpanLabel(self.width, self.offset)
        if permissions != None:
            self.permissions = permissions
        else:
            self.permissions = 0
        self._readable = mmp.Register._permissionsIsRead(self.permissions)
        self._writeable = mmp.Register._permissionsIsWrite(self.permissions)
        if value == None:
            self.value = 0
        else:
            value = _int(value)
            if value == None:
                self.value = 0
            else:
                self.value = value
        if description == None:
            self.description = self.name
        else:
            self.description = description
            self.setToolTip(self.description)
        self.create()
        self.setValue(self.value)

    def onChecked(self):
        isChecked = self.checkBoxUpdate.isChecked()
        self.checked.emit((self.regAddr, isChecked))

    def getName(self):
        return self.name

    def getRegisterAddress(self):
        return self.regAddr

    def isReserved(self):
        return False

    @staticmethod
    def _getSpanLabel(width, offset):
        if width == 1:
            bitString = "[{}]".format(offset)
        else:
            bitString = "[{}:{}]".format(offset + width - 1, offset)
        return bitString

    def isAutoUpdate(self):
        if self._readable:
            return self.checkBoxUpdate.isChecked()
        else:
            return False

    def create(self):
        labelName = qtw.QLabel("{} {}".format(self.spanLabel, self.name))
        labelName.setAlignment(qtc.Qt.AlignCenter)
        self.valueWidget = self._makeValueWidget()
        hbox = qtw.QHBoxLayout()
        #if self._readable:
        #    self.checkBoxUpdate = qtw.QCheckBox("")
        #    hbox.addWidget(self.checkBoxUpdate)
        #    self.checkBoxUpdate.stateChanged.connect(self.onChecked)
        hbox.addWidget(self.valueWidget)
        hbox.setAlignment(qtc.Qt.AlignCenter)
        vbox = qtw.QVBoxLayout()
        vbox.addWidget(labelName)
        vbox.addLayout(hbox)
        vbox.setAlignment(qtc.Qt.AlignCenter)
        self.setLayout(vbox)

    def _makeValueWidget(self):
        le = qtw.QLineEdit()
        le.setAlignment(qtc.Qt.AlignCenter)
        if not self._writeable:
            le.setReadOnly(True)
        return le

    def getValue(self):
        return _int(self.valueWidget.text())

    def setValue(self, value):
        intvalue = _int(value)
        if intvalue != None:
            self.value = intvalue
            self.valueWidget.setText(hex(value))
        else:
            print("value {} yields None".format(value))

class QtGUIWidgetInt(QtGUIWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

class QtGUIWidgetBit(QtGUIWidget):
    def __init__(self, *args, **kwargs):
        width = kwargs.get('width', None)
        if width != None:
            kwargs['width'] = 1 # Force all 'bit' types to be width 1
        super().__init__(*args, **kwargs)

    def _makeValueWidget(self):
        if self._writeable:
            btn = qtw.QPushButton(str(self.value))
            btn.setFlat(True)
            btn.clicked.connect(self.onButton)
        else:
            btn = qtw.QLabel(str(self.value))
            btn.setAlignment(qtc.Qt.AlignCenter)
        btn.setFixedWidth(30)    # HACK ALERT!
        return btn

    def onButton(self):
        self.value = (self.value + 1) % 2
        self.valueWidget.setText(str(self.value))

    def getValue(self):
        return self.value

    def setValue(self, value):
        intvalue = _int(value)
        if intvalue != None:
            self.value = intvalue % 2
            self.valueWidget.setText(str(self.value))
        else:
            print("value {} yields None".format(value))

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

class TestBox(qtw.QMainWindow):
    def __init__(self, dut = None, **kwargs):
        super().__init__(None)
        if dut != None:
            self.dut = dut(**kwargs)
            self.setCentralWidget(self.dut)
            self.show()
        else:
            app.quit()

def testQtGUIWidget(argv):
    layout = 0
    if len(argv) > 1:
        layout = int(argv[1])
    app = qtw.QApplication(sys.argv)
    kwargs = {"label" : "Testing", "width" : 1, "offset" : 8, "permissions" : 0}
    window = TestBox(QtGUIWidgetBit, **kwargs)
    return app.exec_()

def gui(argv):
    USAGE = "python3 {} memoryMapFileName".format(argv[0])
    if len(argv) < 2:
        print(USAGE)
        return False
    filename = argv[1]
    mmPeriph = mmp.MMPeriph(filename)
    app = qtw.QApplication()
    window = QtGUIRegMap(mmPeriph)
    return app.exec_()

def makeGUI(mmPeriph, **kwargs):
    if not hasattr(mmPeriph, 'memoryMapFilename'):
        print("{} must be a valid object which inherits from class MMPeriph".format(mmPeriph))
        return
    filename = mmPeriph.memoryMapFilename
    if not mmPeriph.isReady():
        print("Exiting because mmPeriph.isReady() returned False")
        return
    app = qtw.QApplication([])
    window = QtGUIRegMap(mmPeriph)
    return app.exec_()

if __name__ == "__main__":
    import sys
    #testQtGUIWidget(sys.argv)
    gui(sys.argv)


