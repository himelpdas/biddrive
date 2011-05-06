#!/usr/bin/env python
# -*- coding: utf-8 -*-

import __builtin__
import os
import re
import sys
import threading

DEBUG = True

# Install the new import function:
def custom_import_install(web2py_path):
    _Web2pyImporter(web2py_path)


class _BaseImporter(object):
    """
    The base importer. Dispatch the import the call to the standard Python
    importer.
    """

    _installed = False

    def __init__(self):
        """
        Install this importer and gives access to the standard Python importer.
        """

        if not self._installed:
            _BaseImporter.std_python_importer = __builtin__.__import__
        __builtin__.__import__ = self
        _BaseImporter._installed = True

    def begin(self):
        """
        Many imports can be made for a single import statement. This method
        help the management of this aspect.
        """

    def __call__(self, name, globals={}, locals={}, fromlist=[], level=-1):
        """
        The import method itself.
        """

        return self.std_python_importer(name, globals, locals, fromlist, level)

    def end(self):
        """
        Needed for clean up.
        """


class _DateTrackerImporter(_BaseImporter):
    """
    An importer tracking the date of the module files and reloading them when
    they have changed.
    """

    _PACKAGE_PATH_SUFFIX = os.path.sep+"__init__.py"

    def __init__(self):
        super(_DateTrackerImporter, self).__init__()
        self._import_dates = {} # Import dates of the files of the modules
        # Avoid reloading cause by file modifications of reload:
        self._tl = threading.local()

    def begin(self):
        self._tl._modules_loaded = set()

    def __call__(self, name, globals={}, locals={}, fromlist=[], level=-1):
        """
        The import method itself.
        """

        call_begin_end = self._tl._modules_loaded == None
        if call_begin_end:
            self.begin()

        try:
            self._tl.globals = globals
            self._tl.locals = locals
            self._tl.level = level

            # Check the date and reload if needed:
            self._update_dates(name, fromlist)

            # Try to load the module and update the dates if it works:
            result = super(_DateTrackerImporter, self) \
              .__call__(name, globals, locals, fromlist, level)
            # Module maybe loaded for the 1st time so we need to set the date
            self._update_dates(name, fromlist)
            return result
        except Exception, e:
            raise e  # Don't hide something that went wrong
        finally:
            if call_begin_end:
                self.end()

    def _update_dates(self, name, fromlist):
        """
        Update all the dates associated to the statement import. A single
        import statement may import many modules.
        """

        self._reload_check(name)
        if fromlist:
            for fromlist_name in fromlist:
                self._reload_check("%s.%s" % (name, fromlist_name))

    def _reload_check(self, name):
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
                new_date = os.stat(file).st_mtime
            except:
                self._import_dates.pop(file, None)  # Clean up
                # Handle module changing in package and
                #package changing in module:
                if file.endswith(".py"):
                    # Get path without file ext:
                    file = os.path.splitext(file)[0]
                    reload_mod = os.path.isdir(file) \
                      and os.path.isfile(file+self._PACKAGE_PATH_SUFFIX)
                    mod_to_pack = reload_mod
                else: # Package turning into module?
                    file += ".py"
                    reload_mod = os.path.isfile(file)
                if reload_mod:
                    new_date = os.stat(file).st_mtime # Refresh file date
            if reload_mod or not date or new_date > date:
                self._import_dates[file] = new_date
            if reload_mod or (date and new_date > date):
                if module not in self._tl._modules_loaded:
                    if mod_to_pack:
                        # Module turning into a package:
                        mod_name = module.__name__
                        del sys.modules[mod_name] # Delete the module
                        # Reload the module:
                        super(_DateTrackerImporter, self).__call__ \
                          (mod_name, self._tl.globals, self._tl.locals, [],
                           self._tl.level)
                    else:
                        reload(module)
                        self._tl._modules_loaded.add(module)

    def end(self):
        self._tl._modules_loaded = None

    @classmethod
    def _get_module_file(cls, module):
        """
        Get the absolute path file associated to the module or None.
        """

        file = getattr(module, "__file__", None)
        if file:
            # Make path absolute if not:
            #file = os.path.join(cls.web2py_path, file)

            file = os.path.splitext(file)[0]+".py" # Change .pyc for .py
            if file.endswith(cls._PACKAGE_PATH_SUFFIX):
                file = os.path.dirname(file)  # Track dir for packages
        return file

class _Web2pyImporter(object):
    """
    The standard web2py importer. Like the standard Python importer but it
    tries to transform import statements as something like
    "import applications.app_name.modules.x". If the import failed, fall back
    on _BaseImporter. Either use _BaseImporter or _DateTrackerImporter as
    delegate to do the import.
    """

    _RE_ESCAPED_PATH_SEP = re.escape(os.path.sep)  # os.path.sep escaped for re

    def __init__(self, web2py_path):
        """
        @param web2py_path: The absolute path of the web2py installation.
        """

        global DEBUG
        # Regular expression to match a directory of a web2py application
        # relative to the web2py install.
        # Like web2py installation dir path/applications/app_name/modules.
        # We also capture "applications/app_name" as a group.
        if not hasattr(_Web2pyImporter, "_RE_APP_DIR"):
            _Web2pyImporter._RE_APP_DIR = re.compile( \
                self._RE_ESCAPED_PATH_SEP.join( \
                (
                    "^" + re.escape(web2py_path),
                    "(" + "applications",
                    "[^",
                    "]+)",
                    "",
                    ) ))
        self.web2py_path =  web2py_path
        if DEBUG:
            self.delegate = _DateTrackerImporter()
        else:
            self.delegate = _BaseImporter()
        __builtin__.__import__ = self

    def __call__(self, name, globals={}, locals={}, fromlist=[], level=-1):
        """
        The import method itself.
        """

        delegate = self.delegate
        delegate.begin()
        try:
            # if not relative and not from applications:
            if not name.startswith(".") and level <= 0 \
                    and not name.startswith("applications."):
                # Get the name of the file do the import
                caller_file_name = os.path.join(self.web2py_path, \
                                                globals.get("__file__", ""))
                # Is the path in an application directory?
                match_app_dir = self._RE_APP_DIR.match(caller_file_name)
                if match_app_dir:
                    try:
                        # Get the prefix to add for the import
                        # (like applications.app_name.modules):
                        modules_prefix = \
                            ".".join((match_app_dir.group(1). \
                            replace(os.path.sep, "."), "modules"))
                        if not fromlist:
                            # import like "import x" or "import x.y"
                            return self.__import__dot(modules_prefix, name,
                              globals, locals, fromlist, level)
                        else:
                            # import like "from x import a, b, ..."
                            return delegate(modules_prefix + "." + name,
                              globals, locals, fromlist, level)
                    except ImportError:
                        pass
            return delegate(name, globals, locals, fromlist, level)
        except Exception, e:
            raise e  # Don't hide something that went wrong
        finally:
            delegate.end()

    def __import__dot(self, prefix, name, globals, locals, fromlist,
                      level):
        """
        Here we will import x.y.z as many imports like:
        from applications.app_name.modules import x
        from applications.app_name.modules.x import y
        from applications.app_name.modules.x.y import z.
        x will be the module returned.
        """

        result = None
        for name in name.split("."):
            new_mod = self.delegate(prefix, globals, locals, [name], level)
            try:
                result = result or new_mod.__dict__[name]
            except KeyError:
                raise ImportError()
            prefix += "." + name
        return result
