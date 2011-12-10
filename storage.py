#!/usr/bin/env python

import sqlite3

class DB:

    # Indices for table columns
    STORE, ITEM, FPATH, PRICE, USER = range(5)

    def __init__(self, fpath, lock):
        self.con  = sqlite3.connect(fpath, check_same_thread=False)
        self.cur  = self.con.cursor()
        self.lock = lock
        if self.isEmpty(): self._setup()

    def close(self):
        self.con.close()

    def isEmpty(self):
        query = '''
            SELECT name FROM sqlite_master WHERE type='table' AND
            name='data';
        '''
        self.cur.execute(query)
        return len(self.cur.fetchall()) == 0

    def _setup(self):
        query = '''
            CREATE TABLE data (store TEXT, item TEXT, fpath
            TEXT, price NUMERIC, user TEXT, PRIMARY KEY
            (store, item));
        '''
        self.lock.acquire()
        self.cur.execute(query)
        self.lock.release()

    def insert(self, store, item, fpath, price, user, replace=False):
        if not fpath: fpath = ''
        statement = 'REPLACE' if replace else 'INSERT'
        query = '''
            %s INTO data VALUES ('%s', '%s', '%s', %s, '%s')
        ''' % (statement, store, item, fpath, price, user)
        self.lock.acquire()
        self.cur.execute(query)
        self.con.commit()
        self.lock.release()

    def update(self, store, item, fpath, price, user):
        return self.insert(store, item, fpath, price, user, True)

    def remove(self, **args):
        if 'item' not in args:
            raise Exception('Missing keyword \'item\'')

        query = '''
            DELETE FROM data WHERE item = '%s' 
        ''' % args['item']

        if 'store' in args:
            query += '''AND store = '%s' ''' % args['store']

        self.lock.acquire()
        self.cur.execute(query)
        self.con.commit()
        self.lock.release()

    def _get(self, key=None, value=None):
        query = 'SELECT * FROM data '
        if key and value:
            query += '''WHERE %s = '%s';''' % (key, value)
        self.lock.acquire()
        self.cur.execute(query)
        r = self.cur.fetchall()
        self.lock.release()
        return r

    def get(self, store, item):
        query = '''
            SELECT * FROM data WHERE store = '%s' AND item = '%s';
        ''' % (store, item)
        self.lock.acquire()
        self.cur.execute(query)
        r = self.cur.fetchall()
        self.lock.release()
        return r


class Cache(DB):
    def __init__(self, lock):
        DB.__init__(self, ':memory:', lock)


# vim: ts=8 et sw=4 sts=4 
