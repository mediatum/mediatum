"""
 mediatum - a multimedia content repository

 Copyright (C) 2007 Arne Seifert <seiferta@in.tum.de>
 Copyright (C) 2007 Matthias Kramm <kramm@in.tum.de>

 This program is free software: you can redistribute it and/or modify
 it under the terms of the GNU General Public License as published by
 the Free Software Foundation, either version 3 of the License, or
 (at your option) any later version.

 This program is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 GNU General Public License for more details.

 You should have received a copy of the GNU General Public License
 along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

"""A dictionary where keys keep their order"""

class SortedDict:

    def __init__(self):
        self._keys = []
        self._key2data = {}

    def __cmp__(self, dict):
        if isinstance(dict,SortedDict):
            return cmp(self._key2data, dict.data)
        else:
            return cmp(self._key2data, dict)

    def __len__(self): 
        return len(self._keys)

    def __getitem__(self, key): 
        return self._key2data[key]

    def __setitem__(self, key, item): 
        self._keys += [key]
        self._key2data[key] = item

    def __delitem__(self, key): 
        item = self._key2data[key]
        for i in xrange(len(self._keys)):
            if self._keys[i] == key:
                del self._keys[i]
                del self._key2data[key]
                return
        raise "Internal Error"

    def clear(self): 
        self._key2data.clear()
        self._keys = []

    def copy(self):
        s = SortedDict()
        s._keys = self.keys[:]
        s._key2data = self.key2data.copy()
        return s

    def keys(self): 
        return self._keys

    def items(self): 
        l = []
        for k in self._keys:
            l += [(k,self._key2data[k])]
        return l
    
    def values(self): 
        l = []
        for k in self._keys:
            l += [self._key2data[k]]
        return l

    def has_key(self, key): 
        return self._key2data.has_key(key)

    def update(self, dict):
        for k, v in dict.items():
            if not self.has_key(k):
                self._keys += [k]
            self._key2data[k] = v

    def get(self, key, failobj=None):
        if not self.has_key(key):
            return failobj
        return self._key2data[key]

    def __contains__(self, key):
        return key in self._key2data


"""A dictionary which is only allowed to keep n entries"""

class MaxSizeDictEntry:
    def __init__(self,dict,key,data):
        self.key = key
        self.data = data
        self.parent = dict
        self.next = None
        self.prev = None
        self.inqueue = 1
        self.append()

    def append(self):
        self.next = None
        if self.parent.queue_end is None:
            self.parent.queue_start = self.parent.queue_end = self
            self.prev = None
        else:
            self.parent.queue_end.next = self
            self.prev = self.parent.queue_end
            self.parent.queue_end = self
        self.parent.queuelen = self.parent.queuelen + 1

    def remove(self):
        if self.next:
            self.next.prev = self.prev
        if self.prev:
            self.prev.next = self.next
        if self is self.parent.queue_start:
            self.parent.queue_start = self.next
        if self is self.parent.queue_end:
            self.parent.queue_end = self.prev
        self.next = None
        self.prev = None
        self.parent.queuelen = self.parent.queuelen - 1
        return self.key

    def use(self):
        self.remove()
        self.append()

    def __del__(self):
        if not self.inqueue:
            if self.parent._key2data[self.key] == self:
                del self.parent._key2data[self.key]

class MaxSizeDict:

    def __init__(self, maxsize, keep_weakrefs=0):
        self.maxsize = maxsize
        self._key2data = {}
        self.queuelen = 0
        self.queue_start = None
        self.queue_end = None
        self.keep_weakrefs = keep_weakrefs

    def __cmp__(self, dict):
        if isinstance(dict,SortedDict):
            return cmp(self._key2data, dict.data)
        else:
            return cmp(self._key2data, dict)

    def __len__(self): 
        #return len(self._key2data)
        return self.queuelen

    def __getitem__(self, key): 
        item = self._key2data[key]
        item.use()
        return item.data

    def reduce(self):
        #print "reduce"
        #a = self.queue_start
        #while a:
        #    print a.key,
        #    a = a.next
        #print

        while self.queuelen >= self.maxsize:
            if self.queue_start:
                key = self.queue_start.remove()
                if self.keep_weakrefs:
                    self._key2data[key].inqueue = 0
                else:
                    del self._key2data[key]
            else:
                break

    def __setitem__(self, key, data): 
        try:
            item = self._key2data[key]
            if item.inqueue:
                item.remove()
        except KeyError:
            self.reduce()
        self._key2data[key] = MaxSizeDictEntry(self,key,data)

    def remove(self, key):
        try: 
            item = self._key2data[key]
            if item.inqueue:
                item.remove()
        except KeyError:
            pass
        del self._key2data[key]

    def __delitem__(self, key): 
        self.remove(key)

    def clear(self): 
        self._key2data.clear()
        self.queue_start = None
        self.queue_end = None

    def flush(self):
        self.clear()

    def copy(self):
        s = MaxSizeDict()
        s.update(self)
        return s

    def keys(self): 
        return self._key2data.keys()

    def items(self): 
        l = []
        for k in self._key2data.keys():
            l += [(k,self._key2data[k].data)]
        return l
    
    def values(self): 
        l = []
        for k in self._keys:
            l += [self._key2data[k].data]
        return l

    def has_key(self, key): 
        try:
            item = self._key2data[key]
            item.use()
            return 1
        except KeyError:
            return 0

    def update(self, dict):
        raise "Not supported"

    def get(self, key, failobj=None):
        try:
            item = self._key2data[key]
            item.use()
            return item.data
        except KeyError:
            return failobj

    def __contains__(self, key):
        return self.has_key(key)


if __name__ == "__main__":
    d = MaxSizeDict(10)
    for a in range(1000,1010):
        d[a] = a
    for a in range(1000,1010):
        assert a in d

    for a in range(1010,1020):
        d[a] = a
        if not d.keep_weakrefs:
            assert (a-10) not in d
    
    for a in range(1010,1020):
        assert a in d

    for a in range(1010,1020):
        assert d[a] == a
    
    for a in range(10):
        d[1000+19-a]

    for a in range(1000,1010):
        d[a] = a
        if not d.keep_weakrefs:
            assert (10+9-a) not in d

    d[3] = 4
    assert d[3] == 4

    # --

    class C:
        def __init__(self,id):
            self.id = id

    d = MaxSizeDict(10, keep_weakrefs=1)
    myarray = [0]*10
    for i in range(1,20):
        obj = C(i)
        d[i] = obj
        if i < 10:
            myarray[i] = obj
    d[33] = 33
    for i in range(1,10):
        try:
            obj = d[i]
        except:
            obj = C(i)
        assert obj in myarray


