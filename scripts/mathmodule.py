#! /usr/bin/python3

"""A generic math module for GUIs which allows the user to define variables and compute expressions
dynamically."""

# Goals:
#   CHECK 1. Create dialog to view/define variables
#   CHECK 2. Create a GUI line of: Expression (editable) - Result (read only)
#   CHECK 3. Create GUI container with '+/-' buttons to add/remove expression lines like the above
#       3a. Limit vertical size of container with scroll bar
#   4. Allow results of expressions "above" to be referenced in expression? (I.e. {x} yields value of expression x)
#   5. Create safeties around 'eval' function

# Notes:
#   CHECK * Add "Ok" and "Cancel" buttons to VariableDialog. Caller will only update variableIndexDict on "Ok"
#   * Re-initialize VariableDialog with variableIndexDict
#   * Store/read variableIndexDict in INI file
#   * Adding lines should apply same stretch factors for all lines in layout
#   CHECK * Guard against naming the same variable more than once
#   * Owner of VariableDialog should call dlg.getVariableIndexDict() which is a find/replace dict for matching
#     string variable names to indices into dlg.options (which should be the same order/length as getters list).
#     Then caller can get variable values at eval time by getting values from getters[index]
#   CHECK * Get VariableDialog layout to shrink when lines removed

import PyQt5.QtCore as qtc
import PyQt5.QtGui as qtg
import PyQt5.QtWidgets as qtw
import re

#Signal = qtc.Signal    # pyside
Signal = qtc.pyqtSignal # PyQt5
 
class GUIMathModuleDialog(qtw.QDialog):
    _moduleLabel = "Math Module"
    def __init__(self, parent = None, labelGetterPairs = [], nameIndexPairs = [], expressions = []):
        super().__init__()
        self.setWindowTitle(self._moduleLabel)
        self._initialized = False
        self.parent = parent
        # labelGetterPairs is [(label, getterFunction), ...] in widget line order (for accessing via line index)
        self.labelGetterPairs = list(labelGetterPairs)
        # labelGetterDict is {label : getterFunction, ...} in no order (for accessing getter via label)
        self.labelGetterDict = {}
        self.expressions = list(expressions)
        self._labels = [x[0] for x in self.labelGetterPairs]
        self._getters = [x[1] for x in self.labelGetterPairs]
        self.nameIndexPairs = list(nameIndexPairs)
        for label, getter in self.labelGetterPairs:
            self.labelGetterDict[label] = getter
        self.create()

    def create(self):
        hbox = qtw.QHBoxLayout()
        self.variableWidget = VariableBox(self, self.nameIndexPairs, self._labels)
        self.variableWidget.signalClose.connect(self.onVariableWidgetButton)
        self.expressionWidget = ExpressionBox(self, self.expressions)
        hbox.addWidget(self.variableWidget)
        hbox.addWidget(self.expressionWidget)
        self.setLayout(hbox)
        self._initialized = True
        self.show()

    def _getNameIndexPairs(self):
        self.nameIndexPairs = self.variableWidget.getNameIndexPairs()

    def _updateGetters(self):
        self.labelGetterPairs = []
        for n in range(len(self.nameIndexPairs)):
            name, index = self.nameIndexPairs[n]
            if (index >= 0) and (index < len(self._getters)):
                print("name = {}, index = {}".format(name, index))
                self.labelGetterDict[name] = self._getters[index]
                self.labelGetterPairs.append((name, self._getters[index]))
        print("nameIndexPairs = {}".format(self.nameIndexPairs))

    def onVariableWidgetButton(self, choice):
        if choice == VariableBox._closeApply:
            # Update self._variableGetters
            self._getNameIndexPairs()
            self._updateGetters()

    def evaluate(self):
        exprList = self.expressionWidget.getExpressionList()
        for expr in exprList:
            self._evaluateExpression(expr)
        return

    def _evaluateExpression(self, expressionText):
        # 1. Get expression text from expression line 'lineNum'
        # TODO
        exprFiltered, errorChars = self._replaceVariables(expressionText)
        # 2. String-replace all variables in expression with numeric values
        #   2a. On syntax error: expressionLines[lineNum].highlightCharacters(nStart, nStop)
        # 3. Verify no alphabetic characters remain in filtered expression
        #   3a. If alphabetic characters remain, expressionLines[lineNum].highlightCharacters(nStart, nStop)
        # 4. result = eval(exprFiltered)
        # 5. expressionLines[lineNum].setResult(result)
        return

    def _replaceVariables(self, expressionText):
        """Should return (exprStringFiltered, errorChars) where errorChars = (start, end) indices of
        first invalid text encountered (does not match variable and is not numeric or puctual).
        If errorChars == None, the replacement was successful."""
        # TODO
        return "", None

    @staticmethod
    def _replaceVariable(s, varFrom, varTo):
        regexp = r"\b" + str(varFrom) + r"\b"
        #r = re.compile(regexp)
        print("Looking for {}".format(regexp))
        matches = re.finditer(regexp, s)
        l = []
        lastIndex = 0
        matched = False
        for match in matches:
            matched = True
            start, end = match.span()
            l.append(s[lastIndex:start])
            l.append(varTo)
            lastIndex = end
        if lastIndex < len(s) - 1:
            l.append(s[lastIndex:])
        if matched:
            return ''.join(l)
        return s

    @staticmethod
    def _isAllNumeric(s):
        """Returns (True, None) if string 's' contains no alphabetic characters or underlines
        else returns (False, (indexStart, indexStop)) indicating the first span an alphabetic character
        match."""
        r = re.compile("[a-zA-Z_]")
        s = r.search(s)
        if s:
            return False, s.span()
        return True, None

    def _getReplaceDict(self):
        """Returns a replacement dictionary object of variable names associated with their most-recent
        value (in string form)."""
        d = {}
        for label, getter in self.labelGetterDict.items():
            val = str(getter())
            d[label] = val
        return d

