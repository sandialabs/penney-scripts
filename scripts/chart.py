#!/usr/bin/python3

"""A container for a number of channels, each with a moving window of 'depth' values.
Channels are accessed/referenced by label or index and each window of values has a
FIFO-style interface."""

import fifo

class ChartRecorder():
    """A container for a number of channels, each with a moving window of 'depth' values.
    Channels are accessed/referenced by label or index and each window of values has a
    FIFO-style interface."""
    DEPTH_DEFAULT = 8
    _indexLabel = 0
    _indexFifo = 1
    def __init__(self, depth = DEPTH_DEFAULT):
        self.index = 0
        self.depth = depth
        self._channelFifos = []

    @staticmethod
    def _isString(s):
        # Permissive. Could instead use instanceof()
        if hasattr(s, '__len__'):
            return True
        return False

    @staticmethod
    def _getDefaultLabel(index):
        return str(index)

    def _getFifo(self, ref):
        if self._isString(ref):
            return self._getFifoByLabel(ref)
        return self._getFifoByIndex(ref)

    def _getFifoByIndex(self, index):
        if index > len(self._channelFifos) - 1:
            print("Index {} out of range {}".format(index, len(self._channelFifos)))
            return None
        return self._channelFifos[index][self._indexFifo]

    def _getFifoByLabel(self, label):
        for fLabel, fifo in self._channelFifos:
            if label == fLabel:
                return fifo
        print("Could not find FIFO with label {}".format(label))
        return None

    def _getLabel(self, ref):
        if self._isString(ref):
            for fLabel, fifo in self._channelFifos:
                if ref == fLabel:
                    return fLabel
            print("Could not find FIFO with label {}".format(label))
            return None
        if ref > len(self._channelFifos) - 1:
            print("Index {} out of range {}".format(ref, len(self._channelFifos)))
            return
        return self._channelFifos[ref][self._indexLabel]

    def setDepth(self, depth):
        """Set the depth of subsequently-created FIFOs (should be used before any call to 'addChannel')."""
        self.depth = depth
        return

    def addChannel(self, label = None):
        for n in range(len(self._channelFifos)):
            fLabel = self._channelFifos[n][self._indexLabel]
            if fLabel == label:
                print("Channel with label {} already exists at index {}".format(label, n))
                return None
        chanFifo = fifo.FIFO(self.depth, blockOnFull = False)
        index = self.index
        if label == None:
            label = self._getDefaultLabel(index)
        self._channelFifos.append((label, chanFifo))
        self.index += 1
        return index

    def getIndex(self, label = None):
        if label == None:
            return None
        for n in range(len(self._channelFifos)):
            fLabel = self._channelFifos[n][self._indexLabel]
            if label == fLabel:
                return n
        print("getIndex(): Could not find label {}".format(label))
        return None

    def __len__(self):
        return self.index

    def addValue(self, ref, val):
        """Add value 'val' to channel associated with reference 'ref' which can be either
        a label or an index."""
        fifo = self._getFifo(ref)
        if fifo != None:
            fifo.add(val)
            return True
        return False

    def getAvg(self, ref):
        """Get the average of all values stored in FIFO associated with reference 'ref' (label
        or index).  Returns None if values could not be averaged (e.g. if non-numeric)."""
        fifo = self._getFifo(ref)
        if fifo == None:
            print("getAvg() could not find FIFO from reference {}".format(ref))
            return None
        nVals = len(fifo)   # Returns the number of items stored in the fifo
        if nVals == 0:
            print("FIFO associated with {} is empty".format(ref))
            return None
        vsum = 0
        fault = False
        m = 0
        for n in range(nVals):
            try:
                vsum += fifo[n]
            except:
                fault = True
                break
        if fault:
            m = n
            print("Could not compute average with value {}".format(fifo[n]))
            return None
        return vsum/nVals

    def getLatest(self, ref):
        fifo = self._getFifo(ref)
        if fifo != None:
            return fifo[-1]
        return None

    def printChannel(self, ref):
        fifo = self._getFifo(ref)
        if fifo == None:
            print("Could not locate FIFO by reference {}".format(ref))
            return
        label = self._getLabel(ref)
        avg = self.getAvg(ref)
        latest = self.getLatest(ref)
        vals = []
        for n in range(len(fifo)):
            vals.append(fifo[n])
        print("Channel {}. Vals = {}. Latest = {}. Average = {:.3f}".format(label, vals, latest, avg))
        return

def testChartRecorder(argv):
    import random
    USAGE = "python3 {}".format(argv[0])
    # Set byIndex = True to access FIFOs by index rather than label
    byIndex = False
    chanLabels = ("one", "two", "three", "four")
    depth = 3
    iterations = 10
    chart = ChartRecorder(depth)
    for chan in chanLabels:
        chart.addChannel(chan)
    for n in range(iterations):
        for m in range(len(chanLabels)):
            if byIndex:
                ref = m
            else:
                ref = chanLabels[m]
            chart.addValue(m, random.randint(0, 10))
            chart.printChannel(m)
    return True

if __name__ == "__main__":
    import sys
    testChartRecorder(sys.argv)
