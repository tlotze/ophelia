# Copyright (c) 2006-2010 Thomas Lotze
# See also LICENSE.txt

import functools
import os.path
import threading
import urlparse

import zope.interface
from zope.tales.engine import Engine as TALESEngine

import ophelia.interfaces
import ophelia.input
import ophelia.pagetemplate
from ophelia.util import Namespace


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


class ThreadContext(threading.local):

    def __init__(self):
        self.requests = []
        self.file_contexts = []


_thread_context = ThreadContext()


def push_request(func):
    @functools.wraps(func)
    def wrapper(request, *args, **kwargs):
        _thread_context.requests.append(request)
        try:
            return func(request, *args, **kwargs)
        finally:
            _thread_context.requests.pop()
    return wrapper


def get_request():
    try:
        return _thread_context.requests[-1]
    except IndexError:
        raise LookupError("Could not find request.")


def get_file_context():
    try:
        return _thread_context.file_contexts[-1]
    except IndexError:
        raise LookupError("Could not find file context namespace.")


class Request(object):
    """Ophelia's request object.

    Instantiate as Request(path, template_root, site, **env).

    path: str, path to traverse from the site root, elements separated by '/'
    template_root: str, file system path to the template root
    site: str, absolute URL to site root, ends with '/'
    env: the environment
    """

    zope.interface.implements(ophelia.interfaces.IRequestAPI,
                              ophelia.interfaces.IRequestTraversal)

    innerslot = None
    content = None
    compiled_headers = None
    history = None # XXX deprecated, planned to be removed in 0.3.1

    # XXX This is a temporary solution for overriding the file or directory
    # read during the next traversal step. A better solution would be to put
    # more information in self.path.
    next_name = None

    xml_version = '1.1' # XXX temporary solution

    def __init__(self, path, template_root, site, **env):
        self.path = path
        self.tail = path.split('/')

        self.template_root = self.dir_path = os.path.abspath(template_root)

        if not site.endswith('/'):
            site += '/'
        self.site = self.current = site

        self.env = Namespace(env)
        self.input = env['wsgi.input']
        self.headers = Namespace((key[5:], value)
                                 for key, value in env.iteritems()
                                 if key.startswith('HTTP_'))

        self.context = Namespace(
            __request__=self,
            )
        self.macros = Namespace()

        preset_response_headers = env.get('ophelia.response_headers', {})
        self.response_headers = Namespace(
            (key, 'string:' + value)
            for key, value in preset_response_headers.iteritems())
        self.response_headers['Content-Type'] = \
            "python:'text/html; charset=' + __request__.response_encoding"

        self.stack = []

        self.splitter = ophelia.input.Splitter(**env)
        self.response_encoding = env.get("response_encoding", "utf-8")
        self.index_name = env.get("index_name", "index.html")

        # XXX Handling config syntax doesn't belong here.
        redirect_index = env.get("redirect_index", False)
        if redirect_index not in (True, False):
            redirect_index = redirect_index.lower() in ("on", "true", "yes")
        self.redirect_index = redirect_index

        self.immediate_result = env.get("immediate_result", False)

    def __call__(self, **context):
        self.traverse(**context)
        return self.build()

    @push_request
    def traverse(self, **context):
        self.context.update(context)
        self.history = [self.current]

        # traverse the template root
        if not os.path.isdir(self.template_root):
            raise RuntimeError(
                "The Ophelia template root must be a file system directory.")

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

    def process_file(self, file_path, insert=False, context=None):
        __traceback_info__ = "Processing " + file_path

        # get script and template
        script, text = self.splitter(open(file_path).read())
        # XXX bad hack:
        offset = self.splitter._last_template_offset

        # get_file_context() will find the file context by its name
        file_context = Namespace(
            __file__ = file_path,
            __text__ = text,
            __template__ = ophelia.pagetemplate.PageTemplate(
                text, file_path=file_path, offset=offset),
            )
        if insert:
            self.stack.append(file_context)

        # manipulate the context, restore the predefined variables in the end
        # so any script that might be calling this method can rely on those
        stop_traversal = None
        if script:
            if context is None:
                context = self.context
            old_predef_vars = dict((key, context.get(key))
                                   for key in file_context)
            context.update(file_context)
            _thread_context.file_contexts.append(file_context)
            try:
                try:
                    exec script in context
                except StopTraversal, e:
                    stop_traversal = e
                    if  e.text is not None:
                        file_context.__text__ = e.text
                        file_context.__template__.write(e.text)
            finally:
                context.update(old_predef_vars)
                _thread_context.file_contexts.pop()

        # collect the macros
        self.macros.update(file_context.__template__.macros)

        return file_context, stop_traversal

    def tales_namespace(self, file_context={}):
        tales_ns = Namespace(
            innerslot=self.innerslot,
            macros=self.macros,
            )
        tales_ns.update(TALESEngine.getBaseNames())
        tales_ns.update(self.context)
        tales_ns.update(file_context)
        tales_ns.pop("__builtins__", None)
        return tales_ns

    def build(self):
        self.build_content()
        self.build_headers()
        return self.compiled_headers, self.content

    @push_request
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
            self.innerslot = template(self.tales_namespace(file_context))

        self.content = self.innerslot
        if not self.immediate_result:
            self.content = """<?xml version="%s" encoding="%s" ?>\n%s""" % (
                self.xml_version,
                self.response_encoding,
                self.content.encode(self.response_encoding))

    @push_request
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

    def render_template(self, name):
        file_context, stop_traversal = self.process_file(
            os.path.join(self.dir_path, name))
        return file_context.__template__(self.tales_namespace(file_context))
