#!/usr/bin/env python

import select
import socket
import sys
import time

from commands import *
from event import Event
from exception import ConnectionError
from state import client
from utils import *


# SETTINGS #############################################################

MAX_RECV    = 512
SERVER_HOST = 'localhost'
SERVER_PORT = 8888


# INPUT PROCESSING #####################################################

def read_stdin(s):
    if not s: return

    cmd, args = s.partition(' ')[::2]
    fn = commands.get(cmd.lower())

    if fn: return fn(args)
    else: log('Invalid command.')


def read_tcp(s):
    if not s:
        raise ConnectionError
    try:
        e = Event(decode=s)
        if e.type is not None: return e
    except Exception, e:
        log('---')
        log('Recv malformed data:', s)
        log(e)


# TCP ##################################################################

def connection(h, p):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.connect((h, p))
    except Exception, e:
        log(e)
        return False
    else:
        log('Connected to server.')
    return s


# GLOBALS ##############################################################

state  = client.main_init
locsrv = connection(SERVER_HOST, SERVER_PORT) # Socket to Local Server


# MAIN #################################################################

def listen():
    rl, _, _ = select.select([sys.stdin, locsrv], [], [])
    if rl:
        # return a tuple (Event, bool)
        # bool specifies whether Event should be sent to server
        if sys.stdin in rl:
            return (read_stdin(raw_input()), True)
        elif locsrv in rl:
            return (read_tcp(locsrv.recv(MAX_RECV).strip()), False)
    return (None, False)


def loop():
    quit = False
    while not quit:
        try:
            event, outbound = listen()
        except ConnectionError:
            log('Connection closed by remote party.')
            quit = True
        else:
            if event is not None:
                log('Event of type', event.type)
                if outbound:
                    log('Sending to server')
                    locsrv.send(event.encode())

if __name__ == '__main__':
    if locsrv:
        try:
            loop()
        except KeyboardInterrupt:
            locsrv.close()
        finally:
            log('Exiting.')

# vim: ts=8 et sw=4 sts=4 
