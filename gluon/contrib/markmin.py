# created my Massimo Di Pierro
# license MIT/BSD/GPL
import re
import cgi    

__doc__ = """
# Markmin markup language

## What?

This is a new markup language that we call markmin, it is implemented in the ``render`` function in the ``markmin.py`` module. 

## Why?

We wanted a markup language in less than 100 lines of code with the following requirements:
- less than 100 lines of code
- simple to read
- secure
- support table, ul, ol, code
- support html5 video and audio elements
- can align images and resize them
- can specify class for tables and code elements
- can add anchors anywhere
- does not use _ for markup (since it creates odd behavior)
- automatically links urls

## Where

[[download http://web2py.googlecode.com/hg/gluon/contrib/markmin.py]]

## Usage

``
>>> from markmin import render
>>> render('hello **world**')
<p>hello <b>world</b></p>
``:python

## Exmaples

### Bold, italic, verbatim and links

--------------------------------------------------
**SOURCE**                 | **OUTPUT**
``**bold**``               | **bold** 
``''italic''``             | ''italic'' 
``!`!`varbatim`!`!``       | ``verbatim``
``http://google.com``      | http://google.com
``[[click me #myanchow]]`` | [[click me #myanchor]]
---------------------------------------------------

### More on links

The format is always ``[[title link]]``. Notice you can nest bold, italic and verbatim inside the link title.

### Anchors [[myanchor]]

You can place an ancor anywhere in the text using the syntax ``[[name]]`` where ''name'' is the name of the anchor.
You can then link the anchor with [[link #myanchor]], i.e. ``[[link #myanchor]]``.

### Images

[[some image http://www.google.it/images/srpr/nav_logo13.png right 200px]]
This paragraph has an image alighed to the right with a width of 200px. Its is placed using the code
``[[some image http://www.google.it/images/srpr/nav_logo13.png right 200px]]``.

### Unordered Lists

``
- Dog
- Cat
- Mouse
``

is redered as 
- Dog
- Cat
- Mouse 

Two new lines between items break the list in two lists.

### Ordered Lists

``
+ Dog
+ Cat
+ Mouse
``

is rendered as
+ Dog
+ Cat
+ Mouse


### Tables

Something like this
``
---------
0 | 0 | X
0 | X | 0
X | 0 | 0
-----:abc
``
is a table and is redenered as
---------
0 | 0 | X
0 | X | 0
X | 0 | 0
-----:abc
Four or more dashes delimit the table and | separates the columns.
The ``:abc`` at the end sets the class for the table and it is optional.


### Verbatim, ``<code>``, escaping and extra stuff

``
def test():
    return "this is Python code"
``:python

Optionally a ` inside a ``!`!`...`!`!`` block can be inserted escaped with !`!.
The ``:python`` after the markup is also optional. If present, by default, it is used to set the class of the <code> block.
The behavior can be overwritten by passing an argument ``extra`` to the ``render`` function. For example:

``>>> render("!`!!`!aaa!`!!`!:custom",extra=dict(custom=lambda text: 'x'+text+'x'))``:python

generates

``'xaaax'``:python

(the ``!`!`...`!`!:custom`` block is rendered by the ``custom=lambda`` function passed to ``render``).


### Html5 support

Markmin also supports the <video> and <audio> html5 tags using the notation:
``
[[title link video]]
[[title link audio]]
``

### Caveats
``<ul\>``, ``<ol\>``, ``<code\>``, ``<table\>``, ``<h1\>``, ..., ``<h6\>`` do not have ``<p>...</p>`` around them.

"""

