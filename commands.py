#!/usr/bin/env python

import re

import event
from pdu import pdu
from utils import log

def update(args):

    shop, queries = args.partition(':')[::2]
    if not queries:
        log('Syntax: L1: Ai[-Fi.pdf]/Pi; [Aj/Pj; ...]')
        return

    pat = ( r'\s*'
        + r'(\w*)'          # Ai [match group 1]
        + r'(-(\w*.\w*))?'  # [-i.pdf] (optional) [mg 2, 3]
        + r'\s*/\s*'        # / (and whitespace)
        + r'(\d*)'          # iPrice [mg 4]
        + r'\s*;\s*'        # ; (and whitespace)
    )

    data = []
    for q in re.finditer(pat, queries):
        item  = q.group(1)
        fpath = q.group(3)
        price = q.group(4)
        log('Read: UPDATE shop=%s item=%s fpath=%s price=%s'
                % (shop, item, fpath, price))
        data.append((shop, item, fpath, price))

    return event.Event(pdu.iUpdate, data)


def download(args):
    log("Read: DOWNLOAD", args.split())

def synch(args):
    log("Read: SYNCH", args.split())

def quit(args):
    log("Read: QUIT", args.split())

commands = {
    'update'   : update,
    'download' : download,
    'synch'    : synch,
    'quit'     : quit,
}

# vim: ts=8 et sw=4 sts=4 
