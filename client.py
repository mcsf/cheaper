#!/usr/bin/env python

import select
import socket
import sys
import time
import threading

from commands import *
from event import Event
from exception import ConnectionError
from pdu import pdu
from state import client
from utils import *


# SETTINGS #############################################################

DEBUG    = True
MTU      = 1024
MDB      = 'mDBs.dat'
DEF_USER = 'guest'
DEF_PASS = 'guest'
DEF_SERV = 'S1'
FILE_DIR = 'files'

# Timeouts
T_SYNCH  = 3


# DEBUG ################################################################

def LOG(*msg):
    if DEBUG: log(*msg)


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
        LOG('---')
        LOG('Recv malformed data:', s)
        LOG(e)


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

# Timers
t_synch = None


# WORKER THREADS #######################################################

class FileUploader(threading.Thread):
    def __init__(self, channel, fpath):
        threading.Thread.__init__(self)
        self.channel = channel
        self.fpath   = fpath

    def run(self):
        with open(FILE_DIR + '/' + self.fpath, 'r') as f:
            e = Event(pdu.cUpdSending)
            e["file"] = self.fpath
            while True:
                message=e.read_data_and_encode(f, MTU)
                if len(message) > 0:
                    self.channel.send(message)
                    continue

                e = Event(pdu.cUpdFinished)
                e["file"] = self.fpath
#######INCOMPLETE

                #chunk = f.read(siz)
                #print repr(chunk)
                #if not chunk: break
                #e = Event(pdu.cUpdSending, chunk)
                self.channel.send(e.encode())
            self.channel.send(Event(pdu.cUpdSendDone).encode())
        # a_updOK(...)


class FileDowloader(threading.Thread):
    pass


# MAIN #################################################################

def checkargs():
    argn = len(sys.argv)

    i = 1 if (argn > 1 and sys.argv[1] == '/v') else 0
    return (
        sys.argv[1+i] if argn > 1+i else DEF_USER,
        sys.argv[2+i] if argn > 2+i else DEF_PASS,
        sys.argv[3+i] if argn > 3+i else DEF_SERV,
        bool(i)) # fourth value is verbose switch

def listen():
    rl, _, _ = select.select([sys.stdin, locsrv], [], [])
    if rl:
        if sys.stdin in rl:
            return read_stdin(raw_input())
        elif locsrv in rl:
            return read_tcp(locsrv.recv(MTU).strip())

def loop():
    global quit
    quit = False

    while not quit:
        LOG('STAT', state)
        try:
            in_event = listen()
        except ConnectionError:
            log('Connection closed by remote party.')
            quit = True
        else:
            if in_event is not None:
                LOG('RECV', in_event.type)
                out_event = process(in_event)
                if out_event is not None:
                    LOG('SEND', out_event.type)
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
            state  = client.main_auth_d
            s_data = d
            data = { 'user': user, 'passwd': passwd }
            return Event(pdu.cAuth, data)

        elif event.type == pdu.iSynch:
            state  = client.main_auth_s
            s_data = d
            data = { 'user': user, 'passwd': passwd }
            return Event(pdu.cAuth, data)

        elif event.type == pdu.iQuit:
            quit = True
            return
    # }}}

    elif state == client.main_auth_u: # {{{
        if event.type == pdu.sAuthOK:
            state = client.upd_wait
            shop  = s_data['shop']
            query = s_data['queries'][0]
            return Event(pdu.cUpdate, [shop] + query)

        elif event.type == pdu.sAuthErr:
            quit = True
            a_authErr(d)
            return
    # }}}

    elif state == client.main_auth_d: # {{{
        if event.type == pdu.sAuthOK:
            state = client.dwn_wait
            return Event(pdu.cDownload, s_data)

        elif event.type == pdu.sAuthErr:
            quit = True
            a_authErr(d)
            return
    # }}}

    elif state == client.main_auth_s: # {{{
        if event.type == pdu.sAuthOK:
            state = client.syn_wait
            a_synSetTimeout(d)
            return Event(pdu.cSynch, s_data)

        elif event.type == pdu.sAuthErr:
            quit = True
            a_authErr(d)
            return
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

        elif event.type == pdu.iSynch:
            state = client.syn_wait
            a_synSetTimeout(d)
            return Event(pdu.cSynch, d)

        elif event.type == pdu.iQuit:
            quit = True
            return
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

    elif state == client.dwn_recv: # {{{
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
    # }}}

    elif state == client.syn_wait: # {{{
        if event.type == pdu.sSynOK:
            t_synch.cancel()
            state = client.main_ready
            a_synOK(d)
            return

        elif event.type == pdu.iQuit:
            state = client.syn_wait_quit
            a_synWait(d)
            return
    # }}}

    elif state == client.syn_wait_quit: # {{{
        if event.type == pdu.sSynOK:
            quit = True
            t_synch.cancel()
            return
    # }}}


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

def a_authErr(d):
    log('Authentication error: user \'%s\'.' % user)

def a_updOK(d):
    log('Update OK')

def a_updErr(d):
    log('Update error.')

def a_updSend(d):
    global s_data
    log('Sending file', s_data['queries'][0][1])

def a_dwnOK(d):
    if d:
        log('Report follows:')
        for item in d:
            log('Item %s costs at least %s.' % (item[1], item[3]))
    else:
        log('No results found.')

def a_synOK(d):
    log('Synch OK. Found culprit to be user', d)

def a_synWait(d):
    log('Wait for Synch to end.')

def a_synTimeout():
    global state, quit, locsrv, verbose
    if verbose: log('Synch timeout.')
    if state == client.syn_wait_quit:
        quit = True
        locsrv.shutdown(socket.SHUT_RD)
    else:
        state = client.main_ready
        LOG('STAT', state)

def a_synSetTimeout(d):
    global t_synch
    t_synch = threading.Timer(T_SYNCH, a_synTimeout)
    t_synch.start()

########################################################################


if __name__ == '__main__':

    # Process and get arguments
    user, passwd, srvId, verbose = checkargs()

    # Make a dictionary of existing servers
    servers = {}
    with open(MDB, 'r') as f:
        for line in f.readlines():
            tokens = line.split()
            if len(tokens) != 3:
                if len(tokens) == 0: continue
                LOG("Ignored line in " + MDB + ": " + line)
                continue
            s, h, p = [x.strip() for x in tokens]
            servers[s] = (h, int(p))

    # Dictionary of active connections to servers
    connections = {}
    
    # Initialize the connection to the local server
    try:
        locsrv = connection(*servers[srvId])
    except KeyError:
        raise Exception("Invalid local server ID.")
    
    connections[srvId] = locsrv
    
    if locsrv:
        state = client.main_connected
        try:
            loop()
        except KeyboardInterrupt:
            locsrv.close()
        finally:
            log('Exiting.')


# vim: ts=8 et sw=4 sts=4 fen fdm=marker
