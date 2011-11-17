#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
High-level CSS and JS minification class for web2py. Called by response.include_files()
Created by: Ross Peoples <ross.peoples@gmail.com>
"""

import cssmin
import jsmin
import os

try:
    import cStringIO as StringIO
except ImportError:
    import StringIO

def minify(files, combine_css=True, combine_js=True, minify_css=True, minify_js=True):
    """
    Takes a list of CSS and JS files and combines them into a single CSS and JS file.
    CSS and JS files can optionally be minified (remove whitespace, etc).
    Returns a tuple: (css_string, js_string). If combine_js is False and combine_css
    is False, then returns a tuple: (css_list, js_list).
    """
    
    css_string = StringIO.StringIO()
    js_string = StringIO.StringIO()
    css_list = []
    js_list = []
    dont_minify = ['jquery.js', 'anytime.js']
    for k,f in enumerate(files or []):
        if not f in files[:k]:
            filename = f.lower().split('?')[0]
            path = filename.split('/')
            path = os.sep.join(path[1:])
            abs_filename = os.path.join(os.getcwd(), 'applications', path)
            
            if filename.endswith('.css'):
                if combine_css:
                    fp = open(abs_filename, 'r')
                    contents = fp.read()
                    fp.close()
                    
                    if minify_css:
                        contents = cssmin.cssmin(contents)
                        
                    css_string.write(contents + '\n\n')
                else:
                    css_list.append(filename)
                
            elif filename.endswith('.js'):
                if combine_js:
                    fp = open(abs_filename, 'r')
                    contents = fp.read()
                    fp.close()
                    
                    if minify_js and not filename.endswith('min.js') and not filename in dont_minify:
                        contents = jsmin.jsmin(contents)
                        
                    js_string.write(contents + '\n\n')
                else:
                    js_list.append(filename)
                    
    return_css = css_list
    return_js = js_list
    
    if combine_css:
        return_css = css_string.getvalue()
        css_string.close()
        del css_string
        
    if combine_js:
        return_js = js_string.getvalue()
        js_string.close()
        del js_string
        
    return (return_css, return_js)
        
