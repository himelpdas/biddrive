#!/bin/env python
# -*- coding: utf-8 -*-

"""
This file is part of the web2py Web Framework
Copyrighted by Massimo Di Pierro <mdipierro@cs.depaul.edu>
License: LGPLv3 (http://www.gnu.org/licenses/lgpl.html)

Thanks to
    * Niall Sweeny <niall.sweeny@fonjax.com> for MS SQL support
    * Marcel Leuthi <mluethi@mlsystems.ch> for Oracle support
    * Denes
    * Chris Clark
    * clach05
    * Denes Lengyel
    * and many others who have contributed to current and previous versions

This file contains the DAL support for many relational databases,
including:
- SQLite
- MySQL
- Postgres
- Oracle
- MS SQL
- DB2
- Interbase
- Ingres
- SapDB (experimental)
- Cubrid (experimental)
- CouchDB (experimental)
- MongoDB (in progress)
- Google:nosql
- Google:sql

Example of usage:

>>> # from dal import DAL, Field

### create DAL connection (and create DB if not exists)
>>> db=DAL(('mysql://a:b@locahost/x','sqlite://storage.sqlite'),folder=None)

### define a table 'person' (create/aster as necessary)
>>> person = db.define_table('person',Field('name','string'))

### insert a record
>>> id = person.insert(name='James')

### retrieve it by id
>>> james = person(id)

### retrieve it by name
>>> james = person(name='James')

### retrieve it by arbitrary query
>>> query = (person.name=='James')&(person.name.startswith('J'))
>>> james = db(query).select(person.ALL)[0]

### update one record
>>> james.update_record(name='Jim')

### update multiple records by query
>>> db(person.name.like('J%')).update(name='James')
1

### delete records by query
>>> db(person.name.lower()=='jim').delete()
0

### retrieve multiple records (rows)
>>> people = db(person).select(orderby=person.name,groupby=person.name,limitby=(0,100))

### further filter them
>>> james = people.find(lambda row: row.name=='James').first()
>>> print james.id, james.name
1 James

### check aggrgates
>>> counter = person.id.count()
>>> print db(person).select(counter).first()(counter)
1

### delete one record
>>> james.delete_record()
1

### delete (drop) entire database table
>>> person.drop()

Supported field types:
id string text boolean integer double decimal password upload blob time date datetime,

Supported DAL URI strings:
'sqlite://test.db'
'sqlite:memory'
'jdbc:sqlite://test.db'
'mysql://root:none@localhost/test'
'postgres://mdipierro:none@localhost/test'
'jdbc:postgres://mdipierro:none@localhost/test'
'mssql://web2py:none@A64X2/web2py_test'
'mssql2://web2py:none@A64X2/web2py_test' # alternate mappings
'oracle://username:password@database'
'firebird://user:password@server:3050/database'
'db2://DSN=dsn;UID=user;PWD=pass'
'firebird://username:password@hostname/database'
'firebird_embedded://username:password@c://path'
'informix://user:password@server:3050/database'
'informixu://user:password@server:3050/database' # unicode informix
'google:datastore' # for google app engine datastore
'google:sql' # for google app engine with sql (mysql compatible)
'teradata://DSN=dsn;UID=user;PWD=pass' # experimental

For more info:
help(DAL)
help(Field)
"""

###################################################################################
# this file orly exposes DAL and Field
###################################################################################

__all__ = ['DAL', 'Field']

MAXCHARLENGTH = 2**15 # not quite but reasonable default max char length
DEFAULTLENGTH = {'string':512,
                 'password':512,
                 'upload':512,
                 'text':2**15,
                 'blob':2**31}

import re
import sys
import locale
import os
import types
import cPickle
import datetime
import threading
import time
import cStringIO
import csv
import copy
import socket
import logging
import copy_reg
import base64
import shutil
import marshal
import decimal
import struct
import urllib
import hashlib
import uuid
import glob

CALLABLETYPES = (types.LambdaType, types.FunctionType, types.BuiltinFunctionType,
                 types.MethodType, types.BuiltinMethodType)


###################################################################################
# following checks allows running of dal without web2py as a standalone module
###################################################################################
try:
    from utils import web2py_uuid
except ImportError:
    import uuid
    def web2py_uuid(): return str(uuid.uuid4())

try:
    import portalocker
    have_portalocker = True
except ImportError:
    have_portalocker = False

try:
    import serializers
    have_serializers = True
except ImportError:
    have_serializers = False

try:
    import validators
    have_validators = True
except ImportError:
    have_validators = False

logger = logging.getLogger("web2py.dal")
DEFAULT = lambda:0

sql_locker = threading.RLock()
thread = threading.local()

# internal representation of tables with field
#  <table>.<field>, tables and fields may only be [a-zA-Z0-0_]

regex_dbname = re.compile('^(\w+)(\:\w+)*')
table_field = re.compile('^([\w_]+)\.([\w_]+)$')
regex_content = re.compile('(?P<table>[\w\-]+)\.(?P<field>[\w\-]+)\.(?P<uuidkey>[\w\-]+)\.(?P<name>\w+)\.\w+$')
regex_cleanup_fn = re.compile('[\'"\s;]+')
string_unpack=re.compile('(?<!\|)\|(?!\|)')
regex_python_keywords = re.compile('^(and|del|from|not|while|as|elif|global|or|with|assert|else|if|pass|yield|break|except|import|print|class|exec|in|raise|continue|finally|is|return|def|for|lambda|try)$')



# list of drivers will be built on the fly
# and lists only what is available
drivers = []

try:
    from new import classobj
    from google.appengine.ext import db as gae
    from google.appengine.api import namespace_manager, rdbms
    from google.appengine.api.datastore_types import Key  ### needed for belongs on ID
    from google.appengine.ext.db.polymodel import PolyModel
    drivers.append('google')
except ImportError:
    pass

if not 'google' in drivers:

    try:
        from pysqlite2 import dbapi2 as sqlite3
        drivers.append('pysqlite2')
    except ImportError:
        try:
            from sqlite3 import dbapi2 as sqlite3
            drivers.append('SQLite3')
        except ImportError:
            logger.debug('no sqlite3 or pysqlite2.dbapi2 driver')

    try:
        import contrib.pymysql as pymysql
        drivers.append('pymysql')
    except ImportError:
        logger.debug('no pymysql driver')

    try:
        import psycopg2
        drivers.append('PostgreSQL')
    except ImportError:
        logger.debug('no psycopg2 driver')

    try:
        import cx_Oracle
        drivers.append('Oracle')
    except ImportError:
        logger.debug('no cx_Oracle driver')

    try:
        import pyodbc
        drivers.append('MSSQL/DB2')
    except ImportError:
        logger.debug('no MSSQL/DB2 driver')

    try:
        import kinterbasdb
        drivers.append('Interbase')
    except ImportError:
        logger.debug('no kinterbasdb driver')

    try:
        import firebirdsql
        drivers.append('Firebird')
    except ImportError:
        logger.debug('no Firebird driver')

    try:
        import informixdb
        drivers.append('Informix')
        logger.warning('Informix support is experimental')
    except ImportError:
        logger.debug('no informixdb driver')

    try:
        import sapdb
        drivers.append('SAPDB')
        logger.warning('SAPDB support is experimental')
    except ImportError:
        logger.debug('no sapdb driver')

    try:
        import cubriddb
        drivers.append('Cubrid')
        logger.warning('Cubrid support is experimental')
    except ImportError:
        logger.debug('no cubriddb driver')

    try:
        from com.ziclix.python.sql import zxJDBC
        import java.sql
        # Try sqlite jdbc driver from http://www.zentus.com/sqlitejdbc/
        from org.sqlite import JDBC # required by java.sql; ensure we have it
        drivers.append('zxJDBC')
        logger.warning('zxJDBC support is experimental')
        is_jdbc = True
    except ImportError:
        logger.debug('no zxJDBC driver')
        is_jdbc = False

    try:
        import ingresdbi
        drivers.append('Ingres')
    except ImportError:
        logger.debug('no Ingres driver')
    # NOTE could try JDBC.......

    try:
        import couchdb
        drivers.append('CouchDB')
    except ImportError:
        logger.debug('no couchdb driver')

    try:
        import pymongo
        drivers.append('mongoDB')
    except:
        logger.debug('no mongoDB driver')

def OR(a,b):
    return a|b

def AND(a,b):
    return a&b

if 'google' in drivers:

    is_jdbc = False

    class GAEDecimalProperty(gae.Property):
        """
        GAE decimal implementation
        """
        data_type = decimal.Decimal

        def __init__(self, precision, scale, **kwargs):
            super(GAEDecimalProperty, self).__init__(self, **kwargs)
            d = '1.'
            for x in range(scale):
                d += '0'
            self.round = decimal.Decimal(d)

        def get_value_for_datastore(self, model_instance):
            value = super(GAEDecimalProperty, self).get_value_for_datastore(model_instance)
            if value:
                return str(value)
            else:
                return None

        def make_value_from_datastore(self, value):
            if value:
                return decimal.Decimal(value).quantize(self.round)
            else:
                return None

        def validate(self, value):
            value = super(GAEDecimalProperty, self).validate(value)
            if value is None or isinstance(value, decimal.Decimal):
                return value
            elif isinstance(value, basestring):
                return decimal.Decimal(value)
            raise gae.BadValueError("Property %s must be a Decimal or string." % self.name)

###################################################################################
# class that handles connection pooling (all adapters derived form this one)
###################################################################################

class ConnectionPool(object):

    pools = {}

    @staticmethod
    def set_folder(folder):
        thread.folder = folder

    # ## this allows gluon to commit/rollback all dbs in this thread

    @staticmethod
    def close_all_instances(action):
        """ to close cleanly databases in a multithreaded environment """
        if not hasattr(thread,'instances'):
            return
        while thread.instances:
            instance = thread.instances.pop()
            getattr(instance,action)()
            # ## if you want pools, recycle this connection
            really = True
            if instance.pool_size:
                sql_locker.acquire()
                pool = ConnectionPool.pools[instance.uri]
                if len(pool) < instance.pool_size:
                    pool.append(instance.connection)
                    really = False
                sql_locker.release()
            if really:
                getattr(instance,'close')()
        return

    def find_or_make_work_folder(self):
        """ this actually does not make the folder. it has to be there """
        if hasattr(thread,'folder'):
            self.folder = thread.folder
        else:
            self.folder = thread.folder = ''

        # Creating the folder if it does not exist
        if False and self.folder and not os.path.exists(self.folder):
            os.mkdir(self.folder)

    def pool_connection(self, f):
        if not self.pool_size:
            self.connection = f()
        else:
            uri = self.uri
            sql_locker.acquire()
            if not uri in ConnectionPool.pools:
                ConnectionPool.pools[uri] = []
            if ConnectionPool.pools[uri]:
                self.connection = ConnectionPool.pools[uri].pop()
                sql_locker.release()
            else:
                sql_locker.release()
                self.connection = f()
        if not hasattr(thread,'instances'):
            thread.instances = []
        thread.instances.append(self)


###################################################################################
# this is a generic adapter that does nothing; all others are derived form this one
###################################################################################

