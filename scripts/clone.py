#!/usr/bin/python
from urllib import urlopen
import os
import re
import sys
from optparse import OptionParser
sys.path.append(os.environ['WEB2PY'])
from gluon.html import *

def clone(url, clear=None, menu=None, content=None, ajax=False):
    prefix,url=url.split('://',1)
    prefix+='://'
    html=urlopen(prefix+url).read()
    page=TAG(html)
    a=prefix+url.split('/')[0]
    b=prefix+url.rsplit('/',1)[0]+'/'
    ### replace text with 'xxx'                                                                                   
    if clear:
        for tag in page.elements('p, li, h1, h2, h3, h4, a, li, div, span'):
            for i in range(len(tag.components)):
                c=tag.components[i]
                if isinstance(c,str):
                    tag.components[i]=re.sub('\S','x',c)
    # fix links

    for tag in page.elements(_href=re.compile('^/')):
        tag['_href']=a+tag['_href']
    for tag in page.elements(_href=re.compile('^\w')):
        if not tag['_href'].startswith('http'):
            tag['_href']=b+tag['_href']
    for tag in page.elements(_src=re.compile('^/')):
        tag['_src']=a+tag['_src']
    for tag in page.elements(_src=re.compile('^\w')):
        if not tag['_src'].startswith('http'):
            tag['_src']=b+tag['_src']
    #for tag in page.elements('form'):
    #    tag['_onsubmit']=False
    #    tag['_action']=URL(r=request,args=request.args,vars=request.vars)
    ### replace menu                                                                                              
    if menu:
        tag=page.element(menu)
        if tag:
            tag.components=['{{=MENU(response.menu)}}']
    if content:
        tag=page.element(content)
        if tag:
            tag.components=[XML('<div class="flash">{{=response.flash}}</div>{{include}}')]
    if ajax:
        tag=page.element('script')
        tag.append(XML('{{include "web2py_ajax.html"}}'))
    return page

def main():
    parser = OptionParser()
    parser.add_option("-u", "--url", dest="url", default='http://web2py.com',
                      help="the url of the page to be cloned")
    parser.add_option("-o", "--output", dest="output", default="cloned.html",
                      help="the name of the file containing the cloned page")
    parser.add_option("-m", "--menu", dest="menu", default='#menu',
                      help="the jQuery name of the menu tag")
    parser.add_option("-c", "--content", dest="content", default='#content',
                      help="the jQuery name of the content tag")
    parser.add_option("-t", "--text_clear", dest="clear", default='false',
                      help="true to replace all text with xxxx")
    parser.add_option("-a", "--ajax", dest="ajax", default='true',
                      help="true to replace all text with xxxx")
    (options, args) = parser.parse_args()
    page = clone(options.url,options.clear=='true',options.menu,options.content,options.ajax=='true')
    print page
    open(options.output,'w').write(page.xml())

if __name__=='__main__':
    main()
