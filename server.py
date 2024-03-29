#!/usr/bin/env python

import os
import Queue
import select
import socket
import sys
import time
import threading

import utils
from event import Event
from exception import ConnectionError
from pdu import pdu
from state import server
from storage import DB, Cache


# SETTINGS #############################################################

DEBUG       = True
DB_FILE     = 'data.db'
SERVER_PORT = 8888
MAX_RECV    = 1024
MDB         = 'mDBs.dat'
SHOPS       = 'Shops.dat'
USERS       = 'Users.dat'

# Timeouts
T_DOWNLOAD  = 3
T_SYNCH     = 3


# MISC #################################################################

def checkargs():
    argn = len(sys.argv)
    return (
        int(sys.argv[1]) if argn > 1 else SERVER_PORT,
        sys.argv[2] if argn > 2 else SHOPS,
        sys.argv[3] if argn > 3 else USERS)

def log(*msg):
    global log_lock
    log_lock.acquire()
    utils.log('[main server %s]' % os.getpid(), *msg)
    log_lock.release()


# TCP ##################################################################

def sock_tcp(h, p):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
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
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind((h, p))
    return s


# GLOBALS ##############################################################

log_lock = threading.Lock()
thr_no   = 0
db       = DB(DB_FILE, threading.Lock())
cache    = Cache(threading.Lock())
outgoing = Queue.Queue() # UDP stuff to send out
pending  = {} # a dict of Queue objects


# SERVER THREADS #######################################################