class GUIMathModule(qtw.QWidget):
    """UNUSED FOR NOW"""
    _moduleLabel = "Math Module"
    _nameIndexPairsDefault = (('x', 0),)
    def __init__(self, parent = None, labelGetterPairs = []):
        super().__init__(parent)
        self.parent = parent
        self._initialized = False
        self._getters = []
        self._variableGetters = {}
        self._dlgVariables = None
        self._labels = []
        self._nameIndexPairs = self._getNameIndexPairs()
        self._handleLabelGetters(labelGetterPairs)
        self.create()

    def _handleLabelGetters(self, labelGetterPairs):
        if not hasattr(labelGetterPairs, '__len__'):
            print("labelGetterPairs is not array-like")
            return
        for label, getter in labelGetterPairs:
            self._labels.append(label)
            self._getters.append(getter)

    def setNamesAndIndices(self, nameIndexPairs):
        if not hasattr(nameIndexPairs, '__len__'):
            print("nameIndexPairs is not array-like")
            return
        self._nameIndexPairs = nameIndexPairs
        # Close variable dialog if still open (needs to be refreshed)
        if self._dlgVariables != None:
            self._dlgVariables.close()

    def _getNameIndexPairs(self):
        if self._dlgVariables == None:
            return self._nameIndexPairsDefault
        else:
            self._nameIndexPairs = self._dlgVariables.getNameIndexPairs()

    def onDialogShow(self):
        if self._dlgVariables == None:
            self.createVariableDialog()

    def createVariableDialog(self):
        self._dlgVariables = VariableDialog(self, self._nameIndexPairs, self._labels)
        self._dlgVariables.signalClose.connect(self.onVariableDialogButton)
        self._dlgVariables.closeEvent = self.onVariableDialogClose
        self._dlgVariables.show()

    def onVariableDialogClose(self, evt):
        #print("evt = {}".format(evt))
        del self._dlgVariables
        self._dlgVariables = None

    def onVariableDialogButton(self, choice):
        print("choice = {}".format(choice))
        close = False
        fetch = False
        if choice == VariableDialog._closeOk:
            fetch = True
            close = True
        elif choice == VariableDialog._closeApply:
            fetch = True
        else: # VariableDialog._closeCancel
            close = True
        if fetch:
            # Update self._variableGetters
            self._getNameIndexPairs()
            self._updateGetters()
        if close:
            self._dlgVariables.close()

    def _updateGetters(self):
        for name, index in self._nameIndexPairs:
            if (index >= 0) and (index < len(self._getters)):
                print("name = {}, index = {}".format(name, index))
                self._variableGetters[name] = self._getters[index]
        print("_nameIndexPairs = {}".format(self._nameIndexPairs))

    def create(self):
        groupBox = qtw.QGroupBox(self._moduleLabel, self)
        hbox = qtw.QHBoxLayout()
        self.buttonDialog = qtw.QPushButton("Define Variables")
        self.buttonDialog.clicked.connect(self.onDialogShow)
        hbox.addWidget(self.buttonDialog)
        groupBox.setLayout(hbox)
        vbox = qtw.QVBoxLayout()
        vbox.addWidget(groupBox)
        self.setLayout(vbox)
        self._initialized = True

