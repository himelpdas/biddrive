#!/usr/bin/env python
# -*- coding: utf-8 -*-

import __builtin__
import os
import re
import sys
import threading
import traceback
from gluon import current

NAIVE_IMPORTER = __builtin__.__import__
TRACK_CHANGES = False
INVALID_MODULES = set(sys.modules.keys()).union(('','gluon','applications','custom_import'))

# backward compatibility API 
def custom_import_install():
    __builtin__.__import__ = custom_importer

def track_changes(track=True):
    assert track in (True,False), "must be True or False"
    global TRACK_CHANGES
    TRACK_CHANGES = track

def is_tracking_changes():    
    return TRACK_CHANGES

def custom_importer(name, globals=None, locals=None, fromlist=None, level=-1):
    """
    The web2py custom importer. Like the standard Python importer but it
    tries to transform import statements as something like
    "import applications.app_name.modules.x". 
    If the import failed, fall back on naive_importer
    """

    globals = globals or {}
    locals = locals or {}
    fromlist = fromlist or []

    base_importer = TRACK_IMPORTER if TRACK_CHANGES else NAIVE_IMPORTER

    # if not relative and not from applications:
    if hasattr(current,'request') \
            and level<=0 \
            and not name.split('.')[0] in INVALID_MODULES \
            and isinstance(globals, dict):            
        try:
            items = current.request.folder.split(os.path.sep)
            if not items[-1]: items = items[:-1]
            modules_prefix = '.'.join(items[-2:])+'.modules'
            if not fromlist:
                # import like "import x" or "import x.y"
                result = None
                for itemname in name.split("."):
                    new_mod = base_importer(
                        modules_prefix, globals,locals, [itemname], level)
                    try:
                        result = result or new_mod.__dict__[itemname]
                    except KeyError, e:
                        raise ImportError, 'Cannot import module %s' % str(e)
                    modules_prefix += "." + itemname
                return result
            else:
                # import like "from x import a, b, ..."
                pname = modules_prefix + "." + name
                return base_importer(pname, globals, locals, fromlist, level)
        except ImportError, e1:
            pass # the module does not exist
        except Exception, e2:
            raise e2 # there is an error in the module
    return NAIVE_IMPORTER(name,globals,locals,fromlist,level)


class TrackImporter(object):
    """
    An importer tracking the date of the module files and reloading them when
    they have changed.
    """

    THREAD_LOCAL = threading.local()
    PACKAGE_PATH_SUFFIX = os.path.sep+"__init__.py"

    def __init__(self):
        self._import_dates = {} # Import dates of the files of the modules

    def __call__(self,name,globals=None,locals=None,fromlist=None,level=-1):
        """
        The import method itself.
        """
        globals = globals or {}
        locals = locals or {}
        fromlist = fromlist or []
        if not hasattr(self.THREAD_LOCAL,'_modules_loaded'):
            self.THREAD_LOCAL._modules_loaded = set()
        try:
            # Check the date and reload if needed:
            self._update_dates(name, globals, locals, fromlist, level)
            # Try to load the module and update the dates if it works:
            result = NAIVE_IMPORTER(name, globals, locals, fromlist, level)
            # Module maybe loaded for the 1st time so we need to set the date
            self._update_dates(name, globals, locals, fromlist, level)
            return result
        except Exception, e:
            raise # Don't hide something that went wrong

    def _update_dates(self, name, globals, locals, fromlist, level):
        """
        Update all the dates associated to the statement import. A single
        import statement may import many modules.
        """

        self._reload_check(name, globals, locals, level)
        for fromlist_name in fromlist or []:
            pname = "%s.%s" % (name, fromlist_name)
            self._reload_check(pname, globals, locals, level)

    def _reload_check(self, name, globals, locals, level):
        """
        Update the date associated to the module and reload the module if
        the file has changed.
        """
        module = sys.modules.get(name)
        file = self._get_module_file(module)
        if file:
            date = self._import_dates.get(file)
            new_date = None
            reload_mod = False
            mod_to_pack = False # Module turning into a package? (special case)
            try:
                new_date = os.path.getmtime(file)
            except:
                self._import_dates.pop(file, None)  # Clean up
                # Handle module changing in package and
                #package changing in module:
                if file.endswith(".py"):
                    # Get path without file ext:
                    file = os.path.splitext(file)[0]
                    reload_mod = os.path.isdir(file) \
                      and os.path.isfile(file+self.PACKAGE_PATH_SUFFIX)
                    mod_to_pack = reload_mod
                else: # Package turning into module?
                    file += ".py"
                    reload_mod = os.path.isfile(file)
                if reload_mod:
                    new_date = os.path.getmtime(file) # Refresh file date
            if reload_mod or not date or new_date > date:
                self._import_dates[file] = new_date
            if reload_mod or (date and new_date > date):
                if module not in self.THREAD_LOCAL._modules_loaded:
                    if mod_to_pack:
                        # Module turning into a package:
                        mod_name = module.__name__
                        del sys.modules[mod_name] # Delete the module
                        # Reload the module:
                        NAIVE_IMPORTER(mod_name, globals, locals, [], level)
                    else:
                        reload(module)
                        self.THREAD_LOCAL._modules_loaded.add(module)

    def _get_module_file(self, module):
        """
        Get the absolute path file associated to the module or None.
        """
        file = getattr(module, "__file__", None)
        if file:
            # Make path absolute if not:
            file = os.path.splitext(file)[0]+".py" # Change .pyc for .py
            if file.endswith(self.PACKAGE_PATH_SUFFIX):
                file = os.path.dirname(file)  # Track dir for packages
        return file

TRACK_IMPORTER = TrackImporter()
