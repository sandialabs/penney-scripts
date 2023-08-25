#! /usr/bin/python3

# A file logger class with custom functionality

import time
import os

TIME_FORMAT_MDY = "mdy"
NONE_DEFAULT = "(None)"
LOGFILE_EXTENSION = ".txt"

class Logger():
    _kwEvent = "EVENT"
    _kwNote  = "NOTE"
    def __init__(self, filename = None, filedir = None, separator = ',', terminator = '\n'):
        self.filename = filename
        self.filedir = filedir
        self.separator = separator
        self._terminator = terminator
        self._logItems = []
        if self.filename == None:
            self.filename = self._generateFilename()
        self.filename, self.filepath = self._createAndJoin(name = self.filename, fdir = self.filedir)
        self._startTime = time.time()
        self._isEmpty = True

    @staticmethod
    def _createAndJoin(name = "", fdir = "."):
        if fdir == None:
            fdir = ""
        if fdir != "":
            if not os.path.exists(fdir):
                os.mkdir(fdir)
            if not os.path.isdir(fdir):
                print("{} is not a directory. Defaulting to parent directory.".format(fdir))
                fdir = ""
        # Ensure the filename has the correct extension
        filenameStem, ext = os.path.splitext(name)
        print("filenameStem = {}, ext = {}".format(filenameStem, ext))
        filename = filenameStem + LOGFILE_EXTENSION
        filepath = os.path.join(fdir, name)
        return (filename, filepath)

    @staticmethod
    def _generateFilename():
        datestring, timestring = getDateTimeString()
        timestring = timestring.replace(':', '')
        return "logfile_{}_{}{}".format(datestring, timestring, LOGFILE_EXTENSION)

    def addLogItem(self, label, getter, index = None):
        if index == None:
            self._logItems.append(LogItem(label, getter))
        else:
            index = min(index, len(self._logItems))
            self._logItems.insert(index, LogItem(label, getter))
        return len(self._logItems)

    def begin(self):
        datestring, timestring = getDateTimeString(TIME_FORMAT_MDY)
        s = "# {} - Log file created on {} at {} with logger.py{}".format(
                self.filename, datestring, timestring, self._terminator)
        with open(self.filepath, 'w') as fd:
            fd.write(s)
        self._startTime = time.time()
        self._writeHeader()
        return

    def _writeHeader(self):
        l = ["Time (s)"]
        for logItem in self._logItems:
            l.append(logItem.getLabel())
        s = self.separator.join(l)
        #print(s)
        self._writeLine(s)
        # Consider a header line to be only at the start of a file
        self._isEmpty = True

    def _terminate(self, string):
        if not string.endswith(self._terminator):
            string += self._terminator
        return string

    def _writeLine(self, string):
        string = self._terminate(string)
        with open(self.filepath, 'a') as fd:
            fd.write(string)
        self._isEmpty = False
        return

    def log(self):
        l = ["{:.03f}".format(self._now())]
        for logItem in self._logItems:
            s = logItem.get()
            if s == None:
                s = NONE_DEFAULT
            l.append(s)
        s = self.separator.join(l)
        self._writeLine(s)
        return

    def event(self, string):
        self._addLine(self._kwEvent, string)
        return

    def note(self, string):
        self._addLine(self._kwNote, string)
        return

    def _addLine(self, keyword, string):
        timestamp = self._now()
        string = self._terminate(str(string))
        s = "# {} {:.03f}: {}".format(keyword, timestamp, string)
        self._writeLine(s)
        return

    def deleteIfEmpty(self):
        """Delete logfile if empty (no log lines or events, only header)."""
        if self._isEmpty:
            print("Deleting empty file {}.".format(self.filepath))
            os.remove(self.filepath)
        else:
            print("File not empty {}".format(self._isEmpty))

    def _now(self):
        return time.time() - self._startTime


def getDateTimeString(fmt = None):
    ts = time.localtime()
    if fmt is not None and fmt.lower() == TIME_FORMAT_MDY:
        date = "{1}/{2}/{0}".format(ts.tm_year, ts.tm_mon, ts.tm_mday)
    else:
        date = "{0:04}{1:02}{2:02}".format(ts.tm_year, ts.tm_mon, ts.tm_mday)
    ltime = "{:02}:{:02}".format(ts.tm_hour, ts.tm_min)
    return (date, ltime)

class LogItem():
    def __init__(self, label = "", getter = lambda x: ""):
        self.label = label
        self._getter = getter

    def getLabel(self):
        return self.label

    def get(self):
        return self._getter()

    def __repr__(self):
        return "LogItem({})".format(self.label)

def testLogger(argv):
    USAGE = "python3 {}".format(argv[0])
    def testGet():
        return "Test"
    logger = Logger(filename = None, filedir = "logs", separator = '\t')
    items = (("An item", testGet, 0), ("Second Item (s)", testGet, 1), ("More Things", testGet, 0))
    for label, getter, index in items:
        logger.addLogItem(label, getter, index)
    logger.begin()
    time.sleep(1.0)
    logger.log()
    time.sleep(4.0)
    logger.log()
    time.sleep(0.2)
    logger.event("Hello!")
    time.sleep(1.5)
    logger.log()
    return True

if __name__ == "__main__":
    import sys
    testLogger(sys.argv)

