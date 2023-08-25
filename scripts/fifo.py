#!/usr/bin/python3

# A python FIFO implementation
# * Configurable depth and blocking.
# * Indexable (i.e. fifo[n] returns the nth item waiting in the buffer)
#   Indexes go oldest-to-newest (i.e. 0 is the least-recently added item, -1 is the most-recently added)
# * len(fifo) returns the number of items pending in the fifo

class FIFO(object):
    def __init__(self, bufferDepth = 3, blockOnFull = True):
        """A simple FIFO implementation.
        bufferDepth = the number of items the buffer can hold
        blockOnFull = boolean
            if False: adds to a full buffer are accepted (returns True, last item deleted)
            if True: adds to a full buffer are rejected (returns False, item not added)"""
        self._depth = int(bufferDepth)
        self._blockOnFull = blockOnFull
        self._buffer = [None]*self._depth
        self._addPtr = 0
        self._getPtr = 0
        self._empty = True

    def _incGetPtr(self):
        self._getPtr = (self._getPtr + 1) % self._depth

    def _incAddPtr(self):
        self._addPtr = (self._addPtr + 1) % self._depth

    def reset(self):
        self._addPtr = 0
        self._getPtr = 0
        self._empty = True

    def add(self, item):
        """Add an item to the buffer.
        Blocking Buffer:
            if full, returns False
            else, returns True
        Non-blocking Buffer:
            always returns True
            if Full, the next item to 'get' will be forgotten (garbage-collected)"""
        # Check for full
        if self.isFull():
            if self._blockOnFull:
                return False
            else:
                # Increment (wrap) get pointer to 'forget' last item
                self._incGetPtr()
        self._buffer[self._addPtr] = item
        # Increment (wrap if necessary) add pointer
        self._incAddPtr()
        # It is now not empty
        self._empty = False
        return True

    def get(self):
        """Get the next item in the buffer.
        If empty, returns None
        Else, returns the item"""
        # Check for empty
        if self.isEmpty():
            return None
        # Fetch the item to return
        item = self._buffer[self._getPtr]
        # Increment (wrap if necessary) get pointer
        self._incGetPtr()
        # Now if pointers are equal, we must be empty
        if self._addPtr == self._getPtr:
            self._empty = True
        return item

    def load(self):
        """Get the next item in the buffer without
        incrementing the buffer.  Must call inc() to
        increment the buffer or the item will remain
        in the queue.
        If empty, returns None
        Else, returns the item"""
        # Check for empty
        if self.isEmpty():
            return None
        # Fetch the item to return
        item = self._buffer[self._getPtr]
        return item

    def inc(self):
        """Increment the buffer (forget the next item).
        This should be used with load() to perform a two-stage
        'get' operation which gives you a chance to leave the
        item in the buffer for a future retry of processing."""
        # Check for empty
        if self.isEmpty():
            return None
        # Increment (wrap if necessary) get pointer
        self._incGetPtr()
        # Now if pointers are equal, we must be empty
        if self._addPtr == self._getPtr:
            self._empty = True
        return

    def isFull(self):
        """Return True if the buffer is full, else return False."""
        return (not self._empty) and (self._addPtr == self._getPtr)

    def isEmpty(self):
        """Return True if the buffer is empty, else return False."""
        return self._empty

    def getNumItems(self):
        """Get the number of items currently in the buffer.  Will always
        return a number between 0 and bufferDepth"""
        if self.isFull():
            return self._depth
        else:
            return (self._addPtr + self._depth - self._getPtr) % self._depth

    def __len__(self):
        return self.getNumItems()

    def __getitem__(self, index):
        index = self._convertGetIndex(index)
        if index == None:
            return None
        return self._buffer[index]

    def __setitem__(self, key, value):
        """Not sliceable in the current implementation"""
        try:
            key = int(key)
        except ValueError:
            raise TypeError("Buffer index must be an integer")
        #print("key = {}".format(key))
        index = self._convertSetIndex(key)
        #print("index = {}".format(index))
        if index == None:
            return False
        self._buffer[index] = value
        return True

    def _convertGetIndex(self, index):
        if index < 0:   # If index is negative, convert to positive
            index = self.getNumItems() + index
            if index < 0:   # If it's still negative, it's out of range
                raise IndexError("Buffer index out of range.")
                return None
        if index > self._depth - 1:
            raise IndexError("Buffer index out of range.")
            return None
        if index <= (self.getNumItems() - 1):
            index = (index + self._getPtr) % self._depth
            return index
        return None

    def _convertSetIndex(self, index):
        if index > self._depth - 1:
            raise IndexError("Buffer index out of range.")
            return None
        if index <= (self.getNumItems() - 1):
            index = (index + self._depth - 1 - self._getPtr) % self._depth
            return index
        else:
            return None

    def __str__(self):
        f = []
        for n in range(self.getNumItems()):
            f.append(str(self.__getitem__(n)))
        if len(f) == 0:
            return '[]'
        return '[' + ','.join(f) + ']'

    def __repr__(self):
        return self.__str__()

