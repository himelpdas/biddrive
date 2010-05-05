#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This file is part of the web2py Web Framework (Copyrighted, 2007-2010).
License: GPL v2

Author: Thadeus Burgess

This module was mostly inspired by Uliweb templates created by Limodou, which 
was inspired by web2py's template system. The effort is to merge Uliweb 
templates with web2py so that web2py can have support for block-elements.
"""

import os
import re
import cStringIO

class Node(object):
    """
    Basic Container Object
    """
    def __init__(self, value=None):
        self.value = value

    def __str__(self):
        if self.value:
            return self.value
        else:
            return ''

class BlockNode(Node):
    """
    Block Container.

    This Node can contain other Nodes and will render in a heirarchical order
    of when nodes were added.

    ie::
         
        {{ block test }}
            This is default block test
        {{ end }}
    """
    def __init__(self, name=''):
        """
        name - Name of this Node.
        """
        self.nodes = []
        self.name = name

    def __repr__(self):
        lines = ['{{block %s}}' % self.name]
        for node in self.nodes:
            lines.append(str(node))
        lines.append('{{end}}')
        return ''.join(lines)

    def __str__(self):
        """
        Get this BlockNodes content, not including children Nodes
        """
        lines = []
        for node in self.nodes:
            if not isinstance(node, BlockNode):
                lines.append(str(node))
        return ''.join(lines)

    def append(self, node):
        """
        Add an element to the nodes.

        Keyword Arguments

        - node -- Node object or string to append.
        """
        if isinstance(node, str) or isinstance(node, BlockNode):
            self.nodes.append(node)
        else:
            raise TypeError("Invalid type, must be instance of ``str`` or ``BlockNode``. %s" % node)

    def extend(self, other):
        """
        Extend the list of nodes with another BlockNode class.

        Keyword Arugments

        - other -- BlockNode or Content object to extend from.
        """
        if isinstance(other, BlockNode):
            self.nodes.extend(other.nodes)
        else:
            raise TypeError("Invalid type, must be instance of ``BlockNode``. %s" % other)

    def output(self, blocks):
        """
        Merges all nodes into a single string.

        blocks -- Dictionary of blocks that are extending
        from this template.
        """
        lines = []
        # Get each of our nodes
        for node in self.nodes:
            # If we have a block level node.
            if isinstance(node, BlockNode):
                # If we can override this block.
                if node.name in blocks:
                    # Override block from vars.
                    lines.append(blocks[node.name].output(blocks))
                # Else we take the default
                else:
                    lines.append(node.output(blocks))
            # Else its just a string
            else:
                lines.append(str(node))
        # Now combine all of our lines together.
        return ''.join(lines)

class Content(BlockNode):
    """
    Parent Container -- Used as the root level BlockNode. 

    Contains functions that operate as such.
    """
    def __init__(self, name="ContentBlock"):
        """
        Keyword Arugments

        name -- Unique name for this BlockNode
        """
        self.name = name
        self.nodes = []
        self.blocks = {}

    def __str__(self):
        lines = []
        # For each of our nodes
        for node in self.nodes:
            # If it is a block node.
            if isinstance(node, BlockNode):
                # And the node has a name that corresponds with a block in us
                if node.name in self.blocks:
                    # Use the overriding output.
                    lines.append(self.blocks[node.name].output(self.blocks))
                else:
                    # Otherwise we just use the nodes output.
                    lines.append(node.output(self.blocks))
            else:
                # It is just a string, so include it.
                lines.append(str(node))
        # Merge our list together.
        return ''.join(lines)

    def append(self, node):
        """
        Adds a node to list. If it is a BlockNode then we assign a block for it.
        """
        if isinstance(node, str) or isinstance(node, BlockNode):
            self.nodes.append(node)
            if isinstance(node, BlockNode):
                self.blocks[node.name] = node
        else:
            raise TypeError("Invalid type, must be instance of ``str`` or ``BlockNode``. %s" % node)

    def extend(self, other):
        """
        Extends the objects list of nodes with another objects nodes
        """
        if isinstance(other, BlockNode):
            self.nodes.extend(other.nodes)
            self.blocks.update(other.blocks)
        else:
            raise TypeError("Invalid type, must be instance of ``BlockNode``. %s" % node)

    def clear_content(self):
        self.nodes = []

class TemplateParser(object):
    
    r_tag = re.compile(r'(\{\{.*?\}\})', re.DOTALL)

    r_block_comment = re.compile(r'(""".*?""")', re.DOTALL)

    # These are used for re-indentation.
    # Indent + 1
    re_block = re.compile('^(elif |else:|except:|except |finally:).*$',
                      re.DOTALL)
    # Indent - 1
    re_unblock = re.compile('^(return|continue|break)( .*)?$', re.DOTALL)
    # Indent - 1
    re_pass = re.compile('^pass( .*)?$', re.DOTALL)

    def __init__(self, text,
            name = "ParserContainer" ,
            context = dict(),
            path    = 'views/',
            writer  ='response.write'):

        # Keep a root level name.
        self.name = name
        # Raw text to start parsing.
        self.text = text
        # Writer to use. (refer to the default for an example.)
        # This will end up as
        # "%s(%s, escape=False)" % (self.writer, value)
        self.writer = writer

        # Path of templates
        self.path = path
        # Context for templates.
        self.context = context

        # Create a root level Content that everything will go into.
        self.content = Content(name=name)

        # Stack will hold our current stack of nodes.
        # As we descend into a node, it will be added to the stack
        # And when we leave, it will be removed from the stack.
        # self.content should stay on the stack at all times.
        self.stack = [self.content]

        # Begin parsing.
        self.parse(text)

    def __str__(self):
        """
        Returns the parsed template with correct indentation.
        """
        return TemplateParser.reindent(str(self.content))

    @staticmethod
    def reindent(text):
        """
        Reindents a string of unindented python code.
        """
        
        # Get each of our lines into an array.
        lines       = text.split('\n')
        
        # Our new lines
        new_lines   = []
        
        # Keeps track of how many indents we have.
        # Used for when we need to drop a level of indentaiton
        # only to re-indent on the next line.
        credit      = 0
        
        # Current indentation
        k           = 0

        #################
        # THINGS TO KNOW
        #################

        # k += 1 means indent
        # k -= 1 means unindent
        # credit = 1 means unindent on the next line.
        
        for raw_line in lines:
            line = raw_line.strip()
            
            # If we have a line that contains python code that
            # should be un-indented for this line of code.
            # and then re-indented for the next line.
            if 'elif ' in line or \
                'else:' in line or \
                'except' in line or \
                'finally:' in line:
                    k = k + credit - 1
                    
            # We obviously can't have a negative indentation
            if k < 0: 
                k = 0

            # Add the indentation!
            new_lines.append('    '*k+line)

            # Bank account back to 0 again :(
            credit = 0

            # If we are a pass block, we obviously de-dent.
            if line == 'pass' or line[:5] == 'pass ':
                k -= 1
                
            # If we are any of the following, de-dent.
            # However, we should stay on the same level
            # But the line right after us will be de-dented.
            # So we add one credit to keep us at the level
            # While moving back one indentation level.
            if 'return' in line or \
                'continue' in line or \
                'break' in line:
                credit = 1
                k -= 1

            # If we are an if statement or a semi-colon we 
            # probably need to indent the next line.
            if line[-1:] == ':' or line[:3] == 'if ':
                k += 1

        new_text = '\n'.join(new_lines)
        
        return new_text

    def _get_file_text(self, filename):
        """
        Attempt to open ``filename`` and retrieve its text.

        This will use self.path to search for the file.
        """
        import restricted

        # If they didn't specify a filename, how can we find one!
        if not filename.strip():
            raise Exception, "Invalid template filename"

        # Get the file name, filename looks like ``"template.html"``.
        # We need to eval to remove the qoutations and get the string type.
        filename = eval(filename, self.context)
        
        # Get the path of the file on the system.
        filepath = os.path.join(self.path, filename)

        # Lets try to read teh text.
        try:
            fileobj = open(filepath, 'rb')

            text = fileobj.read()

            fileobj.close()
        except IOError:
            raise restricted.RestrictedError('Processing View %s' % filename,
                  text, '', 'Unable to open included view file: ' + t)

        return text

    def include(self, content, filename):
        """
        Include ``filename`` here.
        """
        text = self._get_file_text(filename)
            
        t = TemplateParser(text, 
                    name=filename,
                    context=self.context, 
                    path=self.path, 
                    writer=self.writer)

        content.extend(t.content)

    def extend(self, filename):
        """
        Extend ``filename``. Anything not declared in a block defined by the 
        parent will be placed in the parent templates ``{{include}}`` block.
        """
        text = self._get_file_text(filename)

        t = TemplateParser(text, 
                    name=filename,
                    context=self.context, 
                    path=self.path, 
                    writer=self.writer)

        # Make a temporary buffer that is unique for parent
        # template.
        buf = BlockNode(name='__include__' + filename)

        # Iterate through each of our nodes
        for node in self.content.nodes:
            # If a node is a block
            if isinstance(node, BlockNode):
                # That happens to be in the parent template
                if node.name in t.content.blocks:
                    # Do not include it
                    continue
            # Otherwise, it should go int the
            # Parent templates {{include}} section.
                buf.append(node)
            else:
                buf.append(node)

        # Clear our current nodes. We will be replacing this with
        # the parent nodes.
        self.content.nodes = []

        # Set our include, unique by filename
        t.content.blocks['__include__' + filename] = buf
        # Extend our blocks
        t.content.extend(self.content)
        # Work off the parent node.
        self.content = t.content

    def parse(self, text):

        # Basically, r_tag.split will split the text into
        # an array containing, 'non-tag', 'tag', 'non-tag', 'tag'
        # so if we alternate this variable, we know
        # what to look for. This is alternate to 
        # line.startswith("{{")
        in_tag = False
        extend = None

        for i in TemplateParser.r_tag.split(text):
            if i:
                if len(self.stack) == 0:
                    raise Exception, "The 'end' tag is unmatched, please check if you have a starting 'block' tag"

                # Our current element in the stack.
                top = self.stack[-1]

                if in_tag:
                    # Get rid of '{{' and '}}'
                    line = i[2:-2].strip()
                    # This is bad joo joo, but lets do it anyway
                    if not line:
                        continue

                    if line.startswith('='):
                        # IE: {{=response.title}}
                        name, value = '=', line[1:].strip()
                    else:
                        v = line.split(' ', 1)
                        if len(v) == 1:
                            # Example
                            # {{ include }}
                            # {{ end }}
                            name, value = v[0], ''
                        else:
                            # Example
                            # {{ block pie }}
                            # {{ include "layout.html" }}
                            # {{ for i in range(10): }}
                            name, value = v

                    # This will replace newlines in block comments
                    # with the newline character. This is so that they
                    # retain their formatting, but squish down to one
                    # line in the rendered template. 
                    
                    # We do not want to replace the newlines in code,
                    # only in block comments.
                    def remove_newline(re_val):
                        # Take the entire match and replace newlines with
                        # escaped newlines.
                        return re_val.group(0).replace('\n', '\\n')

                        
                    # Perform block comment escaping.
                    value = re.sub(TemplateParser.r_block_comment,
                                remove_newline,
                                value)

                    # Now we want to get rid of all newlines that exist
                    # in the line. This does not effect block comments
                    # since we already converted those.
                    value = value.replace('\n', '')

                    if name == 'block':
                        # Make a new node with name.
                        node = BlockNode(name=value.strip())
                        # Append this node to our active node
                        top.append(node)
                        # Make sure to add the node to the stack.
                        # so anything after this gets added
                        # to this node. This allows us to
                        # "nest" nodes.
                        self.stack.append(node)

                    elif name == 'end':
                        # We are done with this node.
                        self.stack.pop()

                    elif name == '=':
                        # So we have a variable to insert into
                        # the template
                        buf = "\n%s(%s)" % (self.writer, value)
                        top.append(buf)

                    elif name == 'include':
                        # If we know the target file to include
                        if value:
                            self.include(top, value)
                        # Otherwise, make a temporary include node
                        # That the child node will know to hook into.
                        else:
                            include_node = BlockNode(name='__include__' + self.name)
                            top.append(include_node)

                    elif name == 'extend':
                        # We need to extend the following
                        # template.
                        extend = value

                    else:
                        # If we don't know where it belongs
                        # we just add it anyways without form
                        # matting.
                        if line and in_tag:
                            top.append("\n%s" % line)
                        
                else:
                    # It is HTML so just include it.
                    buf = "\n%s(%r, escape=False)" % (self.writer, i)
                    top.append(buf)

            # Remeber, tag, not tag, tag, not tag
            in_tag = not in_tag

        # If we need to extend a template.
        if extend:
            self.extend(extend)

# We need this for integration with gluon
def parse_template(filename,
        path    = 'views/',
        context = dict()):
    """
    filename can be a view filename in the views folder or an input stream
    path is the path of a views folder
    context is a dictionary of symbols used to render the template
    """

    # First, if we have a str try to open the file
    if isinstance(filename, str):
        try:
            fp = open(os.path.join(path, filename), 'rb')
            text = fp.read()
            fp.close()
        except IOError:
            raise restricted.RestrictedError('Processing View %s' % filename,
                                             '', 'Unable to find the file')
    else:
        text = filename.read()

    # Use the file contents to get a parsed template and return it.
    return str(TemplateParser(text, context=context, path=path))
        
    
# And this is a generic render function.
# Here for integration with gluon.
def render(content = "hello world",
        stream = None,
        filename = None,
        path = None,
        context = {},):
    """
    >>> render()
    'hello world'
    >>> render(content='abc')
    'abc'
    >>> render(content='abc\\'')
    "abc'"
    >>> render(content='a"\\'bc')
    'a"\\'bc'
    >>> render(content='a\\nbc')
    'a\\nbc'
    >>> render(content='a"bcd"e')
    'a"bcd"e'
    >>> render(content="'''a\\nc'''")
    "'''a\\nc'''"
    >>> render(content="'''a\\'c'''")
    "'''a\'c'''"
    """
    # Here to avoid circular Imports        
    import globals

    # If we don't have anything to render, why bother?
    if not content and not stream and not filename:
        raise SyntaxError, "Must specify a stream or filename or content"

    # Here for legacy purposes, probably can be reduced to something more simple.
    close_stream = False
    if not stream:
        if filename:
            stream = open(filename, 'rb')
            close_stream = True
        if content:
            stream = cStringIO.StringIO(content)

    # Get a response class.
    context['response'] = globals.Response()

    # Execute the template.
    exec(str(TemplateParser(stream.read(), context=context, path=path))) in context
    
    if close_stream:
        stream.close()

    # Returned the rendered content.
    return context['response'].body.getvalue()
    

if __name__ == '__main__':
    import doctest
    doctest.testmod()