class BaseAdapter(ConnectionPool):

    driver = None
    maxcharlength = MAXCHARLENGTH
    commit_on_alter_table = False
    support_distributed_transaction = False
    uploads_in_blob = False
    types = {
        'boolean': 'CHAR(1)',
        'string': 'CHAR(%(length)s)',
        'text': 'TEXT',
        'password': 'CHAR(%(length)s)',
        'blob': 'BLOB',
        'upload': 'CHAR(%(length)s)',
        'integer': 'INTEGER',
        'double': 'DOUBLE',
        'decimal': 'DOUBLE',
        'date': 'DATE',
        'time': 'TIME',
        'datetime': 'TIMESTAMP',
        'id': 'INTEGER PRIMARY KEY AUTOINCREMENT',
        'reference': 'INTEGER REFERENCES %(foreign_key)s ON DELETE %(on_delete_action)s',
        'list:integer': 'TEXT',
        'list:string': 'TEXT',
        'list:reference': 'TEXT',
        }

    def integrity_error(self):
        return self.driver.IntegrityError

    def file_exists(self, filename):
        """
        to be used ONLY for files that on GAE may not be on filesystem
        """
        return os.path.exists(filename)

    def file_open(self, filename, mode='rb', lock=True):
        """
        to be used ONLY for files that on GAE may not be on filesystem
        """
        fileobj = open(filename,mode)
        if have_portalocker and lock:
            if mode in ('r','rb'):
                portalocker.lock(fileobj,portalocker.LOCK_SH)
            elif mode in ('w','wb','a'):
                portalocker.lock(fileobj,portalocker.LOCK_EX)
            else:
                fileobj.close()
                raise RuntimeError, "Unsupported file_open mode"
        return fileobj

    def file_close(self, fileobj, unlock=True):
        """
        to be used ONLY for files that on GAE may not be on filesystem
        """
        if fileobj:
            if have_portalocker and unlock:
                portalocker.unlock(fileobj)
            fileobj.close()

    def file_delete(self, filename):
        os.unlink(filename)

    def __init__(self,db,uri,pool_size=0,folder=None,db_codec ='UTF-8',
                 credential_decoder=lambda x:x, driver_args={},
                 adapter_args={}):
        self.db = db
        self.dbengine = "None"
        self.uri = uri
        self.pool_size = pool_size
        self.folder = folder
        self.db_codec = db_codec
        class Dummy(object):
            lastrowid = 1
            def __getattr__(self, value):
                return lambda *a, **b: []
        self.connection = Dummy()
        self.cursor = Dummy()

    def sequence_name(self,tablename):
        return '%s_sequence' % tablename

    def trigger_name(self,tablename):
        return '%s_sequence' % tablename


    def create_table(self, table, migrate=True, fake_migrate=False, polymodel=None):
        fields = []
        sql_fields = {}
        sql_fields_aux = {}
        TFK = {}
        tablename = table._tablename
        sortable = 0
        for field in table:
            sortable += 1
            k = field.name
            if isinstance(field.type,SQLCustomType):
                ftype = field.type.native or field.type.type
            elif field.type.startswith('reference'):
                referenced = field.type[10:].strip()
                constraint_name = self.constraint_name(tablename, field.name)
                if hasattr(table,'_primarykey'):
                    rtablename,rfieldname = referenced.split('.')
                    rtable = table._db[rtablename]
                    rfield = rtable[rfieldname]
                    # must be PK reference or unique
                    if rfieldname in rtable._primarykey or rfield.unique:
                        ftype = self.types[rfield.type[:9]] % dict(length=rfield.length)
                        # multicolumn primary key reference?
                        if not rfield.unique and len(rtable._primarykey)>1 :
                            # then it has to be a table level FK
                            if rtablename not in TFK:
                                TFK[rtablename] = {}
                            TFK[rtablename][rfieldname] = field.name
                        else:
                            ftype = ftype + \
                                self.types['reference FK'] %dict(\
                                constraint_name=constraint_name,
                                table_name=tablename,
                                field_name=field.name,
                                foreign_key='%s (%s)'%(rtablename, rfieldname),
                                on_delete_action=field.ondelete)
                else:
                    # make a guess here for circular references
                    id_fieldname = referenced in table._db and table._db[referenced]._id.name or 'id'
                    ftype = self.types[field.type[:9]]\
                        % dict(table_name=tablename,
                               field_name=field.name,
                               constraint_name=constraint_name,
                               foreign_key=referenced + ('(%s)' % id_fieldname),
                               on_delete_action=field.ondelete)
            elif field.type.startswith('list:reference'):
                ftype = self.types[field.type[:14]]
            elif field.type.startswith('decimal'):
                precision, scale = map(int,field.type[8:-1].split(','))
                ftype = self.types[field.type[:7]] % \
                    dict(precision=precision,scale=scale)
            elif not field.type in self.types:
                raise SyntaxError, 'Field: unknown field type: %s for %s' % \
                    (field.type, field.name)
            else:
                ftype = self.types[field.type]\
                     % dict(length=field.length)
            if not field.type.startswith('id') and not field.type.startswith('reference'):
                if field.notnull:
                    ftype += ' NOT NULL'
                else:
                    ftype += self.ALLOW_NULL()
                if field.unique:
                    ftype += ' UNIQUE'

            # add to list of fields
            sql_fields[field.name] = dict(sortable=sortable,
                                          type=str(field.type),
                                          sql=ftype)

            if isinstance(field.default,(str,int,float)):
                # caveat: sql_fields and sql_fields_aux differ for default values
                # sql_fields is used to trigger migrations and sql_fields_aux
                # are used for create table
                # the reason is that we do not want to trigger a migration simply
                # because a default value changes
                not_null = self.NOT_NULL(field.default,field.type)
                ftype = ftype.replace('NOT NULL',not_null)
            sql_fields_aux[field.name] = dict(sql=ftype)

            fields.append('%s %s' % (field.name, ftype))
        other = ';'

        # backend-specific extensions to fields
        if self.dbengine == 'mysql':
            if not hasattr(table, "_primarykey"):
                fields.append('PRIMARY KEY(%s)' % table._id.name)
            other = ' ENGINE=InnoDB CHARACTER SET utf8;'

        fields = ',\n    '.join(fields)
        for rtablename in TFK:
            rfields = TFK[rtablename]
            pkeys = table._db[rtablename]._primarykey
            fkeys = [ rfields[k] for k in pkeys ]
            fields = fields + ',\n    ' + \
                     self.types['reference TFK'] %\
                     dict(table_name=tablename,
                     field_name=', '.join(fkeys),
                     foreign_table=rtablename,
                     foreign_key=', '.join(pkeys),
                     on_delete_action=field.ondelete)

        if hasattr(table,'_primarykey'):
            query = '''CREATE TABLE %s(\n    %s,\n    %s) %s''' % \
                (tablename, fields, self.PRIMARY_KEY(', '.join(table._primarykey)),other)
        else:
            query = '''CREATE TABLE %s(\n    %s\n)%s''' % \
                (tablename, fields, other)

        if self.uri.startswith('sqlite:///'):
            path_encoding = sys.getfilesystemencoding() or locale.getdefaultlocale()[1] or 'utf8'
            dbpath = self.uri[9:self.uri.rfind('/')].decode('utf8').encode(path_encoding)
        else:
            dbpath = self.folder

        if not migrate:
            return query
        elif self.uri.startswith('sqlite:memory'):
            table._dbt = None
        elif isinstance(migrate, str):
            table._dbt = os.path.join(dbpath, migrate)
        else:
            table._dbt = os.path.join(dbpath, '%s_%s.table' \
                                          % (table._db._uri_hash, tablename))
        if table._dbt:
            table._loggername = os.path.join(dbpath, 'sql.log')
            logfile = self.file_open(table._loggername, 'a')
        else:
            logfile = None
        if not table._dbt or not self.file_exists(table._dbt):
            if table._dbt:
                logfile.write('timestamp: %s\n'
                               % datetime.datetime.today().isoformat())
                logfile.write(query + '\n')
            if not fake_migrate:
                self.create_sequence_and_triggers(query,table)
                table._db.commit()
            if table._dbt:
                tfile = self.file_open(table._dbt, 'w')
                cPickle.dump(sql_fields, tfile)
                self.file_close(tfile)
                if fake_migrate:
                    logfile.write('faked!\n')
                else:
                    logfile.write('success!\n')
        else:
            tfile = self.file_open(table._dbt, 'r')
            try:
                sql_fields_old = cPickle.load(tfile)
            except EOFError:
                self.file_close(tfile)
                self.file_close(logfile)
                raise RuntimeError, 'File %s appears corrupted' % table._dbt
            self.file_close(tfile)
            if sql_fields != sql_fields_old:
                self.migrate_table(table,
                                   sql_fields, sql_fields_old,
                                   sql_fields_aux, logfile,
                                   fake_migrate=fake_migrate)
        self.file_close(logfile)
        return query

    def migrate_table(
        self,
        table,
        sql_fields,
        sql_fields_old,
        sql_fields_aux,
        logfile,
        fake_migrate=False,
        ):
        tablename = table._tablename
        def fix(item):
            k,v=item
            if not isinstance(v,dict):
                v=dict(type='unkown',sql=v)
            return k.lower(),v
        ### make sure all field names are lower case to avoid conflicts
        sql_fields = dict(map(fix,sql_fields.items()))
        sql_fields_old = dict(map(fix,sql_fields_old.items()))
        sql_fields_aux = dict(map(fix,sql_fields_aux.items()))

        keys = sql_fields.keys()
        for key in sql_fields_old:
            if not key in keys:
                keys.append(key)
        if self.dbengine == 'mssql':
            new_add = '; ALTER TABLE %s ADD ' % tablename
        else:
            new_add = ', ADD '

        metadata_change = False
        sql_fields_current = copy.copy(sql_fields_old)
        for key in keys:
            query = None
            if not key in sql_fields_old:
                sql_fields_current[key] = sql_fields[key]
                query = ['ALTER TABLE %s ADD %s %s;' % \
                         (tablename, key,
                          sql_fields_aux[key]['sql'].replace(', ', new_add))]
                metadata_change = True
            elif self.dbengine == 'sqlite':
                if key in sql_fields:
                    sql_fields_current[key] = sql_fields[key]
                metadata_change = True
            elif not key in sql_fields:
                del sql_fields_current[key]
                if not self.dbengine in ('firebird',):
                    query = ['ALTER TABLE %s DROP COLUMN %s;' % (tablename, key)]
                else:
                    query = ['ALTER TABLE %s DROP %s;' % (tablename, key)]
                metadata_change = True
            elif sql_fields[key]['sql'] != sql_fields_old[key]['sql'] \
                  and not isinstance(table[key].type, SQLCustomType) \
                  and not (table[key].type.startswith('reference') and \
                      sql_fields[key]['sql'].startswith('INT,') and \
                      sql_fields_old[key]['sql'].startswith('INT NOT NULL,')):
                sql_fields_current[key] = sql_fields[key]
                t = tablename
                tt = sql_fields_aux[key]['sql'].replace(', ', new_add)
                if not self.dbengine in ('firebird',):
                    query = ['ALTER TABLE %s ADD %s__tmp %s;' % (t, key, tt),
                             'UPDATE %s SET %s__tmp=%s;' % (t, key, key),
                             'ALTER TABLE %s DROP COLUMN %s;' % (t, key),
                             'ALTER TABLE %s ADD %s %s;' % (t, key, tt),
                             'UPDATE %s SET %s=%s__tmp;' % (t, key, key),
                             'ALTER TABLE %s DROP COLUMN %s__tmp;' % (t, key)]
                else:
                    query = ['ALTER TABLE %s ADD %s__tmp %s;' % (t, key, tt),
                             'UPDATE %s SET %s__tmp=%s;' % (t, key, key),
                             'ALTER TABLE %s DROP %s;' % (t, key),
                             'ALTER TABLE %s ADD %s %s;' % (t, key, tt),
                             'UPDATE %s SET %s=%s__tmp;' % (t, key, key),
                             'ALTER TABLE %s DROP %s__tmp;' % (t, key)]
                metadata_change = True
            elif sql_fields[key]['type'] != sql_fields_old[key]['type']:
                sql_fields_current[key] = sql_fields[key]
                metadata_change = True

            if query:
                logfile.write('timestamp: %s\n'
                              % datetime.datetime.today().isoformat())
                table._db['_lastsql'] = '\n'.join(query)
                for sub_query in query:
                    logfile.write(sub_query + '\n')
                    if not fake_migrate:
                        self.execute(sub_query)
                        # caveat. mysql, oracle and firebird do not allow multiple alter table
                        # in one transaction so we must commit partial transactions and
                        # update table._dbt after alter table.
                        if table._db._adapter.commit_on_alter_table:
                            table._db.commit()
                            tfile = self.file_open(table._dbt, 'w')
                            cPickle.dump(sql_fields_current, tfile)
                            self.file_close(tfile)
                            logfile.write('success!\n')
                    else:
                        logfile.write('faked!\n')
            elif metadata_change:
                tfile = self.file_open(table._dbt, 'w')
                cPickle.dump(sql_fields_current, tfile)
                self.file_close(tfile)

        if metadata_change and \
                not (query and self.dbengine in ('mysql','oracle','firebird')):
            table._db.commit()
            tfile = self.file_open(table._dbt, 'w')
            cPickle.dump(sql_fields_current, tfile)
            self.file_close(tfile)

    def LOWER(self,first):
        return 'LOWER(%s)' % self.expand(first)

    def UPPER(self,first):
        return 'UPPER(%s)' % self.expand(first)

    def EXTRACT(self,first,what):
        return "EXTRACT(%s FROM %s)" % (what, self.expand(first))

    def AGGREGATE(self,first,what):
        return "%s(%s)" % (what,self.expand(first))

    def JOIN(self):
        return 'JOIN'

    def LEFT_JOIN(self):
        return 'LEFT JOIN'

    def RANDOM(self):
        return 'Random()'

    def NOT_NULL(self,default,field_type):
        return 'NOT NULL DEFAULT %s' % self.represent(default,field_type)

    def COALESCE(self,first,second):
        expressions = [self.expand(first)]+[self.expand(e) for e in second]
        return 'COALESCE(%s)' % ','.join(expressions)

    def COALESCE_ZERO(self,first):
        return 'COALESCE(%s,0)' % self.expand(first)

    def RAW(self,first):
        return first

    def ALLOW_NULL(self):
        return ''

    def SUBSTRING(self,field,parameters):
        return 'SUBSTR(%s,%s,%s)' % (self.expand(field), parameters[0], parameters[1])

    def PRIMARY_KEY(self,key):
        return 'PRIMARY KEY(%s)' % key

    def _drop(self,table,mode):
        return ['DROP TABLE %s;' % table]

    def drop(self, table, mode=''):
        if table._dbt:
            logfile = self.file_open(table._loggername, 'a')
        queries = self._drop(table, mode)
        for query in queries:
            if table._dbt:
                logfile.write(query + '\n')
            self.execute(query)
        table._db.commit()
        del table._db[table._tablename]
        del table._db.tables[table._db.tables.index(table._tablename)]
        table._db._update_referenced_by(table._tablename)
        if table._dbt:
            self.file_delete(table._dbt)
            logfile.write('success!\n')

    def _insert(self,table,fields):
        keys = ','.join(f.name for f,v in fields)
        values = ','.join(self.expand(v,f.type) for f,v in fields)
        return 'INSERT INTO %s(%s) VALUES (%s);' % (table, keys, values)

    def insert(self,table,fields):
        query = self._insert(table,fields)
        try:
            self.execute(query)
        except Exception, e:
            if isinstance(e,self.integrity_error_class()):
                return None
            raise e
        if hasattr(table,'_primarykey'):
            return dict([(k[0].name, k[1]) for k in fields \
                             if k[0].name in table._primarykey])
        id = self.lastrowid(table)
        if not isinstance(id,int):
            return id
        rid = Reference(id)
        (rid._table, rid._record) = (table, None)
        return rid

    def bulk_insert(self,table,items):
        return [self.insert(table,item) for item in items]

    def NOT(self,first):
        return '(NOT %s)' % self.expand(first)

    def AND(self,first,second):
        return '(%s AND %s)' % (self.expand(first),self.expand(second))

    def OR(self,first,second):
        return '(%s OR %s)' % (self.expand(first),self.expand(second))

    def BELONGS(self,first,second):
        if isinstance(second,str):
            return '(%s IN (%s))' % (self.expand(first),second[:-1])
        elif second==[] or second==():
            return '(0)'
        items =','.join(self.expand(item,first.type) for item in second)
        return '(%s IN (%s))' % (self.expand(first),items)

    def LIKE(self,first,second):
        return '(%s LIKE %s)' % (self.expand(first),self.expand(second,'string'))

    def STARTSWITH(self,first,second):
        return '(%s LIKE %s)' % (self.expand(first),self.expand(second+'%','string'))

    def ENDSWITH(self,first,second):
        return '(%s LIKE %s)' % (self.expand(first),self.expand('%'+second,'string'))

    def CONTAINS(self,first,second):
        if first.type in ('string','text'):
            key = '%'+str(second).replace('%','%%')+'%'
        elif first.type.startswith('list:'):
            key = '%|'+str(second).replace('|','||').replace('%','%%')+'|%'
        return '(%s LIKE %s)' % (self.expand(first),self.expand(key,'string'))

    def EQ(self,first,second=None):
        if second is None:
            return '(%s IS NULL)' % self.expand(first)
        return '(%s = %s)' % (self.expand(first),self.expand(second,first.type))

    def NE(self,first,second=None):
        if second is None:
            return '(%s IS NOT NULL)' % self.expand(first)
        return '(%s <> %s)' % (self.expand(first),self.expand(second,first.type))

    def LT(self,first,second=None):
        return '(%s < %s)' % (self.expand(first),self.expand(second,first.type))

    def LE(self,first,second=None):
        return '(%s <= %s)' % (self.expand(first),self.expand(second,first.type))

    def GT(self,first,second=None):
        return '(%s > %s)' % (self.expand(first),self.expand(second,first.type))

    def GE(self,first,second=None):
        return '(%s >= %s)' % (self.expand(first),self.expand(second,first.type))

    def ADD(self,first,second):
        return '(%s + %s)' % (self.expand(first),self.expand(second,first.type))

    def SUB(self,first,second):
        return '(%s - %s)' % (self.expand(first),self.expand(second,first.type))

    def MUL(self,first,second):
        return '(%s * %s)' % (self.expand(first),self.expand(second,first.type))

    def DIV(self,first,second):
        return '(%s / %s)' % (self.expand(first),self.expand(second,first.type))

    def MOD(self,first,second):
        return '(%s %% %s)' % (self.expand(first),self.expand(second,first.type))

    def AS(self,first,second):
        return '%s AS %s' % (self.expand(first),second)

    def ON(self,first,second):
        return '%s ON %s' % (self.expand(first),self.expand(second))

    def INVERT(self,first):
        return '%s DESC' % self.expand(first)

    def COMMA(self,first,second):
        return '%s, %s' % (self.expand(first),self.expand(second))

    def expand(self,expression,field_type=None):
        if isinstance(expression,Field):
            return str(expression)
        elif isinstance(expression, (Expression, Query)):
            if not expression.second is None:
                return expression.op(expression.first, expression.second)
            elif not expression.first is None:
                return expression.op(expression.first)
            elif not isinstance(expression.op,str):
                return expression.op()
            else:
                return '(%s)' % expression.op
        elif field_type:
            return self.represent(expression,field_type)
        elif isinstance(expression,(list,tuple)):
            return ','.join([self.represent(item,field_type) for item in expression])
        else:
            return str(expression)

    def alias(self,table,alias):
        """
        given a table object, makes a new table object
        with alias name.
        """
        other = copy.copy(table)
        other['_ot'] = other._tablename
        other['ALL'] = SQLALL(other)
        other['_tablename'] = alias
        for fieldname in other.fields:
            other[fieldname] = copy.copy(other[fieldname])
            other[fieldname]._tablename = alias
            other[fieldname].tablename = alias
            other[fieldname].table = other
        table._db[alias] = other
        return other

    def _truncate(self,table,mode = ''):
        tablename = table._tablename
        return ['TRUNCATE TABLE %s %s;' % (tablename, mode or '')]

    def truncate(self,table,mode= ' '):
        # Prepare functions "write_to_logfile" and "close_logfile"
        if table._dbt:
            logfile = self.file_open(table._loggername, 'a')
        else:
            class Logfile(object):
                def write(self, value):
                    pass
                def close(self):
                    pass
            logfile = Logfile()

        try:
            queries = table._db._adapter._truncate(table, mode)
            for query in queries:
                logfile.write(query + '\n')
                self.execute(query)
            table._db.commit()
            logfile.write('success!\n')
        finally:
            logfile.close()

    def _update(self,tablename,query,fields):
        if query:
            sql_w = ' WHERE ' + self.expand(query)
        else:
            sql_w = ''
        sql_v = ','.join(['%s=%s' % (field.name, self.expand(value,field.type)) for (field,value) in fields])
        return 'UPDATE %s SET %s%s;' % (tablename, sql_v, sql_w)

    def update(self,tablename,query,fields):
        sql = self._update(tablename,query,fields)
        self.execute(sql)
        try:
            return self.cursor.rowcount
        except:
            return None

    def _delete(self,tablename, query):
        if query:
            sql_w = ' WHERE ' + self.expand(query)
        else:
            sql_w = ''
        return 'DELETE FROM %s%s;' % (tablename, sql_w)

    def delete(self,tablename,query):
        sql = self._delete(tablename,query)
        ### special code to handle CASCADE in SQLite
        db = self.db
        table = db[tablename]
        if self.dbengine=='sqlite' and table._referenced_by:
            deleted = [x[table._id.name] for x in db(query).select(table._id)]
        ### end special code to handle CASCADE in SQLite
        self.execute(sql)
        try:
            counter = self.cursor.rowcount
        except:
            counter =  None
        ### special code to handle CASCADE in SQLite
        if self.dbengine=='sqlite' and counter:
            for tablename,fieldname in table._referenced_by:
                f = db[tablename][fieldname]
                if f.type=='reference '+table._tablename and f.ondelete=='CASCADE':
                    db(db[tablename][fieldname].belongs(deleted)).delete()
        ### end special code to handle CASCADE in SQLite
        return counter

    def get_table(self,query):
        tablenames = self.tables(query)
        if len(tablenames)==1:
            return tablenames[0]
        elif len(tablenames)<1:
            raise RuntimeError, "No table selected"
        else:
            raise RuntimeError, "Too many tables selected"

    def _select(self, query, fields, attributes):
        for key in set(attributes.keys())-set(('orderby','groupby','limitby',
                                               'required','cache','left',
                                               'distinct','having', 'join')):
            raise SyntaxError, 'invalid select attribute: %s' % key
        # ## if not fields specified take them all from the requested tables
        new_fields = []
        for item in fields:
            if isinstance(item,SQLALL):
                new_fields += item.table
            else:
                new_fields.append(item)
        fields = new_fields
        tablenames = self.tables(query)
        query = self.filter_tenant(query,tablenames)
        if not fields:
            for table in tablenames:
                for field in self.db[table]:
                    fields.append(field)
        else:
            for field in fields:
                if isinstance(field,basestring) and table_field.match(field):
                    tn,fn = field.split('.')
                    field = self.db[tn][fn]
                for tablename in self.tables(field):
                    if not tablename in tablenames:
                        tablenames.append(tablename)
        if len(tablenames) < 1:
            raise SyntaxError, 'Set: no tables selected'
        sql_f = ', '.join(map(self.expand,fields))
        self._colnames = [c.strip() for c in sql_f.split(', ')]
        if query:
            sql_w = ' WHERE ' + self.expand(query)
        else:
            sql_w = ''
        sql_o = ''
        sql_s = ''
        left = attributes.get('left', False)
        inner_join = attributes.get('join', False)
        distinct = attributes.get('distinct', False)
        groupby = attributes.get('groupby', False)
        orderby = attributes.get('orderby', False)
        having = attributes.get('having', False)
        limitby = attributes.get('limitby', False)
        if distinct is True:
            sql_s += 'DISTINCT'
        elif distinct:
            sql_s += 'DISTINCT ON (%s)' % distinct
        if inner_join:
            icommand = self.JOIN()
            if not isinstance(inner_join, (tuple, list)):
                inner_join = [inner_join]
            ijoint = [t._tablename for t in inner_join if not isinstance(t,Expression)]
            ijoinon = [t for t in inner_join if isinstance(t, Expression)]
            ijoinont = [t.first._tablename for t in ijoinon]
            iexcluded = [t for t in tablenames if not t in ijoint + ijoinont]
        if left:
            join = attributes['left']
            command = self.LEFT_JOIN()
            if not isinstance(join, (tuple, list)):
                join = [join]
            joint = [t._tablename for t in join if not isinstance(t,Expression)]
            joinon = [t for t in join if isinstance(t, Expression)]
            #patch join+left patch (solves problem with ordering in left joins)
            tables_to_merge={}
            [tables_to_merge.update(dict.fromkeys(self.tables(t))) for t in joinon]
            joinont = [t.first._tablename for t in joinon]
            [tables_to_merge.pop(t) for t in joinont if t in tables_to_merge]
            important_tablenames = joint + joinont + tables_to_merge.keys()
            excluded = [t for t in tablenames if not t in important_tablenames ]
        def alias(t):
            return str(self.db[t])
        if inner_join and not left:
            sql_t = ', '.join(alias(t) for t in iexcluded)
            for t in ijoinon:
                sql_t += ' %s %s' % (icommand, str(t))
        elif not inner_join and left:
            sql_t = ', '.join([alias(t) for t in excluded + tables_to_merge.keys()])
            if joint:
                sql_t += ' %s %s' % (command, ','.join([t for t in joint]))
            for t in joinon:
                sql_t += ' %s %s' % (command, str(t))
        elif inner_join and left:
            sql_t = ','.join([alias(t) for t in excluded + \
                                  tables_to_merge.keys() if t in iexcluded ])
            for t in ijoinon:
                sql_t += ' %s %s' % (icommand, str(t))
            if joint:
                sql_t += ' %s %s' % (command, ','.join([t for t in joint]))
            for t in joinon:
                sql_t += ' %s %s' % (command, str(t))
        else:
            sql_t = ', '.join(alias(t) for t in tablenames)
        if groupby:
            if isinstance(groupby, (list, tuple)):
                groupby = xorify(groupby)
            sql_o += ' GROUP BY %s' % self.expand(groupby)
            if having:
                sql_o += ' HAVING %s' % attributes['having']
        if orderby:
            if isinstance(orderby, (list, tuple)):
                orderby = xorify(orderby)
            if str(orderby) == '<random>':
                sql_o += ' ORDER BY %s' % self.RANDOM()
            else:
                sql_o += ' ORDER BY %s' % self.expand(orderby)
        if limitby:
            if not orderby and tablenames:
                sql_o += ' ORDER BY %s' % ', '.join(['%s.%s'%(t,x) for t in tablenames for x in ((hasattr(self.db[t],'_primarykey') and self.db[t]._primarykey) or [self.db[t]._id.name])])
            # oracle does not support limitby
        return self.select_limitby(sql_s, sql_f, sql_t, sql_w, sql_o, limitby)

    def select_limitby(self, sql_s, sql_f, sql_t, sql_w, sql_o, limitby):
        if limitby:
            (lmin, lmax) = limitby
            sql_o += ' LIMIT %i OFFSET %i' % (lmax - lmin, lmin)
        return 'SELECT %s %s FROM %s%s%s;' % (sql_s, sql_f, sql_t, sql_w, sql_o)

    def select(self,query,fields,attributes):
        """
        Always returns a Rows object, even if it may be empty
        """
        def response(sql):
            self.execute(sql)
            return self.cursor.fetchall()
        sql = self._select(query,fields,attributes)
        if attributes.get('cache', None):
            (cache_model, time_expire) = attributes['cache']
            del attributes['cache']
            key = self.uri + '/' + sql
            key = (key<=200) and key or hashlib.md5(key).hexdigest()
            rows = cache_model(key, lambda: response(sql), time_expire)
        else:
            rows = response(sql)
        if isinstance(rows,tuple):
            rows = list(rows)
        limitby = attributes.get('limitby',None) or (0,)
        rows = self.rowslice(rows,limitby[0],None)
        return self.parse(rows,self._colnames)

    def _count(self,query,distinct=None):
        tablenames = self.tables(query)
        if query:
            sql_w = ' WHERE ' + self.expand(query)
        else:
            sql_w = ''
        sql_t = ','.join(tablenames)
        if distinct:
            if isinstance(distinct,(list,tuple)):
                distinct = xorify(distinct)
            sql_d = self.expand(distinct)
            return 'SELECT count(DISTINCT %s) FROM %s%s' % (sql_d, sql_t, sql_w)
        return 'SELECT count(*) FROM %s%s' % (sql_t, sql_w)

    def count(self,query,distinct=None):
        self.execute(self._count(query,distinct))
        return self.cursor.fetchone()[0]


    def tables(self,query):
        tables = set()
        if isinstance(query, Field):
            tables.add(query.tablename)
        elif isinstance(query, (Expression, Query)):
            if not query.first is None:
                tables = tables.union(self.tables(query.first))
            if not query.second is None:
                tables = tables.union(self.tables(query.second))
        return list(tables)

    def commit(self):
        return self.connection.commit()

    def rollback(self):
        return self.connection.rollback()

    def close(self):
        return self.connection.close()

    def distributed_transaction_begin(self,key):
        return

    def prepare(self,key):
        self.connection.prepare()

    def commit_prepared(self,key):
        self.connection.commit()

    def rollback_prepared(self,key):
        self.connection.rollback()

    def concat_add(self,table):
        return ', ADD '

    def constraint_name(self, table, fieldname):
        return '%s_%s__constraint' % (table,fieldname)

    def create_sequence_and_triggers(self, query, table, **args):
        self.execute(query)

    def log_execute(self,*a,**b):
        self.db._lastsql = a[0]
        t0 = time.time()
        ret = self.cursor.execute(*a,**b)
        self.db._timings.append((a[0],time.time()-t0))
        return ret

    def execute(self,*a,**b):
        return self.log_execute(*a, **b)

    def represent(self, obj, fieldtype):
        if isinstance(obj,CALLABLETYPES):
            obj = obj()
        if isinstance(fieldtype, SQLCustomType):
            return fieldtype.encoder(obj)
        if isinstance(obj, (Expression, Field)):
            return str(obj)
        if fieldtype.startswith('list:'):
            if not obj:
                obj = []
            if not isinstance(obj, (list, tuple)):
                obj = [obj]
        if isinstance(obj, (list, tuple)):
            obj = bar_encode(obj)
        if obj is None:
            return 'NULL'
        if obj == '' and not fieldtype[:2] in ['st', 'te', 'pa', 'up']:
            return 'NULL'
        r = self.represent_exceptions(obj,fieldtype)
        if not r is None:
            return r
        if fieldtype == 'boolean':
            if obj and not str(obj)[:1].upper() in ['F', '0']:
                return "'T'"
            else:
                return "'F'"
        if fieldtype == 'id' or fieldtype == 'integer':
            return str(int(obj))
        if fieldtype.startswith('decimal'):
            return str(obj)
        elif fieldtype.startswith('reference'): # reference
            if fieldtype.find('.')>0:
                return repr(obj)
            elif isinstance(obj, (Row, Reference)):
                return str(obj['id'])
            return str(int(obj))
        elif fieldtype == 'double':
            return repr(float(obj))
        if isinstance(obj, unicode):
            obj = obj.encode(self.db_codec)
        if fieldtype == 'blob':
            obj = base64.b64encode(str(obj))
        elif fieldtype == 'date':
            if isinstance(obj, (datetime.date, datetime.datetime)):
                obj = obj.isoformat()[:10]
            else:
                obj = str(obj)
        elif fieldtype == 'datetime':
            if isinstance(obj, datetime.datetime):
                obj = obj.isoformat()[:19].replace('T',' ')
            elif isinstance(obj, datetime.date):
                obj = obj.isoformat()[:10]+' 00:00:00'
            else:
                obj = str(obj)
        elif fieldtype == 'time':
            if isinstance(obj, datetime.time):
                obj = obj.isoformat()[:10]
            else:
                obj = str(obj)
        if not isinstance(obj,str):
            obj = str(obj)
        try:
            obj.decode(self.db_codec)
        except:
            obj = obj.decode('latin1').encode(self.db_codec)
        return "'%s'" % obj.replace("'", "''")

    def represent_exceptions(self, obj, fieldtype):
        return None

    def lastrowid(self,table):
        return None

    def integrity_error_class(self):
        return type(None)

    def rowslice(self,rows,minimum=0,maximum=None):
        """ by default this function does nothing, overload when db does not do slicing """
        return rows

    def parse(self, rows, colnames, blob_decode=True):
        db = self.db
        virtualtables = []
        new_rows = []
        for (i,row) in enumerate(rows):
            new_row = Row()
            for j,colname in enumerate(colnames):
                value = row[j]
                if not table_field.match(colnames[j]):
                    if not '_extra' in new_row:
                        new_row['_extra'] = Row()
                    new_row['_extra'][colnames[j]] = value
                    select_as_parser = re.compile("\s+AS\s+(\S+)")
                    new_column_name = select_as_parser.search(colnames[j])
                    if not new_column_name is None:
                        column_name = new_column_name.groups(0)
                        setattr(new_row,column_name[0],value)
                    continue
                (tablename, fieldname) = colname.split('.')
                table = db[tablename]
                field = table[fieldname]
                field_type = field.type
                if field.type != 'blob' and isinstance(value, str):
                    try:
                        value = value.decode(db._db_codec)
                    except Exception:
                        pass
                if isinstance(value, unicode):
                    value = value.encode('utf-8')
                if not tablename in new_row:
                    colset = new_row[tablename] = Row()
                    if tablename not in virtualtables:
                        virtualtables.append(tablename)
                else:
                    colset = new_row[tablename]

                if isinstance(field_type, SQLCustomType):
                    colset[fieldname] = field_type.decoder(value)
                    # field_type = field_type.type
                elif not isinstance(field_type, str) or value is None:
                    colset[fieldname] = value
                elif isinstance(field_type, str) and \
                        field_type.startswith('reference'):
                    referee = field_type[10:].strip()
                    if not '.' in referee:
                        colset[fieldname] = rid = Reference(value)
                        (rid._table, rid._record) = (db[referee], None)
                    else: ### reference not by id
                        colset[fieldname] = value
                elif field_type == 'boolean':
                    if value == True or str(value)[:1].lower() == 't':
                        colset[fieldname] = True
                    else:
                        colset[fieldname] = False
                elif field_type == 'date' \
                        and (not isinstance(value, datetime.date)\
                                 or isinstance(value, datetime.datetime)):
                    (y, m, d) = map(int, str(value)[:10].strip().split('-'))
                    colset[fieldname] = datetime.date(y, m, d)
                elif field_type == 'time' \
                        and not isinstance(value, datetime.time):
                    time_items = map(int,str(value)[:8].strip().split(':')[:3])
                    if len(time_items) == 3:
                        (h, mi, s) = time_items
                    else:
                        (h, mi, s) = time_items + [0]
                    colset[fieldname] = datetime.time(h, mi, s)
                elif field_type == 'datetime'\
                        and not isinstance(value, datetime.datetime):
                    (y, m, d) = map(int,str(value)[:10].strip().split('-'))
                    time_items = map(int,str(value)[11:19].strip().split(':')[:3])
                    if len(time_items) == 3:
                        (h, mi, s) = time_items
                    else:
                        (h, mi, s) = time_items + [0]
                    colset[fieldname] = datetime.datetime(y, m, d, h, mi, s)
                elif field_type == 'blob' and blob_decode:
                    colset[fieldname] = base64.b64decode(str(value))
                elif field_type.startswith('decimal'):
                    decimals = int(field_type[8:-1].split(',')[-1])
                    if self.dbengine == 'sqlite':
                        value = ('%.' + str(decimals) + 'f') % value
                    if not isinstance(value, decimal.Decimal):
                        value = decimal.Decimal(str(value))
                    colset[fieldname] = value
                elif field_type.startswith('list:integer'):
                    if not self.dbengine=='google:datastore':
                        colset[fieldname] = bar_decode_integer(value)
                    else:
                        colset[fieldname] = value
                elif field_type.startswith('list:reference'):
                    if not self.dbengine=='google:datastore':
                        colset[fieldname] = bar_decode_integer(value)
                    else:
                        colset[fieldname] = value
                elif field_type.startswith('list:string'):
                    if not self.dbengine=='google:datastore':
                        colset[fieldname] = bar_decode_string(value)
                    else:
                        colset[fieldname] = value
                else:
                    colset[fieldname] = value
                if field_type == 'id':
                    id = colset[field.name]
                    colset.update_record = lambda _ = (colset, table, id), **a: update_record(_, a)
                    colset.delete_record = lambda t = table, i = id: t._db(t._id==i).delete()
                    for (referee_table, referee_name) in \
                            table._referenced_by:
                        s = db[referee_table][referee_name]
                        referee_link = db._referee_name and \
                            db._referee_name % dict(table=referee_table,field=referee_name)
                        if referee_link and not referee_link in colset:
                            colset[referee_link] = Set(db, s == id)
                    colset['id'] = id
            new_rows.append(new_row)

        rowsobj = Rows(db, new_rows, colnames, rawrows=rows)

        ### new style virtual fields
        vf = []
        for tablename in virtualtables:
            table = db[tablename]
            fields_virtual = [(f,v) for (f,v) in table.items() if isinstance(v,FieldVirtual)]
            fields_lazy = [(f,v) for (f,v) in table.items() if isinstance(v,FieldLazy)]
            if fields_virtual or fields_lazy:
                for row in rowsobj.records:
                    box = row[tablename] 
                    for f,v in fields_virtual:                    
                        box[f] = v.f(row)
                    for f,v in fields_lazy:                    
                        box[f] = VirtualCommand(v.f,row)

        ### old style virtual fields
        for tablename in virtualtables:
            for item in db[tablename].virtualfields:
                try:
                    rowsobj = rowsobj.setvirtualfields(**{tablename:item})
                except KeyError:
                    # to avoid breaking virtualfields when partial select
                    pass
        return rowsobj

    def filter_tenant(self,query,tablenames):
        fieldname = self.db._request_tenant
        for tablename in tablenames:
            table = self.db[tablename]
            if fieldname in table:
                default = table[fieldname].default
                if not default is None:
                    query = query&(table[fieldname]==default)
        return query

###################################################################################
# List of all the available adapters, they all extend BaseAdapter
###################################################################################

class SQLiteAdapter(BaseAdapter):

    driver = globals().get('sqlite3',None)

    def EXTRACT(self,field,what):
        return "web2py_extract('%s',%s)" % (what,self.expand(field))

    @staticmethod
    def web2py_extract(lookup, s):
        table = {
            'year': (0, 4),
            'month': (5, 7),
            'day': (8, 10),
            'hour': (11, 13),
            'minute': (14, 16),
            'second': (17, 19),
            }
        try:
            (i, j) = table[lookup]
            return int(s[i:j])
        except:
            return None

    def __init__(self,db,uri,pool_size=0,folder=None,db_codec ='UTF-8',
                 credential_decoder=lambda x:x, driver_args={},
                 adapter_args={}):
        self.db = db
        self.dbengine = "sqlite"
        self.uri = uri
        self.pool_size = pool_size
        self.folder = folder
        self.db_codec = db_codec
        self.find_or_make_work_folder()
        path_encoding = sys.getfilesystemencoding() or locale.getdefaultlocale()[1] or 'utf8'
        if uri.startswith('sqlite:memory'):
            dbpath = ':memory:'
        else:
            dbpath = uri.split('://')[1]
            if dbpath[0] != '/':
                dbpath = os.path.join(self.folder.decode(path_encoding).encode('utf8'),dbpath)
        if not 'check_same_thread' in driver_args:
            driver_args['check_same_thread'] = False
        def connect(dbpath=dbpath, driver_args=driver_args):
            return self.driver.Connection(dbpath, **driver_args)
        self.pool_connection(connect)
        self.cursor = self.connection.cursor()
        self.connection.create_function('web2py_extract', 2, SQLiteAdapter.web2py_extract)

    def _truncate(self,table,mode = ''):
        tablename = table._tablename
        return ['DELETE FROM %s;' % tablename,
                "DELETE FROM sqlite_sequence WHERE name='%s';" % tablename]

    def lastrowid(self,table):
        return self.cursor.lastrowid


class JDBCSQLiteAdapter(SQLiteAdapter):

    driver = globals().get('zxJDBC',None)

    def __init__(self,db,uri,pool_size=0,folder=None,db_codec ='UTF-8',
                 credential_decoder=lambda x:x, driver_args={},
                 adapter_args={}):
        self.db = db
        self.dbengine = "sqlite"
        self.uri = uri
        self.pool_size = pool_size
        self.folder = folder
        self.db_codec = db_codec
        self.find_or_make_work_folder()
        path_encoding = sys.getfilesystemencoding() or locale.getdefaultlocale()[1] or 'utf8'
        if uri.startswith('sqlite:memory'):
            dbpath = ':memory:'
        else:
            dbpath = uri.split('://')[1]
            if dbpath[0] != '/':
                dbpath = os.path.join(self.folder.decode(path_encoding).encode('utf8'),dbpath)
        def connect(dbpath=dbpath,driver_args=driver_args):
            return self.driver.connect(java.sql.DriverManager.getConnection('jdbc:sqlite:'+dbpath),**driver_args)
        self.pool_connection(connect)
        self.cursor = self.connection.cursor()
        # FIXME http://www.zentus.com/sqlitejdbc/custom_functions.html for UDFs
        # self.connection.create_function('web2py_extract', 2, SQLiteAdapter.web2py_extract)

    def execute(self,a):
        return self.log_execute(a[:-1])