META = 'META'
regex_verbatim = re.compile('('+META+')|(``(?P<t>.*?)``(:(?P<c>\w+))?)',re.S)
regex_maps = [
    (re.compile('[ \t\r]+\n'),'\n'),
    (re.compile('[ \t\r]+\n'),'\n'),
    (re.compile('\*\*(?P<t>\w+( +\w+)*)\*\*'),'<b>\g<t></b>'),
    (re.compile("''(?P<t>\w+( +\w+)*)''"),'<i>\g<t></i>'),
    (re.compile('^#{6} (?P<t>[^\n]+)',re.M),'\n\n<<h6>\g<t></h6>\n'),
    (re.compile('^#{5} (?P<t>[^\n]+)',re.M),'\n\n<<h5>\g<t></h5>\n'),
    (re.compile('^#{4} (?P<t>[^\n]+)',re.M),'\n\n<<h4>\g<t></h4>\n'),
    (re.compile('^#{3} (?P<t>[^\n]+)',re.M),'\n\n<<h3>\g<t></h3>\n'),
    (re.compile('^#{2} (?P<t>[^\n]+)',re.M),'\n\n<<h2>\g<t></h2>\n'),
    (re.compile('^#{1} (?P<t>[^\n]+)',re.M),'\n\n<<h1>\g<t></h1>\n'),
    (re.compile('^\- +(?P<t>.*)',re.M),'<<ul><li>\g<t></li></ul>'),
    (re.compile('^\+ +(?P<t>.*)',re.M),'<<ol><li>\g<t></li></ol>'),
    (re.compile('</ol>\n<<ol>'),''),
    (re.compile('</ul>\n<<ul>'),''),
    (re.compile('<<'),'\n\n<<'),
    (re.compile('\n\s+\n'),'\n\n')]
regex_table = re.compile('^\-{4,}\n(?P<t>.*?)\n\-{4,}(:(?P<c>\w+))?\n',re.M|re.S)
regex_image_width = re.compile('\[\[(?P<t>.*?) +(?P<k>\S+) +(?P<p>left|right|center) +(?P<w>\d+px)\]\]')
regex_image = re.compile('\[\[(?P<t>.*?) +(?P<k>\S+) +(?P<p>left|right|center)\]\]')
regex_video = re.compile('\[\[(?P<t>.*?) +(?P<k>\S+) +video\]\]')
regex_audio = re.compile('\[\[(?P<t>.*?) +(?P<k>\S+) +audio\]\]')
regex_link = re.compile('\[\[(?P<t>.*?) +(?P<k>\S+)\]\]')
regex_auto = re.compile('(?<!["\w])(?P<k>\w+://[\w\.\-\?&%]+)',re.M)
regex_anchor = re.compile('\[\[(?P<t>\w+)\]\]')

