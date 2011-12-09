#!/usr/bin/env python

import select
import socket
import sys
import time

from commands import *
from event import Event
from exception import ConnectionError
from pdu import pdu
from state import client
from utils import *


# SETTINGS #############################################################

MAX_RECV = 512
MDB      = 'mDBs.dat'
DEF_USER = 'guest'
DEF_PASS = 'guest'
DEF_SERV = 'S1'


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
s_data = None # State related data (see: transition from auth_u to wait)


# MAIN #################################################################

def checkargs():
    argn = len(sys.argv)

    i = 1 if (argn > 1 and sys.argv[1] == '/v') else 0
    return (
        sys.argv[1+i] if argn > 1+i else DEF_USER,
        sys.argv[2+i] if argn > 2+i else DEF_PASS,
        sys.argv[3+i] if argn > 3+i else DEF_SERV,
        bool(i)) # fourth value is verbose switch

def getServer(srvId):
    with open(MDB, 'r') as f:
        for line in f.readlines():
            fields = line.split()
            if fields[0] == srvId:
                return (fields[1], int(fields[2]))

def listen():
    rl, _, _ = select.select([sys.stdin, locsrv], [], [])
    if rl:
        if sys.stdin in rl:
            return read_stdin(raw_input())
        elif locsrv in rl:
            return read_tcp(locsrv.recv(MAX_RECV).strip())

def loop():
    global quit
    quit = False

    while not quit:
        log('STAT', state)
        try:
            in_event = listen()
        except ConnectionError:
            log('Connection closed by remote party.')
            quit = True
        else:
            if in_event is not None:
                log('RECV', in_event.type)
                out_event = process(in_event)
                if out_event is not None:
                    log('SEND', out_event.type)
                    locsrv.send(out_event.encode())

def process(event):
    global state, s_data, quit
    d = event['data']

    if state == client.main_connected: # {{{
        if event.type == pdu.iUpdate:
            state  = client.main_auth_u
            s_data = d
            data = { 'user': user, 'passwd': passwd }
            return Event(pdu.cAuth, data)

        elif event.type == pdu.iDownload:
            state  = client.main_auth_u
            s_data = d
            data = { 'user': user, 'passwd': passwd }
            return Event(pdu.cAuth, data)

        elif event.type == pdu.iSynch:
            state  = client.main_auth_u
            s_data = d
            data = { 'user': user, 'passwd': passwd }
            return Event(pdu.cAuth, data)

        elif event.type == pdu.iQuit:
            quit = True
    # }}}

    elif state == client.main_auth_u: # {{{
        if event.type == pdu.sAuthOK:
            state = client.upd_wait
            shop  = s_data['shop']
            query = s_data['queries'][0]
            return Event(pdu.cUpdate, [shop] + query)
    # }}}

    elif state == client.main_auth_d: # {{{
        if event.type == pdu.sAuthOK:
            state = client.dwn_wait
            return Event(pdu.cDownload, s_data)
    # }}}

    elif state == client.main_auth_s: # {{{
        pass
    # }}}

    elif state == client.main_ready: # {{{
        if event.type == pdu.iUpdate:
            state  = client.upd_wait
            s_data = d
            shop   = s_data['shop']
            query  = s_data['queries'][0]
            return Event(pdu.cUpdate, [shop] + query)

        elif event.type == pdu.iDownload:
            state = client.dwn_wait
            return Event(pdu.cDownload, d)
    # }}}

    elif state == client.upd_wait: # {{{
        if event.type == pdu.sUpdOK:
            if p_updFile(d):
                a_updSend(d)
            if p_updRem(d):
                shop  = s_data['shop']
                query = s_data['queries'][0]
                return Event(pdu.cUpdate, [shop] + query)
            else:
                a_updOK(d)
                state = client.main_ready
                return

        elif event.type == pdu.sUpdErr:
            a_updErr(d)
            state = client.main_ready
            return
    # }}}

    elif state == client.dwn_wait: # {{{
        if event.type == pdu.sDwnInfo:
            if p_dwnFile(d):
                # connect to some server for file retrieval
                # ...
                state = client.dwn_recv
                return Event(pdu.cDwnFile)
            else:
                a_dwnOK(d)
                state = client.main_ready
                return
    # }}}

    elif state == client.dwn_recv:
        if event.type == pdu.sDwnFile:
            # close connection to file server
            # ...
            a_dwnOK(d)
            state = client.main_ready
            return

        elif event.type == pdu.sDwnFileErr:
            # close connection to file server
            # ...
            a_dwnErr(d)
            state = client.main_ready
            return

        elif event.type == 'foo':
            # TODO: event signaling a connection closed by file server
            state = client.main_ready
            return

        elif event.type == 'foo':
            # TODO: event signaling a timeout from file server
            state = client.main_ready
            return


# PREDICATES ###########################################################

# TODO: actually transfer or keep old one
def p_updFile(d):
    return bool(s_data['queries'][0][1])

def p_updRem(d):
    global s_data
    s_data['queries'].pop(0)
    return bool(s_data['queries'])

def p_dwnFile(d):
    pass

# ACTIONS ##############################################################

def a_updOK(d):
    log('Update OK')

def a_updErr(d):
    log('Update error.')

def a_updSend(d):
    global s_data
    log('Sending file', s_data['queries'][0][1])

def a_dwnOK(d):
    log('Download OK')

########################################################################


if __name__ == '__main__':

    # Process and get arguments
    user, passwd, srvId, verbose = checkargs()

    # Connect to server
    try:
        host, port = getServer(srvId)
    except TypeError:
        raise Exception('Unknown server ID.')
    else:
        locsrv = connection(host, port)

    if locsrv:
        state = client.main_connected
        try:
            loop()
        except KeyboardInterrupt:
            locsrv.close()
        finally:
            log('Exiting.')


# vim: ts=8 et sw=4 sts=4 fen fdm=marker
