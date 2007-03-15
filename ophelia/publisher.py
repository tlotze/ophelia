# Copyright (c) 2006-2007 Thomas Lotze
# See also LICENSE.txt

import os.path
import inspect
import urlparse

from zope.tales.engine import Engine as TALESEngine
import zope.pagetemplate.pagetemplate

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


class PageTemplate(zope.pagetemplate.pagetemplate.PageTemplate):
    """Page templates with Ophelia-style namespaces and source tracking.
    """

    publisher = None
    file_path = None

    def __init__(self, publisher, text, file_path=None):
        super(PageTemplate, self).__init__()
        self.publisher = publisher
        self.write(text)
        self.file_path = file_path

    def pt_getContext(self, args=(), options=None, **ignored):
        rval = Namespace(template=self)
        rval.update(self.publisher.tales_namespace())
        return rval

    def pt_source_file(self):
        return self.file_path


###########
# publisher

class Publisher(object):
    """Ophelia's publisher building web pages from TAL page templates
    """

    innerslot = None
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
        template, stop_traversal = self.process_file(file_path)

        if stop_traversal:
            if stop_traversal.content is not None:
                self.innerslot = stop_traversal.content
            if not stop_traversal.use_template:
                template = None
            del self.tail[:]

        if template is not None:
            self.stack.append(template)

    def process_file(self, file_path):
        # make publisher accessible from scripts
        __publisher__ = self

        # get script and template
        script, text = self.splitter(open(file_path).read())
        self.template = PageTemplate(self, text, file_path)

        # manipulate the context
        stop_traversal = None
        if script:
            self.context.__file__ = file_path
            try:
                exec script in self.context
            except StopTraversal, e:
                stop_traversal = e

        # collect the macros, complain if the template doesn't compile
        self.macros.update(self.template.macros)
        if self.template._v_errors:
            self.log_error("Can't compile template at " + file_path)
            raise zope.pagetemplate.pagetemplate.PTRuntimeError(
                str(template._v_errors))

        return self.template, stop_traversal

    def tales_namespace(self):
        tales_ns = Namespace(
            innerslot=lambda: self.innerslot,
            macros=self.macros,
            )
        tales_ns.update(TALESEngine.getBaseNames())
        tales_ns.update(self.context)
        return tales_ns

    def build_content(self):
        # make publisher accessible from TALES expressions
        __publisher__ = self

        while self.stack:
            template = self.stack.pop()
            try:
                self.innerslot = template()
            except:
                self.log_error(
                    "Can't interpret template at " + template.file_path)
                raise

        self.content = """<?xml version="1.1" encoding="%s" ?>\n%s""" % (
            self.response_encoding,
            self.innerslot.encode(self.response_encoding))

    def build_headers(self):
        # make publisher accessible from TALES expressions
        __publisher__ = self

        self.compiled_headers = {}
        tales_context = TALESEngine.getContext(self.tales_namespace())

        for name, expression in self.response_headers.iteritems():
            try:
                compiled = TALESEngine.compile(expression)
            except:
                self.log_error("Can't compile expression for header " + name)
                raise
            try:
                value = str(compiled(tales_context))
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
