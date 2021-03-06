#!/usr/bin/env python
#  -*- mode: python; indent-tabs-mode: nil; -*- coding: iso-8859-1 -*-

"""
GutenbergDatabase.py

Copyright 2009-2014 by Marcello Perathoner

Distributable under the GNU General Public License Version 3 or newer.

"""

from __future__ import unicode_literals

import re
import os
import csv
import datetime

import psycopg2
import psycopg2.extensions

psycopg2.extensions.register_type (psycopg2.extensions.UNICODE)
psycopg2.extensions.register_type (psycopg2.extensions.UNICODEARRAY)

from .Logger import debug, critical

DatabaseError  = psycopg2.DatabaseError
IntegrityError = psycopg2.IntegrityError

DB = None

class xl (object):
    """ Translate numeric indices into field names.

    >>> r = xl (cursor, row)
    >>> r.pk
    >>> r['pk']
    >>> r[0]
    """

    def __init__ (self, cursor, row):
        self.row = row
        self.colname_to_index = dict ([(x[1][0], x[0]) for x in enumerate (cursor.description)])

    def __getitem__ (self, column):
        if isinstance (column, int):
            return self.row[column]
        return self.row[self.colname_to_index[column]]

    def __getattr__ (self, colname):
        return self.row[self.colname_to_index[colname]]

    def get (self, colname, default = None):
        """ Get value from field in row. """
        if colname in self.colname_to_index:
            return self.row[self.colname_to_index [colname]]
        return default


def get_connection_params (args = None):
    """ Get connection parameters from environment. """

    if args is None:
        args = {}

    def _get (param):
        """ Get param either from args or environment or config. """
        if param in args:
            return args[param]
        param = param.upper ()
        if param in os.environ:
            return os.environ[param]
        try:
            return getattr (options.config, param)
        except (NameError, AttributeError):
            return None

    host     = _get ('pghost')
    port     = _get ('pgport')
    database = _get ('pgdatabase')
    user     = _get ('pguser')

    params = { 'host': host,
               'port': int (port),
               'database': database,
               'user': user }

    try:
        def matches (s1, s2):
            """ Match literal value or * """
            if s1 == '*':
                return True
            if s1 == s2:
                return True
            return False

        # scan .pgpass for password
        with open ("~/.pgpass", "r") as f:
            for line in f.readlines ():
                # format: hostname:port:database:username:password
                fields = line.split (':')
                if (matches (fields[0], host) and
                    matches (fields[1], port) and
                    matches (fields[2], database) and
                    matches (fields[3], user)):
                    params['password'] = fields[4]
                    break

    except IOError:
        pass

    return params


def get_sqlalchemy_url ():
    """ Build a connection string for SQLAlchemy. """

    params = get_connection_params ()
    return "postgres://%(user)s:%(password)s@%(host)s:%(port)d/%(database)s'" % params


class Database (object):
    """ Class to connect to PG database. """

    def __init__ (self, args = None):
        self.connection_params = get_connection_params (args)
        self.conn = None


    def connect (self):
        """ connect to database """

        try:
            vpncmd = getattr (options.config, 'PGVPNCMD', None)
            vpncmd = os.environ.get ('PGVPNCMD', vpncmd)
            if vpncmd:
                debug ("Starting VPN ...")
                os.system (vpncmd)

            debug ("Connecting to database ...")

            self.conn = psycopg2.connect (**self.connection_params)

            debug ("Connected to host %s database %s." %
                  (self.connection_params['host'],
                   self.connection_params['database']))

        except psycopg2.DatabaseError as what:
            critical ("Cannot connect to database server (%s)" % what)
            raise


    def get_cursor (self):
        """ Return database cursor. """
        return self.conn.cursor ()
