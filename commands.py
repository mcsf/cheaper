#!/usr/bin/env python

from event import Event
from pdu import pdu
from utils import log

def update(args):

    usage = 'Syntax: L1: Ai[-Fi.pdf]/Pi; [Aj/Pj; ...]'

    shop, queries = args.partition(':')[::2]
    if not queries:
        log(usage)
        return

    data = { 'shop' : shop, 'queries': [] }

    queries = queries.split(';')
    for q in queries:
        if not q: break

        item, price = q.strip().partition('/')[::2]
        if not price:
            log(usage)
            log('Price missing for one or more items.')
            return
        try:
            price = float(price)
        except ValueError:
            log(usage)
            log('Item price must be a real number.')
            return
        item, fpath = item.partition('-')[::2]
        log('Read: UPDATE shop=%s item=%s fpath=%s price=%s'
                % (shop, item, fpath, price))
        data['queries'].append([item, fpath, price])

    return Event(pdu.iUpdate, data)


def download(args):

    usage = 'Syntax: [L1[, L2...]]: A1[, A2...]'

    shops, items = args.partition(':')[::2]

    # Replacement needed in case there are no shops found
    if not items:
        shops, items = items, shops

    if not items:
        log(usage)
        return

    data = {
        'shops': [s.strip() for s in shops.split(',')],
        'items': [i.strip() for i in items.split(',')]
    }

    return Event(pdu.iDownload, data)


def synch(args):

    usage = 'Syntax: L1: A1[-file]/P1->P2'

    store, rest = [x.strip() for x in args.partition(':')[::2]]
    if not rest:
        log(usage)
        return

    item, rest = [x.strip() for x in rest.partition('/')[::2]]
    if not rest:
        log(usage)
        return

    item, fpath = item.partition('-')[::2]

    p1, p2 = [x.strip() for x in rest.partition('->')[::2]]
    if not p2:
        log(usage)
        return

    return Event(pdu.iSynch, [store, item, fpath, float(p1), float(p2)])


def quit(args):
    return Event(pdu.iQuit)

commands = {
    'update'   : update,
    'download' : download,
    'synch'    : synch,
    'quit'     : quit,
}

# vim: ts=8 et sw=4 sts=4 