class ExpressionBox(qtw.QWidget):
    _addLabel = '+'
    def __init__(self, parent = None, expressionList = []):
        super().__init__(parent)
        self.parent = parent
        self.title = "Expressions"
        self.expressionList = list(expressionList)
        self.create()

    def create(self):
        groupBox = qtw.QGroupBox(self.title, self)
        self.layout = qtw.QVBoxLayout()
        self.lines = []
        self.names = []
        for n in range(len(self.expressionList)):
            expression = self.expressionList[n]
            line = ExpressionLine(n, expression)
            line.delete.connect(self.onLineDelete)
            line.edit.connect(self.onLineEdit)
            self.lines.append(line)
            self.layout.addWidget(line)
        self.buttonAdd = qtw.QPushButton(self._addLabel)
        self.buttonAdd.clicked.connect(self.onButtonAdd)
        self.layout.addWidget(self.buttonAdd)
        self.layout.setSizeConstraint(self.layout.SetFixedSize)
        groupBox.setLayout(self.layout)
        vbox = qtw.QVBoxLayout()
        vbox.addWidget(groupBox)
        self.setLayout(vbox)

    def getExpressionList(self):
        expressions = []
        for line in self.lines:
            expressions.append(line.getExpressionText())
        return expressions

    def evaluate(self):
        # TODO - evaluate all expression strings and update results for each line
        pass

    def onLineDelete(self, lineNum):
        self.removeLine(lineNum)

    def onLineEdit(self, lineNum):
        if lineNum > len(self.expressionList) - 1:
            print("Somehow edited a line beyond expression list")
            return
        self.expressionList[lineNum] = line.getExpressionText()
        print("line {} edited. New text = {}".format(self.expressionList[lineNum]))
        return

    def onButtonAdd(self):
        self.appendNewLine()

    def removeLine(self, nLine):
        nLine = min(nLine, len(self.lines) - 1)
        line = self.lines.pop(nLine)
        self.expressionList.pop(nLine)
        self.layout.removeWidget(line)
        del line
        for n in range(nLine, len(self.lines)):
            nOld = self.lines[n].lineNum
            self.lines[n].setLineNum(nOld-1)
        self.updateSize()

    def appendNewLine(self):
        line = ExpressionLine(len(self.lines), "")
        line.delete.connect(self.onLineDelete)
        line.edit.connect(self.onLineEdit)
        self.lines.append(line)
        self.expressionList.append("")
        self.layout.insertWidget(len(self.lines) - 1, line)
        self.updateSize()
        return

    def updateSize(self):
        self.updateGeometry()
        self.setBaseSize(self.layout.totalSizeHint())
        self.adjustSize()
        if self.parent != None:
            if hasattr(self.parent, 'updateSize'):
                self.parent.updateSize()
        #print("Layout size hint: {}".format(self.layout.totalSizeHint()))

