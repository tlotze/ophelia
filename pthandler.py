# Python
import os.path
from StringIO import StringIO
import inspect

# Zope
from zope.tales.engine import Engine as TALESEngine
from zope.tal.htmltalparser import HTMLTALParser
from zope.tal.talgenerator import TALGenerator
from zope.tal.talinterpreter import TALInterpreter

# mod_python
from mod_python import apache


class StopTraversal(Exception):
    """Flow control device for scripts to stop directory traversal."""

    content = "" # str to use instead, interpreted as a template

    def __init__(self, content=None, use_template=False):
        self.content = content
        self.use_template = use_template


class Namespace(object):
    """Objects which exist only to carry attributes"""
    pass


class ScriptGlobals(dict):
    """Global variable dict for script calls."""
    pass


class SPI(object):
    """Basic script programmers' interface"""

    StopTraversal = StopTraversal
    Namespace = Namespace

    def context(self):
        return self._getScriptGlobals()["context"]
    context = property(context)

    def request(self):
        return self._getScriptGlobals()["request"]
    request = property(request)

    def trav_path(self):
        return self._getScriptGlobals()["trav_path"]
    trav_path = property(trav_path)

    def trav_tail(self):
        return self._getScriptGlobals()["trav_tail"]
    trav_tail = property(trav_tail)

    def discardOuterTemplates(self):
        templates = self._getScriptGlobals["__templates__"]
        del templates[:-1]

    def _getScriptGlobals(self):
        for frame_record in inspect.stack():
            candidate = frame_record[0].f_globals
            if type(candidate) == ScriptGlobals:
                return candidate
        else:
            raise LookupError("Could not find script globals.")
spi = SPI()


# generic request handler
def handler(request):
    """generic request handler building pages from TAL templates

    never raises a 404 but declines instead
    may raise anything else

    The intent is for templates to take precedence, falling back on any static
    content gracefully.
    """
    request_options = request.get_options()

    # is this for us?
    filename = os.path.abspath(request.filename)
    doc_root = os.path.abspath(request_options.get("DocumentRoot") or
                               request.document_root())
    if not filename.startswith(doc_root):
        return apache.DECLINED

    # determine the template path
    template_root = os.path.abspath(request_options["TemplateRoot"])
    template_path = filename.replace(doc_root, template_root, 1)

    # create a list of path elements to walk
    path = template_path
    tail = []
    while path != template_root:
        path, next = os.path.split(path)
        tail.insert(0, next)

    # initialize the environment
    context = Namespace()
    slots = Namespace()
    macros = {}

    # scripting environment
    script_globals = ScriptGlobals(globals())
    script_globals.update({
            "globals": lambda: script_globals,
            "apache": apache,
            "spi": spi,
            "context": context,
            "request": request,
            })

    # traverse the levels
    template_levels = []
    script_globals["__templates__"] = template_levels

    while True:
        # some path house-keeping
        if not os.path.exists(path):
            return apache.DECLINED
        elif os.path.isdir(path):
            pypath = os.path.join(path, "py")
            ptpath = os.path.join(path, "pt")
            have_dir = True
        else:
            pypath = path + ".py"
            ptpath = path
            have_dir = False
        template_levels.append(ptpath)

        # manipulate the context
        if os.path.exists(pypath):
            script_globals["trav_path"] = path
            script_globals["trav_tail"] = tuple(tail)
            try:
                execfile(pypath, script_globals)
            except apache.SERVER_RETURN, e:
                if e[0] is apache.HTTP_NOT_FOUND:
                    return apache.DECLINED
                else:
                    raise
            except StopTraversal, e:
                if not e.use_template:
                    del template_levels[-1]
                slots.inner = e.content
                break

        # prepare the next traversal step, if any
        if tail:
            next = tail.pop(0)
        elif have_dir:
            next = "index.html"
        else:
            break
        path = os.path.join(path, next)

    # compile the templates
    templates = []

    for ptpath in template_levels:
        if os.path.exists(ptpath):
            generator = TALGenerator(TALESEngine, xml=False,
                                     source_file=ptpath)
            parser = HTMLTALParser(generator)

            try:
                parser.parseString(unicode(file(ptpath).read(), "utf-8"))
            except:
                request.log_error("%s: can't compile template %s." %
                                  (filename, ptpath),
                                  apache.APLOG_ERR)
                raise

            program, _macros = parser.getCode()
            templates.append((path, program))
            macros.update(_macros)

    # interpret the templates
    engine_ns = {
        "apache": apache,
        "request": request,
        "context": context,
        "slots": slots,
        "macros": macros,
        }
    engine_ns.update(TALESEngine.getBaseNames())
    engine_context = TALESEngine.getContext(engine_ns)
    out = StringIO(u"")

    while templates:
        path, program = templates.pop()
        out.truncate(0)
        try:
            TALInterpreter(program, macros, engine_context, out,
                           strictinsert=False)()
        except:
            request.log_error("%s: can't interpret template at %s." %
                              (filename, path),
                              apache.APLOG_ERR)
            raise
        else:
            slots.inner = out.getvalue()

    # deliver the page
    content = slots.inner.encode("utf-8")

    request.content_type = "text/html; charset=utf-8"
    request.set_content_length(len(content))

    if request.header_only:
        request.write("")
    else:
        request.write(content)

    return apache.OK