class ClientHandler(threading.Thread):
    def __init__(self, channel, client):
        global thr_no
        thr_no += 1

        threading.Thread.__init__(self)
        self.daemon  = True
        self.thr_no  = thr_no
        self.strid   = '[handler %s]' % thr_no
        self.channel = channel
        self.client  = client
        self.state   = server.main_anonymous
        self.user    = None

    def listen(self):
        rl, _, _ = select.select([self.channel], [], [])
        if rl:
            if self.channel in rl:
                return self.read(self.channel.recv(MAX_RECV).strip())

    def log(self, *msg):
        if not DEBUG: return
        global log_lock
        log_lock.acquire()
        utils.log(self.strid, *msg)
        log_lock.release()

    def process(self, event):
        d = event['data']
        self.log('Processing event:', event)

        if self.state == server.main_anonymous: # {{{
            if event.type == pdu.cAuth:
                if self.p_sAuthOK(d):
                    self.state = server.main_ready
                    return Event(pdu.sAuthOK)
                else:
                    self.quit = True
                    return Event(pdu.sAuthErr)
        # }}}

        elif self.state == server.main_ready: # {{{
            if event.type == pdu.cUpdate:
                if self.p_updShopOK(d) and self.p_updValueOK(d):
                    if self.p_updFile(d):
                        self.a_updRecvFile(d)
                    # Table structure is (store, item, fpath, price, user)
                    db.update(*(d + [self.user]))
                    return Event(pdu.sUpdOK)
                else:
                    return Event(pdu.sUpdErr)


            elif event.type == pdu.cDownload:

                shops, bests = self.p_dwnHasInfo(d)

                if bests:
                    # Local server has all the info it needs and immediately
                    # replies to client
                    return Event(pdu.sDwnInfo, bests)

                else:

                    self.log('DWN shops, bests =', shops, bests)

                    items   = d['items']
                    horizon = [s for s in servers.keys() if
                                self.p_dwnServerUseful(s, shops)]

                    self.log('DWN items, horizon =', items, horizon)

                    # Generate Queue to communicate with ServerHandlers
                    pending[self.thr_no] = Queue.Queue()

                    for item in items:
                        shopsvisited = []

                        rqst = Event(pdu.sDwnRqst, (self.thr_no, item, shops))

                        for s in horizon:
                            # Skip if we have enough data
                            if self.p_dwnSkipServer(s, shopsvisited):
                                continue

                            # Send request to server
                            dst = servers[s]
                            outgoing.put((rqst, dst))

                            # Wait for a reply
                            try:
                                resp = pending[self.thr_no].get(True, T_DOWNLOAD)
                            # Or timeout and move on to next server
                            except Queue.Empty:
                                continue
                            # Handle response data
                            else:
                                _, best = resp['data']
                                self.log('DWN RECV best =', best)
                                if best:
                                    cache.update(*best)
                                    shopsvisited.insert(0, shop)

                    # Go through newly added data and return best prices to
                    # client
                    _, bests = self.p_dwnHasInfo(d, True)
                    return Event(pdu.sDwnInfo, bests)


            elif event.type == pdu.cSynch:
                # Get data
                shop, item, fpath, p1, p2 = d

                # Generate Request event for other servers
                rqst = Event(pdu.sSynRqst,
                        [self.thr_no, shop, item, p1, p2, self.user])

                # Queue through which ServerHandlers will signal their completion
                pending[self.thr_no] = Queue.Queue()

                # Send out the requests
                for s, dst in servers.items():
                    outgoing.put((rqst, dst))

                try:
                    # Wait for *any* result to arrive to the queue or timeout
                    resp = pending[self.thr_no].get(True, T_SYNCH)
                except Queue.Empty:
                    # no server replied.
                    self.log('Synch timeout')
                else:
                    _, user = resp['data']
                    self.log('Forwarding', resp.type)
                    return Event(pdu.sSynOK, user)

        # }}}


    # Predicates
    def p_sAuthOK(self, d):
        self.user  = d['user']
        self.strid = '[handler %s, client %s]' % (thr_no, self.user)
        return users.get(d['user']) == d['passwd']

    def p_updShopOK(self, d):
        return d[0] in localshops

    def p_updValueOK(self, d):
        return type(d[3]) in [float, int]

    def p_updFile(self, d):
        return bool(d[2])

    def p_dwnHasInfo(self, d, ignoreerrors=False):
        items = d['items']
        shops = d['shops'] or allshops
        bests = []

        for item in items:

            info = []
            for shop in shops:
                found = False
                fetches = [db.get(shop, item), cache.get(shop, item)]
                for f in fetches:
                    if f:
                        info.insert(0, f[0])
                        found = True
                if not found and not ignoreerrors:
                    return shops, None

            self.log('DWN INFO', info)

            if not info: return shops, None

            # Select cheapest item
            best = info[0]
            for i in info:
                if i[db.PRICE] < best[db.PRICE]:
                    best = i
            bests.insert(0, best)

        return shops, bests

    def p_dwnServerUseful(self, s, shops):
        for shop in servershops[s]:
            if shop in shops:
                return True
        return False

    def p_dwnSkipServer(self, s, v):
        for shop in servershops[s]:
            if shop not in v:
                return False
        return True


    # Actions
    def a_updRecvFile(self, d):
        pass


    def read(self, s):
        if not s:
            raise ConnectionError
        try:
            e = Event(decode=s)
            if e.type is not None: return e
        except Exception:
            self.log('WARN Recv malformed data:', s)

    def write(self, e):
        self.channel.send(e.encode())

    def run(self):
        self.log('Handling connections from client', self.client)
        self.quit = False
        while not self.quit:
            self.log('STAT', self.state)
            try:
                in_event = self.listen()
            except ConnectionError:
                self.quit = True
            else:
                if in_event is not None:
                    self.log('RECV', in_event.type)
                    out_event = self.process(in_event)
                    if out_event is not None:
                        self.log('SEND', out_event.type)
                        self.write(out_event)
        self.log('Thread closing.')
        if self.thr_no in pending: # Cleanup
            pending.pop(self.thr_no)
        self.channel.close()


