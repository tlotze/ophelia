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

    text = "" # unicode, template text to use for this traversal step

    def __init__(self, text=None):
        self.text = text


class NotFound(Exception):
    """Signals that Ophelia can't find all files needed by the request."""
    pass


class Redirect(Exception):
    """Signals that the server should redirect the client to another URI."""

    def __init__(self, uri, path=None):
        parts = list(urlparse.urlsplit(uri))
        if path is not None:
            parts[2] = path
        self.uri = urlparse.urlunsplit(parts)


class Namespace(dict):
    """Objects which exist only to carry attributes.

    Attributes are also accessible as mapping items.
    """

    def __init__(self, *args, **kwargs):
        self.__dict__ = self
        super(Namespace, self).__init__(*args, **kwargs)


class PageTemplateTracebackSupplement(object):

    def __init__(self, template):
        self.template = template

    @property
    def warnings(self):
        return self.template._v_errors


class PageTemplate(zope.pagetemplate.pagetemplate.PageTemplate):
    """Page templates with Ophelia-style namespaces and source tracking.

    Call parameters: the namespace of file context variables
    """

    publisher = None
    file_path = None

    def __init__(self, publisher, text, file_path=None):
        super(PageTemplate, self).__init__()
        self.publisher = publisher
        self.write(text)
        self.file_path = file_path

    @property
    def macros(self):
        __traceback_supplement__ = (PageTemplateTracebackSupplement, self)
        macros = super(PageTemplate, self).macros
        if self._v_errors:
            raise zope.pagetemplate.PTRuntimeError(
                "Can't compile template at %s." % self.file_path)
        return macros

    def pt_getContext(self, args=(), options=None, **ignored):
        return Namespace(self.publisher.tales_namespace(args[0]))

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

    def __init__(self, path, root, site, request):
        """Set up the publisher for traversing path.

        path: str, path to traverse from the template root,
                   elements are separated by '/'
        root: str, file system path to the template root
        site: str, absolute URL to site root, ends with '/'
        request: the request object
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
        self.current = self.site
        self.file_path = self.root
        self.history = []
        self.stack = []

        # traverse the template root
        if not os.path.isdir(self.file_path):
            raise NotFound
        self.traverse_dir(self.file_path)

        while self.tail:
            # determine the next traversal step
            next = self.tail.pop(0)

            # add to traversal history
            self.current += next

            # try to find a file to read
            self.file_path = os.path.join(self.file_path, next)

            if os.path.isdir(self.file_path):
                self.current += '/'
                self.traverse_dir(self.file_path)
            elif os.path.isfile(self.file_path):
                self.traverse_file(self.file_path)
            else:
                raise NotFound

    def traverse_dir(self, dir_path):
        if not self.tail:
            raise Redirect(self.request.unparsed_uri,
                           path=self.request.uri + '/')

        file_path = os.path.join(dir_path, "__init__")
        if os.path.isfile(file_path):
            self.traverse_file(file_path)

        if self.redirect_index and self.tail == [self.index_name]:
            raise Redirect(self.request.unparsed_uri,
                           path=self.request.uri[:-len(self.index_name)])

        if self.tail == [""]:
            self.tail[0] = self.index_name

    def traverse_file(self, file_path):
        file_context, stop_traversal = self.process_file(file_path)
        if stop_traversal:
            if stop_traversal.text is not None:
                file_context.__template__.write(stop_traversal.text)
            del self.tail[:]

        self.stack.append(file_context)
        self.history.append(self.current)

    def process_file(self, file_path):
        __traceback_info__ = "Processing " + file_path

        # get script and template
        script, text = self.splitter(open(file_path).read())

        # get_file_context() will find the file context by its name
        file_context = Namespace(
            __file__ = file_path,
            __text__ = text,
            __template__ = PageTemplate(self, text, file_path),
            )

        # manipulate the context
        stop_traversal = None
        if script:
            try:
                exec script in file_context, self.context
            except StopTraversal, e:
                stop_traversal = e

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

    def process_file_relative(self, name):
        base = self.file_path
        if not os.path.isdir(base):
            base = os.path.dirname(base)

        file_path = os.path.join(base, name)

        file_context, stop_traversal = self.process_file(file_path)
        if stop_traversal:
            file_context.__template__.write(stop_traversal.text)

        return file_context

    def load_macros(self, name):
        self.process_file_relative(name)

    def insert_template(self, name):
        self.stack.append(self.process_file_relative(name))

    def interpret_template(self, name):
        file_context = self.process_file_relative(name)
        return file_context.__template__(file_context)


###########
# functions

def get_publisher():
    for frame_record in inspect.stack():
        candidate = frame_record[0].f_locals.get("self")
        if isinstance(candidate, Publisher):
            return candidate
    else:
        raise LookupError("Could not find publisher.")


def get_file_context():
    for frame_record in inspect.stack():
        candidate = frame_record[0].f_locals.get("file_context")
        if isinstance(candidate, Namespace):
            return candidate
    else:
        raise LookupError("Could not find file context namespace.")
