#!/usr/bin/env python

import sqlite3

class DB:
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
            CREATE TABLE data (store VARCHAR(20), item VARCHAR(20), fpath
            VARCHAR(20), price NUMERIC(10,2), user VARCHAR(20), PRIMARY KEY
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

    def get(self, key=None, value=None):
        query = 'SELECT * FROM data '
        if key and value:
            query += '''WHERE %s = '%s';''' % (key, value)
        self.lock.acquire()
        self.cur.execute(query)
        self.lock.release()
        return self.cur.fetchall()


class Cache(DB):
    def __init__(self, lock):
        DB.__init__(self, ':memory:', lock)


# vim: ts=8 et sw=4 sts=4 
