#!/usr/bin/env python

import os
import select
import socket
import threading

import utils
from event import Event
from exception import ConnectionError
from state import server


# SETTINGS #############################################################

MAX_RECV    = 512
SERVER_PORT = 8888


# MISC #################################################################

def log(*msg):
    global log_lock
    log_lock.acquire()
    utils.log('[main server %s]' % os.getpid())
    utils.log(*msg)
    log_lock.release()


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

log_lock = threading.Lock()
thr_no = 1 # global counter for server threads

c_tcp  = sock_tcp('', SERVER_PORT) # For incoming client PDUs
#c_udp  = sock_udp('', SERVER_PORT) # For incoming server PDUs


# SERVER THREADS #######################################################

class ClientHandler(threading.Thread):
    def __init__(self, channel, client):
        global thr_no
        self.count   = thr_no
        self.strid   = '[handler %s, client %s]' % (thr_no, client)
        self.channel = channel
        self.client  = client
        self.state   = server.main_init
        thr_no += 1
        threading.Thread.__init__(self)

    def listen(self):
        rl, _, _ = select.select([self.channel], [], [])
        if rl:
            if self.channel in rl:
                return self.read(self.channel.recv(MAX_RECV).strip())

    def log(self, *msg):
        global log_lock
        log_lock.acquire()
        utils.log(self.strid)
        utils.log(*msg)
        log_lock.release()

    def read(self, s):
        if not s:
            raise ConnectionError
        try:
            e = Event(decode=s)
            if e.type is not None: return e
        except Exception, e:
            self.log('---')
            raise e
            self.log('Recv malformed data:', s)
            self.log(e)

    def run(self):
        self.log('Handling connections from client', self.client)
        quit = False
        while not quit:
            try:
                event = self.listen()
            except ConnectionError:
                quit = True
            else:
                if event is not None:
                    log('Event of type', event.type)


class ServerHandler(threading.Thread):
    pass # this will eventually handle UDP stuff

# MAIN #################################################################

if __name__ == '__main__':
    if c_tcp:
        while True:
            new_chan, new_client = c_tcp.accept()
            ClientHandler(new_chan, new_client).start()
            log('Accepted new connection.')


# vim: ts=8 et sw=4 sts=4 
