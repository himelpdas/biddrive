"""
This file is part of the web2py Web Framework
Copyrighted by Massimo Di Pierro <mdipierro@cs.depaul.edu>
License: LGPLv3 (http://www.gnu.org/licenses/lgpl.html)
"""
import datetime
from .storage import Storage
from .html import TAG
from .html import xmlescape
from .languages import lazyT
from .contrib import rss2
import collections

try:
    import json as json_parser                      # try stdlib (Python 2.6)
except ImportError:
    try:
        import simplejson as json_parser            # try external module
    except:
        from .contrib.simplejson import json_parser    # fallback to pure-Python module

def custom_json(o):
    if hasattr(o,'custom_json') and isinstance(o.custom_json, collections.Callable):
        return o.custom_json()
    if isinstance(o, (datetime.date,
                      datetime.datetime,
                      datetime.time)):
        return o.isoformat()[:19].replace('T',' ')
    elif isinstance(o, int):
        return int(o)
    elif isinstance(o, lazyT):
        return str(o)
    elif hasattr(o,'as_list') and isinstance(o.as_list, collections.Callable):
        return o.as_list()
    elif hasattr(o,'as_dict') and isinstance(o.as_dict, collections.Callable):
        return o.as_dict()
    else:
        raise TypeError(repr(o) + " is not JSON serializable")


def xml_rec(value, key):
    if hasattr(value,'custom_xml') and isinstance(value.custom_xml, collections.Callable):
        return value.custom_xml()
    elif isinstance(value, (dict, Storage)):
        return TAG[key](*[TAG[k](xml_rec(v, '')) for k, v in list(value.items())])
    elif isinstance(value, list):
        return TAG[key](*[TAG.item(xml_rec(item, '')) for item in value])
    elif hasattr(value,'as_list') and isinstance(value.as_list, collections.Callable):
        return str(xml_rec(value.as_list(),''))
    elif hasattr(value,'as_dict') and isinstance(value.as_dict, collections.Callable):
        return str(xml_rec(value.as_dict(),''))
    else:
        return xmlescape(value)


def xml(value, encoding='UTF-8', key='document'):
    return ('<?xml version="1.0" encoding="%s"?>' % encoding) + str(xml_rec(value,key))


def json(value,default=custom_json):
    return json_parser.dumps(value,default=default)


def csv(value):
    return ''


def rss(feed):
    if not 'entries' in feed and 'items' in feed:
        feed['entries'] = feed['items']
    now=datetime.datetime.now()
    rss = rss2.RSS2(title = feed['title'],
                    link = str(feed['link']),
                    description = feed['description'],
                    lastBuildDate = feed.get('created_on', now),
                    items = [rss2.RSSItem(\
                                        title=entry['title'],
                                        link=str(entry['link']),
                                        description=entry['description'],
                                        pubDate=entry.get('created_on', now)
                                        )\
                                    for entry in feed['entries']
                                    ]
                    )
    return rss2.dumps(rss)



