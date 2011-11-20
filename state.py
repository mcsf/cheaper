#!/usr/bin/env python

from enum import Enum

client = Enum([
    'main_init',
    'main_connected',
    'main_auth_u',
    'main_auth_d',
    'main_auth_s',
    'main_ready',

    'upd_wait',
    'upd_loop',

    'dwn_wait',
    'dwn_recv',

    'syn_wait',
    'syn_wait_quit',
])

server = Enum([
    'main_init',
    'main_anonymous',
    'main_ready',

    'dwn_gather',

    'syn_wait',

    'dwn_aux_gather',
])


# vim: ts=8 et sw=4 sts=4 