class MySQLAdapter(BaseAdapter):

    driver = globals().get('pymysql',None)
    maxcharlength = 255
    commit_on_alter_table = True
    support_distributed_transaction = True
    types = {
        'boolean': 'CHAR(1)',
        'string': 'VARCHAR(%(length)s)',
        'text': 'LONGTEXT',
        'password': 'VARCHAR(%(length)s)',
        'blob': 'LONGBLOB',
        'upload': 'VARCHAR(%(length)s)',
        'integer': 'INT',
        'double': 'DOUBLE',
        'decimal': 'NUMERIC(%(precision)s,%(scale)s)',
        'date': 'DATE',
        'time': 'TIME',
        'datetime': 'DATETIME',
        'id': 'INT AUTO_INCREMENT NOT NULL',
        'reference': 'INT, INDEX %(field_name)s__idx (%(field_name)s), FOREIGN KEY (%(field_name)s) REFERENCES %(foreign_key)s ON DELETE %(on_delete_action)s',
        'list:integer': 'LONGTEXT',
        'list:string': 'LONGTEXT',
        'list:reference': 'LONGTEXT',
        }

    def RANDOM(self):
        return 'RAND()'

    def SUBSTRING(self,field,parameters):
        return 'SUBSTRING(%s,%s,%s)' % (self.expand(field), parameters[0], parameters[1])

    def _drop(self,table,mode):
        # breaks db integrity but without this mysql does not drop table
        return ['SET FOREIGN_KEY_CHECKS=0;','DROP TABLE %s;' % table,'SET FOREIGN_KEY_CHECKS=1;']

    def distributed_transaction_begin(self,key):
        self.execute('XA START;')

    def prepare(self,key):
        self.execute("XA END;")
        self.execute("XA PREPARE;")

    def commit_prepared(self,ley):
        self.execute("XA COMMIT;")

    def rollback_prepared(self,key):
        self.execute("XA ROLLBACK;")

    def concat_add(self,table):
        return '; ALTER TABLE %s ADD ' % table

    def __init__(self,db,uri,pool_size=0,folder=None,db_codec ='UTF-8',
                 credential_decoder=lambda x:x, driver_args={},
                 adapter_args={}):
        self.db = db
        self.dbengine = "mysql"
        self.uri = uri
        self.pool_size = pool_size
        self.folder = folder
        self.db_codec = db_codec
        self.find_or_make_work_folder()
        uri = uri.split('://')[1]
        m = re.compile('^(?P<user>[^:@]+)(\:(?P<password>[^@]*))?@(?P<host>[^\:/]+)(\:(?P<port>[0-9]+))?/(?P<db>[^?]+)(\?set_encoding=(?P<charset>\w+))?$').match(uri)
        if not m:
            raise SyntaxError, \
                "Invalid URI string in DAL: %s" % self.uri
        user = credential_decoder(m.group('user'))
        if not user:
            raise SyntaxError, 'User required'
        password = credential_decoder(m.group('password'))
        if not password:
            password = ''
        host = m.group('host')
        if not host:
            raise SyntaxError, 'Host name required'
        db = m.group('db')
        if not db:
            raise SyntaxError, 'Database name required'
        port = int(m.group('port') or '3306')
        charset = m.group('charset') or 'utf8'
        driver_args.update(dict(db=db,
                                user=credential_decoder(user),
                                passwd=credential_decoder(password),
                                host=host,
                                port=port,
                                charset=charset))
        def connect(driver_args=driver_args):
            return self.driver.connect(**driver_args)
        self.pool_connection(connect)
        self.cursor = self.connection.cursor()
        self.execute('SET FOREIGN_KEY_CHECKS=1;')
        self.execute("SET sql_mode='NO_BACKSLASH_ESCAPES';")

    def lastrowid(self,table):
        self.execute('select last_insert_id();')
        return int(self.cursor.fetchone()[0])

class PostgreSQLAdapter(BaseAdapter):

    driver = globals().get('psycopg2',None)

    support_distributed_transaction = True
    types = {
        'boolean': 'CHAR(1)',
        'string': 'VARCHAR(%(length)s)',
        'text': 'TEXT',
        'password': 'VARCHAR(%(length)s)',
        'blob': 'BYTEA',
        'upload': 'VARCHAR(%(length)s)',
        'integer': 'INTEGER',
        'double': 'FLOAT8',
        'decimal': 'NUMERIC(%(precision)s,%(scale)s)',
        'date': 'DATE',
        'time': 'TIME',
        'datetime': 'TIMESTAMP',
        'id': 'SERIAL PRIMARY KEY',
        'reference': 'INTEGER REFERENCES %(foreign_key)s ON DELETE %(on_delete_action)s',
        'list:integer': 'TEXT',
        'list:string': 'TEXT',
        'list:reference': 'TEXT',
        }

    def sequence_name(self,table):
        return '%s_id_Seq' % table

    def RANDOM(self):
        return 'RANDOM()'

    def distributed_transaction_begin(self,key):
        return

    def prepare(self,key):
        self.execute("PREPARE TRANSACTION '%s';" % key)

    def commit_prepared(self,key):
        self.execute("COMMIT PREPARED '%s';" % key)

    def rollback_prepared(self,key):
        self.execute("ROLLBACK PREPARED '%s';" % key)

    def create_sequence_and_triggers(self, query, table, **args):
        # following lines should only be executed if table._sequence_name does not exist
        # self.execute('CREATE SEQUENCE %s;' % table._sequence_name)
        # self.execute("ALTER TABLE %s ALTER COLUMN %s SET DEFAULT NEXTVAL('%s');" \
        #              % (table._tablename, table._fieldname, table._sequence_name))
        self.execute(query)

    def __init__(self,db,uri,pool_size=0,folder=None,db_codec ='UTF-8',
                 credential_decoder=lambda x:x, driver_args={},
                 adapter_args={}):
        self.db = db
        self.dbengine = "postgres"
        self.uri = uri
        self.pool_size = pool_size
        self.folder = folder
        self.db_codec = db_codec
        self.find_or_make_work_folder()
        uri = uri.split('://')[1]
        m = re.compile('^(?P<user>[^:@]+)(\:(?P<password>[^@]*))?@(?P<host>[^\:@/]+)(\:(?P<port>[0-9]+))?/(?P<db>[^\?]+)(\?sslmode=(?P<sslmode>.+))?$').match(uri)
        if not m:
            raise SyntaxError, "Invalid URI string in DAL"
        user = credential_decoder(m.group('user'))
        if not user:
            raise SyntaxError, 'User required'
        password = credential_decoder(m.group('password'))
        if not password:
            password = ''
        host = m.group('host')
        if not host:
            raise SyntaxError, 'Host name required'
        db = m.group('db')
        if not db:
            raise SyntaxError, 'Database name required'
        port = m.group('port') or '5432'
        sslmode = m.group('sslmode')
        if sslmode:
            msg = ("dbname='%s' user='%s' host='%s'"
                   "port=%s password='%s' sslmode='%s'") \
                   % (db, user, host, port, password, sslmode)
        else:
            msg = ("dbname='%s' user='%s' host='%s'"
                   "port=%s password='%s'") \
                   % (db, user, host, port, password)
        def connect(msg=msg,driver_args=driver_args):
            return self.driver.connect(msg,**driver_args)
        self.pool_connection(connect)
        self.connection.set_client_encoding('UTF8')
        self.cursor = self.connection.cursor()
        self.execute('BEGIN;')
        self.execute("SET CLIENT_ENCODING TO 'UNICODE';")
        self.execute("SET standard_conforming_strings=on;")

    def lastrowid(self,table):
        self.execute("select currval('%s')" % table._sequence_name)
        return int(self.cursor.fetchone()[0])

    def LIKE(self,first,second):
        return '(%s ILIKE %s)' % (self.expand(first),self.expand(second,'string'))

    def STARTSWITH(self,first,second):
        return '(%s ILIKE %s)' % (self.expand(first),self.expand(second+'%','string'))

    def ENDSWITH(self,first,second):
        return '(%s ILIKE %s)' % (self.expand(first),self.expand('%'+second,'string'))

    def CONTAINS(self,first,second):
        if first.type in ('string','text'):
            key = '%'+str(second).replace('%','%%')+'%'
        elif first.type.startswith('list:'):
            key = '%|'+str(second).replace('|','||').replace('%','%%')+'|%'
        return '(%s ILIKE %s)' % (self.expand(first),self.expand(key,'string'))

class JDBCPostgreSQLAdapter(PostgreSQLAdapter):

    def __init__(self,db,uri,pool_size=0,folder=None,db_codec ='UTF-8',
                 credential_decoder=lambda x:x, driver_args={},
                 adapter_args={}):
        self.db = db
        self.dbengine = "postgres"
        self.uri = uri
        self.pool_size = pool_size
        self.folder = folder
        self.db_codec = db_codec
        self.find_or_make_work_folder()
        uri = uri.split('://')[1]
        m = re.compile('^(?P<user>[^:@]+)(\:(?P<password>[^@]*))?@(?P<host>[^\:/]+)(\:(?P<port>[0-9]+))?/(?P<db>.+)$').match(uri)
        if not m:
            raise SyntaxError, "Invalid URI string in DAL"
        user = credential_decoder(m.group('user'))
        if not user:
            raise SyntaxError, 'User required'
        password = credential_decoder(m.group('password'))
        if not password:
            password = ''
        host = m.group('host')
        if not host:
            raise SyntaxError, 'Host name required'
        db = m.group('db')
        if not db:
            raise SyntaxError, 'Database name required'
        port = m.group('port') or '5432'
        msg = ('jdbc:postgresql://%s:%s/%s' % (host, port, db), user, password)
        def connect(msg=msg,driver_args=driver_args):
            return self.driver.connect(*msg,**driver_args)
        self.pool_connection(connect)
        self.connection.set_client_encoding('UTF8')
        self.cursor = self.connection.cursor()
        self.execute('BEGIN;')
        self.execute("SET CLIENT_ENCODING TO 'UNICODE';")


class OracleAdapter(BaseAdapter):

    driver = globals().get('cx_Oracle',None)

    commit_on_alter_table = False
    types = {
        'boolean': 'CHAR(1)',
        'string': 'VARCHAR2(%(length)s)',
        'text': 'CLOB',
        'password': 'VARCHAR2(%(length)s)',
        'blob': 'CLOB',
        'upload': 'VARCHAR2(%(length)s)',
        'integer': 'INT',
        'double': 'FLOAT',
        'decimal': 'NUMERIC(%(precision)s,%(scale)s)',
        'date': 'DATE',
        'time': 'CHAR(8)',
        'datetime': 'DATE',
        'id': 'NUMBER PRIMARY KEY',
        'reference': 'NUMBER, CONSTRAINT %(constraint_name)s FOREIGN KEY (%(field_name)s) REFERENCES %(foreign_key)s ON DELETE %(on_delete_action)s',
        'list:integer': 'CLOB',
        'list:string': 'CLOB',
        'list:reference': 'CLOB',
        }

    def sequence_name(self,tablename):
        return '%s_sequence' % tablename

    def trigger_name(self,tablename):
        return '%s_trigger' % tablename

    def LEFT_JOIN(self):
        return 'LEFT OUTER JOIN'

    def RANDOM(self):
        return 'dbms_random.value'

    def NOT_NULL(self,default,field_type):
        return 'DEFAULT %s NOT NULL' % self.represent(default,field_type)

    def _drop(self,table,mode):
        sequence_name = table._sequence_name
        return ['DROP TABLE %s %s;' % (table, mode), 'DROP SEQUENCE %s;' % sequence_name]

    def select_limitby(self, sql_s, sql_f, sql_t, sql_w, sql_o, limitby):
        if limitby:
            (lmin, lmax) = limitby
            if len(sql_w) > 1:
                sql_w_row = sql_w + ' AND w_row > %i' % lmin
            else:
                sql_w_row = 'WHERE w_row > %i' % lmin
            return 'SELECT %s %s FROM (SELECT w_tmp.*, ROWNUM w_row FROM (SELECT %s FROM %s%s%s) w_tmp WHERE ROWNUM<=%i) %s %s %s;' % (sql_s, sql_f, sql_f, sql_t, sql_w, sql_o, lmax, sql_t, sql_w_row, sql_o)
        return 'SELECT %s %s FROM %s%s%s;' % (sql_s, sql_f, sql_t, sql_w, sql_o)

    def constraint_name(self, tablename, fieldname):
        constraint_name = BaseAdapter.constraint_name(self, tablename, fieldname)
        if len(constraint_name)>30:
            constraint_name = '%s_%s__constraint' % (tablename[:10], fieldname[:7])
        return constraint_name

    def represent_exceptions(self, obj, fieldtype):
        if fieldtype == 'blob':
            obj = base64.b64encode(str(obj))
            return ":CLOB('%s')" % obj
        elif fieldtype == 'date':
            if isinstance(obj, (datetime.date, datetime.datetime)):
                obj = obj.isoformat()[:10]
            else:
                obj = str(obj)
            return "to_date('%s','yyyy-mm-dd')" % obj
        elif fieldtype == 'datetime':
            if isinstance(obj, datetime.datetime):
                obj = obj.isoformat()[:19].replace('T',' ')
            elif isinstance(obj, datetime.date):
                obj = obj.isoformat()[:10]+' 00:00:00'
            else:
                obj = str(obj)
            return "to_date('%s','yyyy-mm-dd hh24:mi:ss')" % obj
        return None

    def __init__(self,db,uri,pool_size=0,folder=None,db_codec ='UTF-8',
                 credential_decoder=lambda x:x, driver_args={},
                 adapter_args={}):
        self.db = db
        self.dbengine = "oracle"
        self.uri = uri
        self.pool_size = pool_size
        self.folder = folder
        self.db_codec = db_codec
        self.find_or_make_work_folder()
        uri = uri.split('://')[1]
        if not 'threaded' in driver_args:
            driver_args['threaded']=True
        def connect(uri=uri,driver_args=driver_args):
            return self.driver.connect(uri,**driver_args)
        self.pool_connection(connect)
        self.cursor = self.connection.cursor()
        self.execute("ALTER SESSION SET NLS_DATE_FORMAT = 'YYYY-MM-DD HH24:MI:SS';")
        self.execute("ALTER SESSION SET NLS_TIMESTAMP_FORMAT = 'YYYY-MM-DD HH24:MI:SS';")
    oracle_fix = re.compile("[^']*('[^']*'[^']*)*\:(?P<clob>CLOB\('([^']+|'')*'\))")

    def execute(self, command):
        args = []
        i = 1
        while True:
            m = self.oracle_fix.match(command)
            if not m:
                break
            command = command[:m.start('clob')] + str(i) + command[m.end('clob'):]
            args.append(m.group('clob')[6:-2].replace("''", "'"))
            i += 1
        return self.log_execute(command[:-1], args)

    def create_sequence_and_triggers(self, query, table, **args):
        tablename = table._tablename
        sequence_name = table._sequence_name
        trigger_name = table._trigger_name
        self.execute(query)
        self.execute('CREATE SEQUENCE %s START WITH 1 INCREMENT BY 1 NOMAXVALUE;' % sequence_name)
        self.execute('CREATE OR REPLACE TRIGGER %s BEFORE INSERT ON %s FOR EACH ROW BEGIN SELECT %s.nextval INTO :NEW.id FROM DUAL; END;\n' % (trigger_name, tablename, sequence_name))

    def lastrowid(self,table):
        sequence_name = table._sequence_name
        self.execute('SELECT %s.currval FROM dual;' % sequence_name)
        return int(self.cursor.fetchone()[0])


class MSSQLAdapter(BaseAdapter):

    driver = globals().get('pyodbc',None)

    types = {
        'boolean': 'BIT',
        'string': 'VARCHAR(%(length)s)',
        'text': 'TEXT',
        'password': 'VARCHAR(%(length)s)',
        'blob': 'IMAGE',
        'upload': 'VARCHAR(%(length)s)',
        'integer': 'INT',
        'double': 'FLOAT',
        'decimal': 'NUMERIC(%(precision)s,%(scale)s)',
        'date': 'DATETIME',
        'time': 'CHAR(8)',
        'datetime': 'DATETIME',
        'id': 'INT IDENTITY PRIMARY KEY',
        'reference': 'INT NULL, CONSTRAINT %(constraint_name)s FOREIGN KEY (%(field_name)s) REFERENCES %(foreign_key)s ON DELETE %(on_delete_action)s',
        'reference FK': ', CONSTRAINT FK_%(constraint_name)s FOREIGN KEY (%(field_name)s) REFERENCES %(foreign_key)s ON DELETE %(on_delete_action)s',
        'reference TFK': ' CONSTRAINT FK_%(foreign_table)s_PK FOREIGN KEY (%(field_name)s) REFERENCES %(foreign_table)s (%(foreign_key)s) ON DELETE %(on_delete_action)s',
        'list:integer': 'TEXT',
        'list:string': 'TEXT',
        'list:reference': 'TEXT',
        }

    def EXTRACT(self,field,what):
        return "DATEPART(%s,%s)" % (what, self.expand(field))

    def LEFT_JOIN(self):
        return 'LEFT OUTER JOIN'

    def RANDOM(self):
        return 'NEWID()'

    def ALLOW_NULL(self):
        return ' NULL'

    def SUBSTRING(self,field,parameters):
        return 'SUBSTRING(%s,%s,%s)' % (self.expand(field), parameters[0], parameters[1])

    def PRIMARY_KEY(self,key):
        return 'PRIMARY KEY CLUSTERED (%s)' % key

    def select_limitby(self, sql_s, sql_f, sql_t, sql_w, sql_o, limitby):
        if limitby:
            (lmin, lmax) = limitby
            sql_s += ' TOP %i' % lmax
        return 'SELECT %s %s FROM %s%s%s;' % (sql_s, sql_f, sql_t, sql_w, sql_o)

    def represent_exceptions(self, obj, fieldtype):
        if fieldtype == 'boolean':
            if obj and not str(obj)[0].upper() == 'F':
                return '1'
            else:
                return '0'
        return None

    def __init__(self,db,uri,pool_size=0,folder=None,db_codec ='UTF-8',
                 credential_decoder=lambda x:x, driver_args={},
                    adapter_args={}, fake_connect=False):
        self.db = db
        self.dbengine = "mssql"
        self.uri = uri
        self.pool_size = pool_size
        self.folder = folder
        self.db_codec = db_codec
        self.find_or_make_work_folder()
        # ## read: http://bytes.com/groups/python/460325-cx_oracle-utf8
        uri = uri.split('://')[1]
        if '@' not in uri:
            try:
                m = re.compile('^(?P<dsn>.+)$').match(uri)
                if not m:
                    raise SyntaxError, \
                        'Parsing uri string(%s) has no result' % self.uri
                dsn = m.group('dsn')
                if not dsn:
                    raise SyntaxError, 'DSN required'
            except SyntaxError, e:
                logger.error('NdGpatch error')
                raise e
            cnxn = 'DSN=%s' % dsn
        else:
            m = re.compile('^(?P<user>[^:@]+)(\:(?P<password>[^@]*))?@(?P<host>[^\:/]+)(\:(?P<port>[0-9]+))?/(?P<db>[^\?]+)(\?(?P<urlargs>.*))?$').match(uri)
            if not m:
                raise SyntaxError, \
                    "Invalid URI string in DAL: %s" % uri
            user = credential_decoder(m.group('user'))
            if not user:
                raise SyntaxError, 'User required'
            password = credential_decoder(m.group('password'))
            if not password:
                password = ''
            host = m.group('host')
            if not host:
                raise SyntaxError, 'Host name required'
            db = m.group('db')
            if not db:
                raise SyntaxError, 'Database name required'
            port = m.group('port') or '1433'
            # Parse the optional url name-value arg pairs after the '?'
            # (in the form of arg1=value1&arg2=value2&...)
            # Default values (drivers like FreeTDS insist on uppercase parameter keys)
            argsdict = { 'DRIVER':'{SQL Server}' }
            urlargs = m.group('urlargs') or ''
            argpattern = re.compile('(?P<argkey>[^=]+)=(?P<argvalue>[^&]*)')
            for argmatch in argpattern.finditer(urlargs):
                argsdict[str(argmatch.group('argkey')).upper()] = argmatch.group('argvalue')
            urlargs = ';'.join(['%s=%s' % (ak, av) for (ak, av) in argsdict.items()])
            cnxn = 'SERVER=%s;PORT=%s;DATABASE=%s;UID=%s;PWD=%s;%s' \
                % (host, port, db, user, password, urlargs)
        def connect(cnxn=cnxn,driver_args=driver_args):
            return self.driver.connect(cnxn,**driver_args)
        if not fake_connect:
            self.pool_connection(connect)
            self.cursor = self.connection.cursor()

    def lastrowid(self,table):
        #self.execute('SELECT @@IDENTITY;')
        self.execute('SELECT SCOPE_IDENTITY();')
        return int(self.cursor.fetchone()[0])

    def integrity_error_class(self):
        return pyodbc.IntegrityError

    def rowslice(self,rows,minimum=0,maximum=None):
        if maximum is None:
            return rows[minimum:]
        return rows[minimum:maximum]


class MSSQL2Adapter(MSSQLAdapter):
    types = {
        'boolean': 'CHAR(1)',
        'string': 'NVARCHAR(%(length)s)',
        'text': 'NTEXT',
        'password': 'NVARCHAR(%(length)s)',
        'blob': 'IMAGE',
        'upload': 'NVARCHAR(%(length)s)',
        'integer': 'INT',
        'double': 'FLOAT',
        'decimal': 'NUMERIC(%(precision)s,%(scale)s)',
        'date': 'DATETIME',
        'time': 'CHAR(8)',
        'datetime': 'DATETIME',
        'id': 'INT IDENTITY PRIMARY KEY',
        'reference': 'INT, CONSTRAINT %(constraint_name)s FOREIGN KEY (%(field_name)s) REFERENCES %(foreign_key)s ON DELETE %(on_delete_action)s',
        'reference FK': ', CONSTRAINT FK_%(constraint_name)s FOREIGN KEY (%(field_name)s) REFERENCES %(foreign_key)s ON DELETE %(on_delete_action)s',
        'reference TFK': ' CONSTRAINT FK_%(foreign_table)s_PK FOREIGN KEY (%(field_name)s) REFERENCES %(foreign_table)s (%(foreign_key)s) ON DELETE %(on_delete_action)s',
        'list:integer': 'NTEXT',
        'list:string': 'NTEXT',
        'list:reference': 'NTEXT',
        }

    def represent(self, obj, fieldtype):
        value = BaseAdapter.represent(self, obj, fieldtype)
        if (fieldtype == 'string' or fieldtype == 'text') and value[:1]=="'":
            value = 'N'+value
        return value

    def execute(self,a):
        return self.log_execute(a.decode('utf8'))


class FireBirdAdapter(BaseAdapter):

    driver = globals().get('pyodbc',None)

    commit_on_alter_table = False
    support_distributed_transaction = True
    types = {
        'boolean': 'CHAR(1)',
        'string': 'VARCHAR(%(length)s)',
        'text': 'BLOB SUB_TYPE 1',
        'password': 'VARCHAR(%(length)s)',
        'blob': 'BLOB SUB_TYPE 0',
        'upload': 'VARCHAR(%(length)s)',
        'integer': 'INTEGER',
        'double': 'DOUBLE PRECISION',
        'decimal': 'DECIMAL(%(precision)s,%(scale)s)',
        'date': 'DATE',
        'time': 'TIME',
        'datetime': 'TIMESTAMP',
        'id': 'INTEGER PRIMARY KEY',
        'reference': 'INTEGER REFERENCES %(foreign_key)s ON DELETE %(on_delete_action)s',
        'list:integer': 'BLOB SUB_TYPE 1',
        'list:string': 'BLOB SUB_TYPE 1',
        'list:reference': 'BLOB SUB_TYPE 1',
        }

    def sequence_name(self,tablename):
        return 'genid_%s' % tablename

    def trigger_name(self,tablename):
        return 'trg_id_%s' % tablename

    def RANDOM(self):
        return 'RAND()'

    def NOT_NULL(self,default,field_type):
        return 'DEFAULT %s NOT NULL' % self.represent(default,field_type)

    def SUBSTRING(self,field,parameters):
        return 'SUBSTRING(%s from %s for %s)' % (self.expand(field), parameters[0], parameters[1])

    def _drop(self,table,mode):
        sequence_name = table._sequence_name
        return ['DROP TABLE %s %s;' % (table, mode), 'DROP GENERATOR %s;' % sequence_name]

    def select_limitby(self, sql_s, sql_f, sql_t, sql_w, sql_o, limitby):
        if limitby:
            (lmin, lmax) = limitby
            sql_s += ' FIRST %i SKIP %i' % (lmax - lmin, lmin)
        return 'SELECT %s %s FROM %s%s%s;' % (sql_s, sql_f, sql_t, sql_w, sql_o)

    def _truncate(self,table,mode = ''):
        return ['DELETE FROM %s;' % table._tablename,
                'SET GENERATOR %s TO 0;' % table._sequence_name]

    def __init__(self,db,uri,pool_size=0,folder=None,db_codec ='UTF-8',
                 credential_decoder=lambda x:x, driver_args={},
                 adapter_args={}):
        self.db = db
        self.dbengine = "firebird"
        self.uri = uri
        self.pool_size = pool_size
        self.folder = folder
        self.db_codec = db_codec
        self.find_or_make_work_folder()
        uri = uri.split('://')[1]
        m = re.compile('^(?P<user>[^:@]+)(\:(?P<password>[^@]*))?@(?P<host>[^\:/]+)(\:(?P<port>[0-9]+))?/(?P<db>.+?)(\?set_encoding=(?P<charset>\w+))?$').match(uri)
        if not m:
            raise SyntaxError, "Invalid URI string in DAL: %s" % uri
        user = credential_decoder(m.group('user'))
        if not user:
            raise SyntaxError, 'User required'
        password = credential_decoder(m.group('password'))
        if not password:
            password = ''
        host = m.group('host')
        if not host:
            raise SyntaxError, 'Host name required'
        port = int(m.group('port') or 3050)
        db = m.group('db')
        if not db:
            raise SyntaxError, 'Database name required'
        charset = m.group('charset') or 'UTF8'
        driver_args.update(dict(dsn='%s/%s:%s' % (host,port,db),
                                   user = credential_decoder(user),
                                   password = credential_decoder(password),
                                   charset = charset))
        if adapter_args.has_key('driver_name'):
            if adapter_args['driver_name'] == 'kinterbasdb':
                self.driver = kinterbasdb
            elif adapter_args['driver_name'] == 'firebirdsql':
                self.driver = firebirdsql
        else:
            self.driver = kinterbasdb
        def connect(driver_args=driver_args):
            return self.driver.connect(**driver_args)
        self.pool_connection(connect)
        self.cursor = self.connection.cursor()

    def create_sequence_and_triggers(self, query, table, **args):
        tablename = table._tablename
        sequence_name = table._sequence_name
        trigger_name = table._trigger_name
        self.execute(query)
        self.execute('create generator %s;' % sequence_name)
        self.execute('set generator %s to 0;' % sequence_name)
        self.execute('create trigger %s for %s active before insert position 0 as\nbegin\nif(new.id is null) then\nbegin\nnew.id = gen_id(%s, 1);\nend\nend;' % (trigger_name, tablename, sequence_name))

    def lastrowid(self,table):
        sequence_name = table._sequence_name
        self.execute('SELECT gen_id(%s, 0) FROM rdb$database' % sequence_name)
        return int(self.cursor.fetchone()[0])


