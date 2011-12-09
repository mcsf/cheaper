#!/usr/bin/env python

from base64 import b64decode, b64encode
from myyaml import safe_dump, safe_load

from utils import log

MAX_SIZ = 1024

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
        self['data'] = data if data else []
        if 'decode' in kwargs:
            self.decode(kwargs['decode'])

    def encode(self):
        data = {}
        data['attrs'] = self.__dict__.copy()
        data['data']  = self.copy()
        s = b64encode(safe_dump(data))
        #Make sure we never send something too big
        assert len(s) <= MAX_SIZ
        return s

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

    def read_data_and_encode(self, f, max_size=MAX_SIZ):
        data = {}
        data['attrs'] = self.__dict__.copy()
        data['data']  = self.copy()
        
        # this makes the yaml module represent the field as binary.
        data['data']['data'] = "\777"
        
        # we want to find out in which line the string above is being represented.
        yaml_doc=safe_dump(data).splitlines()
        yaml_doc
        data_line=yaml_doc.index("    /w==")

        # Replace it with just the identation spaces.
        yaml_doc[data_line] = "    "

        # Find out how much space would the YAML document take before adding the file chunk.
        size=0     
        for line in yaml_doc:
            size+=len(line) + 1
        
        # convert maximum PDU size in maximum yaml document size before converting to base64.
        print size
        size_avail = (max_size / 4) * 3
        # subtract space already occupied by the yaml without the file fragment
        size_avail -= size
        print size_avail
        # convert size available into maximum size before converting the read chunk into base64
        read_size = (size_avail / 4) * 3
        print read_size

        # Read as much as we can with the given space.
        chunk=f.read(read_size)
        
        if len(chunk) == 0:
            raise Exception('Finished file transfer.')

        # Place the base64 representation of the chunk into the line.
        yaml_doc[data_line] += b64encode(chunk)

        # Join the yaml list back into a string.
        msg=""
        for line in yaml_doc:
            msg += line + "\n"
            
        # return the base64 representation of yaml document.
        return b64encode(msg)
        
        
            
        
        
        


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
