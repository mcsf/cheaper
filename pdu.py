#!/usr/bin/env python

from enum import Enum

pdu = Enum([
    'iUpdate',
    'iDownload',
    'iSynch',
    'iQuit',

    'cAuth',
    'sAuthOK',
    'sAuthErr',

    'cUpdate',
    'sUpdOK',
    'sUpdErr',
    'cSending',
    'cSendDone',

    'cDownload',
    'sDwnInfo',
    'cDwnFile',
    'sDwnFile',
    'sDwnFileDone',
    'sDwnFileErr',
    'sDwnRqst',
    'sDwnResp',

    'cSynch',
    'sSynOK',
    'sSynRqst',
    'sSynResp',
])


# vim: ts=8 et sw=4 sts=4 
