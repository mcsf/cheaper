#!/usr/bin/env python

from base64 import b64decode, b64encode
from yaml import safe_dump, safe_load

from utils import log

# To decode serialized Events, either will do:
#
#   e = Event()
#   e.decode(string)
#
# or just:
#
#   e = Event(decode=string)

class Event(dict):

    def __init__(self, name=None, data=None, **kwargs):
        self.type = name
        if data: self['data'] = data
        if 'decode' in kwargs:
            self.decode(kwargs['decode'])

    def encode(self):
        data = {}
        data['attrs'] = self.__dict__.copy()
        data['data']  = self.copy()
        return b64encode(safe_dump(data))

    def decode(self, s):
        try:
            data = safe_load(b64decode(s))
        except Exception, e:
            raise Exception('Malformed input: %s' % e)

        if not data: return

        if not 'attrs' in data or not 'data' in data:
            raise Exception('Malformed object.')

        self.__dict__.update(data['attrs'])
        self.update(data['data'])
        return self


class UpdateEvent(Event):
    def __init__(self, data):
        Event.__init__(self, 'update', data)


#def test():
#    e1 = UpdateEvent([[1,2,3], [4,5,6]])
#    e2 = Event(decode=e1.encode())
#    assert e1 is not e2
#    assert e1 == e2
#    assert e1.type == e2.type
#    assert e1.__dict__ == e2.__dict__
#    assert e1.__dict__ is not e2.__dict__


# vim: ts=8 et sw=4 sts=4 
