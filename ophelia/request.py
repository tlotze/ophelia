# Copyright (c) 2006-2007 Thomas Lotze
# See also LICENSE.txt

import os.path
import inspect
import urlparse

from zope.tales.engine import Engine as TALESEngine

import ophelia.input
import ophelia.pagetemplate
from ophelia.util import Namespace


########################
# exceptions and classes

class StopTraversal(Exception):
    """Flow control device for scripts to stop directory traversal."""

    text = "" # unicode, template text to use for this traversal step

    def __init__(self, text=None):
        self.text = text


class NotFound(Exception):
    """Signals that Ophelia can't find all files needed by the request."""
    pass


class Redirect(Exception):
    """Signals that the server should redirect the client to another URI."""

    def __init__(self, uri=None, path=None):
        if uri is None:
            uri = get_request().site
        parts = list(urlparse.urlsplit(uri))
        if path is not None:
            parts[2] = urlparse.urlsplit(path)[2]
        self.uri = urlparse.urlunsplit(parts)


#########
# request

class Request(object):
    """Ophelia's request object."""

    innerslot = None
    content = None
    compiled_headers = None
    current = None
    history = None
    stack = None
    dir_path = None

    # XXX This is a temporary solution for overriding the file or directory
    # read during the next traversal step. A better solution would be to put
    # more information in self.path.
    next_name = None

    def __init__(self, path, root, site, env):
        """Set up the request for traversing path.

        path: str, path to traverse from the template root,
                   elements are separated by '/'
        root: str, file system path to the template root
        site: str, absolute URL to site root, ends with '/'
        env: the environment namespace
        """
        self.path = path
        self.tail = path.split('/')

        self.root = os.path.abspath(root)

        if not site.endswith('/'):
            site += '/'
        self.site = site

        self.context = Namespace(
            __request__=self,
            )
        self.macros = Namespace()
        self.response_headers = {
            "Content-Type":
            "python:'text/html; charset=' + __request__.response_encoding"}
        self.env = env
        self.splitter = ophelia.input.Splitter(**env)
        self.response_encoding = env.get("ResponseEncoding", "utf-8")
        self.index_name = env.get("IndexName", "index.html")
        self.redirect_index = (env.get("RedirectIndex", "").lower() == "on")

    def __call__(self):
        """Build the requested resource.

        returns (dict, unicode), response headers and page content
        """
        self.traverse()
        return self.build()

    def build(self):
        self.build_content()
        self.build_headers()

        return self.compiled_headers, self.content

    def traverse(self):
        self.current = self.site
        self.history = [self.current]
        self.stack = []

        # traverse the template root
        if not os.path.isdir(self.root):
            raise NotFound

        self.dir_path = self.root
        self.traverse_dir()

        while self.tail:
            self.traverse_next()
            if self.history[-1:] != [self.current]:
                self.history.append(self.current)

    def traverse_next(self):
        # determine the next traversal step
        next = self.get_next()

        self.current += next
        if self.tail:
            self.current += '/'

        # try to find a file to read
        name = self.next_name
        self.next_name = None
        if name is None:
            name = next or self.index_name
        next_path = os.path.join(self.dir_path, name)

        if os.path.isdir(next_path):
            self.dir_path = next_path
            self.traverse_dir()
        elif os.path.isfile(next_path):
            self.traverse_file(next_path)
        else:
            raise NotFound

    def get_next(self):
        next = self.tail.pop(0)

        if ((self.tail and not next) or
            (self.redirect_index and
             next == self.index_name and not self.tail) or
            next == "."):
            raise Redirect(path=self.current + '/'.join(self.tail))

        if next == "..":
            path_segments = urlparse.urlsplit(self.current)[2].split('/')
            path_segments[-2:] = self.tail
            raise Redirect(path='/'.join(path_segments))

        return next

    def traverse_dir(self):
        if not self.tail:
            raise Redirect(path=self.current + '/')

        file_path = os.path.join(self.dir_path, "__init__")
        if os.path.isfile(file_path):
            self.traverse_file(file_path)

    def traverse_file(self, file_path):
        file_context, stop_traversal = self.process_file(file_path,
                                                         insert=True)
        if stop_traversal:
            del self.tail[:]

    def process_file(self, file_path, insert=False):
        __traceback_info__ = "Processing " + file_path

        # get script and template
        script, text = self.splitter(open(file_path).read())

        # get_file_context() will find the file context by its name
        file_context = Namespace(
            __file__ = file_path,
            __text__ = text,
            __template__ = ophelia.pagetemplate.PageTemplate(self, text,
                                                             file_path),
            )
        if insert:
            self.stack.append(file_context)

        # manipulate the context, restore the predefined variables in the end
        # so any script that might be calling this method can rely on those
        stop_traversal = None
        if script:
            old_predef_vars = dict((key, self.context.get(key))
                                   for key in file_context)
            self.context.update(file_context)
            try:
                try:
                    exec script in self.context
                except StopTraversal, e:
                    stop_traversal = e
                    if  e.text is not None:
                        file_context.__text__ = e.text
                        file_context.__template__.write(e.text)
            finally:
                self.context.update(old_predef_vars)

        # collect the macros
        self.macros.update(file_context.__template__.macros)

        return file_context, stop_traversal

    def tales_namespace(self, file_context={}):
        tales_ns = Namespace(
            innerslot=lambda: self.innerslot,
            macros=self.macros,
            )
        tales_ns.update(TALESEngine.getBaseNames())
        tales_ns.update(file_context)
        tales_ns.update(self.context)
        return tales_ns

    def build_content(self):
        while self.stack:
            # get_file_context() will find the file context by its name
            file_context = self.stack.pop()
            template = file_context.__template__

            # apply some common sense and interpret whitespace-only templates
            # as non-existent instead of as describing an empty innerslot
            if not template._text.strip():
                continue

            __traceback_info__ = "Template at " + file_context.__file__
            self.innerslot = template(file_context)

        self.content = """<?xml version="1.1" encoding="%s" ?>\n%s""" % (
            self.response_encoding,
            self.innerslot.encode(self.response_encoding))

    def build_headers(self):
        self.compiled_headers = {}
        tales_context = TALESEngine.getContext(self.tales_namespace())

        for name, expression in self.response_headers.iteritems():
            __traceback_info__ = "Header %s: %s" % (name, expression)
            self.compiled_headers[name] = tales_context.evaluate(expression)

    def load_macros(self, name):
        self.process_file(os.path.join(self.dir_path, name))

    def insert_template(self, name):
        self.process_file(os.path.join(self.dir_path, name), insert=True)

    def interpret_template(self, name):
        file_context, stop_traversal = self.process_file(
            os.path.join(self.dir_path, name))
        return file_context.__template__(file_context)


###########
# functions

def get_request():
    for frame_record in inspect.stack():
        candidate = frame_record[0].f_locals.get("self")
        if isinstance(candidate, Request):
            return candidate
    else:
        raise LookupError("Could not find request.")


def get_file_context():
    for frame_record in inspect.stack():
        candidate = frame_record[0].f_locals.get("file_context")
        if isinstance(candidate, Namespace):
            return candidate
    else:
        raise LookupError("Could not find file context namespace.")