class ExpressionLine(qtw.QWidget):
    delete = Signal(int)
    edit = Signal(int)
    _deleteLabel = '-'
    _colorDefault = 'black'
    _colorHighlight = 'red'
    _textEditHeight = 60 # Magic number!
    def __init__(self, lineNum = 0, expression = ""):
        super().__init__(None)
        self.lineNum = lineNum
        hbox = qtw.QHBoxLayout()
        self.labelNum = qtw.QLabel()
        self.setLineNum(lineNum)
        self.textEditExp = qtw.QTextEdit(parent = self)
        self.textEditExp.setText(expression)
        self.textEditExp.textChanged.connect(self.onTextEdit)
        self.textEditExp.setMaximumHeight(self._textEditHeight)
        labelEquals = qtw.QLabel('=')
        self.resultLabel = qtw.QLabel()
        self.buttonDelete = qtw.QPushButton(self._deleteLabel)
        self.buttonDelete.clicked.connect(self.onButtonDelete)
        hbox.addWidget(self.labelNum)
        hbox.addWidget(self.textEditExp, 3)
        hbox.addWidget(labelEquals)
        hbox.addWidget(self.resultLabel, 2)
        hbox.addWidget(self.buttonDelete, 0)
        self.setLayout(hbox)
        return

    def setLineNum(self, n):
        self.lineNum = n
        self.labelNum.setText("{}. ".format(n))

    def onTextEdit(self):
        self.edit.emit(self.lineNum)

    def getExpressionText(self):
        return self.textEditExp.toPlainText()

    def onButtonDelete(self):
        self.delete.emit(self.lineNum)

    def setResult(self, result):
        self.resultLabel.setText("{:.3f}".format(result))

