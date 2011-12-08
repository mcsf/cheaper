#!/usr/bin/env python

import os
import select
import socket
import sys
import threading

import utils
from event import Event
from exception import ConnectionError
from pdu import pdu
from state import server


# SETTINGS #############################################################

SERVER_PORT = 8888
MAX_RECV    = 512
MDB         = 'mDBs.dat'
SHOPS       = 'Shops.dat'
USERS       = 'Users.dat'


# MISC #################################################################

def checkargs():
    argn = len(sys.argv)
    if argn != 4:
        raise Exception('Expected 3 arguments, got %s.' % str(argn - 1))
    else:
        return (int(sys.argv[1]), sys.argv[2], sys.argv[3])


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


# SERVER THREADS #######################################################

class ClientHandler(threading.Thread):
    def __init__(self, channel, client):
        global thr_no
        self.count   = thr_no
        self.strid   = '[handler %s, client %s]' % (thr_no, client)
        self.channel = channel
        self.client  = client
        self.state   = server.main_anonymous
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

    def process(self, event):
        self.log('Processing event:', event)
        if   self.state == server.main_anonymous:
            if  event.type == pdu.cAuth:
                if self.p_sAuthOK(event['data']):
                    self.state = server.main_ready
                    return Event(pdu.sAuthOK)
                else:
                    self.quit = True

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

    def write(self, e):
        self.channel.send(e.encode())

    def run(self):
        self.log('Handling connections from client', self.client)
        self.quit = False
        while not self.quit:
            self.log('Waiting in state', self.state)
            try:
                in_event = self.listen()
            except ConnectionError:
                self.quit = True
            else:
                if in_event is not None:
                    self.log('Inbound event of type', in_event.type)
                    out_event = self.process(in_event)
                    if out_event is not None:
                        self.log('Outbound event of type', out_event.type)
                        self.write(out_event)
        self.log('Thread closing.')
        self.channel.close()


    # Predicates
    def p_sAuthOK(self, data):
        user   = data['user']
        passwd = data['passwd']

        with open(USERS, 'r') as f:
            for line in f.readlines():
                u, p = line.split()
                if user == u and passwd == p:
                    return True
            return False


class ServerHandler(threading.Thread):
    pass # this will eventually handle UDP stuff

# MAIN #################################################################

if __name__ == '__main__':

    # Process and get arguments
    port, shops, users = checkargs()

    # Start listening
    c_tcp  = sock_tcp('', port) # For incoming client PDUs
    #c_udp  = sock_udp('', port) # For incoming server PDUs

    if c_tcp:
        while True:
            new_chan, new_client = c_tcp.accept()
            ClientHandler(new_chan, new_client).start()
            log('Accepted new connection.')


# vim: ts=8 et sw=4 sts=4 
