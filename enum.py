#!/usr/bin/env python

class Enum(set):
    def __getattr__(self, name):
        if name in self:
            return name
        raise AttributeError

# vim: ts=8 et sw=4 sts=4 