#class VariableDialog(qtw.QDialog):
class VariableBox(qtw.QWidget):
    signalClose= Signal(int)
    _closeCancel = 0
    _closeOk = 1
    _closeApply = 2
    _defaultPairs = (("x", 0),)
    _addLabel = "+"
    def __init__(self, parent = None, nameIndexPairs = [], options = [], hasOkCancel = False):
        super().__init__(None)
        self.parent = parent
        self._hasOkCancel = hasOkCancel
        self.title = "Variables"
        if len(nameIndexPairs) == 0:
            self.nameIndexPairs = self._defaultPairs
        else:
            self.nameIndexPairs = nameIndexPairs
        self.options = options
        self.create()

    def create(self):
        groupBox = qtw.QGroupBox(self.title, self)
        self.layout = qtw.QVBoxLayout()
        self.lines = []
        self.names = []
        for n in range(len(self.nameIndexPairs)):
            name, index = self.nameIndexPairs[n]
            line = VariableLine(n, name, self.options, index = index)
            line.delete.connect(self.onLineDelete)
            line.edit.connect(self.onLineEdit)
            self.lines.append(line)
            self.names.append(name)
            self.layout.addWidget(line)
        self.buttonAdd = qtw.QPushButton(self._addLabel)
        self.buttonAdd.clicked.connect(self.onButtonAdd)
        self.layout.addWidget(self.buttonAdd)
        self.layout.setSizeConstraint(self.layout.SetFixedSize)
        groupBox.setLayout(self.layout)
        vbox = qtw.QVBoxLayout()
        vbox.addWidget(groupBox)
        hboxButton = qtw.QHBoxLayout()
        self.buttonApply = qtw.QPushButton("Apply")
        self.buttonApply.clicked.connect(self.onButtonApply)
        if self._hasOkCancel:
            self.buttonOk = qtw.QPushButton("Ok")
            self.buttonCancel = qtw.QPushButton("Cancel")
            self.buttonOk.clicked.connect(self.onButtonOk)
            self.buttonCancel.clicked.connect(self.onButtonCancel)
        hboxButton.addStretch(1)
        if self._hasOkCancel:
            hboxButton.addWidget(self.buttonOk)
            hboxButton.addWidget(self.buttonApply)
            hboxButton.addWidget(self.buttonCancel)
        else:
            hboxButton.addWidget(self.buttonApply)
        hboxButton.addStretch(1)
        vbox.addLayout(hboxButton)
        self.setLayout(vbox)
        return

    def onLineDelete(self, nLine):
        self.removeLine(nLine)
        return

    def onLineEdit(self, nLine):
        newName = self.lines[nLine].getVariableName()
        # Store old name in case we need to put it back
        oldName = self.names[nLine]
        # Remove old name so we don't get a hit on the 'if' statement below
        self.names[nLine] = ""
        if newName in self.names:
            self.lines[nLine].highlight()
            # put old name back in list
            self.names[nLine] = oldName
            # Ignore new name until changed again
        else:
            self.names[nLine] = newName
            self.lines[nLine].unhighlight()
        print("Line {} edited: new name {}".format(nLine, self.names[nLine]))

    def onButtonAdd(self):
        self.appendNewLine()

    def removeLine(self, nLine):
        nLine = min(nLine, len(self.lines) - 1)
        line = self.lines.pop(nLine)
        self.names.pop(nLine)
        self.layout.removeWidget(line)
        del line
        for n in range(nLine, len(self.lines)):
            nOld = self.lines[n].lineNum
            self.lines[n].setLineNum(nOld-1)
        self.updateSize()

    def appendNewLine(self):
        name = self._getNewName()
        line = VariableLine(len(self.lines), name, self.options, index = 0)
        line.delete.connect(self.onLineDelete)
        line.edit.connect(self.onLineEdit)
        self.lines.append(line)
        self.names.append(name)
        self.layout.insertWidget(len(self.lines) - 1, line)
        self.updateSize()
        return

    def updateSize(self):
        if hasattr(self, "updateGeometry"):
            self.updateGeometry()
        if hasattr(self, "setBaseSize"):
            self.setBaseSize(self.layout.totalSizeHint())
        if hasattr(self, "adjustSize"):
            self.adjustSize()
        if self.parent != None:
            if hasattr(self.parent, 'updateSize'):
                self.parent.updateSize()
        #print("Layout size hint: {}".format(self.layout.totalSizeHint()))

    def getVariableIndexDict(self):
        d = {}
        for line in self.lines:
            name = line.getVariableName()
            index = line.getVariableIndex()
            d[name] = index
        return d

    def getNameIndexPairs(self):
        """Same as getVariableIndexDict but returns list of pairs instead of dict"""
        l = []
        for line in self.lines:
            name = line.getVariableName()
            index = line.getVariableIndex()
            l.append((name, index))
        return l

    def _getNewName(self):
        """Get a new (unused) variable name"""
        x = ord('x')
        z = ord('z')
        A = ord('A')
        name = None
        # Should return 'x', 'y', 'z', 'A', 'B', 'C', etc.
        for n in range(x, x+52):
            if n < z + 1:
                c = chr(n)
            else:
                c = chr(n - z + A - 1)
            if c not in self.names:
                name = c
                break
        if name != None:
            return name
        # We've somehow used all alphabetic characters, try myVar0-myVar999
        for n in range(1000):
            name = 'myVar' + str(n)
            if name not in self.names:
                return name
        print("I give up")
        return None

    def onButtonCancel(self):
        print("cancel")
        self.signalClose.emit(self._closeCancel)

    def onButtonOk(self):
        print("ok")
        self.signalClose.emit(self._closeOk)

    def onButtonApply(self):
        print("apply")
        self.signalClose.emit(self._closeApply)

