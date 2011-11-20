#!/usr/bin/env python

from __future__ import print_function
from sys import stderr


def log(*msg):
    print(*msg, file=stderr)

# vim: ts=8 et sw=4 sts=4 
