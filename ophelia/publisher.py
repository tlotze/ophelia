# Python
import os.path
import inspect
from StringIO import StringIO

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

    def __call__(self, path, root, request, log_error):
        """Publish the resource at path.

        path: str, path to traverse from the template root, starts with '/',
                   ends '/' if directory, elements are separated by '/'
        root: str, absolute file system path to the template root,
                   does not end with '/'
        request: the request object
        log_error: callable taking an error message as an argument

        returns unicode, page content

        may raise anything
        """
        # initialize file path parts and sanity check
        path = os.path.abspath(path)
        root = os.path.abspath(root)
        current = ""
        tail = path.split('/')
        if tail[0]:
            raise ValueError("Path must start with '/', got " + path)

        # initialize the environment
        context = Namespace()
        self.macros = Namespace()
        tales_names = Namespace()
        response_headers = {}

        script_globals = {
            "__publisher__": self,
                "context": context,
                "tales_names": tales_names,
                "response_headers": response_headers,
                }

        self.request = request
        self.log_error = log_error
        self.splitter = ophelia.template.Splitter(request)
        self.path = path
        self.root = root
        self.tail = tail
        self.stack = stack = []
        self.history = history = []

        tales_names.context = context
        tales_names.macros = self.macros

        # traverse the levels
        while tail:
            # determine the next traversal step
            next = tail.pop(0)
            if not (next or tail):
                next = "index.html"
            current = os.path.join(current, next)

            # try to find a file to read
            file_path = os.path.join(root, current)
            if not os.path.exists(file_path):
                raise NotFound

            isdir = os.path.isdir(file_path)
            history.append(current + (isdir and "/" or ""))

            if isdir:
                file_path = os.path.join(file_path, "__init__")
                if not os.path.exists(file_path):
                    continue

            # get script and template
            script, template = self.splitter(file(file_path).read())

            # manipulate the context
            if script:
                self.file_path = file_path
                self.isdir = isdir
                self.current = current
                self.template = template
                try:
                    exec script in script_globals
                except StopTraversal, e:
                    if e.content is not None:
                        self.innerslot = e.content
                    if not e.use_template:
                        self.template = None
                    del tail[:]
                template = self.template

            # compile the template, collect the macros
            if template:
                generator = TALGenerator(TALESEngine, xml=False,
                                         source_file=file_path)
                parser = HTMLTALParser(generator)

                try:
                    parser.parseString(template)
                except:
                    log_error("Can't compile template at " + file_path)
                    raise

                program, macros = parser.getCode()
                stack.append((program, file_path))
                self.macros.update(macros)

        # initialize the template environment
        engine_ns = Namespace(tales_names)
        engine_ns.innerslot = lambda: self.innerslot
        engine_ns.update(TALESEngine.getBaseNames())
        engine_context = TALESEngine.getContext(engine_ns)
        out = StringIO(u"")

        # interpret the templates
        while stack:
            program, file_path = stack.pop()
            out.truncate(0)
            try:
                TALInterpreter(program, self.macros, engine_context, out,
                               strictinsert=False)()
            except:
                log_error("Can't interpret template at " + file_path)
                raise
            else:
                self.innerslot = out.getvalue()

        # set the request headers
        for name, expression in response_headers.iteritems():
            try:
                compiled = TALESEngine.compile(expression)
            except:
                log_error("Can't compile header expression at " + file_path)
                raise
            try:
                value = str(compiled(engine_context))
            except:
                log_error("Can't interpret header expression at " + file_path)
                raise
            request.headers_out[name] = value

        # return the content
        content = """<?xml version="1.1" encoding="utf-8" ?>\n""" + \
                  self.innerslot.encode("utf-8")
        return content

    def load_macros(self, *args):
        for name in args:
            file_path = os.path.join(os.path.dirname(self.file_path), name)
            try:
                content = file(file_path).read()
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

def get_script_globals():
    for frame_record in inspect.stack():
        candidate = frame_record[0].f_globals
        if "__publisher__" in candidate:
            return candidate
    else:
        raise LookupError("Could not find script globals.")


def get_publisher():
    return get_script_globals()["__publisher__"]