class Stack(FIFO):
    """In a First-In-Last-Out (FILO/LIFO) buffer, if the add and get pointers are
    equal, it's empty.  Otherwise, the add pointer should always be 1 ahead of the
    get pointer.
    This Stack implementation also pegs its index at both ends.
    A negative index where abs(index) > numEntries will always return item 0.
    A positive index > numEntries will always return item -1."""
    def __init__(self, bufferDepth = 3, blockOnFull = True):
        super().__init__(bufferDepth, blockOnFull)
        self._numItems = 0

    def reset(self):
        self._addPtr = 0
        self._getPtr = 0
        self._numItems = 0
        self._empty = True

    def _convertGetIndex(self, index):
        nitems = self.getNumItems()
        if nitems == 0:
            return None
        if index < 0:   # If index is negative, convert to positive
            index = nitems - (abs(index) % nitems)
        # We don't want people peeking on memory that "doesn't exist"
        index = (self._getPtr - min(index, nitems-1)) % self._depth
        return index

    def _convertSetIndex(self, index):
        nitems = self.getNumItems()
        if nitems == 0:
            raise IndexError("Cannot set item at index {} because the entry does not exist.".format(index))
            return None
        if index < 0:   # If index is negative, convert to positive
            index = nitems - (abs(index) % nitems)
        if index <= (nitems - 1):
            index = (self._getPtr - index) % self._depth
            #index = (index + self._depth - 1 - self._getPtr) % self._depth
            return index
        else:
            raise IndexError("Cannot set item at index {} because the entry does not exist.".format(index))
            return None

    def isFull(self):
        if self._numItems == self._depth:
            return True
        return False

    def add(self, item):
        """Add an item to the buffer.
        Blocking Buffer:
            if full, returns False
            else, returns True
        Non-blocking Buffer:
            always returns True
            if Full, the next item to 'get' will be forgotten (garbage-collected)"""
        # Check for full
        if self.isFull():
            if self._blockOnFull:
                return False
            else:
                # Decrement _numItems because it will be incremented by _incPtrs
                self._numItems -= 1
        self._buffer[self._addPtr] = item
        # Increment (wrap if necessary) pointers
        self._incPtrs()
        # It is now not empty
        self._empty = False
        return True

    def get(self):
        """Get the next item in the buffer.
        If empty, returns None
        Else, returns the item"""
        # Check for empty
        if self.isEmpty():
            return None
        # Fetch the item to return
        item = self._buffer[self._getPtr]
        # Decrement pointers
        self._decPtrs()
        # Now if pointers are equal, we must be empty
        if self._numItems == 0:
            self._empty = True
        return item

    def getNumItems(self):
        """Get the number of items currently in the buffer.  Will always
        return a number between 0 and bufferDepth - 1"""
        return self._numItems

    def _incPtrs(self):
        """A Stack should set the get pointer to the previous location of the add ptr on
        increment."""
        self._getPtr = self._addPtr
        self._addPtr = (self._addPtr + 1) % self._depth
        self._numItems += 1

    def _decPtrs(self):
        """A Stack should set the add pointer to the previous location of the get ptr on
        decrement."""
        self._addPtr = self._getPtr
        self._getPtr = (self._getPtr - 1) % self._depth
        self._numItems -= 1

def _testFIFO(argv):
    blockOnFull = input("Block FIFO on full buffer [T/F]: ?")
    if blockOnFull == '' or blockOnFull.lower()[0] == 'f':
        blockOnFull = False
        print("Shift on full buffer.")
    else:
        blockOnFull = True
        print("Block on full buffer.")
    
    fifo = FIFO(3, blockOnFull)
    while True:
        try:
            query = input("Add [a], get [g], or index[i]? ")
            if query == '':
                raise KeyboardInterrupt()
            if query.lower()[0] == 'a':
                toAdd = input("String to add: ")
                result = fifo.add(toAdd)
                print("Result: {}".format(result))
            elif query.lower()[0] == 'g':
                result = fifo.get()
                if result == None:
                    print("Buffer is empty")
                else:
                    print("Got: {}".format(result))
            elif query.lower()[0] == 'i':
                while True:
                    index = input("Index: ")
                    try:
                        index = int(index)
                        break
                    except ValueError:
                        print("Index must be an integer")
                print("fifo[{}] = {}".format(index, fifo[index]))
        except KeyboardInterrupt:
            print("Exiting...")
            break
        except IndexError:
            print("Index out of range!")

def _doFifoTestNonBlocking(argv):
    _s = ["A", "B", "C", "D", "E", "F", "G"]
    _b = ["H", "I", "J", "K"]
    fifo = FIFO(len(_s), blockOnFull=False)
    passed = True
    for item in _s:
        if fifo.add(item):
            print("Adding {}, len = {}".format(item, len(fifo)))
        else:
            print("Could not add {}".format(item))
            passed = False
    print("Looping...")
    for item in fifo:
        print(item)
    print("Adding more...")
    for item in _b:
        if fifo.add(item):
            print("Adding {}, len = {}".format(item, len(fifo)))
        else:
            print("Could not add {}".format(item))
            passed = False
    print("Looping...")
    for item in fifo:
        print(item)
    if passed:
        print("All tests passed")
        return 0
    else:
        print("Tests failed.")
        return -1