class FireBirdEmbeddedAdapter(FireBirdAdapter):

    def __init__(self,db,uri,pool_size=0,folder=None,db_codec ='UTF-8',
                 credential_decoder=lambda x:x, driver_args={},
                 adapter_args={}):
        self.db = db
        self.dbengine = "firebird"
        self.uri = uri
        self.pool_size = pool_size
        self.folder = folder
        self.db_codec = db_codec
        self.find_or_make_work_folder()
        uri = uri.split('://')[1]
        m = re.compile('^(?P<user>[^:@]+)(\:(?P<password>[^@]*))?@(?P<path>[^\?]+)(\?set_encoding=(?P<charset>\w+))?$').match(uri)
        if not m:
            raise SyntaxError, \
                "Invalid URI string in DAL: %s" % self.uri
        user = credential_decoder(m.group('user'))
        if not user:
            raise SyntaxError, 'User required'
        password = credential_decoder(m.group('password'))
        if not password:
            password = ''
        pathdb = m.group('path')
        if not pathdb:
            raise SyntaxError, 'Path required'
        charset = m.group('charset')
        if not charset:
            charset = 'UTF8'
        host = ''
        driver_args.update(dict(host=host,
                                   database=pathdb,
                                   user=credential_decoder(user),
                                   password=credential_decoder(password),
                                   charset=charset))
        #def connect(driver_args=driver_args):
        #    return kinterbasdb.connect(**driver_args)
        if adapter_args.has_key('driver_name'):
            if adapter_args['driver_name'] == 'kinterbasdb':
                self.driver = kinterbasdb
            elif adapter_args['driver_name'] == 'firebirdsql':
                self.driver = firebirdsql
        else:
            self.driver = kinterbasdb
        def connect(driver_args=driver_args):
            return self.driver.connect(**driver_args)
        self.pool_connection(connect)
        self.cursor = self.connection.cursor()


class InformixAdapter(BaseAdapter):

    driver = globals().get('informixdb',None)

    types = {
        'boolean': 'CHAR(1)',
        'string': 'VARCHAR(%(length)s)',
        'text': 'BLOB SUB_TYPE 1',
        'password': 'VARCHAR(%(length)s)',
        'blob': 'BLOB SUB_TYPE 0',
        'upload': 'VARCHAR(%(length)s)',
        'integer': 'INTEGER',
        'double': 'FLOAT',
        'decimal': 'NUMERIC(%(precision)s,%(scale)s)',
        'date': 'DATE',
        'time': 'CHAR(8)',
        'datetime': 'DATETIME',
        'id': 'SERIAL',
        'reference': 'INTEGER REFERENCES %(foreign_key)s ON DELETE %(on_delete_action)s',
        'reference FK': 'REFERENCES %(foreign_key)s ON DELETE %(on_delete_action)s CONSTRAINT FK_%(table_name)s_%(field_name)s',
        'reference TFK': 'FOREIGN KEY (%(field_name)s) REFERENCES %(foreign_table)s (%(foreign_key)s) ON DELETE %(on_delete_action)s CONSTRAINT TFK_%(table_name)s_%(field_name)s',
        'list:integer': 'BLOB SUB_TYPE 1',
        'list:string': 'BLOB SUB_TYPE 1',
        'list:reference': 'BLOB SUB_TYPE 1',
        }

    def RANDOM(self):
        return 'Random()'

    def NOT_NULL(self,default,field_type):
        return 'DEFAULT %s NOT NULL' % self.represent(default,field_type)

    def select_limitby(self, sql_s, sql_f, sql_t, sql_w, sql_o, limitby):
        if limitby:
            (lmin, lmax) = limitby
            fetch_amt = lmax - lmin
            dbms_version = int(self.connection.dbms_version.split('.')[0])
            if lmin and (dbms_version >= 10):
                # Requires Informix 10.0+
                sql_s += ' SKIP %d' % (lmin, )
            if fetch_amt and (dbms_version >= 9):
                # Requires Informix 9.0+
                sql_s += ' FIRST %d' % (fetch_amt, )
        return 'SELECT %s %s FROM %s%s%s;' % (sql_s, sql_f, sql_t, sql_w, sql_o)

    def represent_exceptions(self, obj, fieldtype):
        if fieldtype == 'date':
            if isinstance(obj, (datetime.date, datetime.datetime)):
                obj = obj.isoformat()[:10]
            else:
                obj = str(obj)
            return "to_date('%s','yyyy-mm-dd')" % obj
        elif fieldtype == 'datetime':
            if isinstance(obj, datetime.datetime):
                obj = obj.isoformat()[:19].replace('T',' ')
            elif isinstance(obj, datetime.date):
                obj = obj.isoformat()[:10]+' 00:00:00'
            else:
                obj = str(obj)
            return "to_date('%s','yyyy-mm-dd hh24:mi:ss')" % obj
        return None

    def __init__(self,db,uri,pool_size=0,folder=None,db_codec ='UTF-8',
                 credential_decoder=lambda x:x, driver_args={},
                 adapter_args={}):
        self.db = db
        self.dbengine = "informix"
        self.uri = uri
        self.pool_size = pool_size
        self.folder = folder
        self.db_codec = db_codec
        self.find_or_make_work_folder()
        uri = uri.split('://')[1]
        m = re.compile('^(?P<user>[^:@]+)(\:(?P<password>[^@]*))?@(?P<host>[^\:/]+)(\:(?P<port>[0-9]+))?/(?P<db>.+)$').match(uri)
        if not m:
            raise SyntaxError, \
                "Invalid URI string in DAL: %s" % self.uri
        user = credential_decoder(m.group('user'))
        if not user:
            raise SyntaxError, 'User required'
        password = credential_decoder(m.group('password'))
        if not password:
            password = ''
        host = m.group('host')
        if not host:
            raise SyntaxError, 'Host name required'
        db = m.group('db')
        if not db:
            raise SyntaxError, 'Database name required'
        user = credential_decoder(user)
        password = credential_decoder(password)
        dsn = '%s@%s' % (db,host)
        driver_args.update(dict(user=user,password=password,autocommit=True))
        def connect(dsn=dsn,driver_args=driver_args):
            return self.driver.connect(dsn,**driver_args)
        self.pool_connection(connect)
        self.cursor = self.connection.cursor()

    def execute(self,command):
        if command[-1:]==';':
            command = command[:-1]
        return self.log_execute(command)

    def lastrowid(self,table):
        return self.cursor.sqlerrd[1]

    def integrity_error_class(self):
        return informixdb.IntegrityError


class DB2Adapter(BaseAdapter):

    driver = globals().get('pyodbc',None)

    types = {
        'boolean': 'CHAR(1)',
        'string': 'VARCHAR(%(length)s)',
        'text': 'CLOB',
        'password': 'VARCHAR(%(length)s)',
        'blob': 'BLOB',
        'upload': 'VARCHAR(%(length)s)',
        'integer': 'INT',
        'double': 'DOUBLE',
        'decimal': 'NUMERIC(%(precision)s,%(scale)s)',
        'date': 'DATE',
        'time': 'TIME',
        'datetime': 'TIMESTAMP',
        'id': 'INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY NOT NULL',
        'reference': 'INT, FOREIGN KEY (%(field_name)s) REFERENCES %(foreign_key)s ON DELETE %(on_delete_action)s',
        'reference FK': ', CONSTRAINT FK_%(constraint_name)s FOREIGN KEY (%(field_name)s) REFERENCES %(foreign_key)s ON DELETE %(on_delete_action)s',
        'reference TFK': ' CONSTRAINT FK_%(foreign_table)s_PK FOREIGN KEY (%(field_name)s) REFERENCES %(foreign_table)s (%(foreign_key)s) ON DELETE %(on_delete_action)s',
        'list:integer': 'CLOB',
        'list:string': 'CLOB',
        'list:reference': 'CLOB',
        }

    def LEFT_JOIN(self):
        return 'LEFT OUTER JOIN'

    def RANDOM(self):
        return 'RAND()'

    def select_limitby(self, sql_s, sql_f, sql_t, sql_w, sql_o, limitby):
        if limitby:
            (lmin, lmax) = limitby
            sql_o += ' FETCH FIRST %i ROWS ONLY' % lmax
        return 'SELECT %s %s FROM %s%s%s;' % (sql_s, sql_f, sql_t, sql_w, sql_o)

    def represent_exceptions(self, obj, fieldtype):
        if fieldtype == 'blob':
            obj = base64.b64encode(str(obj))
            return "BLOB('%s')" % obj
        elif fieldtype == 'datetime':
            if isinstance(obj, datetime.datetime):
                obj = obj.isoformat()[:19].replace('T','-').replace(':','.')
            elif isinstance(obj, datetime.date):
                obj = obj.isoformat()[:10]+'-00.00.00'
            return "'%s'" % obj
        return None

    def __init__(self,db,uri,pool_size=0,folder=None,db_codec ='UTF-8',
                 credential_decoder=lambda x:x, driver_args={},
                 adapter_args={}):
        self.db = db
        self.dbengine = "db2"
        self.uri = uri
        self.pool_size = pool_size
        self.folder = folder
        self.db_codec = db_codec
        self.find_or_make_work_folder()
        cnxn = uri.split('://', 1)[1]
        def connect(cnxn=cnxn,driver_args=driver_args):
            return self.driver.connect(cnxn,**driver_args)
        self.pool_connection(connect)
        self.cursor = self.connection.cursor()

    def execute(self,command):
        if command[-1:]==';':
            command = command[:-1]
        return self.log_execute(command)

    def lastrowid(self,table):
        self.execute('SELECT DISTINCT IDENTITY_VAL_LOCAL() FROM %s;' % table)
        return int(self.cursor.fetchone()[0])

    def rowslice(self,rows,minimum=0,maximum=None):
        if maximum is None:
            return rows[minimum:]
        return rows[minimum:maximum]


class TeradataAdapter(DB2Adapter):

    driver = globals().get('pyodbc',None)

    types = {
        'boolean': 'CHAR(1)',
        'string': 'VARCHAR(%(length)s)',
        'text': 'CLOB',
        'password': 'VARCHAR(%(length)s)',
        'blob': 'BLOB',
        'upload': 'VARCHAR(%(length)s)',
        'integer': 'INT',
        'double': 'DOUBLE',
        'decimal': 'NUMERIC(%(precision)s,%(scale)s)',
        'date': 'DATE',
        'time': 'TIME',
        'datetime': 'TIMESTAMP',
        'id': 'INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY NOT NULL',
        'reference': 'INT, FOREIGN KEY (%(field_name)s) REFERENCES %(foreign_key)s ON DELETE %(on_delete_action)s',
        'reference FK': ', CONSTRAINT FK_%(constraint_name)s FOREIGN KEY (%(field_name)s) REFERENCES %(foreign_key)s ON DELETE %(on_delete_action)s',
        'reference TFK': ' CONSTRAINT FK_%(foreign_table)s_PK FOREIGN KEY (%(field_name)s) REFERENCES %(foreign_table)s (%(foreign_key)s) ON DELETE %(on_delete_action)s',
        'list:integer': 'CLOB',
        'list:string': 'CLOB',
        'list:reference': 'CLOB',
        }


    def __init__(self,db,uri,pool_size=0,folder=None,db_codec ='UTF-8',
                 credential_decoder=lambda x:x, driver_args={},
                 adapter_args={}):
        self.db = db
        self.dbengine = "teradata"
        self.uri = uri
        self.pool_size = pool_size
        self.folder = folder
        self.db_codec = db_codec
        self.find_or_make_work_folder()
        cnxn = uri.split('://', 1)[1]
        def connect(cnxn=cnxn,driver_args=driver_args):
            return self.driver.connect(cnxn,**driver_args)
        self.pool_connection(connect)
        self.cursor = self.connection.cursor()


INGRES_SEQNAME='ii***lineitemsequence' # NOTE invalid database object name
                                       # (ANSI-SQL wants this form of name
                                       # to be a delimited identifier)

class IngresAdapter(BaseAdapter):

    driver = globals().get('ingresdbi',None)

    types = {
        'boolean': 'CHAR(1)',
        'string': 'VARCHAR(%(length)s)',
        'text': 'CLOB',
        'password': 'VARCHAR(%(length)s)',  ## Not sure what this contains utf8 or nvarchar. Or even bytes?
        'blob': 'BLOB',
        'upload': 'VARCHAR(%(length)s)',  ## FIXME utf8 or nvarchar... or blob? what is this type?
        'integer': 'INTEGER4', # or int8...
        'double': 'FLOAT8',
        'decimal': 'NUMERIC(%(precision)s,%(scale)s)',
        'date': 'ANSIDATE',
        'time': 'TIME WITHOUT TIME ZONE',
        'datetime': 'TIMESTAMP WITHOUT TIME ZONE',
        'id': 'integer4 not null unique with default next value for %s' % INGRES_SEQNAME,
        'reference': 'integer4, FOREIGN KEY (%(field_name)s) REFERENCES %(foreign_key)s ON DELETE %(on_delete_action)s',
        'reference FK': ', CONSTRAINT FK_%(constraint_name)s FOREIGN KEY (%(field_name)s) REFERENCES %(foreign_key)s ON DELETE %(on_delete_action)s',
        'reference TFK': ' CONSTRAINT FK_%(foreign_table)s_PK FOREIGN KEY (%(field_name)s) REFERENCES %(foreign_table)s (%(foreign_key)s) ON DELETE %(on_delete_action)s', ## FIXME TODO
        'list:integer': 'CLOB',
        'list:string': 'CLOB',
        'list:reference': 'CLOB',
        }

    def LEFT_JOIN(self):
        return 'LEFT OUTER JOIN'

    def RANDOM(self):
        return 'RANDOM()'

    def select_limitby(self, sql_s, sql_f, sql_t, sql_w, sql_o, limitby):
        if limitby:
            (lmin, lmax) = limitby
            fetch_amt = lmax - lmin
            if fetch_amt:
                sql_s += ' FIRST %d ' % (fetch_amt, )
            if lmin:
                # Requires Ingres 9.2+
                sql_o += ' OFFSET %d' % (lmin, )
        return 'SELECT %s %s FROM %s%s%s;' % (sql_s, sql_f, sql_t, sql_w, sql_o)

    def __init__(self,db,uri,pool_size=0,folder=None,db_codec ='UTF-8',
                 credential_decoder=lambda x:x, driver_args={},
                 adapter_args={}):
        self.db = db
        self.dbengine = "ingres"
        self.uri = uri
        self.pool_size = pool_size
        self.folder = folder
        self.db_codec = db_codec
        self.find_or_make_work_folder()
        connstr = self._uri.split(':', 1)[1]
        # Simple URI processing
        connstr = connstr.lstrip()
        while connstr.startswith('/'):
            connstr = connstr[1:]
        database_name=connstr # Assume only (local) dbname is passed in
        vnode = '(local)'
        servertype = 'ingres'
        trace = (0, None) # No tracing
        driver_args.update(dict(database=database_name,
                                   vnode=vnode,
                                   servertype=servertype,
                                   trace=trace))
        def connect(driver_args=driver_args):
            return self.driver.connect(**driver_args)
        self.pool_connection(connect)
        self.cursor = self.connection.cursor()

    def create_sequence_and_triggers(self, query, table, **args):
        # post create table auto inc code (if needed)
        # modify table to btree for performance....
        # Older Ingres releases could use rule/trigger like Oracle above.
        if hasattr(table,'_primarykey'):
            modify_tbl_sql = 'modify %s to btree unique on %s' % \
                (table._tablename,
                 ', '.join(["'%s'" % x for x in table.primarykey]))
            self.execute(modify_tbl_sql)
        else:
            tmp_seqname='%s_iisq' % table._tablename
            query=query.replace(INGRES_SEQNAME, tmp_seqname)
            self.execute('create sequence %s' % tmp_seqname)
            self.execute(query)
            self.execute('modify %s to btree unique on %s' % (table._tablename, 'id'))


    def lastrowid(self,table):
        tmp_seqname='%s_iisq' % table
        self.execute('select current value for %s' % tmp_seqname)
        return int(self.cursor.fetchone()[0]) # don't really need int type cast here...

    def integrity_error_class(self):
        return ingresdbi.IntegrityError


class IngresUnicodeAdapter(IngresAdapter):
    types = {
        'boolean': 'CHAR(1)',
        'string': 'NVARCHAR(%(length)s)',
        'text': 'NCLOB',
        'password': 'NVARCHAR(%(length)s)',  ## Not sure what this contains utf8 or nvarchar. Or even bytes?
        'blob': 'BLOB',
        'upload': 'VARCHAR(%(length)s)',  ## FIXME utf8 or nvarchar... or blob? what is this type?
        'integer': 'INTEGER4', # or int8...
        'double': 'FLOAT8',
        'decimal': 'NUMERIC(%(precision)s,%(scale)s)',
        'date': 'ANSIDATE',
        'time': 'TIME WITHOUT TIME ZONE',
        'datetime': 'TIMESTAMP WITHOUT TIME ZONE',
        'id': 'integer4 not null unique with default next value for %s'% INGRES_SEQNAME,
        'reference': 'integer4, FOREIGN KEY (%(field_name)s) REFERENCES %(foreign_key)s ON DELETE %(on_delete_action)s',
        'reference FK': ', CONSTRAINT FK_%(constraint_name)s FOREIGN KEY (%(field_name)s) REFERENCES %(foreign_key)s ON DELETE %(on_delete_action)s',
        'reference TFK': ' CONSTRAINT FK_%(foreign_table)s_PK FOREIGN KEY (%(field_name)s) REFERENCES %(foreign_table)s (%(foreign_key)s) ON DELETE %(on_delete_action)s', ## FIXME TODO
        'list:integer': 'NCLOB',
        'list:string': 'NCLOB',
        'list:reference': 'NCLOB',
        }

class SAPDBAdapter(BaseAdapter):

    driver = globals().get('sapdb',None)
    support_distributed_transaction = False
    types = {
        'boolean': 'CHAR(1)',
        'string': 'VARCHAR(%(length)s)',
        'text': 'LONG',
        'password': 'VARCHAR(%(length)s)',
        'blob': 'LONG',
        'upload': 'VARCHAR(%(length)s)',
        'integer': 'INT',
        'double': 'FLOAT',
        'decimal': 'FIXED(%(precision)s,%(scale)s)',
        'date': 'DATE',
        'time': 'TIME',
        'datetime': 'TIMESTAMP',
        'id': 'INT PRIMARY KEY',
        'reference': 'INT, FOREIGN KEY (%(field_name)s) REFERENCES %(foreign_key)s ON DELETE %(on_delete_action)s',
        'list:integer': 'LONG',
        'list:string': 'LONG',
        'list:reference': 'LONG',
        }

    def sequence_name(self,table):
        return '%s_id_Seq' % table

    def select_limitby(self, sql_s, sql_f, sql_t, sql_w, sql_o, limitby):
        if limitby:
            (lmin, lmax) = limitby
            if len(sql_w) > 1:
                sql_w_row = sql_w + ' AND w_row > %i' % lmin
            else:
                sql_w_row = 'WHERE w_row > %i' % lmin
            return '%s %s FROM (SELECT w_tmp.*, ROWNO w_row FROM (SELECT %s FROM %s%s%s) w_tmp WHERE ROWNO=%i) %s %s %s;' % (sql_s, sql_f, sql_f, sql_t, sql_w, sql_o, lmax, sql_t, sql_w_row, sql_o)
        return 'SELECT %s %s FROM %s%s%s;' % (sql_s, sql_f, sql_t, sql_w, sql_o)

    def create_sequence_and_triggers(self, query, table, **args):
        # following lines should only be executed if table._sequence_name does not exist
        self.execute('CREATE SEQUENCE %s;' % table._sequence_name)
        self.execute("ALTER TABLE %s ALTER COLUMN %s SET DEFAULT NEXTVAL('%s');" \
                         % (table._tablename, table._id.name, table._sequence_name))
        self.execute(query)

    def __init__(self,db,uri,pool_size=0,folder=None,db_codec ='UTF-8',
                 credential_decoder=lambda x:x, driver_args={},
                 adapter_args={}):
        self.db = db
        self.dbengine = "sapdb"
        self.uri = uri
        self.pool_size = pool_size
        self.folder = folder
        self.db_codec = db_codec
        self.find_or_make_work_folder()
        uri = uri.split('://')[1]
        m = re.compile('^(?P<user>[^:@]+)(\:(?P<password>[^@]*))?@(?P<host>[^\:@/]+)(\:(?P<port>[0-9]+))?/(?P<db>[^\?]+)(\?sslmode=(?P<sslmode>.+))?$').match(uri)
        if not m:
            raise SyntaxError, "Invalid URI string in DAL"
        user = credential_decoder(m.group('user'))
        if not user:
            raise SyntaxError, 'User required'
        password = credential_decoder(m.group('password'))
        if not password:
            password = ''
        host = m.group('host')
        if not host:
            raise SyntaxError, 'Host name required'
        db = m.group('db')
        if not db:
            raise SyntaxError, 'Database name required'
        def connect(user=user,password=password,database=db,
                    host=host,driver_args=driver_args):
            return self.driver.Connection(user,password,database,
                                          host,**driver_args)
        self.pool_connection(connect)
        # self.connection.set_client_encoding('UTF8')
        self.cursor = self.connection.cursor()

    def lastrowid(self,table):
        self.execute("select %s.NEXTVAL from dual" % table._sequence_name)
        return int(self.cursor.fetchone()[0])

class CubridAdapter(MySQLAdapter):

    driver = globals().get('cubriddb',None)

    def __init__(self,db,uri,pool_size=0,folder=None,db_codec ='UTF-8',
                 credential_decoder=lambda x:x, driver_args={},
                 adapter_args={}):
        self.db = db
        self.dbengine = "cubrid"
        self.uri = uri
        self.pool_size = pool_size
        self.folder = folder
        self.db_codec = db_codec
        self.find_or_make_work_folder()
        uri = uri.split('://')[1]
        m = re.compile('^(?P<user>[^:@]+)(\:(?P<password>[^@]*))?@(?P<host>[^\:/]+)(\:(?P<port>[0-9]+))?/(?P<db>[^?]+)(\?set_encoding=(?P<charset>\w+))?$').match(uri)
        if not m:
            raise SyntaxError, \
                "Invalid URI string in DAL: %s" % self.uri
        user = credential_decoder(m.group('user'))
        if not user:
            raise SyntaxError, 'User required'
        password = credential_decoder(m.group('password'))
        if not password:
            password = ''
        host = m.group('host')
        if not host:
            raise SyntaxError, 'Host name required'
        db = m.group('db')
        if not db:
            raise SyntaxError, 'Database name required'
        port = int(m.group('port') or '30000')
        charset = m.group('charset') or 'utf8'
        user=credential_decoder(user),
        passwd=credential_decoder(password),
        def connect(host,port,db,user,passwd,driver_args=driver_args):
            return self.driver.connect(host,port,db,user,passwd,**driver_args)
        self.pool_connection(connect)
        self.cursor = self.connection.cursor()
        self.execute('SET FOREIGN_KEY_CHECKS=1;')
        self.execute("SET sql_mode='NO_BACKSLASH_ESCAPES';")


######## GAE MySQL ##########

class DatabaseStoredFile:

    web2py_filesystem = False

    def __init__(self,db,filename,mode):
        if db._adapter.dbengine != 'mysql':
            raise RuntimeError, "only MySQL can store metadata .table files in database for now"
        self.db = db
        self.filename = filename
        self.mode = mode
        if not self.web2py_filesystem:
            self.db.executesql("CREATE TABLE IF NOT EXISTS web2py_filesystem (path VARCHAR(512), content LONGTEXT, PRIMARY KEY(path) ) ENGINE=InnoDB;")
            DatabaseStoredFile.web2py_filesystem = True
        self.p=0
        self.data = ''
        if mode in ('r','rw','a'):
            query = "SELECT content FROM web2py_filesystem WHERE path='%s'" % filename
            rows = self.db.executesql(query)
            if rows:
                self.data = rows[0][0]
            elif os.path.exists(filename):
                datafile = open(filename, 'r')
                try:
                    self.data = datafile.read()
                finally:
                    datafile.close()
            elif mode in ('r','rw'):
                raise RuntimeError, "File %s does not exist" % filename

    def read(self, bytes):
        data = self.data[self.p:self.p+bytes]
        self.p += len(data)
        return data

    def readline(self):
        i = self.data.find('\n',self.p)+1
        if i>0:
            data, self.p = self.data[self.p:i], i
        else:
            data, self.p = self.data[self.p:], len(self.data)
        return data

    def write(self,data):
        self.data += data

    def close(self):
        self.db.executesql("DELETE FROM web2py_filesystem WHERE path='%s'" % self.filename)
        query = "INSERT INTO web2py_filesystem(path,content) VALUES ('%s','%s')" % \
            (self.filename, self.data.replace("'","''"))
        self.db.executesql(query)
        self.db.commit()

    @staticmethod
    def exists(db,filename):
        if os.path.exists(filename):
            return True
        query = "SELECT path FROM web2py_filesystem WHERE path='%s'" % filename
        if db.executesql(query):
            return True
        return False


class UseDatabaseStoredFile:

    def file_exists(self, filename):
        return DatabaseStoredFile.exists(self.db,filename)

    def file_open(self, filename, mode='rb', lock=True):
        return DatabaseStoredFile(self.db,filename,mode)

    def file_close(self, fileobj, unlock=True):
        fileobj.close()

    def file_delete(self,filename):
        query = "DELETE FROM web2py_filesystem WHERE path='%s'" % filename
        self.db.executesql(query)
        self.db.commit()

