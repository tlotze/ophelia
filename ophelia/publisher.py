# Python
import os.path
from StringIO import StringIO
import re

# Zope
from zope.tales.engine import Engine as TALESEngine
from zope.tal.htmltalparser import HTMLTALParser
from zope.tal.talgenerator import TALGenerator
from zope.tal.talinterpreter import TALInterpreter

# mod_python
from mod_python import apache


########################
# exceptions and classes

class StopTraversal(Exception):
    """Flow control device for scripts to stop directory traversal."""

    content = "" # str to use instead, interpreted as a template

    def __init__(self, content=None, use_template=False):
        self.content = content
        self.use_template = use_template


class Namespace(object):
    """Objects which exist only to carry attributes"""
    pass


class _ScriptGlobals(dict):
    """Global variable dict for script calls."""
    pass


###########
# publisher

def publish(path, root, request):
    """Ophelia's publisher building web pages from TAL page templates

    returns unicode, page content

    may raise anything
    """
    # create a list of path elements to walk
    tail = []
    while path != root:
        path, next = os.path.split(path)
        tail.insert(0, next)

    # initialize the environment
    context = Namespace()
    traversal = Namespace()

    script_globals = _ScriptGlobals()
    script_globals.update({
            "globals": lambda: script_globals,
            "context": context,
            "request": request,
            "traversal": traversal,
            })

    traversal.tail = tail
    traversal.stack = stack = []
    traversal.macros = Namespace()

    # traverse the levels
    while True:
        # some path house-keeping
        if not os.path.exists(path):
            raise apache.SERVER_RETURN(apache.DECLINED)
        elif os.path.isdir(path):
            file_path = os.path.join(path, "__init__")
            if not os.path.exists(file_path):
                file_path = None
            have_dir = True
        else:
            file_path = path
            have_dir = False

        # get script and template
        if file_path:
            script, template = scriptAndTemplate(file(file_path).read())
        else:
            script = None
            template = None

        # manipulate the context
        if script:
            traversal.path = path
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
                request.log_error("Can't compile template at " + file_path,
                                  apache.APLOG_ERR)
                raise

            program, macros = parser.getCode()
            stack.append((program, file_path))
            traversal.macros.__dict__.update(macros)

        # prepare the next traversal step, if any
        if tail:
            next = tail.pop(0)
        elif have_dir:
            next = "index.html"
        else:
            break
        path = os.path.join(path, next)

    # interpret the templates
    engine_ns = {
        "context": context,
        "macros": macros,
        "innerslot": lambda: traversal.innerslot,
        }
    engine_ns.update(TALESEngine.getBaseNames())
    engine_context = TALESEngine.getContext(engine_ns)
    out = StringIO(u"")

    while stack:
        program, file_path = stack.pop()
        out.truncate(0)
        try:
            TALInterpreter(program, macros, engine_context, out,
                           strictinsert=False)()
        except:
            request.log_error("Can't interpret template at " + file_path,
                              apache.APLOG_ERR)
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
