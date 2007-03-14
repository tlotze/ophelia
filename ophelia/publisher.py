# Copyright (c) 2006-2007 Thomas Lotze
# See also LICENSE.txt

import os.path
import inspect
from StringIO import StringIO
import urlparse

from zope.tales.engine import Engine as TALESEngine
from zope.tal.htmltalparser import HTMLTALParser
from zope.tal.talgenerator import TALGenerator
from zope.tal.talinterpreter import TALInterpreter

import ophelia.template


########################
# exceptions and classes

class StopTraversal(Exception):
    """Flow control device for scripts to stop directory traversal."""

    content = "" # str to use instead, interpreted as a template

    def __init__(self, content=None, use_template=False):
        self.content = content
        self.use_template = use_template


class NotFound(Exception):
    """Signals that Ophelia can't find all files needed by the request."""
    pass


class Redirect(Exception):
    """Signals that the server should redirect the client to another URI."""

    def __init__(self, uri):
        self.uri = uri


class Namespace(dict):
    """Objects which exist only to carry attributes.

    Attributes are also accessible as mapping items.
    """

    def __init__(self, *args, **kwargs):
        self.__dict__ = self
        super(Namespace, self).__init__(*args, **kwargs)


###########
# publisher

class Publisher(object):
    """Ophelia's publisher building web pages from TAL page templates
    """

    innerslot = None
    tales_context = None
    content = None
    compiled_headers = None
    current = None
    history = None
    stack = None
    file_path = None

    def __init__(self, path, root, site, request, log_error):
        """Set up the publisher for traversing path.

        path: str, path to traverse from the template root,
                   elements are separated by '/'
        root: str, file system path to the template root
        site: str, absolute URL to site root, ends with '/'
        request: the request object
        log_error: callable taking an error message as an argument
        """
        self.path = path
        self.tail = path.split('/')

        self.root = os.path.abspath(root)

        if not site.endswith('/'):
            site += '/'
        self.site = site

        self.context = Namespace(
            __publisher__=self,
            )
        self.macros = Namespace()
        self.response_headers = {}
        self.request = request
        self.options = options = request.get_options()
        self.log_error = log_error
        self.splitter = ophelia.template.Splitter(options)
        self.response_encoding = options.get("ResponseEncoding", "utf-8")
        self.index_name = options.get("IndexName", "index.html")
        self.redirect_index = (
            options.get("RedirectIndex", "").lower() == "on")

    def __call__(self):
        """Publish the resource at path.

        returns (dict, unicode), response headers and page content
        """
        self.traverse()
        return self.build()

    def build(self):
        self.set_tales_context()

        self.build_content()
        self.build_headers()

        return self.compiled_headers, self.content

    def traverse(self):
        tail = self.tail
        self.current = current = self.site
        self.history = [current]
        self.file_path = file_path = self.root
        self.stack = []

        # traverse the template root
        if not os.path.isdir(file_path):
            raise NotFound
        self.traverse_dir(file_path)

        while tail:
            # determine the next traversal step
            next = tail.pop(0)
            if not tail:
                if self.redirect_index and next == self.index_name:
                    self.redirect(path=self.request.uri[:-len(next)])
                if not next:
                    next = self.index_name

            # add to traversal history
            current += next
            if tail:
                current += '/'
            self.current = current
            self.history.append(current)

            # try to find a file to read
            self.file_path = file_path = os.path.join(file_path, next)

            if os.path.isdir(file_path):
                self.traverse_dir(file_path)
            elif os.path.isfile(file_path):
                self.traverse_file(file_path)
            else:
                raise NotFound

    def redirect(self, path=None):
        parts = list(urlparse.urlparse(self.request.unparsed_uri))
        if path is not None:
            parts[2] = path
        raise Redirect(urlparse.urlunparse(parts))

    def traverse_dir(self, dir_path):
        if not self.tail:
            self.redirect(path=self.request.uri + '/')
        file_path = os.path.join(dir_path, "__init__")
        if os.path.isfile(file_path):
            self.traverse_file(file_path)

    def traverse_file(self, file_path):
        program, stop_traversal = self.process_file(file_path)

        if stop_traversal:
            if stop_traversal.content is not None:
                self.innerslot = stop_traversal.content
            if not stop_traversal.use_template:
                program = None
            del self.tail[:]

        if program is not None:
            self.stack.append((program, file_path))

    def process_file(self, file_path):
        # make publisher accessible from scripts
        __publisher__ = self

        # get script and template
        script, self.template = self.splitter(open(file_path).read())

        # manipulate the context
        stop_traversal = None
        if script:
            self.context.__file__ = file_path
            try:
                exec script in self.context
            except StopTraversal, e:
                stop_traversal = e

        # compile the template, collect program and macros
        if self.template:
            generator = TALGenerator(TALESEngine, xml=False,
                                     source_file=file_path)
            parser = HTMLTALParser(generator)

            try:
                parser.parseString(self.template)
            except:
                self.log_error("Can't compile template at " + file_path)
                raise

            program, macros = parser.getCode()
            self.macros.update(macros)
        else:
            program = None

        return program, stop_traversal

    def set_tales_context(self):
        tales_ns = Namespace(
            innerslot=lambda: self.innerslot,
            macros=self.macros,
            )
        tales_ns.update(TALESEngine.getBaseNames())
        tales_ns.update(self.context)
        self.tales_context = TALESEngine.getContext(tales_ns)

    def build_content(self):
        # make publisher accessible from TALES expressions
        __publisher__ = self

        out = StringIO(u"")

        while self.stack:
            program, file_path = self.stack.pop()
            out.truncate(0)
            try:
                TALInterpreter(program, self.macros, self.tales_context, out,
                               strictinsert=False)()
            except:
                self.log_error("Can't interpret template at " + file_path)
                raise
            else:
                self.innerslot = out.getvalue()

        self.content = """<?xml version="1.1" encoding="%s" ?>\n%s""" % (
            self.response_encoding,
            self.innerslot.encode(self.response_encoding))

    def build_headers(self):
        # make publisher accessible from TALES expressions
        __publisher__ = self

        self.compiled_headers = {}

        for name, expression in self.response_headers.iteritems():
            try:
                compiled = TALESEngine.compile(expression)
            except:
                self.log_error("Can't compile expression for header " + name)
                raise
            try:
                value = str(compiled(self.tales_context))
            except:
                log_error("Can't interpret expression for header " + name)
                raise
            self.compiled_headers[name] = value

    def load_macros(self, *args):
        base = self.file_path
        if not os.path.isdir(base):
            base = os.path.dirname(base)

        old_file_path = self.context.__file__
        old_template = self.template

        for name in args:
            file_path = os.path.join(base, name)
            try:
                self.process_file(file_path)
            except:
                self.log_error("Can't read macros from " + file_path)
                raise

        self.context.__file__ = old_file_path
        self.template = old_template


###########
# functions

def get_publisher():
    for frame_record in inspect.stack():
        candidate = frame_record[0].f_locals.get("__publisher__")
        if isinstance(candidate, Publisher):
            return candidate
    else:
        raise LookupError("Could not find publisher.")
