# Python
import os.path
from StringIO import StringIO

# Zope
from zope.tales.engine import Engine as TALESEngine
from zope.tal.htmltalparser import HTMLTALParser
from zope.tal.talgenerator import TALGenerator
from zope.tal.talinterpreter import TALInterpreter

# Ophelia
import ophelia, ophelia.template


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


class _ScriptGlobals(dict):
    """Global variable dict for script calls."""
    pass


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
        macros = Namespace()
        traversal = Namespace()
        tales_names = Namespace()
        response_headers = {}

        script_globals = _ScriptGlobals({
                "log_error": log_error,
                "context": context,
                "macros": macros,
                "request": request,
                "traversal": traversal,
                "tales_names": tales_names,
                "response_headers": response_headers,
                })

        traversal.splitter = ophelia.template.Splitter(request)
        traversal.path = path
        traversal.root = root
        traversal.tail = tail
        traversal.stack = stack = []
        traversal.history = history = []

        tales_names.context = context
        tales_names.macros = macros

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
            script, template = traversal.splitter(file(file_path).read())

            # manipulate the context
            if script:
                traversal.file_path = file_path
                traversal.isdir = isdir
                traversal.current = current
                traversal.template = template
                try:
                    exec script in script_globals
                except StopTraversal, e:
                    if e.content is not None:
                        traversal.innerslot = e.content
                    if not e.use_template:
                        traversal.template = None
                    del tail[:]
                template = traversal.template

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

                program, macros_ = parser.getCode()
                stack.append((program, file_path))
                macros.update(macros_)

        # initialize the template environment
        engine_ns = Namespace(tales_names)
        engine_ns.innerslot = lambda: traversal.innerslot
        engine_ns.update(TALESEngine.getBaseNames())
        engine_context = TALESEngine.getContext(engine_ns)
        out = StringIO(u"")

        # interpret the templates
        while stack:
            program, file_path = stack.pop()
            out.truncate(0)
            try:
                TALInterpreter(program, macros, engine_context, out,
                               strictinsert=False)()
            except:
                log_error("Can't interpret template at " + file_path)
                raise
            else:
                traversal.innerslot = out.getvalue()

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
                  traversal.innerslot.encode("utf-8")
        return content