class GoogleSQLAdapter(UseDatabaseStoredFile,MySQLAdapter):

    def __init__(self, db, uri='google:sql://realm:domain/database',
                 pool_size=0, folder=None, db_codec='UTF-8',
                 credential_decoder = lambda x:x, driver_args={},
                 adapter_args={}):

        self.db = db
        self.dbengine = "mysql"
        self.uri = uri
        self.pool_size = pool_size
        self.folder = folder
        self.db_codec = db_codec
        self.folder = folder or '$HOME/'+thread.folder.split('/applications/',1)[1]

        m = re.compile('^(?P<instance>.*)/(?P<db>.*)$').match(self.uri[len('google:sql://'):])
        if not m:
            raise SyntaxError, "Invalid URI string in SQLDB: %s" % self._uri
        instance = credential_decoder(m.group('instance'))
        db = credential_decoder(m.group('db'))
        driver_args['instance'] = instance
        createdb = adapter_args.get('createdb',True)
        if not createdb:
            driver_args['database'] = db
        def connect(driver_args=driver_args):
            return rdbms.connect(**driver_args)
        self.pool_connection(connect)
        self.cursor = self.connection.cursor()
        if createdb:
            # self.execute('DROP DATABASE %s' % db)
            self.execute('CREATE DATABASE IF NOT EXISTS %s' % db)
            self.execute('USE %s' % db)
        self.execute("SET FOREIGN_KEY_CHECKS=1;")
        self.execute("SET sql_mode='NO_BACKSLASH_ESCAPES';")

class NoSQLAdapter(BaseAdapter):

    @staticmethod
    def to_unicode(obj):
        if isinstance(obj, str):
            return obj.decode('utf8')
        elif not isinstance(obj, unicode):
            return unicode(obj)
        return obj

    def represent(self, obj, fieldtype):
        if isinstance(obj,CALLABLETYPES):
            obj = obj()
        if isinstance(fieldtype, SQLCustomType):
            return fieldtype.encoder(obj)
        if isinstance(obj, (Expression, Field)):
            raise SyntaxError, "non supported on GAE"
        if self.dbengine=='google:datastore' in globals():
            if isinstance(fieldtype, gae.Property):
                return obj
        if fieldtype.startswith('list:'):
            if not obj:
                obj = []
            if not isinstance(obj, (list, tuple)):
                obj = [obj]
        if obj == '' and  not fieldtype[:2] in ['st','te','pa','up']:
            return None
        if not obj is None:
            if isinstance(obj, list) and not fieldtype.startswith('list'):
                obj = [self.represent(o, fieldtype) for o in obj]
            elif fieldtype in ('integer','id'):
                obj = long(obj)
            elif fieldtype == 'double':
                obj = float(obj)
            elif fieldtype.startswith('reference'):
                if isinstance(obj, (Row, Reference)):
                    obj = obj['id']
                obj = long(obj)
            elif fieldtype == 'boolean':
                if obj and not str(obj)[0].upper() == 'F':
                    obj = True
                else:
                    obj = False
            elif fieldtype == 'date':
                if not isinstance(obj, datetime.date):
                    (y, m, d) = map(int,str(obj).strip().split('-'))
                    obj = datetime.date(y, m, d)
                elif isinstance(obj,datetime.datetime):
                    (y, m, d) = (obj.year, obj.month, obj.day)
                    obj = datetime.date(y, m, d)
            elif fieldtype == 'time':
                if not isinstance(obj, datetime.time):
                    time_items = map(int,str(obj).strip().split(':')[:3])
                    if len(time_items) == 3:
                        (h, mi, s) = time_items
                    else:
                        (h, mi, s) = time_items + [0]
                    obj = datetime.time(h, mi, s)
            elif fieldtype == 'datetime':
                if not isinstance(obj, datetime.datetime):
                    (y, m, d) = map(int,str(obj)[:10].strip().split('-'))
                    time_items = map(int,str(obj)[11:].strip().split(':')[:3])
                    while len(time_items)<3:
                        time_items.append(0)
                    (h, mi, s) = time_items
                    obj = datetime.datetime(y, m, d, h, mi, s)
            elif fieldtype == 'blob':
                pass
            elif fieldtype.startswith('list:string'):
                return map(self.to_unicode,obj)
            elif fieldtype.startswith('list:'):
                return map(int,obj)
            else:
                obj = self.to_unicode(obj)
        return obj

    def _insert(self,table,fields):
        return 'insert %s in %s' % (fields, table)

    def _count(self,query,distinct=None):
        return 'count %s' % repr(query)

    def _select(self,query,fields,attributes):
        return 'select %s where %s' % (repr(fields), repr(query))

    def _delete(self,tablename, query):
        return 'delete %s where %s' % (repr(tablename),repr(query))

    def _update(self,tablename,query,fields):
        return 'update %s (%s) where %s' % (repr(tablename),
                                            repr(fields),repr(query))

    def commit(self):
        """
        remember: no transactions on many NoSQL
        """
        pass

    def rollback(self):
        """
        remember: no transactions on many NoSQL
        """
        pass

    def close(self):
        """
        remember: no transactions on many NoSQL
        """
        pass


    # these functions should never be called!
    def OR(self,first,second): raise SyntaxError, "Not supported"
    def AND(self,first,second): raise SyntaxError, "Not supported"
    def AS(self,first,second): raise SyntaxError, "Not supported"
    def ON(self,first,second): raise SyntaxError, "Not supported"
    def STARTSWITH(self,first,second=None): raise SyntaxError, "Not supported"
    def ENDSWITH(self,first,second=None): raise SyntaxError, "Not supported"
    def ADD(self,first,second): raise SyntaxError, "Not supported"
    def SUB(self,first,second): raise SyntaxError, "Not supported"
    def MUL(self,first,second): raise SyntaxError, "Not supported"
    def DIV(self,first,second): raise SyntaxError, "Not supported"
    def LOWER(self,first): raise SyntaxError, "Not supported"
    def UPPER(self,first): raise SyntaxError, "Not supported"
    def EXTRACT(self,first,what): raise SyntaxError, "Not supported"
    def AGGREGATE(self,first,what): raise SyntaxError, "Not supported"
    def LEFT_JOIN(self): raise SyntaxError, "Not supported"
    def RANDOM(self): raise SyntaxError, "Not supported"
    def SUBSTRING(self,field,parameters):  raise SyntaxError, "Not supported"
    def PRIMARY_KEY(self,key):  raise SyntaxError, "Not supported"
    def LIKE(self,first,second): raise SyntaxError, "Not supported"
    def drop(self,table,mode):  raise SyntaxError, "Not supported"
    def alias(self,table,alias): raise SyntaxError, "Not supported"
    def migrate_table(self,*a,**b): raise SyntaxError, "Not supported"
    def distributed_transaction_begin(self,key): raise SyntaxError, "Not supported"
    def prepare(self,key): raise SyntaxError, "Not supported"
    def commit_prepared(self,key): raise SyntaxError, "Not supported"
    def rollback_prepared(self,key): raise SyntaxError, "Not supported"
    def concat_add(self,table): raise SyntaxError, "Not supported"
    def constraint_name(self, table, fieldname): raise SyntaxError, "Not supported"
    def create_sequence_and_triggers(self, query, table, **args): pass
    def log_execute(self,*a,**b): raise SyntaxError, "Not supported"
    def execute(self,*a,**b): raise SyntaxError, "Not supported"
    def represent_exceptions(self, obj, fieldtype): raise SyntaxError, "Not supported"
    def lastrowid(self,table): raise SyntaxError, "Not supported"
    def integrity_error_class(self): raise SyntaxError, "Not supported"
    def rowslice(self,rows,minimum=0,maximum=None): raise SyntaxError, "Not supported"


class GAEF(object):
    def __init__(self,name,op,value,apply):
        self.name=name=='id' and '__key__' or name
        self.op=op
        self.value=value
        self.apply=apply
    def __repr__(self):
        return '(%s %s %s:%s)' % (self.name, self.op, repr(self.value), type(self.value))

class GoogleDatastoreAdapter(NoSQLAdapter):
    uploads_in_blob = True
    types = {}

    def file_exists(self, filename): pass
    def file_open(self, filename, mode='rb', lock=True): pass
    def file_close(self, fileobj, unlock=True): pass

    def __init__(self,db,uri,pool_size=0,folder=None,db_codec ='UTF-8',
                 credential_decoder=lambda x:x, driver_args={},
                 adapter_args={}):
        self.types.update({
                'boolean': gae.BooleanProperty,
                'string': (lambda: gae.StringProperty(multiline=True)),
                'text': gae.TextProperty,
                'password': gae.StringProperty,
                'blob': gae.BlobProperty,
                'upload': gae.StringProperty,
                'integer': gae.IntegerProperty,
                'double': gae.FloatProperty,
                'decimal': GAEDecimalProperty,
                'date': gae.DateProperty,
                'time': gae.TimeProperty,
                'datetime': gae.DateTimeProperty,
                'id': None,
                'reference': gae.IntegerProperty,
                'list:string': (lambda: gae.StringListProperty(default=None)),
                'list:integer': (lambda: gae.ListProperty(int,default=None)),
                'list:reference': (lambda: gae.ListProperty(int,default=None)),
        })
        self.db = db
        self.uri = uri
        self.dbengine = 'google:datastore'
        self.folder = folder
        db['_lastsql'] = ''
        self.db_codec = 'UTF-8'
        self.pool_size = 0
        match = re.compile('.*://(?P<namespace>.+)').match(uri)
        if match:
            namespace_manager.set_namespace(match.group('namespace'))

    def create_table(self,table,migrate=True,fake_migrate=False, polymodel=None):
        myfields = {}
        for k in table.fields:
            if isinstance(polymodel,Table) and k in polymodel.fields():
                continue
            field = table[k]
            attr = {}
            if isinstance(field.type, SQLCustomType):
                ftype = self.types[field.type.native or field.type.type](**attr)
            elif isinstance(field.type, gae.Property):
                ftype = field.type
            elif field.type.startswith('id'):
                continue
            elif field.type.startswith('decimal'):
                precision, scale = field.type[7:].strip('()').split(',')
                precision = int(precision)
                scale = int(scale)
                ftype = GAEDecimalProperty(precision, scale, **attr)
            elif field.type.startswith('reference'):
                if field.notnull:
                    attr = dict(required=True)
                referenced = field.type[10:].strip()
                ftype = self.types[field.type[:9]](table._db[referenced])
            elif field.type.startswith('list:reference'):
                if field.notnull:
                    attr = dict(required=True)
                referenced = field.type[15:].strip()
                ftype = self.types[field.type[:14]](**attr)
            elif field.type.startswith('list:'):
                ftype = self.types[field.type](**attr)
            elif not field.type in self.types\
                 or not self.types[field.type]:
                raise SyntaxError, 'Field: unknown field type: %s' % field.type
            else:
                ftype = self.types[field.type](**attr)
            myfields[field.name] = ftype
        if not polymodel:
            table._tableobj = classobj(table._tablename, (gae.Model, ), myfields)
        elif polymodel==True:
            table._tableobj = classobj(table._tablename, (PolyModel, ), myfields)
        elif isinstance(polymodel,Table):
            table._tableobj = classobj(table._tablename, (polymodel._tableobj, ), myfields)
        else:
            raise SyntaxError, "polymodel must be None, True, a table or a tablename"
        return None

    def expand(self,expression,field_type=None):
        if isinstance(expression,Field):
            if expression.type in ('text','blob'):
                raise SyntaxError, 'AppEngine does not index by: %s' % expression.type
            return expression.name
        elif isinstance(expression, (Expression, Query)):
            if not expression.second is None:
                return expression.op(expression.first, expression.second)
            elif not expression.first is None:
                return expression.op(expression.first)
            else:
                return expression.op()
        elif field_type:
                return self.represent(expression,field_type)
        elif isinstance(expression,(list,tuple)):
            return ','.join([self.represent(item,field_type) for item in expression])
        else:
            return str(expression)

    ### TODO from gql.py Expression
    def AND(self,first,second):
        a = self.expand(first)
        b = self.expand(second)
        if b[0].name=='__key__' and a[0].name!='__key__':
            return b+a
        return a+b

    def EQ(self,first,second=None):
        if isinstance(second, Key):
            return [GAEF(first.name,'=',second,lambda a,b:a==b)]
        return [GAEF(first.name,'=',self.represent(second,first.type),lambda a,b:a==b)]

    def NE(self,first,second=None):
        if first.type != 'id':
            return [GAEF(first.name,'!=',self.represent(second,first.type),lambda a,b:a!=b)]
        else:
            second = Key.from_path(first._tablename, long(second))
            return [GAEF(first.name,'!=',second,lambda a,b:a!=b)]

    def LT(self,first,second=None):
        if first.type != 'id':
            return [GAEF(first.name,'<',self.represent(second,first.type),lambda a,b:a<b)]
        else:
            second = Key.from_path(first._tablename, long(second))
            return [GAEF(first.name,'<',second,lambda a,b:a<b)]

    def LE(self,first,second=None):
        if first.type != 'id':
            return [GAEF(first.name,'<=',self.represent(second,first.type),lambda a,b:a<=b)]
        else:
            second = Key.from_path(first._tablename, long(second))
            return [GAEF(first.name,'<=',second,lambda a,b:a<=b)]

    def GT(self,first,second=None):
        if first.type != 'id' or second==0 or second == '0':
            return [GAEF(first.name,'>',self.represent(second,first.type),lambda a,b:a>b)]
        else:
            second = Key.from_path(first._tablename, long(second))
            return [GAEF(first.name,'>',second,lambda a,b:a>b)]

    def GE(self,first,second=None):
        if first.type != 'id':
            return [GAEF(first.name,'>=',self.represent(second,first.type),lambda a,b:a>=b)]
        else:
            second = Key.from_path(first._tablename, long(second))
            return [GAEF(first.name,'>=',second,lambda a,b:a>=b)]

    def INVERT(self,first):
        return '-%s' % first.name

    def COMMA(self,first,second):
        return '%s, %s' % (self.expand(first),self.expand(second))

    def BELONGS(self,first,second=None):
        if not isinstance(second,(list, tuple)):
            raise SyntaxError, "Not supported"
        if first.type != 'id':
            return [GAEF(first.name,'in',self.represent(second,first.type),lambda a,b:a in b)]
        else:
            second = [Key.from_path(first._tablename, i) for i in second]
            return [GAEF(first.name,'in',second,lambda a,b:a in b)]

    def CONTAINS(self,first,second):
        if not first.type.startswith('list:'):
            raise SyntaxError, "Not supported"
        return [GAEF(first.name,'=',self.expand(second,first.type[5:]),lambda a,b:a in b)]

    def NOT(self,first):
        nops = { self.EQ: self.NE,
                 self.NE: self.EQ,
                 self.LT: self.GE,
                 self.GT: self.LE,
                 self.LE: self.GT,
                 self.GE: self.LT}
        if not isinstance(first,Query):
            raise SyntaxError, "Not suported"
        nop = nops.get(first.op,None)
        if not nop:
            raise SyntaxError, "Not suported %s" % first.op.__name__
        first.op = nop
        return self.expand(first)

    def truncate(self,table,mode):
        self.db(table._id > 0).delete()

    def select_raw(self,query,fields=None,attributes=None):
        fields = fields or []
        attributes = attributes or {}
        new_fields = []
        for item in fields:
            if isinstance(item,SQLALL):
                new_fields += item.table
            else:
                new_fields.append(item)
        fields = new_fields
        if query:
            tablename = self.get_table(query)
        elif fields:
            tablename = fields[0].tablename
            query = fields[0].table._id>0
        else:
            raise SyntaxError, "Unable to determine a tablename"
        query = self.filter_tenant(query,[tablename])
        tableobj = self.db[tablename]._tableobj
        items = tableobj.all()
        filters = self.expand(query)
        for filter in filters:
            if filter.name=='__key__' and filter.op=='>' and filter.value==0:
                continue
            elif filter.name=='__key__' and filter.op=='=':
                if filter.value==0:
                    items = []
                elif isinstance(filter.value, Key):
                    item = tableobj.get(filter.value)
                    items = (item and [item]) or []
                else:
                    item = tableobj.get_by_id(filter.value)
                    items = (item and [item]) or []
            elif isinstance(items,list): # i.e. there is a single record!
                items = [i for i in items if filter.apply(getattr(item,filter.name),
                                                          filter.value)]
            else:
                if filter.name=='__key__': items.order('__key__')
                items = items.filter('%s %s' % (filter.name,filter.op),filter.value)
        if not isinstance(items,list):
            if attributes.get('left', None):
                raise SyntaxError, 'Set: no left join in appengine'
            if attributes.get('groupby', None):
                raise SyntaxError, 'Set: no groupby in appengine'
            orderby = attributes.get('orderby', False)
            if orderby:
                ### THIS REALLY NEEDS IMPROVEMENT !!!
                if isinstance(orderby, (list, tuple)):
                    orderby = xorify(orderby)
                if isinstance(orderby,Expression):
                    orderby = self.expand(orderby)
                orders = orderby.split(', ')
                for order in orders:
                    order={'-id':'-__key__','id':'__key__'}.get(order,order)
                    items = items.order(order)
            if attributes.get('limitby', None):
                (lmin, lmax) = attributes['limitby']
                (limit, offset) = (lmax - lmin, lmin)
                items = items.fetch(limit, offset=offset)
        fields = self.db[tablename].fields
        return (items, tablename, fields)

    def select(self,query,fields,attributes):
        (items, tablename, fields) = self.select_raw(query,fields,attributes)
        # self.db['_lastsql'] = self._select(query,fields,attributes)
        rows = [
            [t=='id' and int(item.key().id()) or getattr(item, t) for t in fields]
            for item in items]
        colnames = ['%s.%s' % (tablename, t) for t in fields]
        return self.parse(rows, colnames, False)


    def count(self,query,distinct=None):
        if distinct:
            raise RuntimeError, "COUNT DISTINCT not supported"
        (items, tablename, fields) = self.select_raw(query)
        # self.db['_lastsql'] = self._count(query)
        try:
            return len(items)
        except TypeError:
            return items.count(limit=None)

    def delete(self,tablename, query):
        """
        This function was changed on 2010-05-04 because according to
        http://code.google.com/p/googleappengine/issues/detail?id=3119
        GAE no longer support deleting more than 1000 records.
        """
        # self.db['_lastsql'] = self._delete(tablename,query)
        (items, tablename, fields) = self.select_raw(query)
        # items can be one item or a query
        if not isinstance(items,list):
            counter = items.count(limit=None)
            leftitems = items.fetch(1000)
            while len(leftitems):
                gae.delete(leftitems)
                leftitems = items.fetch(1000)
        else:
            counter = len(items)
            gae.delete(items)
        return counter

    def update(self,tablename,query,update_fields):
        # self.db['_lastsql'] = self._update(tablename,query,update_fields)
        (items, tablename, fields) = self.select_raw(query)
        counter = 0
        for item in items:
            for field, value in update_fields:
                setattr(item, field.name, self.represent(value,field.type))
            item.put()
            counter += 1
        logger.info(str(counter))
        return counter

    def insert(self,table,fields):
        dfields=dict((f.name,self.represent(v,f.type)) for f,v in fields)
        # table._db['_lastsql'] = self._insert(table,fields)
        tmp = table._tableobj(**dfields)
        tmp.put()
        rid = Reference(tmp.key().id())
        (rid._table, rid._record) = (table, None)
        return rid

    def bulk_insert(self,table,items):
        parsed_items = []
        for item in items:
            dfields=dict((f.name,self.represent(v,f.type)) for f,v in item)
            parsed_items.append(table._tableobj(**dfields))
        gae.put(parsed_items)
        return True

def uuid2int(uuidv):
    return uuid.UUID(uuidv).int

def int2uuid(n):
    return str(uuid.UUID(int=n))

class CouchDBAdapter(NoSQLAdapter):
    uploads_in_blob = True
    types = {
                'boolean': bool,
                'string': str,
                'text': str,
                'password': str,
                'blob': str,
                'upload': str,
                'integer': long,
                'double': float,
                'date': datetime.date,
                'time': datetime.time,
                'datetime': datetime.datetime,
                'id': long,
                'reference': long,
                'list:string': list,
                'list:integer': list,
                'list:reference': list,
        }

    def file_exists(self, filename): pass
    def file_open(self, filename, mode='rb', lock=True): pass
    def file_close(self, fileobj, unlock=True): pass

    def expand(self,expression,field_type=None):
        if isinstance(expression,Field):
            if expression.type=='id':
                return "%s._id" % expression.tablename
        return BaseAdapter.expand(self,expression,field_type)

    def AND(self,first,second):
        return '(%s && %s)' % (self.expand(first),self.expand(second))

    def OR(self,first,second):
        return '(%s || %s)' % (self.expand(first),self.expand(second))

    def EQ(self,first,second):
        if second is None:
            return '(%s == null)' % self.expand(first)
        return '(%s == %s)' % (self.expand(first),self.expand(second,first.type))

    def NE(self,first,second):
        if second is None:
            return '(%s != null)' % self.expand(first)
        return '(%s != %s)' % (self.expand(first),self.expand(second,first.type))

    def COMMA(self,first,second):
        return '%s + %s' % (self.expand(first),self.expand(second))

    def represent(self, obj, fieldtype):
        value = NoSQLAdapter.represent(self, obj, fieldtype)
        if fieldtype=='id':
            return repr(str(int(value)))
        return repr(not isinstance(value,unicode) and value or value.encode('utf8'))

    def __init__(self,db,uri='couchdb://127.0.0.1:5984',
                 pool_size=0,folder=None,db_codec ='UTF-8',
                 credential_decoder=lambda x:x, driver_args={},
                 adapter_args={}):
        self.db = db
        self.uri = uri
        self.dbengine = 'couchdb'
        self.folder = folder
        db['_lastsql'] = ''
        self.db_codec = 'UTF-8'
        self.pool_size = pool_size

        url='http://'+uri[10:]
        def connect(url=url,driver_args=driver_args):
            return couchdb.Server(url,**driver_args)
        self.pool_connection(connect)

    def create_table(self, table, migrate=True, fake_migrate=False, polymodel=None):
        if migrate:
            try:
                self.connection.create(table._tablename)
            except:
                pass

    def insert(self,table,fields):
        id = uuid2int(web2py_uuid())
        ctable = self.connection[table._tablename]
        values = dict((k.name,NoSQLAdapter.represent(self,v,k.type)) for k,v in fields)
        values['_id'] = str(id)
        ctable.save(values)
        return id

    def _select(self,query,fields,attributes):
        if not isinstance(query,Query):
            raise SyntaxError, "Not Supported"
        for key in set(attributes.keys())-set(('orderby','groupby','limitby',
                                               'required','cache','left',
                                               'distinct','having')):
            raise SyntaxError, 'invalid select attribute: %s' % key
        new_fields=[]
        for item in fields:
            if isinstance(item,SQLALL):
                new_fields += item.table
            else:
                new_fields.append(item)
        def uid(fd):
            return fd=='id' and '_id' or fd
        def get(row,fd):
            return fd=='id' and int(row['_id']) or row.get(fd,None)
        fields = new_fields
        tablename = self.get_table(query)
        fieldnames = [f.name for f in (fields or self.db[tablename])]
        colnames = ['%s.%s' % (tablename,k) for k in fieldnames]
        fields = ','.join(['%s.%s' % (tablename,uid(f)) for f in fieldnames])
        fn="function(%(t)s){if(%(query)s)emit(%(order)s,[%(fields)s]);}" %\
            dict(t=tablename,
                 query=self.expand(query),
                 order='%s._id' % tablename,
                 fields=fields)
        return fn, colnames

    def select(self,query,fields,attributes):
        if not isinstance(query,Query):
            raise SyntaxError, "Not Supported"
        fn, colnames = self._select(query,fields,attributes)
        tablename = colnames[0].split('.')[0]
        ctable = self.connection[tablename]
        rows = [cols['value'] for cols in ctable.query(fn)]
        return self.parse(rows, colnames, False)

    def delete(self,tablename,query):
        if not isinstance(query,Query):
            raise SyntaxError, "Not Supported"
        if query.first.type=='id' and query.op==self.EQ:
            id = query.second
            tablename = query.first.tablename
            assert(tablename == query.first.tablename)
            ctable = self.connection[tablename]
            try:
                del ctable[str(id)]
                return 1
            except couchdb.http.ResourceNotFound:
                return 0
        else:
            tablename = self.get_table(query)
            rows = self.select(query,[self.db[tablename]._id],{})
            ctable = self.connection[tablename]
            for row in rows:
                del ctable[str(row.id)]
            return len(rows)

    def update(self,tablename,query,fields):
        if not isinstance(query,Query):
            raise SyntaxError, "Not Supported"
        if query.first.type=='id' and query.op==self.EQ:
            id = query.second
            tablename = query.first.tablename
            ctable = self.connection[tablename]
            try:
                doc = ctable[str(id)]
                for key,value in fields:
                    doc[key.name] = NoSQLAdapter.represent(self,value,self.db[tablename][key.name].type)
                ctable.save(doc)
                return 1
            except couchdb.http.ResourceNotFound:
                return 0
        else:
            tablename = self.get_table(query)
            rows = self.select(query,[self.db[tablename]._id],{})
            ctable = self.connection[tablename]
            table = self.db[tablename]
            for row in rows:
                doc = ctable[str(row.id)]
                for key,value in fields:
                    doc[key.name] = NoSQLAdapter.represent(self,value,table[key.name].type)
                ctable.save(doc)
            return len(rows)

    def count(self,query,distinct=None):
        if distinct:
            raise RuntimeError, "COUNT DISTINCT not supported"
        if not isinstance(query,Query):
            raise SyntaxError, "Not Supported"
        tablename = self.get_table(query)
        rows = self.select(query,[self.db[tablename]._id],{})
        return len(rows)

def cleanup(text):
    """
    validates that the given text is clean: only contains [0-9a-zA-Z_]
    """

    if re.compile('[^0-9a-zA-Z_]').findall(text):
        raise SyntaxError, \
            'only [0-9a-zA-Z_] allowed in table and field names, received %s' \
            % text
    return text


