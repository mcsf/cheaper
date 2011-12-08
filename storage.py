#!/usr/bin/env python

import sqlite3

class DB:
    def __init__(self, fpath):
	self.con = sqlite3.connect(fpath)
	self.cur = self.con.cursor()
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
            VARCHAR(20), price NUMERIC(10,2), author VARCHAR(20), PRIMARY KEY
            (store, item));
        '''
        self.cur.execute(query)

    def insert(self, store, item, fpath, price, author, replace=False):
        if not fpath: fpath = ''
        statement = 'REPLACE' if replace else 'INSERT'
        query = '''
            %s INTO data VALUES ('%s', '%s', '%s', %s, '%s')
        ''' % (statement, store, item, fpath, price, author)
        self.cur.execute(query)
        self.con.commit()

    def update(self, store, item, fpath, price, author):
        return self.insert(store, item, fpath, price, author, True)

    def remove(self, **args):
        if 'item' not in args:
            raise Exception('Missing keyword \'item\'')

        query = '''
            DELETE FROM data WHERE item = '%s' 
        ''' % args['item']

        if 'store' in args:
            query += '''AND store = '%s' ''' % args['store']

        self.cur.execute(query)
        self.con.commit()

    def get(self, key=None, value=None):
        query = 'SELECT * FROM data '
        if key and value:
            query += '''WHERE %s = '%s';''' % (key, value)
        self.cur.execute(query)
        return self.cur.fetchall()


class Cache(DB):
    def __init__(self):
        DB.__init__(self, ':memory:')


# vim: ts=8 et sw=4 sts=4 