def render(text,extra={},sep='p'):
    """
    >>> render('this is\\n# a section\\nparagraph')
    '<p>this is</p><h1>a section</h1><p>paragraph</p>'
    >>> render('this is\\n## a subsection\\nparagraph')
    '<p>this is</p><h2>a subsection</h2><p>paragraph</p>'
    >>> render('this is\\n### a subsubsection\\nparagraph')
    '<p>this is</p><h3>a subsubsection</h3><p>paragraph</p>'
    >>> render('**hello world**')
    '<p><b>hello world</b></p>'
    >>> render('``hello world``')
    '<code class="">hello world</code>'
    >>> render('``hello world``:python')
    '<code class="python">hello world</code>'
    >>> render('``\\nhello world\\n``:python')
    '<pre><code class="python">\\nhello world\\n</code></pre>'
    >>> render("''hello world''")
    '<p><i>hello world</i></p>'
    >>> render('** hello** **world**')
    '<p>** hello** <b>world</b></p>'

    >>> render('- this\\n- is\\n- a list\\n\\nand this\\n- is\\n- another')
    '<ul><li>this</li><li>is</li><li>a list</li></ul><p>and this</p><ul><li>is</li><li>another</li></ul>'

    >>> render('+ this\\n+ is\\n+ a list\\n\\nand this\\n+ is\\n+ another')
    '<ol><li>this</li><li>is</li><li>a list</li></ol><p>and this</p><ol><li>is</li><li>another</li></ol>'

    >>> render("----\\na | b\\nc | d\\n----\\n")
    '<table class=""><tr><td>a</td><td>b</td></tr><tr><td>c</td><td>d</td></tr></table>'

    >>> render('[[this is a link http://example.com]]')
    '<p><a href="http://example.com">this is a link</a></p>'

    >>> render('[[this is an image http://example.com left]]')    
    '<p><img src="http://example.com" alt="this is an image" align="left" /></p>'
    >>> render('[[this is an image http://example.com left 200px]]')
    '<p><img src="http://example.com" alt="this is an image" align="left" width="200px" /></p>'

    >>> render('[[this is an image http://example.com video]]')    
    '<p><video src="http://example.com" controls></video></p>'
    >>> render('[[this is an image http://example.com audio]]')    
    '<p><audio src="http://example.com" controls></audio></p>'

    >>> render('[[this is a **link** http://example.com]]')
    '<p><a href="http://example.com">this is a <b>link</b></a></p>'

    >>> render("``aaa``:custom",extra=dict(custom=lambda text: 'x'+text+'x'))
    'xaaax'
    """
    #############################################################
    # replace all blocks marked with ``...``:class with META
    # store them into segments they will be treated as verbatim
    #############################################################
    segments, i = [], 0
    while True:
        item = regex_verbatim.search(text,i)
        if not item: break
        if item.group()==META:
            segments.append((None,None))
            text = text[:item.start()]+META+text[item.end():]
        else:
            segments.append((item.group('t').replace('!`!','`'),item.group('c') or ''))
            text = text[:item.start()]+META+text[item.end():]
        i=item.start()+3

    #############################################################
    # do h1,h2,h3,h4,h5,h6,b,i,ol,ul and normalize spaces
    #############################################################
    text = '\n'.join(t.strip() for t in text.split('\n'))
    text = cgi.escape(text)
    for regex, sub in regex_maps:
        text = regex.sub(sub,text)
 
    #############################################################
    # process tables
    #############################################################
    while True:
        item = regex_table.search(text)
        if not item: break
        c = item.group('c') or ''
        rows = item.group('t').replace('\n','</td></tr><tr><td>').replace(' | ','</td><td>')
        text = text[:item.start()] + '<<table class="%s"><tr><td>'%c + rows + '</td></tr></table>' + text[item.end():]

    #############################################################
    # deal with images, videos, audios and links
    #############################################################

    text = regex_image_width.sub('<img src="\g<k>" alt="\g<t>" align="\g<p>" width="\g<w>" />', text)
    text = regex_image.sub('<img src="\g<k>" alt="\g<t>" align="\g<p>" />', text)
    text = regex_video.sub('<video src="\g<k>" controls></video>', text)
    text = regex_audio.sub('<audio src="\g<k>" controls></audio>', text)
    text = regex_link.sub('<a href="\g<k>">\g<t></a>', text)
    text = regex_auto.sub('<a href="\g<k>">\g<k></a>', text)
    text = regex_anchor.sub('<span id="\g<t>"><span>', text)
    
    #############################################################
    # deal with paragraphs (trick <<ul, <<ol, <<table, <<h1, etc)
    # the << indicates that there should NOT be a new paragraph
    # META indicates a verbatim block therefore no new paragraph
    #############################################################
    items = [item.strip() for item in text.split('\n\n')]
    if sep=='p':
        text = ''.join(p[:2]!='<<' and p!=META and '<p>%s</p>'%p or '%s'%p for p in items if p)
    elif sep=='br':
        text = '<br />'.join(items)

    #############################################################
    # finally get rid of <<
    #############################################################
    text=text.replace('<<','<')
    
    #############################################################
    # process all verbatim text
    #############################################################
    parts = text.split(META)
    text = parts[0]
    for i,(a,b) in enumerate(segments):
        if a==None: code=META
        elif b in extra:
            code = extra[b](a)
        elif a[0]=='\n' or a[-1]=='\n':
            code='<pre><code class="%s">%s</code></pre>' % (b,cgi.escape(a))
        else:
            code='<code class="%s">%s</code>' % (b,cgi.escape(a))
        text = text+code+parts[i+1]
    ### end restore verbatim
    return text

if __name__ == '__main__':
    import sys
    import doctest
    if len(sys.argv)>0:
        open(sys.argv[1],'w').write('<html><body>'+render(__doc__)+'</body></html>')
    else:
        doctest.testmod()
