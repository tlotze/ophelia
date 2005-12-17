# Python
import os.path
from StringIO import StringIO
import re

# Zope
from zope.tales.engine import Engine as TALESEngine
from zope.tal.htmltalparser import HTMLTALParser
from zope.tal.talgenerator import TALGenerator
from zope.tal.talinterpreter import TALInterpreter


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


class Namespace(object):
    """Objects which exist only to carry attributes"""
    pass


class _ScriptGlobals(dict):
    """Global variable dict for script calls."""
    pass


###########
# publisher

def publish(path, root, request, log_error):
    """Ophelia's publisher building web pages from TAL page templates

    path: str, path to traverse from the template root, must start with '/',
               end with '/' if directory, elements are separated by '/'
    root: str, absolute file system path to the template root,
               mustn't end with '/'
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

    script_globals = _ScriptGlobals()
    script_globals.update({
            "globals": lambda: script_globals,
            "context": context,
            "macros": macros,
            "request": request,
            "traversal": traversal,
            "tales_names": tales_names,
            })

    traversal.path = path
    traversal.root = root
    traversal.tail = tail
    traversal.stack = stack = []

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
        if isdir:
            file_path = os.path.join(file_path, "__init__")
            if not os.path.exists(file_path):
                continue

        # get script and template
        script, template = scriptAndTemplate(file(file_path).read())

        # manipulate the context
        if script:
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
            macros.__dict__.update(macros_)

    # initialize the template environment
    engine_ns = tales_names.__dict__
    engine_ns["innerslot"] = lambda: traversal.innerslot
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

    # return the content
    content = traversal.innerslot.encode("utf-8")
    return content


CODING_PATTERN = re.compile("coding[=:]\s*([-\w.]+)")

def scriptAndTemplate(content):
    """split file content into Python script and template

    content: str

    returns (unicode, unicode): Python script and template

    may raise UnicodeDecodeError
    may raise IndexError if <?ophelia ... ?> is not closed
    """

    coding = "iso-8859-15"
    script = ""
    template = content

    if content.startswith("<?ophelia"):
        lines = content.splitlines(True)

        coding_declaration = lines.pop(0)
        if not coding_declaration.rstrip().endswith("?>"):
            script_lines = []
            next = lines.pop(0)
            while next.rstrip() != "?>":
                script_lines.append(next)
                next = lines.pop(0)
            script = "".join(script_lines)
        template = "".join(lines)

        coding_match = CODING_PATTERN.search(coding_declaration)
        if coding_match:
            coding = coding_match.group(1)
            if type(coding) == tuple:
                coding = coding[0]

    return script.decode(coding), template.decode(coding)
