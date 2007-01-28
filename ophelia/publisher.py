# Python
import os.path
import inspect
from StringIO import StringIO
import urlparse

# Zope
from zope.tales.engine import Engine as TALESEngine
from zope.tal.htmltalparser import HTMLTALParser
from zope.tal.talgenerator import TALGenerator
from zope.tal.talinterpreter import TALInterpreter

# Ophelia
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
    history = None
    file_path = None

    def __init__(self, path, root, site, request, log_error):
        """Set up the publisher for traversing path.

        path: str, path to traverse from the template root,
                   empty or starts with '/', elements are separated by '/'
        root: str, file system path to the template root
        site: str, absolute URL to site root, ends with '/'
        request: the request object
        log_error: callable taking an error message as an argument
        """
        # Don't look at the path at this point. How to respond to an empty
        # path or one that doesn't start with '/' is traversal logic which I'd
        # rather keep out of __init__.
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
        self.log_error = log_error
        self.splitter = ophelia.template.Splitter(request)
        self.stack = []
        self.response_encoding = request.get_options().get(
            "ResponseEncoding", "utf-8")

    def __call__(self):
        """Publish the resource at path.

        returns (dict, unicode), response headers and page content
        """
        self.traverse()
        self.set_tales_context()

        self.build_content()
        self.build_headers()

        return self.compiled_headers, self.content

    def traverse(self):
        tail = self.tail
        self.current = current = ""
        self.history = [""]
        self.file_path = file_path = self.root

        # traverse the template root
        if tail.pop(0) or not os.path.isdir(file_path):
            raise NotFound
        self.process_dir(file_path)

        while tail:
            # determine the next traversal step
            next = tail.pop(0)
            if not (next or tail):
                next = "index.html"

            # add to traversal history
            current += next
            if tail:
                current += '/'
            self.current = current
            self.history.append(current)

            # try to find a file to read
            self.file_path = file_path = os.path.join(file_path, next)

            if os.path.isdir(file_path):
                self.process_dir(file_path)
            elif os.path.isfile(file_path):
                self.process_file(file_path)
            else:
                raise NotFound

    def redirect(self, path=None):
        parts = list(urlparse.urlparse(self.request.unparsed_uri))
        if path is not None:
            parts[2] = path
        raise Redirect(urlparse.urlunparse(parts))

    def process_dir(self, dir_path):
        if not self.tail:
            self.redirect(path=self.request.uri + '/')
        file_path = os.path.join(dir_path, "__init__")
        if os.path.isfile(file_path):
            self.process_file(file_path)

    def process_file(self, file_path):
        # get script and template
        script, self.template = self.splitter(open(file_path).read())

        # manipulate the context
        if script:
            self.context.__file__ = file_path
            try:
                exec script in self.context
            except StopTraversal, e:
                if e.content is not None:
                    self.innerslot = e.content
                if not e.use_template:
                    self.template = None
                del self.tail[:]

        # compile the template, collect the macros
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
            self.stack.append((program, file_path))
            self.macros.update(macros)

    def set_tales_context(self):
        tales_ns = Namespace(
            innerslot=lambda: self.innerslot,
            macros=self.macros,
            )
        tales_ns.update(TALESEngine.getBaseNames())
        tales_ns.update(self.context)
        self.tales_context = TALESEngine.getContext(tales_ns)

    def build_content(self):
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
        for name in args:
            file_path = os.path.join(self.file_path, name)
            try:
                content = open(file_path).read()
            except:
                self.log_error("Can't read macro file at " + file_path)
                raise

            script, template = self.splitter(content)
            if script:
                self.log_error("Macro file contains a script at " + file_path)
                raise ValueError(
                    "Macro file contains a script at " + file_path)

            generator = TALGenerator(TALESEngine, xml=False,
                                     source_file=file_path)
            parser = HTMLTALParser(generator)

            try:
                parser.parseString(template)
            except:
                self.log_error("Can't compile template at " + file_path)
                raise

            program, macros = parser.getCode()
            self.macros.update(macros)


###########
# functions

def get_context():
    for frame_record in inspect.stack():
        candidate = frame_record[0].f_globals
        if "__publisher__" in candidate:
            return candidate
    else:
        raise LookupError("Could not find context namespace.")


def get_publisher():
    return get_context()["__publisher__"]