class VariableLine(qtw.QWidget):
    delete = Signal(int)
    edit = Signal(int)
    _deleteLabel = '-'
    _colorDefault = 'black'
    _colorHighlight = 'red'
    def __init__(self, lineNum = 0, name = "", options = [], index = 0):
        super().__init__(None)
        if index > len(options) - 1:
            index = 0
        self.lineNum = lineNum
        hbox = qtw.QHBoxLayout()
        self.labelNum = qtw.QLabel()
        self.setLineNum(lineNum)
        self.lineEditName = qtw.QLineEdit()
        self.lineEditName.setText(name)
        self.lineEditName.editingFinished.connect(self.onLineEdit)
        labelEquals = qtw.QLabel('=')
        self.comboBoxOptions = qtw.QComboBox()
        self.comboBoxOptions.addItems(options)
        self.comboBoxOptions.setCurrentIndex(index)
        self.buttonDelete = qtw.QPushButton(self._deleteLabel)
        self.buttonDelete.clicked.connect(self.onButtonDelete)
        hbox.addWidget(self.labelNum)
        hbox.addWidget(self.lineEditName, 1)
        hbox.addWidget(labelEquals)
        hbox.addWidget(self.comboBoxOptions)
        hbox.addWidget(self.buttonDelete, 0)
        self.setLayout(hbox)
        return

    def setLineNum(self, n):
        self.lineNum = n
        self.labelNum.setText("{}. ".format(n))

    def getVariableName(self):
        return self.lineEditName.text()

    def getVariableIndex(self):
        return self.comboBoxOptions.currentIndex()

    def onButtonDelete(self):
        self.delete.emit(self.lineNum)

    def onLineEdit(self):
        self.edit.emit(self.lineNum)

    def unhighlight(self):
        self.lineEditName.setStyleSheet("color: {};".format(self._colorDefault))

    def highlight(self):
        self.lineEditName.setStyleSheet("color: {};".format(self._colorHighlight))

class TestBox(qtw.QMainWindow):
    def __init__(self, dut = None, **kwargs):
        super().__init__(None)
        if dut != None:
            #self.dut = dut(**kwargs)
            self.dut = dut(parent = self, **kwargs) # Hack
            self.setCentralWidget(self.dut)
            self.show()
        else:
            app.quit()

    def updateSize(self):
        self.updateGeometry()
        self.resize(self.minimumSizeHint())

def testVariableDialog(argv):
    USAGE = "python3 {}".format(argv[0])
    app = qtw.QApplication(argv)
    nameIndexPairs = (("x", 0), ("y", 1), ("z", 2))
    options = ["one", "two", "three", "four"]
    window = TestBox(VariableDialog, nameIndexPairs = nameIndexPairs, options = options)
    return app.exec_()

def testGUIMathModule(argv):
    USAGE = "python3 {}".format(argv[0])
    app = qtw.QApplication(argv)
    window = TestBox(GUIMathModule)
    return app.exec_()

def testExpressionBox(argv):
    USAGE = "python3 {}".format(argv[0])
    app = qtw.QApplication(argv)
    expressionList = ("once upon a time", "I made a widget", "and it was ugly")
    window = TestBox(ExpressionBox, expressionList = expressionList)
    return app.exec_()

def testGUIMathModuleDialog(argv):
    import random
    USAGE = "python3 {}".format(argv[0])
    app = qtw.QApplication(argv)
    def getter():
        return random.randint(0, 10)
    labelGetterPairs = (("one", getter), ("two", getter), ("three", getter))
    nameIndexPairs = (("x", 2), ("y", 1), ("z", 0))
    expressions = ("once upon a time", "I made a widget", "and it was ugly")
    window = TestBox(GUIMathModuleDialog, labelGetterPairs = labelGetterPairs,
                     nameIndexPairs = nameIndexPairs, expressions = expressions)
    return app.exec_()

def test_isAllNumeric(argv):
    USAGE = "python3 {} expression".format(argv[0])
    if len(argv) < 2:
        print(USAGE)
        return False
    expr = argv[1]
    passed, s = GUIMathModuleDialog._isAllNumeric(expr)
    if passed:
        print("Pass")
    else:
        print("Fail, {}".format(s))
    return True

def test_replaceVariable(argv):
    USAGE = "python3 {} from to string".format(argv[0])
    if len(argv) < 4:
        print(USAGE)
        return False
    sfrom = argv[1]
    sto = argv[2]
    s = argv[3]
    result = GUIMathModuleDialog._replaceVariable(s, sfrom, sto)
    print("result = {}".format(result))
    return True

if __name__ == "__main__":
    import sys
    #testVariableDialog(sys.argv)
    #testExpressionBox(sys.argv)
    #testGUIMathModule(sys.argv)
    #testGUIMathModuleDialog(sys.argv)
    #test_isAllNumeric(sys.argv)
    test_replaceVariable(sys.argv)
