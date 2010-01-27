from markdown2 import *
from gluon.html import XML

def WIKI(text, encoding="utf8", safe_mode='escape',**attributes):
    if not text:
        test = ''
    if attributes.has_key('extras'):
        extras = attributes['extras']
        del attributes['extra']
    else:
        extras=None
    text = text.decode(encoding,'replace')

    return XML(markdown(text,extras=extras,safe_mode=safe_mode)\
                   .encode(encoding,'xmlcharrefreplace'),**attributes)
