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
    'cUpdSending',
    'cUpdSendDone',

    'cDownload',
    'sDwnInfo',
    'cDwnFile',
    'sDwnFile',
    'sDwnFileErr',
    'sDwnRqst',
    'sDwnResp',

    'cSynch',
    'sSynOK',
    'sSynRqst',
    'sSynResp',
])


# vim: ts=8 et sw=4 sts=4 