def _testStack(argv):
    blockOnFull = input("Block Stack on full buffer [T/F]: ?")
    if blockOnFull == '' or blockOnFull.lower()[0] == 'f':
        blockOnFull = False
        print("Shift on full buffer.")
    else:
        blockOnFull = True
        print("Block on full buffer.")
    stack = Stack(3, blockOnFull)
    while True:
        try:
            query = input("Add [a], get [g], or index[i]? ")
            if query == '':
                raise KeyboardInterrupt()
            if query.lower()[0] == 'a':
                toAdd = input("String to add: ")
                result = stack.add(toAdd)
                print("Result: {}".format(result))
            elif query.lower()[0] == 'g':
                result = stack.get()
                if result == None:
                    print("Buffer is empty")
                else:
                    print("Got: {}".format(result))
            elif query.lower()[0] == 'i':
                while True:
                    index = input("Index: ")
                    try:
                        index = int(index)
                        break
                    except ValueError:
                        print("Index must be an integer")
                print("stack[{}] = {}".format(index, stack[index]))
        except KeyboardInterrupt:
            print("Exiting...")
            break
        except IndexError:
            print("Index out of range!")

def _doStackTestBlocking(argv):
    _s = ["A", "B", "C", "D", "E", "F", "G"]
    _b = ["H", "I", "J", "K"]
    stack = Stack(len(_s), blockOnFull=True)
    passed = True
    for item in _s:
        if stack.add(item):
            print("Adding {}, len = {}".format(item, len(stack)))
        else:
            print("Could not add {}".format(item))
            passed = False
    print(stack)
    print("Checking indices...")
    l = len(_s)
    for n in range(l):
        match = _s[-(n+1)]
        if stack[n] != match:
            print("stack[{}] = {} while _s[{}] = {}".format(n, stack[n], -(n+1), match))
            passed = False
    toAdd = len(_b) # Add more to test blocking/shifting
    print("Adding {} more".format(toAdd))
    for item in _b:
        stack.add(item)
    print(stack)
    print("Checking indices...")
    for n in range(l):
        match = _s[-(n+1)]
        if stack[n] != match:
            print("stack[{}] = {} while _s[{}] = {}".format(n, stack[n], -(n+1), match))
            passed = False
    print("Getting...")
    _limit = 100
    while True:
        _limit -= 1
        if _limit == 0:
            print("Hit loop limit")
            passed = False
            break
        item = stack.get()
        if item == None:
            break
        print("Got {}. len = {}".format(item, len(stack)))
    print("Adding one more")
    stack.add('X')
    print("Checking memory access...")
    for n in range(10):
        m = n-5
        item = stack[m]
        if item not in (None, 'X'):
            print("I found {} at index {}".format(item, m))
            passed = False
    if passed:
        print("All tests passed.")
        return 0
    else:
        print("Tests failed")
        return -1

def _doStackTestNonBlocking(argv):
    _s = ["A", "B", "C", "D", "E", "F", "G"]
    _b = ["H", "I", "J", "K"]
    stack = Stack(len(_s), blockOnFull=False)
    passed = True
    for item in _s:
        if stack.add(item):
            print("Adding {}, len = {}".format(item, len(stack)))
        else:
            print("Could not add {}".format(item))
            passed = False
    print(stack)
    print("Checking indices...")
    l = len(_s)
    for n in range(l):
        if stack[n] != _s[-(n+1)]:
            print("stack[{}] = {} while _s[{}] = {}".format(n, stack[n], -(n+1), _s[-(n+1)]))
            passed = False
    toAdd = len(_b) # Add more to test blocking/shifting
    print("Adding {} more".format(toAdd))
    for item in _b:
        stack.add(item)
    print(stack)
    print("Checking indices...")
    for n in range(l):
        if n < toAdd:
            match = _b[toAdd-1-n]
        else:
            match = _s[l-1-n+toAdd]
        if stack[n] != match:
            print("stack[{}] = {}. Should be {}".format(n, stack[n], match))
            passed = False
    print("Getting...")
    _limit = 100
    while True:
        _limit -= 1
        if _limit == 0:
            print("Hit loop limit")
            passed = False
            break
        item = stack.get()
        if item == None:
            break
        print("Got {}. len = {}".format(item, len(stack)))
    print("Adding one more")
    stack.add('X')

    print("Checking memory access...")
    for n in range(10):
        m = n-5
        item = stack[m]
        if item not in (None, 'X'):
            print("I found {} at index {}".format(item, m))
            passed = False
    if passed:
        print("All tests passed.")
        return 0
    else:
        print("Tests failed")
        return -1

if __name__ == "__main__":
    import sys
    #_testFIFO(sys.argv)
    #_testStack(sys.argv)
    #_doStackTestNonBlocking(sys.argv)
    #_doStackTestBlocking(sys.argv)
    _doFifoTestNonBlocking(sys.argv)