class MongoDBAdapter(NoSQLAdapter):
    uploads_in_blob = True
    types = {
                'boolean': bool,
                'string': str,
                'text': str,
                'password': str,
                'blob': str,
                'upload': str,
                'integer': long,
                'double': float,
                'date': datetime.date,
                'time': datetime.time,
                'datetime': datetime.datetime,
                'id': long,
                'reference': long,
                'list:string': list,
                'list:integer': list,
                'list:reference': list,
        }

    def __init__(self,db,uri='mongodb://127.0.0.1:5984/db',
                 pool_size=0,folder=None,db_codec ='UTF-8',
                 credential_decoder=lambda x:x, driver_args={},
                 adapter_args={}):
        self.db = db
        self.uri = uri
        self.dbengine = 'mongodb'
        self.folder = folder
        db['_lastsql'] = ''
        self.db_codec = 'UTF-8'
        self.pool_size = pool_size

        m = re.compile('^(?P<host>[^\:/]+)(\:(?P<port>[0-9]+))?/(?P<db>.+)$').match(self.uri[10:])
        if not m:
            raise SyntaxError, "Invalid URI string in DAL: %s" % self.uri
        host = m.group('host')
        if not host:
            raise SyntaxError, 'mongodb: host name required'
        dbname = m.group('db')
        if not dbname:
            raise SyntaxError, 'mongodb: db name required'
        port = m.group('port') or 27017
        driver_args.update(dict(host=host,port=port))
        def connect(dbname=dbname,driver_args=driver_args):
            return pymongo.Connection(**driver_args)[dbname]
        self.pool_connection(connect)

    def insert(self,table,fields):
        ctable = self.connection[table._tablename]
        values = dict((k,self.represent(v,table[k].type)) for k,v in fields)
        ctable.insert(values)
        return uuid2int(id)


    def count(self,query):
        raise RuntimeError, "Not implemented"

    def select(self,query,fields,attributes):
        raise RuntimeError, "Not implemented"

    def delete(self,tablename, query):
        raise RuntimeError, "Not implemented"

    def update(self,tablename,query,fields):
        raise RuntimeError, "Not implemented"


########################################################################
# end of adapters
########################################################################

ADAPTERS = {
    'sqlite': SQLiteAdapter,
    'sqlite:memory': SQLiteAdapter,
    'mysql': MySQLAdapter,
    'postgres': PostgreSQLAdapter,
    'oracle': OracleAdapter,
    'mssql': MSSQLAdapter,
    'mssql2': MSSQL2Adapter,
    'db2': DB2Adapter,
    'teradata': TeradataAdapter,
    'informix': InformixAdapter,
    'firebird': FireBirdAdapter,
    'firebird_embedded': FireBirdAdapter,
    'ingres': IngresAdapter,
    'ingresu': IngresUnicodeAdapter,
    'sapdb': SAPDBAdapter,
    'cubrid': CubridAdapter,
    'jdbc:sqlite': JDBCSQLiteAdapter,
    'jdbc:sqlite:memory': JDBCSQLiteAdapter,
    'jdbc:postgres': JDBCPostgreSQLAdapter,
    'gae': GoogleDatastoreAdapter, # discouraged, for backward compatibility
    'google:datastore': GoogleDatastoreAdapter,
    'google:sql': GoogleSQLAdapter,
    'couchdb': CouchDBAdapter,
    'mongodb': MongoDBAdapter,
}


def sqlhtml_validators(field):
    """
    Field type validation, using web2py's validators mechanism.

    makes sure the content of a field is in line with the declared
    fieldtype
    """
    if not have_validators:
        return []
    field_type, field_length = field.type, field.length
    if isinstance(field_type, SQLCustomType):
        if hasattr(field_type, 'validator'):
            return field_type.validator
        else:
            field_type = field_type.type
    elif not isinstance(field_type,str):
        return []
    requires=[]
    def ff(r,id):
        row=r(id)
        if not row:
            return id
        elif hasattr(r, '_format') and isinstance(r._format,str):
            return r._format % row
        elif hasattr(r, '_format') and callable(r._format):
            return r._format(row)
        else:
            return id
    if field_type == 'string':
        requires.append(validators.IS_LENGTH(field_length))
    elif field_type == 'text':
        requires.append(validators.IS_LENGTH(field_length))
    elif field_type == 'password':
        requires.append(validators.IS_LENGTH(field_length))
    elif field_type == 'double':
        requires.append(validators.IS_FLOAT_IN_RANGE(-1e100, 1e100))
    elif field_type == 'integer':
        requires.append(validators.IS_INT_IN_RANGE(-1e100, 1e100))
    elif field_type.startswith('decimal'):
        requires.append(validators.IS_DECIMAL_IN_RANGE(-10**10, 10**10))
    elif field_type == 'date':
        requires.append(validators.IS_DATE())
    elif field_type == 'time':
        requires.append(validators.IS_TIME())
    elif field_type == 'datetime':
        requires.append(validators.IS_DATETIME())
    elif field.db and field_type.startswith('reference') and \
            field_type.find('.') < 0 and \
            field_type[10:] in field.db.tables:
        referenced = field.db[field_type[10:]]
        def repr_ref(id, r=referenced, f=ff): return f(r, id)
        field.represent = field.represent or repr_ref
        if hasattr(referenced, '_format') and referenced._format:
            requires = validators.IS_IN_DB(field.db,referenced._id,
                                           referenced._format)
            if field.unique:
                requires._and = validators.IS_NOT_IN_DB(field.db,field)
            if field.tablename == field_type[10:]:
                return validators.IS_EMPTY_OR(requires)
            return requires
    elif field.db and field_type.startswith('list:reference') and \
            field_type.find('.') < 0 and \
            field_type[15:] in field.db.tables:
        referenced = field.db[field_type[15:]]
        def list_ref_repr(ids, r=referenced, f=ff):
            if not ids:
                return None
            refs = r._db(r._id.belongs(ids)).select(r._id)
            return (refs and ', '.join(str(f(r,ref.id)) for ref in refs) or '')
        field.represent = field.represent or list_ref_repr
        if hasattr(referenced, '_format') and referenced._format:
            requires = validators.IS_IN_DB(field.db,referenced._id,
                                           referenced._format,multiple=True)
        else:
            requires = validators.IS_IN_DB(field.db,referenced._id,
                                           multiple=True)
        if field.unique:
            requires._and = validators.IS_NOT_IN_DB(field.db,field)
        return requires
    elif field_type.startswith('list:'):
        def repr_list(values): return', '.join(str(v) for v in (values or []))
        field.represent = field.represent or repr_list
    if field.unique:
        requires.insert(0,validators.IS_NOT_IN_DB(field.db,field))
    sff = ['in', 'do', 'da', 'ti', 'de', 'bo']
    if field.notnull and not field_type[:2] in sff:
        requires.insert(0, validators.IS_NOT_EMPTY())
    elif not field.notnull and field_type[:2] in sff and requires:
        requires[-1] = validators.IS_EMPTY_OR(requires[-1])
    return requires


def bar_escape(item):
    return str(item).replace('|', '||')

def bar_encode(items):
    return '|%s|' % '|'.join(bar_escape(item) for item in items if str(item).strip())

def bar_decode_integer(value):
    return [int(x) for x in value.split('|') if x.strip()]

def bar_decode_string(value):
    return [x.replace('||', '|') for x in string_unpack.split(value[1:-1]) if x.strip()]


class Row(dict):

    """
    a dictionary that lets you do d['a'] as well as d.a
    this is only used to store a Row
    """

    def __getitem__(self, key):
        key=str(key)
        m = table_field.match(key)
        if key in self.get('_extra',{}):
            return self._extra[key]
        elif m:
            try:
                return dict.__getitem__(self, m.group(1))[m.group(2)]
            except KeyError:
                key = m.group(2)
        return dict.__getitem__(self, key)

    def __call__(self,key):
        return self.__getitem__(key)

    def __setitem__(self, key, value):
        dict.__setitem__(self, str(key), value)

    def __getattr__(self, key):
        return self[key]

    def __setattr__(self, key, value):
        self[key] = value

    def __repr__(self):
        return '<Row ' + dict.__repr__(self) + '>'

    def __int__(self):
        return dict.__getitem__(self,'id')

    def __eq__(self,other):
        try:
            return self.as_dict() == other.as_dict()
        except AttributeError:
            return False

    def __ne__(self,other):
        return not (self == other)

    def __copy__(self):
        return Row(dict(self))

    def as_dict(self,datetime_to_str=False):
        SERIALIZABLE_TYPES = (str,unicode,int,long,float,bool,list)
        d = dict(self)
        for k in copy.copy(d.keys()):
            v=d[k]
            if d[k] is None:
                continue
            elif isinstance(v,Row):
                d[k]=v.as_dict()
            elif isinstance(v,Reference):
                d[k]=int(v)
            elif isinstance(v,decimal.Decimal):
                d[k]=float(v)
            elif isinstance(v, (datetime.date, datetime.datetime, datetime.time)):
                if datetime_to_str:
                    d[k] = v.isoformat().replace('T',' ')[:19]
            elif not isinstance(v,SERIALIZABLE_TYPES):
                del d[k]
        return d


def Row_unpickler(data):
    return Row(cPickle.loads(data))

def Row_pickler(data):
    return Row_unpickler, (cPickle.dumps(data.as_dict(datetime_to_str=False)),)

copy_reg.pickle(Row, Row_pickler, Row_unpickler)


################################################################################
# Everything below should be independent on the specifics of the
# database and should for RDBMs and some NoSQL databases
################################################################################

class SQLCallableList(list):
    def __call__(self):
        return copy.copy(self)


class DAL(dict):

    """
    an instance of this class represents a database connection

    Example::

       db = DAL('sqlite://test.db')
       db.define_table('tablename', Field('fieldname1'),
                                    Field('fieldname2'))
    """

    @staticmethod
    def set_folder(folder):
        """
        # ## this allows gluon to set a folder for this thread
        # ## <<<<<<<<< Should go away as new DAL replaces old sql.py
        """
        BaseAdapter.set_folder(folder)

    @staticmethod
    def distributed_transaction_begin(*instances):
        if not instances:
            return
        thread_key = '%s.%s' % (socket.gethostname(), threading.currentThread())
        keys = ['%s.%i' % (thread_key, i) for (i,db) in instances]
        instances = enumerate(instances)
        for (i, db) in instances:
            if not db._adapter.support_distributed_transaction():
                raise SyntaxError, \
                    'distributed transaction not suported by %s' % db._dbname
        for (i, db) in instances:
            db._adapter.distributed_transaction_begin(keys[i])

    @staticmethod
    def distributed_transaction_commit(*instances):
        if not instances:
            return
        instances = enumerate(instances)
        thread_key = '%s.%s' % (socket.gethostname(), threading.currentThread())
        keys = ['%s.%i' % (thread_key, i) for (i,db) in instances]
        for (i, db) in instances:
            if not db._adapter.support_distributed_transaction():
                raise SyntaxError, \
                    'distributed transaction not suported by %s' % db._dbanme
        try:
            for (i, db) in instances:
                db._adapter.prepare(keys[i])
        except:
            for (i, db) in instances:
                db._adapter.rollback_prepared(keys[i])
            raise RuntimeError, 'failure to commit distributed transaction'
        else:
            for (i, db) in instances:
                db._adapter.commit_prepared(keys[i])
        return


    def __init__(self, uri='sqlite://dummy.db',
                 pool_size=0, folder=None,
                 db_codec='UTF-8', check_reserved=None,
                 migrate=True, fake_migrate=False,
                 migrate_enabled=True, fake_migrate_all=False,
                 decode_credentials=False, driver_args=None,
                 adapter_args=None, attempts=5, auto_import=False):
        """
        Creates a new Database Abstraction Layer instance.

        Keyword arguments:

        :uri: string that contains information for connecting to a database.
               (default: 'sqlite://dummy.db')
        :pool_size: How many open connections to make to the database object.
        :folder: <please update me>
        :db_codec: string encoding of the database (default: 'UTF-8')
        :check_reserved: list of adapters to check tablenames and column names
                         against sql reserved keywords. (Default None)

        * 'common' List of sql keywords that are common to all database types
                such as "SELECT, INSERT". (recommended)
        * 'all' Checks against all known SQL keywords. (not recommended)
                <adaptername> Checks against the specific adapters list of keywords
                (recommended)
        * '<adaptername>_nonreserved' Checks against the specific adapters
                list of nonreserved keywords. (if available)
        :migrate (defaults to True) sets default migrate behavior for all tables
        :fake_migrate (defaults to False) sets default fake_migrate behavior for all tables
        :migrate_enabled (defaults to True). If set to False disables ALL migrations
        :fake_migrate_all (defaults to False). If sets to True fake migrates ALL tables
        :attempts (defaults to 5). Number of times to attempt connecting
        """
        if not decode_credentials:
            credential_decoder = lambda cred: cred
        else:
            credential_decoder = lambda cred: urllib.unquote(cred)
        if folder:
            self.set_folder(folder)
        self._uri = uri
        self._pool_size = pool_size
        self._db_codec = db_codec
        self._lastsql = ''
        self._timings = []
        self._pending_references = {}
        self._request_tenant = 'request_tenant'
        self._common_fields = []
        self._referee_name = '%(table)s'
        if not str(attempts).isdigit() or attempts < 0:
            attempts = 5
        if uri:
            uris = isinstance(uri,(list,tuple)) and uri or [uri]
            error = ''
            connected = False
            for k in range(attempts):
                for uri in uris:
                    try:
                        if is_jdbc and not uri.startswith('jdbc:'):
                            uri = 'jdbc:'+uri
                        self._dbname = regex_dbname.match(uri).group()
                        if not self._dbname in ADAPTERS:
                            raise SyntaxError, "Error in URI '%s' or database not supported" % self._dbname
                        # notice that driver args or {} else driver_args
                        # defaults to {} global, not correct
                        args = (self,uri,pool_size,folder,
                                db_codec, credential_decoder,
                                driver_args or {}, adapter_args or {})
                        self._adapter = ADAPTERS[self._dbname](*args)
                        connected = True
                        break
                    except SyntaxError:
                        raise
                    except Exception, error:
                        sys.stderr.write('DEBUG_c: Exception %r' % ((Exception, error,),))
                if connected:
                    break
                else:
                    time.sleep(1)
            if not connected:
                raise RuntimeError, "Failure to connect, tried %d times:\n%s" % (attempts, error)
        else:
            args = (self,'None',0,folder,db_codec)
            self._adapter = BaseAdapter(*args)
            migrate = fake_migrate = False
        adapter = self._adapter
        self._uri_hash = hashlib.md5(adapter.uri).hexdigest()
        self.tables = SQLCallableList()
        self.check_reserved = check_reserved
        if self.check_reserved:
            from reserved_sql_keywords import ADAPTERS as RSK
            self.RSK = RSK
        self._migrate = migrate
        self._fake_migrate = fake_migrate
        self._migrate_enabled = migrate_enabled
        self._fake_migrate_all = fake_migrate_all
        if auto_import:
            self.import_table_definitions(adapter.folder)

    def import_table_definitions(self,path,migrate=False,fake_migrate=False):
        pattern = os.path.join(path,self._uri_hash+'_*.table')
        for filename in glob.glob(pattern):
            tfile = self._adapter.file_open(filename, 'r')
            try:
                sql_fields = cPickle.load(tfile)
                name = filename[len(pattern)-7:-6]
                mf = [(value['sortable'],Field(key,type=value['type'])) \
                          for key, value in sql_fields.items()]
                mf.sort(lambda a,b: cmp(a[0],b[0]))
                self.define_table(name,*[item[1] for item in mf],
                                  **dict(migrate=migrate,fake_migrate=fake_migrate))
            finally:
                self._adapter.file_close(tfile)

    def check_reserved_keyword(self, name):
        """
        Validates ``name`` against SQL keywords
        Uses self.check_reserve which is a list of
        operators to use.
        self.check_reserved
        ['common', 'postgres', 'mysql']
        self.check_reserved
        ['all']
        """
        for backend in self.check_reserved:
            if name.upper() in self.RSK[backend]:
                raise SyntaxError, 'invalid table/column name "%s" is a "%s" reserved SQL keyword' % (name, backend.upper())

    def __contains__(self, tablename):
        if self.has_key(tablename):
            return True
        else:
            return False

    def parse_as_rest(self,patterns,args,vars,query=None,nested_select=True):
        """
        EXAMPLE:

db.define_table('person',Field('name'),Field('info'))
db.define_table('pet',Field('person',db.person),Field('name'),Field('info'))

@request.restful()
def index():
    def GET(*kargs,**kvars):
        patterns = [
            "/persons[person]",
            "/{person.name.startswith}",
            "/{person.name}/:field",
            "/{person.name}/pets[pet.person]",
            "/{person.name}/pet[pet.person]/{pet.name}",
            "/{person.name}/pet[pet.person]/{pet.name}/:field"
            ]
        parser = db.parse_as_rest(patterns,kargs,kvars)
        if parser.status == 200:
            return dict(content=parser.response)
        else:
            raise HTTP(parser.status,parser.error)
    def POST(table_name,**kvars):
        if table_name == 'person':
            return db.person.validate_and_insert(**kvars)
        elif table_name == 'pet':
            return db.pet.validate_and_insert(**kvars)
        else:
            raise HTTP(400)
    return locals()
        """

        db = self
        re1 = re.compile('^{[^\.]+\.[^\.]+(\.(lt|gt|le|ge|eq|ne|contains|startswith|year|month|day|hour|minute|second))?(\.not)?}$')
        re2 = re.compile('^.+\[.+\]$')

        def auto_table(table,base='',depth=0):
            patterns = []
            for field in db[table].fields:
                if base:
                    tag = '%s/%s' % (base,field.replace('_','-'))
                else:
                    tag = '/%s/%s' % (table.replace('_','-'),field.replace('_','-'))
                f = db[table][field]
                if not f.readable: continue
                if f.type=='id' or 'slug' in field or f.type.startswith('reference'):
                    tag += '/{%s.%s}' % (table,field)
                    patterns.append(tag)
                    patterns.append(tag+'/:field')
                elif f.type.startswith('boolean'):
                    tag += '/{%s.%s}' % (table,field)
                    patterns.append(tag)
                    patterns.append(tag+'/:field')
                elif f.type.startswith('double') or f.type.startswith('integer'):
                    tag += '/{%s.%s.ge}/{%s.%s.lt}' % (table,field,table,field)
                    patterns.append(tag)
                    patterns.append(tag+'/:field')
                elif f.type.startswith('list:'):
                    tag += '/{%s.%s.contains}' % (table,field)
                    patterns.append(tag)
                    patterns.append(tag+'/:field')
                elif f.type in ('date','datetime'):
                    tag+= '/{%s.%s.year}' % (table,field)
                    patterns.append(tag)
                    patterns.append(tag+'/:field')
                    tag+='/{%s.%s.month}' % (table,field)
                    patterns.append(tag)
                    patterns.append(tag+'/:field')
                    tag+='/{%s.%s.day}' % (table,field)
                    patterns.append(tag)
                    patterns.append(tag+'/:field')
                if f.type in ('datetime','time'):
                    tag+= '/{%s.%s.hour}' % (table,field)
                    patterns.append(tag)
                    patterns.append(tag+'/:field')
                    tag+='/{%s.%s.minute}' % (table,field)
                    patterns.append(tag)
                    patterns.append(tag+'/:field')
                    tag+='/{%s.%s.second}' % (table,field)
                    patterns.append(tag)
                    patterns.append(tag+'/:field')
                if depth>0:
                    for rtable,rfield in db[table]._referenced_by:
                        tag+='/%s[%s.%s]' % (rtable,rtable,rfield)
                        patterns.append(tag)
                        patterns += auto_table(rtable,base=tag,depth=depth-1)
            return patterns

        if patterns=='auto':
            patterns=[]
            for table in db.tables:
                if not table.startswith('auth_'):
                    patterns += auto_table(table,base='',depth=1)
        else:
            i = 0
            while i<len(patterns):
                pattern = patterns[i]
                tokens = pattern.split('/')
                if tokens[-1].startswith(':auto') and re2.match(tokens[-1]):
                    new_patterns = auto_table(tokens[-1][tokens[-1].find('[')+1:-1],'/'.join(tokens[:-1]))
                    patterns = patterns[:i]+new_patterns+patterns[i+1:]
                    i += len(new_patterns)
                else:
                    i += 1
        if '/'.join(args) == 'patterns':
            return Row({'status':200,'pattern':'list',
                        'error':None,'response':patterns})
        for pattern in patterns:
            otable=table=None
            dbset=db(query)
            i=0
            tags = pattern[1:].split('/')
            # print pattern
            if len(tags)!=len(args):
                continue
            for tag in tags:
                # print i, tag, args[i]
                if re1.match(tag):
                    # print 're1:'+tag
                    tokens = tag[1:-1].split('.')
                    table, field = tokens[0], tokens[1]
                    if not otable or table == otable:
                        if len(tokens)==2 or tokens[2]=='eq':
                            query = db[table][field]==args[i]
                        elif tokens[2]=='ne':
                            query = db[table][field]!=args[i]
                        elif tokens[2]=='lt':
                            query = db[table][field]<args[i]
                        elif tokens[2]=='gt':
                            query = db[table][field]>args[i]
                        elif tokens[2]=='ge':
                            query = db[table][field]>=args[i]
                        elif tokens[2]=='le':
                            query = db[table][field]<=args[i]
                        elif tokens[2]=='year':
                            query = db[table][field].year()==args[i]
                        elif tokens[2]=='month':
                            query = db[table][field].month()==args[i]
                        elif tokens[2]=='day':
                            query = db[table][field].day()==args[i]
                        elif tokens[2]=='hour':
                            query = db[table][field].hour()==args[i]
                        elif tokens[2]=='minute':
                            query = db[table][field].minutes()==args[i]
                        elif tokens[2]=='second':
                            query = db[table][field].seconds()==args[i]
                        elif tokens[2]=='startswith':
                            query = db[table][field].startswith(args[i])
                        elif tokens[2]=='contains':
                            query = db[table][field].contains(args[i])
                        else:
                            raise RuntimeError, "invalid pattern: %s" % pattern
                        if len(tokens)==4 and tokens[3]=='not':
                            query = ~query
                        elif len(tokens)>=4:
                            raise RuntimeError, "invalid pattern: %s" % pattern
                        dbset=dbset(query)
                    else:
                        raise RuntimeError, "missing relation in pattern: %s" % pattern
                elif otable and re2.match(tag) and args[i]==tag[:tag.find('[')]:
                    # print 're2:'+tag
                    ref = tag[tag.find('[')+1:-1]
                    if '.' in ref:
                        table,field = ref.split('.')
                        # print table,field
                        if nested_select:
                            try:
                                dbset=db(db[table][field].belongs(dbset._select(db[otable]._id)))
                            except ValueError:
                                return Row({'status':400,'pattern':pattern,
                                            'error':'invalid path','response':None})
                        else:
                            items = [item.id for item in dbset.select(db[otable]._id)]
                            dbset=db(db[table][field].belongs(items))
                    else:
                        dbset=dbset(db[ref])
                elif tag==':field' and table:
                    # # print 're3:'+tag
                    field = args[i]
                    if not field in db[table]: break
                    try:
                        item =  dbset.select(db[table][field],limitby=(0,1)).first()
                    except ValueError:
                        return Row({'status':400,'pattern':pattern,
                                    'error':'invalid path','response':None})
                    if not item:
                        return Row({'status':404,'pattern':pattern,
                                    'error':'record not found','response':None})
                    else:
                        return Row({'status':200,'response':item[field],
                                    'pattern':pattern})
                elif tag != args[i]:
                    break
                otable = table
                i += 1
                if i==len(tags) and table:
                    otable,ofield = vars.get('order','%s.%s' % (table,field)).split('.',1)
                    try:
                        if otable[:1]=='~': orderby = ~db[otable[1:]][ofield]
                        else: orderby = db[otable][ofield]
                    except KeyError:
                        return Row({'status':400,'error':'invalid orderby','response':None})
                    fields = [field for field in db[table] if field.readable]
                    count = dbset.count()
                    try:
                        limits = (int(vars.get('min',0)),int(vars.get('max',1000)))
                        if limits[0]<0 or limits[1]<limits[0]: raise ValueError
                    except ValueError:
                        Row({'status':400,'error':'invalid limits','response':None})
                    if count > limits[1]-limits[0]:
                        Row({'status':400,'error':'too many records','response':None})
                    try:
                        response = dbset.select(limitby=limits,orderby=orderby,*fields)
                    except ValueError:
                        return Row({'status':400,'pattern':pattern,
                                    'error':'invalid path','response':None})
                    return Row({'status':200,'response':response,'pattern':pattern})
        return Row({'status':400,'error':'no matching pattern','response':None})


    def define_table(
        self,
        tablename,
        *fields,
        **args
        ):

        for key in args:
            if key not in [
                    'migrate',
                    'primarykey',
                    'fake_migrate',
                    'format',
                    'trigger_name',
                    'sequence_name',
                    'polymodel']:
                raise SyntaxError, 'invalid table "%s" attribute: %s' % (tablename, key)
        migrate = self._migrate_enabled and args.get('migrate',self._migrate)
        fake_migrate = self._fake_migrate_all or args.get('fake_migrate',self._fake_migrate)
        format = args.get('format',None)
        trigger_name = args.get('trigger_name', None)
        sequence_name = args.get('sequence_name', None)
        primarykey=args.get('primarykey',None)
        polymodel=args.get('polymodel',None)
        if not isinstance(tablename,str):
            raise SyntaxError, "missing table name"
        tablename = cleanup(tablename)
        lowertablename = tablename.lower()

        if tablename.startswith('_') or hasattr(self,lowertablename) or \
                regex_python_keywords.match(tablename):
            raise SyntaxError, 'invalid table name: %s' % tablename
        elif lowertablename in self.tables:
            raise SyntaxError, 'table already defined: %s' % tablename
        elif self.check_reserved:
            self.check_reserved_keyword(tablename)

        if self._common_fields:
            fields = [f for f in fields] + [f for f in self._common_fields]

        t = self[tablename] = Table(self, tablename, *fields,
                                    **dict(primarykey=primarykey,
                                    trigger_name=trigger_name,
                                    sequence_name=sequence_name))
        # db magic
        if self._uri in (None,'None'):
            return t

        t._create_references()

        if migrate or self._adapter.dbengine=='google:datastore':
            try:
                sql_locker.acquire()
                self._adapter.create_table(t,migrate=migrate,
                                           fake_migrate=fake_migrate,
                                           polymodel=polymodel)
            finally:
                sql_locker.release()
        else:
            t._dbt = None
        self.tables.append(tablename)
        t._format = format
        return t

    def __iter__(self):
        for tablename in self.tables:
            yield self[tablename]

    def __getitem__(self, key):
        return dict.__getitem__(self, str(key))

    def __setitem__(self, key, value):
        dict.__setitem__(self, str(key), value)

    def __getattr__(self, key):
        return self[key]

    def __setattr__(self, key, value):
        if key[:1]!='_' and key in self:
            raise SyntaxError, \
                'Object %s exists and cannot be redefined' % key
        self[key] = value

    def __repr__(self):
        return '<DAL ' + dict.__repr__(self) + '>'

    def __call__(self, query=None):
        if isinstance(query,Table):
            query = query._id>0
        elif isinstance(query,Field):
            query = query!=None
        return Set(self, query)

    def commit(self):
        self._adapter.commit()

    def rollback(self):
        self._adapter.rollback()

    def executesql(self, query, placeholders=None, as_dict=False):
        """
        placeholders is optional and will always be None when using DAL
        if using raw SQL with placeholders, placeholders may be
        a sequence of values to be substituted in
        or, *if supported by the DB driver*, a dictionary with keys
        matching named placeholders in your SQL.

        Added 2009-12-05 "as_dict" optional argument. Will always be
        None when using DAL. If using raw SQL can be set to True
        and the results cursor returned by the DB driver will be
        converted to a sequence of dictionaries keyed with the db
        field names. Tested with SQLite but should work with any database
        since the cursor.description used to get field names is part of the
        Python dbi 2.0 specs. Results returned with as_dict = True are
        the same as those returned when applying .to_list() to a DAL query.

        [{field1: value1, field2: value2}, {field1: value1b, field2: value2b}]

        --bmeredyk
        """
        if placeholders:
            self._adapter.execute(query, placeholders)
        else:
            self._adapter.execute(query)
        if as_dict:
            if not hasattr(self._adapter.cursor,'description'):
                raise RuntimeError, "database does not support executesql(...,as_dict=True)"
            # Non-DAL legacy db query, converts cursor results to dict.
            # sequence of 7-item sequences. each sequence tells about a column.
            # first item is always the field name according to Python Database API specs
            columns = self._adapter.cursor.description
            # reduce the column info down to just the field names
            fields = [f[0] for f in columns]
            # will hold our finished resultset in a list
            data = self._adapter.cursor.fetchall()
            # convert the list for each row into a dictionary so it's
            # easier to work with. row['field_name'] rather than row[0]
            return [dict(zip(fields,row)) for row in data]
        # see if any results returned from database
        try:
            return self._adapter.cursor.fetchall()
        except:
            return None

    def _update_referenced_by(self, other):
        for tablename in self.tables:
            by = self[tablename]._referenced_by
            by[:] = [item for item in by if not item[0] == other]

    def export_to_csv_file(self, ofile, *args, **kwargs):
        for table in self.tables:
            ofile.write('TABLE %s\r\n' % table)
            self(self[table]._id > 0).select().export_to_csv_file(ofile, *args, **kwargs)
            ofile.write('\r\n\r\n')
        ofile.write('END')

    def import_from_csv_file(self, ifile, id_map=None, null='<NULL>',
                             unique='uuid', *args, **kwargs):
        if id_map is None: id_map={}
        for line in ifile:
            line = line.strip()
            if not line:
                continue
            elif line == 'END':
                return
            elif not line.startswith('TABLE ') or not line[6:] in self.tables:
                raise SyntaxError, 'invalid file format'
            else:
                tablename = line[6:]
                self[tablename].import_from_csv_file(ifile, id_map, null,
                                                     unique, *args, **kwargs)


