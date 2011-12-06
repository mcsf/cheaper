#!/usr/bin/env python

import os
import select
import socket

import utils
from event import Event
from exception import ConnectionError
from state import server

# SETTINGS #############################################################

MAX_RECV    = 512
SERVER_PORT = 8888


# INPUT PROCESSING #####################################################

def log(*msg):
    pid = os.getpid()
    ident = '[main server %s]' % pid
    try:
        if client:
            ident = '[server %s, client %s]' % (pid, client)
    except NameError:
        pass

    utils.log(ident)
    utils.log(*msg)

def read_tcp(s):
    if not s:
        raise ConnectionError
    try:
        e = Event(decode=s)
        if e.type is not None: return e
    except Exception, e:
        log('---')
        raise e
        log('Recv malformed data:', s)
        log(e)

def read_udp(s):
    pass

# TCP ##################################################################

def sock_tcp(h, p):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind((h, p))
        s.listen(0)
    except Exception, e:
        log(e)
        return False
    else:
        log('Server listening.')
    return s

def sock_udp(h, p):
    return socket.socket(socket.AF_INET, socket.SOCK_DGRAM)


# GLOBALS ##############################################################

state  = server.main_init
c_tcp  = sock_tcp('', SERVER_PORT) # For incoming client PDUs
c_udp  = sock_udp('', SERVER_PORT) # For incoming server PDUs
client = None


# MAIN #################################################################

def listen():
    rl, _, _ = select.select([c_tcp, c_udp], [], [])
    if rl:
        if c_tcp in rl:
            return read_tcp(c_tcp.recv(MAX_RECV).strip())
        elif c_udp in rl:
            pass

def loop():
    quit = False
    while not quit:
        try:
            event = listen()
        except ConnectionError:
            quit = True
        else:
            if event is not None:
                log('Event of type', event.type)

if __name__ == '__main__':
    if c_tcp:
#       try:
            while True:
                new_conn, new_client = c_tcp.accept()
                pid = os.fork()
                if pid == 0:
                    c_tcp, client = new_conn, new_client
                    log('Handling connections from client', client)
                    break
                log('Accepted new connection')
#       except KeyboardInterrupt:
#           c_tcp.close()
#       else:
            loop()
#       finally:
            log('Exiting.')


# vim: ts=8 et sw=4 sts=4 