class ServerHandler(threading.Thread):
    def __init__(self, rqst, dst, queue):
        global thr_no
        thr_no += 1

        threading.Thread.__init__(self)
        self.strid   = '[udp-handler %s]' % thr_no
        self.rqst    = rqst
        self.dst     = dst
        self.queue   = queue
        self.daemon  = True

    def log(self, *msg):
        if not DEBUG: return
        utils.log(self.strid, *msg)

    def write(self, s):
        self.queue.put((s, self.dst))

    def run(self):
        d = self.rqst['data']
        self.log('RECV %s FROM %s' % (self.rqst.type, self.dst))

        if self.rqst.type == pdu.sDwnRqst:
            thr_no, item, shops = d
            # Get pricing info from DB and cache
            info = []
            for shop in shops:
                found = False
                fetches = [db.get(shop, item), cache.get(shop, item)]
                for f in fetches:
                    if f:
                        info.insert(0, f[0])
                        found = True
                if not found:
                    self.write(Event(pdu.sDwnResp, (thr_no, None)))
                    return
            # Determine store offering best price
            best = info[0]
            for i in info:
                if i[db.PRICE] < best[db.PRICE]:
                    best = i
            # Return that information
            self.write(Event(pdu.sDwnResp, (thr_no, best)))
            return

        elif self.rqst.type == pdu.sDwnResp:
            thr_no, _ = d
            pending[thr_no].put(self.rqst)
            return

        elif self.rqst.type == pdu.sSynRqst:
            thr_no, store, item, p1, p2, new_user = d
            entries = db.get(store, item)
            # (store, item) form a primary key, so 'entries' can only have 0 or
            # 1 elements. Using a 'for' is just syntactic sugar addiction.
            for e in entries:
                # if the mistake is found in the DB
                if e[db.PRICE] == p1:
                    # find its culprit
                    old_user = e[db.USER]
                    # fix the DB entry
                    db.update(store, item, e[db.FPATH], p2, new_user)
                    # forward the culprit's username:
                    self.write(Event(pdu.sSynResp, [thr_no, old_user]))
                    return

        elif self.rqst.type == pdu.sSynResp:
            thr_no, user = d
            pending[thr_no].put(self.rqst)
            return


class UDPListener(threading.Thread):
    def __init__(self, channel, lock, queue):
        threading.Thread.__init__(self)
        self.daemon  = True
        self.channel = channel
        self.lock = lock
        self.queue = queue

    def read(self, data, src):
        if not data: raise ConnectionError
        try:
            e = Event(decode=data)
        except Exception:
            self.log('WARN Recv malformed data:', s)
        else:
            if e.type is not None: return (e, src)

    def log(self, *s):
        if not DEBUG: return
        utils.log('[udp-main]', *s)

    def listen(self):
        rl, _, _ = select.select([self.channel], [], [])
        if rl:
            if self.channel in rl:
                self.lock.acquire()
                data, src = self.channel.recvfrom(MAX_RECV)
                self.lock.release()
                return self.read(data, src)

    def run(self):
        while True:
            event, src = self.listen()
            if event is not None:
                self.log('RECV', event.type)
                ServerHandler(event, src, self.queue).start()


class UDPDispatcher(threading.Thread):
    def __init__(self, channel, lock, queue):
        threading.Thread.__init__(self)
        self.channel = channel
        self.lock    = lock
        self.queue   = queue
        self.daemon  = True

    def log(self, *msg):
        if not DEBUG: return
        utils.log('[udp-dispatch]', *msg)

    def run(self):
        while True:
            event, src = self.queue.get()
            self.log('Dispatching', event.type)
            self.lock.acquire()
            self.channel.sendto(event.encode(), src)
            self.lock.release()


# MAIN #################################################################

if __name__ == '__main__':

    # Process and get arguments
    port, f_shops, f_users = checkargs()

    allshops = set([])
    servershops = {}
    with open(f_shops, 'r') as f:
        for line in f.readlines():
            p = line.partition(' ')[::2]
            h = p[0]
            s = [i.strip() for i in p[1].split(',')]
            for each in s: allshops.add(each)
            servershops[h] = s

    users = {}
    with open(f_users, 'r') as f:
        for line in f.readlines():
            u, p = line.split()
            users[u] = p

    servers = {}
    with open(MDB, 'r') as f:
        for line in f.readlines():
            s, h, p = [x.strip() for x in line.split()]
            servers[s] = (h, int(p))

    hostname = socket.gethostname()
    srvid, localshops = None, None
    for k, v in servers.items():
        if v[0] == hostname and v[1] == port:
            srvid = k
            break

    try:
        servers.pop(srvid)
        localshops = servershops.pop(srvid)
    except KeyError:
        raise Exception('Missing description for this server\'s hostname'
                + ' in file %s' % MDB)

    # Start listening
    c_tcp  = sock_tcp('', port) # For incoming client PDUs
    c_udp  = sock_udp('', port) # For incoming server PDUs

    if c_udp:
        l = threading.Lock()
        UDPListener(c_udp, l, outgoing).start()
        UDPDispatcher(c_udp, l, outgoing).start()

    if c_tcp:
        while True:
            new_chan, new_client = c_tcp.accept()
            ClientHandler(new_chan, new_client).start()
            if DEBUG: log('Accepted new connection.')


# vim: ts=8 et sw=4 sts=4 fen fdm=marker