class SQLALL(object):
    """
    Helper class providing a comma-separated string having all the field names
    (prefixed by table name and '.')

    normally only called from within gluon.sql
    """

    def __init__(self, table):
        self.table = table

    def __str__(self):
        return ', '.join([str(field) for field in self.table])


class Reference(int):

    def __allocate(self):
        if not self._record:
            self._record = self._table[int(self)]
        if not self._record:
            raise RuntimeError, "Using a recursive select but encountered a broken reference: %s %d"%(self._table, int(self))

    def __getattr__(self, key):
        if key == 'id':
            return int(self)
        self.__allocate()
        return self._record.get(key, None)

    def get(self, key): 
        return self.__getattr__(key) 
        
    def __setattr__(self, key, value):
        if key.startswith('_'):
            int.__setattr__(self, key, value)
            return
        self.__allocate()
        self._record[key] =  value

    def __getitem__(self, key):
        if key == 'id':
            return int(self)
        self.__allocate()
        return self._record.get(key, None)

    def __setitem__(self,key,value):
        self.__allocate()
        self._record[key] = value


def Reference_unpickler(data):
    return marshal.loads(data)

def Reference_pickler(data):
    try:
        marshal_dump = marshal.dumps(int(data))
    except AttributeError:
        marshal_dump = 'i%s' % struct.pack('<i', int(data))
    return (Reference_unpickler, (marshal_dump,))

copy_reg.pickle(Reference, Reference_pickler, Reference_unpickler)


class Table(dict):

    """
    an instance of this class represents a database table

    Example::

        db = DAL(...)
        db.define_table('users', Field('name'))
        db.users.insert(name='me') # print db.users._insert(...) to see SQL
        db.users.drop()
    """

    def __init__(
        self,
        db,
        tablename,
        *fields,
        **args
        ):
        """
        Initializes the table and performs checking on the provided fields.

        Each table will have automatically an 'id'.

        If a field is of type Table, the fields (excluding 'id') from that table
        will be used instead.

        :raises SyntaxError: when a supplied field is of incorrect type.
        """
        self._tablename = tablename
        self._sequence_name = args.get('sequence_name',None) or \
            db and db._adapter.sequence_name(tablename)
        self._trigger_name = args.get('trigger_name',None) or \
            db and db._adapter.trigger_name(tablename)

        primarykey = args.get('primarykey', None)
        fieldnames,newfields=set(),[]
        if primarykey:
            if not isinstance(primarykey,list):
                raise SyntaxError, \
                    "primarykey must be a list of fields from table '%s'" \
                    % tablename
            self._primarykey = primarykey
        elif not [f for f in fields if isinstance(f,Field) and f.type=='id']:
            field = Field('id', 'id')
            newfields.append(field)
            fieldnames.add('id')
            self._id = field
        for field in fields:
            if not isinstance(field, (Field, Table)):
                raise SyntaxError, \
                    'define_table argument is not a Field or Table: %s' % field
            elif isinstance(field, Field) and not field.name in fieldnames:
                if hasattr(field, '_db'):
                    field = copy.copy(field)
                newfields.append(field)
                fieldnames.add(field.name)
                if field.type=='id':
                    self._id = field
            elif isinstance(field, Table):
                table = field
                for field in table:
                    if not field.name in fieldnames and not field.type=='id':
                        newfields.append(copy.copy(field))
                        fieldnames.add(field.name)
            else:
                # let's ignore new fields with duplicated names!!!
                pass
        fields = newfields
        self._db = db
        tablename = tablename
        self.fields = SQLCallableList()
        self.virtualfields = []
        fields = list(fields)

        if db and self._db._adapter.uploads_in_blob==True:
            for field in fields:
                if isinstance(field, Field) and field.type == 'upload'\
                        and field.uploadfield is True:
                    tmp = field.uploadfield = '%s_blob' % field.name
                    fields.append(self._db.Field(tmp, 'blob', default=''))

        lower_fieldnames = set()
        reserved = dir(Table) + ['fields']
        for field in fields:
            if db and db.check_reserved:
                db.check_reserved_keyword(field.name)
            elif field.name in reserved:
                raise SyntaxError, "field name %s not allowed" % field.name

            if field.name.lower() in lower_fieldnames:
                raise SyntaxError, "duplicate field %s in table %s" \
                    % (field.name, tablename)
            else:
                lower_fieldnames.add(field.name.lower())

            self.fields.append(field.name)
            self[field.name] = field
            if field.type == 'id':
                self['id'] = field
            field.tablename = field._tablename = tablename
            field.table = field._table = self
            field.db = field._db = self._db
            if self._db and not field.type in ('text','blob') and \
                    self._db._adapter.maxcharlength < field.length:
                field.length = self._db._adapter.maxcharlength
            if field.requires == DEFAULT:
                field.requires = sqlhtml_validators(field)
        self.ALL = SQLALL(self)

        if hasattr(self,'_primarykey'):
            for k in self._primarykey:
                if k not in self.fields:
                    raise SyntaxError, \
                        "primarykey must be a list of fields from table '%s " % tablename
                else:
                    self[k].notnull = True

    def _validate(self,**vars):
        errors = Row()
        for key,value in vars.items():
            value,error = self[key].validate(value)
            if error:
                errors[key] = error
        return errors

    def _create_references(self):
        pr = self._db._pending_references
        self._referenced_by = []
        for fieldname in self.fields:
            field=self[fieldname]
            if isinstance(field.type,str) and field.type[:10] == 'reference ':
                ref = field.type[10:].strip()
                if not ref.split():
                    raise SyntaxError, 'Table: reference to nothing: %s' %ref
                refs = ref.split('.')
                rtablename = refs[0]
                if not rtablename in self._db:
                    pr[rtablename] = pr.get(rtablename,[]) + [field]
                    continue
                rtable = self._db[rtablename]
                if len(refs)==2:
                    rfieldname = refs[1]
                    if not hasattr(rtable,'_primarykey'):
                        raise SyntaxError,\
                            'keyed tables can only reference other keyed tables (for now)'
                    if rfieldname not in rtable.fields:
                        raise SyntaxError,\
                            "invalid field '%s' for referenced table '%s' in table '%s'" \
                            % (rfieldname, rtablename, self._tablename)
                rtable._referenced_by.append((self._tablename, field.name))
        for referee in pr.get(self._tablename,[]):
            self._referenced_by.append((referee._tablename,referee.name))

    def _filter_fields(self, record, id=False):
        return dict([(k, v) for (k, v) in record.items() if k
                     in self.fields and (self[k].type!='id' or id)])

    def _build_query(self,key):
        """ for keyed table only """
        query = None
        for k,v in key.iteritems():
            if k in self._primarykey:
                if query:
                    query = query & (self[k] == v)
                else:
                    query = (self[k] == v)
            else:
                raise SyntaxError, \
                'Field %s is not part of the primary key of %s' % \
                (k,self._tablename)
        return query

    def __getitem__(self, key):
        if not key:
            return None
        elif isinstance(key, dict):
            """ for keyed table """
            query = self._build_query(key)
            rows = self._db(query).select()
            if rows:
                return rows[0]
            return None
        elif str(key).isdigit():
            return self._db(self._id == key).select(limitby=(0,1)).first()
        elif key:
            return dict.__getitem__(self, str(key))

    def __call__(self, key=DEFAULT, **kwargs):
        if key!=DEFAULT:
            if isinstance(key, Query):
                record = self._db(key).select(limitby=(0,1)).first()
            elif not str(key).isdigit():
                record = None
            else:
                record = self._db(self._id == key).select(limitby=(0,1)).first()
            if record:
                for k,v in kwargs.items():
                    if record[k]!=v: return None
            return record
        elif kwargs:
            query = reduce(lambda a,b:a&b,[self[k]==v for k,v in kwargs.items()])
            return self._db(query).select(limitby=(0,1)).first()
        else:
            return None

    def __setitem__(self, key, value):
        if isinstance(key, dict) and isinstance(value, dict):
            """ option for keyed table """
            if set(key.keys()) == set(self._primarykey):
                value = self._filter_fields(value)
                kv = {}
                kv.update(value)
                kv.update(key)
                if not self.insert(**kv):
                    query = self._build_query(key)
                    self._db(query).update(**self._filter_fields(value))
            else:
                raise SyntaxError,\
                    'key must have all fields from primary key: %s'%\
                    (self._primarykey)
        elif str(key).isdigit():
            if key == 0:
                self.insert(**self._filter_fields(value))
            elif not self._db(self._id == key)\
                    .update(**self._filter_fields(value)):
                raise SyntaxError, 'No such record: %s' % key
        else:
            if isinstance(key, dict):
                raise SyntaxError,\
                    'value must be a dictionary: %s' % value
            dict.__setitem__(self, str(key), value)

    def __delitem__(self, key):
        if isinstance(key, dict):
            query = self._build_query(key)
            if not self._db(query).delete():
                raise SyntaxError, 'No such record: %s' % key
        elif not str(key).isdigit() or not self._db(self._id == key).delete():
            raise SyntaxError, 'No such record: %s' % key

    def __getattr__(self, key):
        return self[key]

    def __setattr__(self, key, value):
        if key in self:
            raise SyntaxError, 'Object exists and cannot be redefined: %s' % key
        self[key] = value

    def __iter__(self):
        for fieldname in self.fields:
            yield self[fieldname]

    def __repr__(self):
        return '<Table ' + dict.__repr__(self) + '>'

    def __str__(self):
        if self.get('_ot', None):
            return '%s AS %s' % (self._ot, self._tablename)
        return self._tablename

    def _drop(self, mode = ''):
        return self._db._adapter._drop(self, mode)

    def drop(self, mode = ''):
        return self._db._adapter.drop(self,mode)

    def _listify(self,fields,update=False):
        new_fields = []
        new_fields_names = []
        for name in fields:
            if not name in self.fields:
                if name != 'id':
                    raise SyntaxError, 'Field %s does not belong to the table' % name
            else:
                new_fields.append((self[name],fields[name]))
                new_fields_names.append(name)
        for ofield in self:
            if not ofield.name in new_fields_names:
                if not update and not ofield.default is None:
                    new_fields.append((ofield,ofield.default))
                elif update and not ofield.update is None:
                    new_fields.append((ofield,ofield.update))
        for ofield in self:
            if not ofield.name in new_fields_names and ofield.compute:
                try:
                    new_fields.append((ofield,ofield.compute(Row(fields))))
                except KeyError:
                    pass
            if not update and ofield.required and not ofield.name in new_fields_names:
                raise SyntaxError,'Table: missing required field: %s' % ofield.name
        return new_fields

    def _insert(self, **fields):
        return self._db._adapter._insert(self,self._listify(fields))

    def insert(self, **fields):
        return self._db._adapter.insert(self,self._listify(fields))

    def validate_and_insert(self,**fields):
        response = Row()
        response.errors = self._validate(**fields)
        if not response.errors:
            response.id = self.insert(**fields)
        else:
            response.id = None
        return response

    def update_or_insert(self, key=DEFAULT, **values):
        if key==DEFAULT:
            record = self(**values)
        else:
            record = self(key)
        if record:
            record.update_record(**values)
            newid = None
        else:
            newid = self.insert(**values)
        return newid

    def bulk_insert(self, items):
        """
        here items is a list of dictionaries
        """
        items = [self._listify(item) for item in items]
        return self._db._adapter.bulk_insert(self,items)

    def _truncate(self, mode = None):
        return self._db._adapter._truncate(self, mode)

    def truncate(self, mode = None):
        return self._db._adapter.truncate(self, mode)

    def import_from_csv_file(
        self,
        csvfile,
        id_map=None,
        null='<NULL>',
        unique='uuid',
        *args, **kwargs
        ):
        """
        import records from csv file. Column headers must have same names as
        table fields. field 'id' is ignored. If column names read 'table.file'
        the 'table.' prefix is ignored.
        'unique' argument is a field which must be unique
        (typically a uuid field)
        """

        delimiter = kwargs.get('delimiter', ',')
        quotechar = kwargs.get('quotechar', '"')
        quoting = kwargs.get('quoting', csv.QUOTE_MINIMAL)

        reader = csv.reader(csvfile, delimiter=delimiter, quotechar=quotechar, quoting=quoting)
        colnames = None
        if isinstance(id_map, dict):
            if not self._tablename in id_map:
                id_map[self._tablename] = {}
            id_map_self = id_map[self._tablename]

        def fix(field, value, id_map):
            if value == null:
                value = None
            elif field.type=='blob':
                value = base64.b64decode(value)
            elif field.type=='double':
                if not value.strip():
                    value = None
                else:
                    value = float(value)
            elif field.type=='integer':
                if not value.strip():
                    value = None
                else:
                    value = int(value)
            elif field.type.startswith('list:string'):
                value = bar_decode_string(value)
            elif field.type.startswith('list:reference'):
                ref_table = field.type[10:].strip()
                value = [id_map[ref_table][int(v)] \
                             for v in bar_decode_string(value)]
            elif field.type.startswith('list:'):
                value = bar_decode_integer(value)
            elif id_map and field.type.startswith('reference'):
                try:
                    value = id_map[field.type[9:].strip()][value]
                except KeyError:
                    pass
            return (field.name, value)

        def is_id(colname):
            if colname in self:
                return self[colname].type == 'id'
            else:
                return False

        for line in reader:
            if not line:
                break
            if not colnames:
                colnames = [x.split('.',1)[-1] for x in line][:len(line)]
                cols, cid = [], []
                for i,colname in enumerate(colnames):
                    if is_id(colname):
                        cid = i
                    else:
                        cols.append(i)
                    if colname == unique:
                        unique_idx = i
            else:
                items = [fix(self[colnames[i]], line[i], id_map) \
                             for i in cols if colnames[i] in self.fields]
                # Validation. Check for duplicate of 'unique' &,
                # if present, update instead of insert.
                if not unique or unique not in colnames:
                    new_id = self.insert(**dict(items))
                else:
                    unique_value = line[unique_idx]
                    query = self._db[self][unique] == unique_value
                    record = self._db(query).select().first()
                    if record:
                        record.update_record(**dict(items))
                        new_id = record[self._id.name]
                    else:
                        new_id = self.insert(**dict(items))
                if id_map and cid != []:
                    id_map_self[line[cid]] = new_id

    def with_alias(self, alias):
        return self._db._adapter.alias(self,alias)

    def on(self, query):
        return Expression(self._db,self._db._adapter.ON,self,query)



class Expression(object):

    def __init__(
        self,
        db,
        op,
        first=None,
        second=None,
        type=None,
        ):

        self.db = db
        self.op = op
        self.first = first
        self.second = second
        ### self._tablename =  first._tablename ## CHECK
        if not type and first and hasattr(first,'type'):
            self.type = first.type
        else:
            self.type = type

    def sum(self):
        return Expression(self.db, self.db._adapter.AGGREGATE, self, 'SUM', self.type)

    def max(self):
        return Expression(self.db, self.db._adapter.AGGREGATE, self, 'MAX', self.type)

    def min(self):
        return Expression(self.db, self.db._adapter.AGGREGATE, self, 'MIN', self.type)

    def len(self):
        return Expression(self.db, self.db._adapter.AGGREGATE, self, 'LENGTH', 'integer')

    def lower(self):
        return Expression(self.db, self.db._adapter.LOWER, self, None, self.type)

    def upper(self):
        return Expression(self.db, self.db._adapter.UPPER, self, None, self.type)

    def year(self):
        return Expression(self.db, self.db._adapter.EXTRACT, self, 'year', 'integer')

    def month(self):
        return Expression(self.db, self.db._adapter.EXTRACT, self, 'month', 'integer')

    def day(self):
        return Expression(self.db, self.db._adapter.EXTRACT, self, 'day', 'integer')

    def hour(self):
        return Expression(self.db, self.db._adapter.EXTRACT, self, 'hour', 'integer')

    def minutes(self):
        return Expression(self.db, self.db._adapter.EXTRACT, self, 'minute', 'integer')

    def coalesce(self,*others):
        return Expression(self.db, self.db._adapter.COALESCE, self, others, self.type)

    def coalesce_zero(self):
        return Expression(self.db, self.db._adapter.COALESCE_ZERO, self, None, self.type)

    def seconds(self):
        return Expression(self.db, self.db._adapter.EXTRACT, self, 'second', 'integer')

    def __getslice__(self, start, stop):
        if start < 0:
            pos0 = '(%s - %d)' % (self.len(), abs(start) - 1)
        else:
            pos0 = start + 1

        if stop < 0:
            length = '(%s - %d - %s)' % (self.len(), abs(stop) - 1, pos0)
        elif stop == sys.maxint:
            length = self.len()
        else:
            length = '(%s - %s)' % (stop + 1, pos0)
        return Expression(self.db,self.db._adapter.SUBSTRING,
                          self, (pos0, length), self.type)

    def __getitem__(self, i):
        return self[i:i + 1]

    def __str__(self):
        return self.db._adapter.expand(self,self.type)

    def __or__(self, other):  # for use in sortby
        return Expression(self.db,self.db._adapter.COMMA,self,other,self.type)

    def __invert__(self):
        if hasattr(self,'_op') and self.op == self.db._adapter.INVERT:
            return self.first
        return Expression(self.db,self.db._adapter.INVERT,self,type=self.type)

    def __add__(self, other):
        return Expression(self.db,self.db._adapter.ADD,self,other,self.type)

    def __sub__(self, other):
        if self.type == 'integer':
            result_type = 'integer'
        elif self.type in ['date','time','datetime','double']:
            result_type = 'double'
        else:
            raise SyntaxError, "subtraction operation not supported for type"
        return Expression(self.db,self.db._adapter.SUB,self,other,
                          result_type)
    def __mul__(self, other):
        return Expression(self.db,self.db._adapter.MUL,self,other,self.type)

    def __div__(self, other):
        return Expression(self.db,self.db._adapter.DIV,self,other,self.type)

    def __mod__(self, other):
        return Expression(self.db,self.db._adapter.MOD,self,other,self.type)

    def __eq__(self, value):
        return Query(self.db, self.db._adapter.EQ, self, value)

    def __ne__(self, value):
        return Query(self.db, self.db._adapter.NE, self, value)

    def __lt__(self, value):
        return Query(self.db, self.db._adapter.LT, self, value)

    def __le__(self, value):
        return Query(self.db, self.db._adapter.LE, self, value)

    def __gt__(self, value):
        return Query(self.db, self.db._adapter.GT, self, value)

    def __ge__(self, value):
        return Query(self.db, self.db._adapter.GE, self, value)

    def like(self, value):
        return Query(self.db, self.db._adapter.LIKE, self, value)

    def belongs(self, value):
        return Query(self.db, self.db._adapter.BELONGS, self, value)

    def startswith(self, value):
        if not self.type in ('string', 'text'):
            raise SyntaxError, "startswith used with incompatible field type"
        return Query(self.db, self.db._adapter.STARTSWITH, self, value)

    def endswith(self, value):
        if not self.type in ('string', 'text'):
            raise SyntaxError, "endswith used with incompatible field type"
        return Query(self.db, self.db._adapter.ENDSWITH, self, value)
    
    def contains(self, value, all=False):
        if isinstance(value,(list,tuple)):
            subqueries = [self.contains(str(v).strip()) for v in value if str(v).strip()]
            return reduce(all and AND or OR, subqueries)
        if not self.type in ('string', 'text') and not self.type.startswith('list:'):
            raise SyntaxError, "contains used with incompatible field type"
        return Query(self.db, self.db._adapter.CONTAINS, self, value)

    def with_alias(self,alias):
        return Expression(self.db,self.db._adapter.AS,self,alias,self.type)

    # for use in both Query and sortby


class SQLCustomType(object):
    """
    allows defining of custom SQL types

    Example::

        decimal = SQLCustomType(
            type ='double',
            native ='integer',
            encoder =(lambda x: int(float(x) * 100)),
            decoder = (lambda x: Decimal("0.00") + Decimal(str(float(x)/100)) )
            )

        db.define_table(
            'example',
            Field('value', type=decimal)
            )

    :param type: the web2py type (default = 'string')
    :param native: the backend type
    :param encoder: how to encode the value to store it in the backend
    :param decoder: how to decode the value retrieved from the backend
    :param validator: what validators to use ( default = None, will use the
        default validator for type)
    """

    def __init__(
        self,
        type='string',
        native=None,
        encoder=None,
        decoder=None,
        validator=None,
        _class=None,
        ):

        self.type = type
        self.native = native
        self.encoder = encoder or (lambda x: x)
        self.decoder = decoder or (lambda x: x)
        self.validator = validator
        self._class = _class or type

    def startswith(self, dummy=None):
        return False

    def __getslice__(self, a=0, b=100):
        return None

    def __getitem__(self, i):
        return None

    def __str__(self):
        return self._class

class FieldVirtual(object):
    def __init__(self,f):
        self.f = f

class FieldLazy(object):
    def __init__(self,f):
        self.f = f
        

