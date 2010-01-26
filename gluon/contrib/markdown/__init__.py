from markdown2 import *
from gluon.html import XML

def WIKI(text, encoding="utf8", safe_mode='escape',**attributes):
    if not text:
        test = ''
    if attributes.has_key('extras'):
        extras = attributes['extras']
    else:
        extras=None
    text = text.decode(encoding,'replace')

    xml_attributes = {}
    for key in ('sanitize','permitted_tags','allowed_attributes'):
        if key in attributes:
            xml_attributes = attributes[key]        

    return XML(markdown(text,extras=extras,safe_mode=safe_mode).encode(encoding,'xmlcharrefreplace'),**xml_attributes)
