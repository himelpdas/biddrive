USAGE = """
from web2py main folder
python scripts/make_min_web2py.py /path/to/minweb2py

it will mkdir minweb2py and build a minimal web2py installation
- no admin, no examples, one line welcome
- no scripts
- drops same rarely used contrib modules
- more modules could be dropped but minimal difference
"""

REQUIRED = """
anyserver.py
applications/
applications/__init__.py
applications/welcome/
applications/welcome/controllers/
applications/welcome/controllers/default.py
fcgihandler.py
gaehandler.py
gluon/
gluon/__init__.py
gluon/admin.py
gluon/cache.py
gluon/cfs.py
gluon/compileapp.py
gluon/contenttype.py
gluon/contrib/
gluon/contrib/__init__.py
gluon/contrib/AuthorizeNet.py
gluon/contrib/gae_memcache.py
gluon/contrib/gae_retry.py
gluon/contrib/gateways/
gluon/contrib/gateways/__init__.py
gluon/contrib/gateways/fcgi.py
gluon/contrib/login_methods/
gluon/contrib/login_methods/__init__.py
gluon/contrib/login_methods/basic_auth.py
gluon/contrib/login_methods/cas_auth.py
gluon/contrib/login_methods/email_auth.py
gluon/contrib/login_methods/extended_login_form.py
gluon/contrib/login_methods/gae_google_account.py
gluon/contrib/login_methods/ldap_auth.py
gluon/contrib/login_methods/linkedin_account.py
gluon/contrib/login_methods/loginza.py
gluon/contrib/login_methods/oauth10a_account.py
gluon/contrib/login_methods/oauth20_account.py
gluon/contrib/login_methods/openid_auth.py
gluon/contrib/login_methods/pam_auth.py
gluon/contrib/login_methods/rpx_account.py
gluon/contrib/markmin/
gluon/contrib/markmin/__init__.py
gluon/contrib/markmin/markmin.html
gluon/contrib/markmin/markmin2html.py
gluon/contrib/markmin/markmin2latex.py
gluon/contrib/markmin/markmin2pdf.py
gluon/contrib/memcache/
gluon/contrib/memcache/__init__.py
gluon/contrib/memcache/memcache.py
gluon/contrib/memdb.py
gluon/contrib/pam.py
gluon/contrib/rss2.py
gluon/contrib/shell.py
gluon/contrib/simplejson/
gluon/contrib/simplejson/__init__.py
gluon/contrib/simplejson/decoder.py
gluon/contrib/simplejson/encoder.py
gluon/contrib/simplejson/ordered_dict.py
gluon/contrib/simplejson/scanner.py
gluon/contrib/simplejson/tool.py
gluon/contrib/taskbar_widget.py
gluon/contrib/user_agent_parser.py
gluon/custom_import.py
gluon/dal.py
gluon/debug.py
gluon/decoder.py
gluon/fileutils.py
gluon/globals.py
gluon/highlight.py
gluon/html.py
gluon/http.py
gluon/import_all.py
gluon/languages.py
gluon/main.py
gluon/myregex.py
gluon/newcron.py
gluon/portalocker.py
gluon/reserved_sql_keywords.py
gluon/restricted.py
gluon/rewrite.py
gluon/rocket.py
gluon/sanitizer.py
gluon/serializers.py
gluon/settings.py
gluon/shell.py
gluon/sql.py
gluon/sqlhtml.py
gluon/storage.py
gluon/streamer.py
gluon/template.py
gluon/tools.py
gluon/utils.py
gluon/validators.py
gluon/widget.py
gluon/winservice.py
gluon/xmlrpc.py
VERSION
web2py.py
wsgihandler.py
"""

import sys, os, shutil

def main():
    if len(sys.argv)<2:
        print USAGE
    target = sys.argv[1]
    os.mkdir(target)
    files_and_folders = sorted(x.strip() for x in REQUIRED.split('\n') \
                                   if x and not x[0]=='#')
    for f in files_and_folders:
        if f.endswith('/'):
            os.mkdir(target+'/'+f)
        elif f=='applications/welcome/controllers/default.py':
            open(target+'/'+f,'w').write('def index(): return "hello"\n')
        else:
            shutil.copyfile(f,target+'/'+f)

if __name__=='__main__': main()