class Field(Expression):

    Virtual = FieldVirtual
    Lazy = FieldLazy

    """
    an instance of this class represents a database field

    example::

        a = Field(name, 'string', length=32, default=None, required=False,
            requires=IS_NOT_EMPTY(), ondelete='CASCADE',
            notnull=False, unique=False,
            uploadfield=True, widget=None, label=None, comment=None,
            uploadfield=True, # True means store on disk,
                              # 'a_field_name' means store in this field in db
                              # False means file content will be discarded.
            writable=True, readable=True, update=None, authorize=None,
            autodelete=False, represent=None, uploadfolder=None,
            uploadseparate=False # upload to separate directories by uuid_keys
                                 # first 2 character and tablename.fieldname
                                 # False - old behavior
                                 # True - put uploaded file in
                                 #   <uploaddir>/<tablename>.<fieldname>/uuid_key[:2]
                                 #        directory)

    to be used as argument of DAL.define_table

    allowed field types:
    string, boolean, integer, double, text, blob,
    date, time, datetime, upload, password

    strings must have a length of Adapter.maxcharlength by default (512 or 255 for mysql)
    fields should have a default or they will be required in SQLFORMs
    the requires argument is used to validate the field input in SQLFORMs

    """

    def __init__(
        self,
        fieldname,
        type='string',
        length=None,
        default=DEFAULT,
        required=False,
        requires=DEFAULT,
        ondelete='CASCADE',
        notnull=False,
        unique=False,
        uploadfield=True,
        widget=None,
        label=None,
        comment=None,
        writable=True,
        readable=True,
        update=None,
        authorize=None,
        autodelete=False,
        represent=None,
        uploadfolder=None,
        uploadseparate=False,
        compute=None,
        custom_store=None,
        custom_retrieve=None,
        custom_delete=None,
        ):
        self.db = None
        self.op = None
        self.first = None
        self.second = None
        if not isinstance(fieldname,str):
            raise SyntaxError, "missing field name"
        if fieldname.startswith(':'):
            fieldname,readable,writable=fieldname[1:],False,False
        elif fieldname.startswith('.'):
            fieldname,readable,writable=fieldname[1:],False,False
        if '=' in fieldname:
            fieldname,default = fieldname.split('=',1)
        self.name = fieldname = cleanup(fieldname)
        if hasattr(Table,fieldname) or fieldname[0] == '_' or \
                regex_python_keywords.match(fieldname):
            raise SyntaxError, 'Field: invalid field name: %s' % fieldname
        if isinstance(type, Table):
            type = 'reference ' + type._tablename
        self.type = type  # 'string', 'integer'
        self.length = (length is None) and DEFAULTLENGTH.get(type,512) or length
        if default==DEFAULT:
            self.default = update or None
        else:
            self.default = default
        self.required = required  # is this field required
        self.ondelete = ondelete.upper()  # this is for reference fields only
        self.notnull = notnull
        self.unique = unique
        self.uploadfield = uploadfield
        self.uploadfolder = uploadfolder
        self.uploadseparate = uploadseparate
        self.widget = widget
        self.label = label or ' '.join(item.capitalize() for item in fieldname.split('_'))
        self.comment = comment
        self.writable = writable
        self.readable = readable
        self.update = update
        self.authorize = authorize
        self.autodelete = autodelete
        if not represent and type in ('list:integer','list:string'):
            represent=lambda x: ', '.join(str(y) for y in x or [])
        self.represent = represent
        self.compute = compute
        self.isattachment = True
        self.custom_store = custom_store
        self.custom_retrieve = custom_retrieve
        self.custom_delete = custom_delete
        if self.label is None:
            self.label = ' '.join([x.capitalize() for x in
                                  fieldname.split('_')])
        if requires is None:
            self.requires = []
        else:
            self.requires = requires

    def store(self, file, filename=None, path=None):
        if self.custom_store:
            return self.custom_store(file,filename,path)
        if not filename:
            filename = file.name
        filename = os.path.basename(filename.replace('/', os.sep)\
                                        .replace('\\', os.sep))
        m = re.compile('\.(?P<e>\w{1,5})$').search(filename)
        extension = m and m.group('e') or 'txt'
        uuid_key = web2py_uuid().replace('-', '')[-16:]
        encoded_filename = base64.b16encode(filename).lower()
        newfilename = '%s.%s.%s.%s' % \
            (self._tablename, self.name, uuid_key, encoded_filename)
        newfilename = newfilename[:200] + '.' + extension
        if isinstance(self.uploadfield,Field):
            blob_uploadfield_name = self.uploadfield.uploadfield
            keys={self.uploadfield.name: newfilename,
                  blob_uploadfield_name: file.read()}
            self.uploadfield.table.insert(**keys)
        elif self.uploadfield == True:
            if path:
                pass
            elif self.uploadfolder:
                path = self.uploadfolder
            elif self.db._adapter.folder:
                path = os.path.join(self.db._adapter.folder, '..', 'uploads')
            else:
                raise RuntimeError, "you must specify a Field(...,uploadfolder=...)"
            if self.uploadseparate:
                path = os.path.join(path,"%s.%s" % (self._tablename, self.name),uuid_key[:2])
            if not os.path.exists(path):
                os.makedirs(path)
            pathfilename = os.path.join(path, newfilename)
            dest_file = open(pathfilename, 'wb')
            try:
                shutil.copyfileobj(file, dest_file)
            finally:
                dest_file.close()
        return newfilename

    def retrieve(self, name, path=None):
        if self.custom_retrieve:
            return self.custom_retrieve(name, path)
        import http
        if self.authorize or isinstance(self.uploadfield, str):
            row = self.db(self == name).select().first()
            if not row:
                raise http.HTTP(404)
        if self.authorize and not self.authorize(row):
            raise http.HTTP(403)
        try:
            m = regex_content.match(name)
            if not m or not self.isattachment:
                raise TypeError, 'Can\'t retrieve %s' % name
            filename = base64.b16decode(m.group('name'), True)
            filename = regex_cleanup_fn.sub('_', filename)
        except (TypeError, AttributeError):
            filename = name
        if isinstance(self.uploadfield, str):  # ## if file is in DB
            return (filename, cStringIO.StringIO(row[self.uploadfield] or ''))
        elif isinstance(self.uploadfield,Field):
            blob_uploadfield_name = self.uploadfield.uploadfield
            query = self.uploadfield == name
            data = self.uploadfield.table(query)[blob_uploadfield_name]
            return (filename, cStringIO.StringIO(data))
        else:
            # ## if file is on filesystem
            if path:
                pass
            elif self.uploadfolder:
                path = self.uploadfolder
            else:
                path = os.path.join(self.db._adapter.folder, '..', 'uploads')
            if self.uploadseparate:
                t = m.group('table')
                f = m.group('field')
                u = m.group('uuidkey')
                path = os.path.join(path,"%s.%s" % (t,f),u[:2])
            return (filename, open(os.path.join(path, name), 'rb'))

    def formatter(self, value):
        if value is None or not self.requires:
            return value
        if not isinstance(self.requires, (list, tuple)):
            requires = [self.requires]
        elif isinstance(self.requires, tuple):
            requires = list(self.requires)
        else:
            requires = copy.copy(self.requires)
        requires.reverse()
        for item in requires:
            if hasattr(item, 'formatter'):
                value = item.formatter(value)
        return value

    def validate(self, value):
        if not self.requires:
            return (value, None)
        requires = self.requires
        if not isinstance(requires, (list, tuple)):
            requires = [requires]
        for validator in requires:
            (value, error) = validator(value)
            if error:
                return (value, error)
        return (value, None)

    def count(self):
        return Expression(self.db, self.db._adapter.AGGREGATE, self, 'COUNT', 'integer')

    def __nonzero__(self):
        return True

    def __str__(self):
        try:
            return '%s.%s' % (self.tablename, self.name)
        except:
            return '<no table>.%s' % self.name


def raw(s): return Expression(None,s)

class Query(object):

    """
    a query object necessary to define a set.
    it can be stored or can be passed to DAL.__call__() to obtain a Set

    Example::

        query = db.users.name=='Max'
        set = db(query)
        records = set.select()

    """

    def __init__(
        self,
        db,
        op,
        first=None,
        second=None,
        ):
        self.db = self._db = db
        self.op = op
        self.first = first
        self.second = second

    def __str__(self):
        return self.db._adapter.expand(self)

    def __and__(self, other):
        return Query(self.db,self.db._adapter.AND,self,other)

    def __or__(self, other):
        return Query(self.db,self.db._adapter.OR,self,other)

    def __invert__(self):
        if self.op==self.db._adapter.NOT:
            return self.first
        return Query(self.db,self.db._adapter.NOT,self)


regex_quotes = re.compile("'[^']*'")


def xorify(orderby):
    if not orderby:
        return None
    orderby2 = orderby[0]
    for item in orderby[1:]:
        orderby2 = orderby2 | item
    return orderby2


class Set(object):

    """
    a Set represents a set of records in the database,
    the records are identified by the query=Query(...) object.
    normally the Set is generated by DAL.__call__(Query(...))

    given a set, for example
       set = db(db.users.name=='Max')
    you can:
       set.update(db.users.name='Massimo')
       set.delete() # all elements in the set
       set.select(orderby=db.users.id, groupby=db.users.name, limitby=(0,10))
    and take subsets:
       subset = set(db.users.id<5)
    """

    def __init__(self, db, query):
        self.db = db
        self._db = db # for backward compatibility
        self.query = query

    def __call__(self, query):
        if isinstance(query,Table):
            query = query._id>0
        elif isinstance(query,str):
            query = raw(query)
        elif isinstance(query,Field):
            query = query!=None
        if self.query:
            return Set(self.db, self.query & query)
        else:
            return Set(self.db, query)

    def _count(self,distinct=None):
        return self.db._adapter._count(self.query,distinct)

    def _select(self, *fields, **attributes):
        return self.db._adapter._select(self.query,fields,attributes)

    def _delete(self):
        tablename=self.db._adapter.get_table(self.query)
        return self.db._adapter._delete(tablename,self.query)

    def _update(self, **update_fields):
        tablename = self.db._adapter.get_table(self.query)
        fields = self.db[tablename]._listify(update_fields,update=True)
        return self.db._adapter._update(tablename,self.query,fields)

    def isempty(self):
        return not self.select(limitby=(0,1))

    def count(self,distinct=None):
        return self.db._adapter.count(self.query,distinct)

    def select(self, *fields, **attributes):
        return self.db._adapter.select(self.query,fields,attributes)

    def delete(self):
        tablename=self.db._adapter.get_table(self.query)
        self.delete_uploaded_files()
        return self.db._adapter.delete(tablename,self.query)

    def update(self, **update_fields):
        tablename = self.db._adapter.get_table(self.query)
        fields = self.db[tablename]._listify(update_fields,update=True)
        if not fields:
            raise SyntaxError, "No fields to update"
        self.delete_uploaded_files(update_fields)
        return self.db._adapter.update(tablename,self.query,fields)

    def validate_and_update(self, **update_fields):
        tablename = self.db._adapter.get_table(self.query)
        response = Row()
        response.errors = self.db[tablename]._validate(**update_fields)
        fields = self.db[tablename]._listify(update_fields,update=True)
        if not fields:
            raise SyntaxError, "No fields to update"
        self.delete_uploaded_files(update_fields)
        if not response.errors:
            response.updated = self.db._adapter.update(tablename,self.query,fields)
        else:
            response.updated = None
        return response

    def delete_uploaded_files(self, upload_fields=None):
        table = self.db[self.db._adapter.tables(self.query)[0]]
        # ## mind uploadfield==True means file is not in DB
        if upload_fields:
            fields = upload_fields.keys()
        else:
            fields = table.fields
        fields = [f for f in fields if table[f].type == 'upload'
                   and table[f].uploadfield == True
                   and table[f].autodelete]
        if not fields:
            return
        for record in self.select(*[table[f] for f in fields]):
            for fieldname in fields:
                field = table[fieldname]
                oldname = record.get(fieldname, None)
                if not oldname:
                    continue
                if upload_fields and oldname == upload_fields[fieldname]:
                    continue
                if field.custom_delete:
                    field.custom_delete(oldname)
                else:
                    uploadfolder = field.uploadfolder
                    if not uploadfolder:
                        uploadfolder = os.path.join(self.db._adapter.folder, '..', 'uploads')
                    if field.uploadseparate:
                        items = oldname.split('.')
                        uploadfolder = os.path.join(uploadfolder,
                                                    "%s.%s" % (items[0], items[1]),
                                                    items[2][:2])
                    oldpath = os.path.join(uploadfolder, oldname)
                    if os.path.exists(oldpath):
                        os.unlink(oldpath)

def update_record(pack, a=None):
    (colset, table, id) = pack
    b = a or dict(colset)
    c = dict([(k,v) for (k,v) in b.items() if k in table.fields and table[k].type!='id'])
    table._db(table._id==id).update(**c)
    for (k, v) in c.items():
        colset[k] = v

class VirtualCommand(object):
    def __init__(self,method,row):
        self.method=method
        #self.instance=instance
        self.row=row
    def __call__(self,*args,**kwargs):
        return self.method(self.row,*args,**kwargs)

def lazy_virtualfield(f):
    f.__lazy__ = True
    return f

class Rows(object):

    """
    A wrapper for the return value of a select. It basically represents a table.
    It has an iterator and each row is represented as a dictionary.
    """

    # ## TODO: this class still needs some work to care for ID/OID

    def __init__(
        self,
        db=None,
        records=[],
        colnames=[],
        compact=True,
        rawrows=None
        ):
        self.db = db
        self.records = records
        self.colnames = colnames
        self.compact = compact
        self.response = rawrows

    def setvirtualfields(self,**keyed_virtualfields):
        """
        db.define_table('x',Field('number','integer'))
        if db(db.x).isempty(): [db.x.insert(number=i) for i in range(10)]

        from gluon.dal import lazy_virtualfield

        class MyVirtualFields(object):
            # normal virtual field (backward compatible, discouraged)
            def normal_shift(self): return self.x.number+1
            # lazy virtual field (because of @staticmethod)
            @lazy_virtualfield
            def lazy_shift(instance,row,delta=4): return row.x.number+delta
        db.x.virtualfields.append(MyVirtualFields())

        for row in db(db.x).select():
            print row.number, row.normal_shift, row.lazy_shift(delta=7)
        """
        if not keyed_virtualfields:
            return self
        for row in self.records:
            for (tablename,virtualfields) in keyed_virtualfields.items():
                attributes = dir(virtualfields)
                if not tablename in row:
                    box = row[tablename] = Row()
                else:
                    box = row[tablename]
                updated = False
                for attribute in attributes:
                    if attribute[0] != '_':
                        method = getattr(virtualfields,attribute)
                        if hasattr(method,'__lazy__'):
                            box[attribute]=VirtualCommand(method,row)
                        elif type(method)==types.MethodType:
                            if not updated:
                                virtualfields.__dict__.update(row)
                                updated = True
                            box[attribute]=method()
        return self

    def __and__(self,other):
        if self.colnames!=other.colnames: raise Exception, 'Cannot & incompatible Rows objects'
        records = self.records+other.records
        return Rows(self.db,records,self.colnames)

    def __or__(self,other):
        if self.colnames!=other.colnames: raise Exception, 'Cannot | incompatible Rows objects'
        records = self.records
        records += [record for record in other.records \
                        if not record in records]
        return Rows(self.db,records,self.colnames)

    def __nonzero__(self):
        if len(self.records):
            return 1
        return 0

    def __len__(self):
        return len(self.records)

    def __getslice__(self, a, b):
        return Rows(self.db,self.records[a:b],self.colnames)

    def __getitem__(self, i):
        row = self.records[i]
        keys = row.keys()
        if self.compact and len(keys) == 1 and keys[0] != '_extra':
            return row[row.keys()[0]]
        return row

    def __iter__(self):
        """
        iterator over records
        """

        for i in xrange(len(self)):
            yield self[i]

    def __str__(self):
        """
        serializes the table into a csv file
        """

        s = cStringIO.StringIO()
        self.export_to_csv_file(s)
        return s.getvalue()

    def first(self):
        if not self.records:
            return None
        return self[0]

    def last(self):
        if not self.records:
            return None
        return self[-1]

    def find(self,f):
        """
        returns a new Rows object, a subset of the original object,
        filtered by the function f
        """
        if not self.records:
            return Rows(self.db, [], self.colnames)
        records = []
        for i in range(0,len(self)):
            row = self[i]
            if f(row):
                records.append(self.records[i])
        return Rows(self.db, records, self.colnames)

    def exclude(self, f):
        """
        removes elements from the calling Rows object, filtered by the function f,
        and returns a new Rows object containing the removed elements
        """
        if not self.records:
            return Rows(self.db, [], self.colnames)
        removed = []
        i=0
        while i<len(self):
            row = self[i]
            if f(row):
                removed.append(self.records[i])
                del self.records[i]
            else:
                i += 1
        return Rows(self.db, removed, self.colnames)

    def sort(self, f, reverse=False):
        """
        returns a list of sorted elements (not sorted in place)
        """
        return Rows(self.db,sorted(self,key=f,reverse=reverse),self.colnames)

    def as_list(self,
                compact=True,
                storage_to_dict=True,
                datetime_to_str=True):
        """
        returns the data as a list or dictionary.
        :param storage_to_dict: when True returns a dict, otherwise a list(default True)
        :param datetime_to_str: convert datetime fields as strings (default True)
        """
        (oc, self.compact) = (self.compact, compact)
        if storage_to_dict:
            items = [item.as_dict(datetime_to_str) for item in self]
        else:
            items = [item for item in self]
        self.compact = compact
        return items


    def as_dict(self,
                key='id',
                compact=True,
                storage_to_dict=True,
                datetime_to_str=True):
        """
        returns the data as a dictionary of dictionaries (storage_to_dict=True) or records (False)

        :param key: the name of the field to be used as dict key, normally the id
        :param compact: ? (default True)
        :param storage_to_dict: when True returns a dict, otherwise a list(default True)
        :param datetime_to_str: convert datetime fields as strings (default True)
        """
        rows = self.as_list(compact, storage_to_dict, datetime_to_str)
        if isinstance(key,str) and key.count('.')==1:
            (table, field) = key.split('.')
            return dict([(r[table][field],r) for r in rows])
        elif isinstance(key,str):
            return dict([(r[key],r) for r in rows])
        else:
            return dict([(key(r),r) for r in rows])

    def export_to_csv_file(self, ofile, null='<NULL>', *args, **kwargs):
        """
        export data to csv, the first line contains the column names

        :param ofile: where the csv must be exported to
        :param null: how null values must be represented (default '<NULL>')
        :param delimiter: delimiter to separate values (default ',')
        :param quotechar: character to use to quote string values (default '"')
        :param quoting: quote system, use csv.QUOTE_*** (default csv.QUOTE_MINIMAL)
        :param represent: use the fields .represent value (default False)
        :param colnames: list of column names to use (default self.colnames)
                         This will only work when exporting rows objects!!!!
                         DO NOT use this with db.export_to_csv()
        """
        delimiter = kwargs.get('delimiter', ',')
        quotechar = kwargs.get('quotechar', '"')
        quoting = kwargs.get('quoting', csv.QUOTE_MINIMAL)
        represent = kwargs.get('represent', False)
        writer = csv.writer(ofile, delimiter=delimiter,
                            quotechar=quotechar, quoting=quoting)
        colnames = kwargs.get('colnames', self.colnames)
        # a proper csv starting with the column names
        writer.writerow(colnames)

        def none_exception(value):
            """
            returns a cleaned up value that can be used for csv export:
            - unicode text is encoded as such
            - None values are replaced with the given representation (default <NULL>)
            """
            if value is None:
                return null
            elif isinstance(value, unicode):
                return value.encode('utf8')
            elif isinstance(value,Reference):
                return int(value)
            elif hasattr(value, 'isoformat'):
                return value.isoformat()[:19].replace('T', ' ')
            elif isinstance(value, (list,tuple)): # for type='list:..'
                return bar_encode(value)
            return value

        for record in self:
            row = []
            for col in colnames:
                if not table_field.match(col):
                    row.append(record._extra[col])
                else:
                    (t, f) = col.split('.')
                    field = self.db[t][f]
                    if isinstance(record.get(t, None), (Row,dict)):
                        value = record[t][f]
                    else:
                        value = record[f]
                    if field.type=='blob' and not value is None:
                        value = base64.b64encode(value)
                    elif represent and field.represent:
                        value = field.represent(value)
                    row.append(none_exception(value))
            writer.writerow(row)

    def xml(self):
        """
        serializes the table using sqlhtml.SQLTABLE (if present)
        """

        import sqlhtml
        return sqlhtml.SQLTABLE(self).xml()

    def json(self, mode='object', default=None):
        """
        serializes the table to a JSON list of objects
        """
        mode = mode.lower()
        if not mode in ['object', 'array']:
            raise SyntaxError, 'Invalid JSON serialization mode: %s' % mode

        def inner_loop(record, col):
            (t, f) = col.split('.')
            res = None
            if not table_field.match(col):
                key = col
                res = record._extra[col]
            else:
                key = f
                if isinstance(record.get(t, None), Row):
                    res = record[t][f]
                else:
                    res = record[f]
            if mode == 'object':
                return (key, res)
            else:
                return res

        if mode == 'object':
            items = [dict([inner_loop(record, col) for col in
                     self.colnames]) for record in self]
        else:
            items = [[inner_loop(record, col) for col in self.colnames]
                     for record in self]
        if have_serializers:
            return serializers.json(items,default=default or serializers.custom_json)
        else:
            import simplejson
            return simplejson.dumps(items)

def Rows_unpickler(data):
    return cPickle.loads(data)

def Rows_pickler(data):
    return Rows_unpickler, \
        (cPickle.dumps(data.as_list(storage_to_dict=True,
                                    datetime_to_str=False)),)

copy_reg.pickle(Rows, Rows_pickler, Rows_unpickler)


################################################################################
# dummy function used to define some doctests
################################################################################

def test_all():
    """

    >>> if len(sys.argv)<2: db = DAL(\"sqlite://test.db\")
    >>> if len(sys.argv)>1: db = DAL(sys.argv[1])
    >>> tmp = db.define_table('users',\
              Field('stringf', 'string', length=32, required=True),\
              Field('booleanf', 'boolean', default=False),\
              Field('passwordf', 'password', notnull=True),\
              Field('uploadf', 'upload'),\
              Field('blobf', 'blob'),\
              Field('integerf', 'integer', unique=True),\
              Field('doublef', 'double', unique=True,notnull=True),\
              Field('datef', 'date', default=datetime.date.today()),\
              Field('timef', 'time'),\
              Field('datetimef', 'datetime'),\
              migrate='test_user.table')

   Insert a field

    >>> db.users.insert(stringf='a', booleanf=True, passwordf='p', blobf='0A',\
                       uploadf=None, integerf=5, doublef=3.14,\
                       datef=datetime.date(2001, 1, 1),\
                       timef=datetime.time(12, 30, 15),\
                       datetimef=datetime.datetime(2002, 2, 2, 12, 30, 15))
    1

    Drop the table

    >>> db.users.drop()

    Examples of insert, select, update, delete

    >>> tmp = db.define_table('person',\
              Field('name'),\
              Field('birth','date'),\
              migrate='test_person.table')
    >>> person_id = db.person.insert(name=\"Marco\",birth='2005-06-22')
    >>> person_id = db.person.insert(name=\"Massimo\",birth='1971-12-21')

    commented len(db().select(db.person.ALL))
    commented 2

    >>> me = db(db.person.id==person_id).select()[0] # test select
    >>> me.name
    'Massimo'
    >>> db(db.person.name=='Massimo').update(name='massimo') # test update
    1
    >>> db(db.person.name=='Marco').select().first().delete_record() # test delete
    1

    Update a single record

    >>> me.update_record(name=\"Max\")
    >>> me.name
    'Max'

    Examples of complex search conditions

    >>> len(db((db.person.name=='Max')&(db.person.birth<'2003-01-01')).select())
    1
    >>> len(db((db.person.name=='Max')&(db.person.birth<datetime.date(2003,01,01))).select())
    1
    >>> len(db((db.person.name=='Max')|(db.person.birth<'2003-01-01')).select())
    1
    >>> me = db(db.person.id==person_id).select(db.person.name)[0]
    >>> me.name
    'Max'

    Examples of search conditions using extract from date/datetime/time

    >>> len(db(db.person.birth.month()==12).select())
    1
    >>> len(db(db.person.birth.year()>1900).select())
    1

    Example of usage of NULL

    >>> len(db(db.person.birth==None).select()) ### test NULL
    0
    >>> len(db(db.person.birth!=None).select()) ### test NULL
    1

    Examples of search conditions using lower, upper, and like

    >>> len(db(db.person.name.upper()=='MAX').select())
    1
    >>> len(db(db.person.name.like('%ax')).select())
    1
    >>> len(db(db.person.name.upper().like('%AX')).select())
    1
    >>> len(db(~db.person.name.upper().like('%AX')).select())
    0

    orderby, groupby and limitby

    >>> people = db().select(db.person.name, orderby=db.person.name)
    >>> order = db.person.name|~db.person.birth
    >>> people = db().select(db.person.name, orderby=order)

    >>> people = db().select(db.person.name, orderby=db.person.name, groupby=db.person.name)

    >>> people = db().select(db.person.name, orderby=order, limitby=(0,100))

    Example of one 2 many relation

    >>> tmp = db.define_table('dog',\
               Field('name'),\
               Field('birth','date'),\
               Field('owner',db.person),\
               migrate='test_dog.table')
    >>> db.dog.insert(name='Snoopy', birth=None, owner=person_id)
    1

    A simple JOIN

    >>> len(db(db.dog.owner==db.person.id).select())
    1

    >>> len(db().select(db.person.ALL, db.dog.name,left=db.dog.on(db.dog.owner==db.person.id)))
    1

    Drop tables

    >>> db.dog.drop()
    >>> db.person.drop()

    Example of many 2 many relation and Set

    >>> tmp = db.define_table('author', Field('name'),\
                            migrate='test_author.table')
    >>> tmp = db.define_table('paper', Field('title'),\
                            migrate='test_paper.table')
    >>> tmp = db.define_table('authorship',\
            Field('author_id', db.author),\
            Field('paper_id', db.paper),\
            migrate='test_authorship.table')
    >>> aid = db.author.insert(name='Massimo')
    >>> pid = db.paper.insert(title='QCD')
    >>> tmp = db.authorship.insert(author_id=aid, paper_id=pid)

    Define a Set

    >>> authored_papers = db((db.author.id==db.authorship.author_id)&(db.paper.id==db.authorship.paper_id))
    >>> rows = authored_papers.select(db.author.name, db.paper.title)
    >>> for row in rows: print row.author.name, row.paper.title
    Massimo QCD

    Example of search condition using  belongs

    >>> set = (1, 2, 3)
    >>> rows = db(db.paper.id.belongs(set)).select(db.paper.ALL)
    >>> print rows[0].title
    QCD

    Example of search condition using nested select

    >>> nested_select = db()._select(db.authorship.paper_id)
    >>> rows = db(db.paper.id.belongs(nested_select)).select(db.paper.ALL)
    >>> print rows[0].title
    QCD

    Example of expressions

    >>> mynumber = db.define_table('mynumber', Field('x', 'integer'))
    >>> db(mynumber.id>0).delete()
    0
    >>> for i in range(10): tmp = mynumber.insert(x=i)
    >>> db(mynumber.id>0).select(mynumber.x.sum())[0](mynumber.x.sum())
    45

    >>> db(mynumber.x+2==5).select(mynumber.x + 2)[0](mynumber.x + 2)
    5

    Output in csv

    >>> print str(authored_papers.select(db.author.name, db.paper.title)).strip()
    author.name,paper.title\r
    Massimo,QCD

    Delete all leftover tables

    >>> DAL.distributed_transaction_commit(db)

    >>> db.mynumber.drop()
    >>> db.authorship.drop()
    >>> db.author.drop()
    >>> db.paper.drop()
    """
################################################################################
# deprecated since the new DAL; here only for backward compatibility
################################################################################

SQLField = Field
SQLTable = Table
SQLXorable = Expression
SQLQuery = Query
SQLSet = Set
SQLRows = Rows
SQLStorage = Row
SQLDB = DAL
GQLDB = DAL
DAL.Field = Field  # was necessary in gluon/globals.py session.connect
DAL.Table = Table  # was necessary in gluon/globals.py session.connect

################################################################################
# run tests
################################################################################

if __name__ == '__main__':
    import doctest
    doctest.testmod()




