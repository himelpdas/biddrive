#!/usr/bin/env python

from distutils.core import setup
from gluon.fileutils import tar, untar, read_file, write_file
import tarfile
import sys

def tar(file, filelist, expression='^.+$'):
    """
    tars dir/files into file, only tars file that match expression
    """

    tar = tarfile.TarFile(file, 'w')
    try:
        for element in filelist:
            try:
                for file in listdir(element, expression, add_dirs=True):
                    tar.add(os.path.join(element, file), file, False)
            except:
                tar.add(element)
    finally:
        tar.close()

def start():
    """
    Version number is setup automatically. See the comments in code for
    potential testing and gotchas that have not been fully investigated.
    """
    # Web2py versioning layout causes some glitches when creating distributions
    # in some situations setting the version here and not in the setup function
    # seems to help. The problem occured sometimes when manually setting a string
    # like '1.98.2' in the setup functions but never when using a string like
    # '1.1.1' for some reason... undetermined cause
    # everything seems to go fine until you attempt to install the package with
    # pip at which point it hangs and gives a message about PKG_INFO in a tmp dir
    version=read_file("VERSION").split()[1]
    if 'sdist' in sys.argv:
        tar('gluon/env.tar',['applications','VERSION','splashlogo.gif'])
    setup(name='web2py',
        version=version,
          description="""full-stack framework for rapid development and prototyping
        of secure database-driven web-based applications, written and
        programmable in Python.""",
          long_description="""
        Everything in one package with no dependencies. Development, deployment,
        debugging, testing, database administration and maintenance of applications can
        be done via the provided web interface. web2py has no configuration files,
        requires no installation, can run off a USB drive. web2py uses Python for the
        Model, the Views and the Controllers, has a built-in ticketing system to manage
        errors, an internationalization engine, works with SQLite, PostgreSQL, MySQL,
        MSSQL, FireBird, Oracle, IBM DB2, Informix, Ingres, sybase and Google App Engine via a
        Database Abstraction Layer. web2py includes libraries to handle
        HTML/XML, RSS, ATOM, CSV, RTF, JSON, AJAX, XMLRPC, WIKI markup. Production
        ready, capable of upload/download streaming of very large files, and always
        backward compatible.
        """,
          author='Massimo Di Pierro',
          author_email='mdipierro@cs.depaul.edu',
          license = 'http://web2py.com/examples/default/license',
          classifiers = ["Development Status :: 5 - Production/Stable"],
          url='http://web2py.com',
          platforms ='Windows, Linux, Mac, Unix, Windows Mobile',
          packages=['gluon',
                    'gluon/contrib',
                    'gluon/contrib/gateways',
                    'gluon/contrib/login_methods',
                    'gluon/contrib/markdown',
                    'gluon/contrib/markmin',
                    'gluon/contrib/memcache',
                    'gluon/contrib/pyfpdf',
                    'gluon/contrib/pymysql',
                    'gluon/contrib/pyrtf',
                    'gluon/contrib/pysimplesoap',
                    'gluon/contrib/simplejson',
                    'gluon/tests',
                    ],
          package_data = {'gluon':['env.tar']},
          scripts = ['mkweb2pyenv','runweb2py','web2py_clone'],
          )

def usage_prompt():
    print "##########################################"
    print "after installing via pip you can create a"
    print "local clone of Web2py by doing taking the"
    print "following steps:"
    print ""
    print "* install mercurial to your virtualenv"
    print "    pip install mercural"
    print ""
    print "* run the web2py_clone command"
    print "    web2py_clone"
    print ""
    print "* Start web2py as usual by running"
    print "    python web2py.py"
    print "from the web2py directory"
    print "##########################################"

if __name__ == '__main__':
    # asking for user input here breaks distribution packaging
    # during pip install package_name for some reason so
    # please test this well aspect before releasing.
    start()
    usage_prompt()
