#!/usr/bin/env python

from __future__ import print_function
from sys import stderr


def log(*msg):
    print(*msg, file=stderr)

# vim: ts=8 et sw=4 sts=4 


class pdu_reader():
    def __init__(self, stream):
        buffer=""
        self.stream = stream
        
    def read(self):
        """ Returns a PDU string from self.stream. """
        # Find index of first occurence of \n in the buffer.
                
        # read from stream until we have a full PDU.
        if self.buffer.find("\n") == -1:
            tmp=""
            while tmp.find("\n") == -1: 
                tmp = self.stream.recv(1024)
                self.buffer += tmp

        i = self.buffer.find("\n")
        pdu = self.buffer[:i]
        self.buffer = self.buffer[i+1:]
        return pdu
        
