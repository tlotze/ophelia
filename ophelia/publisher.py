# Python
import os.path
from StringIO import StringIO

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
    slots = Namespace()
    macros = {}

    # scripting environment
    script_globals = _ScriptGlobals(globals())
    from ophelia import oapi
    script_globals.update({
            "globals": lambda: script_globals,
            "apache": apache,
            "oapi": oapi,
            "context": context,
            "request": request,
            })

    # traverse the levels
    template_levels = []
    script_globals["__templates__"] = template_levels

    while True:
        # some path house-keeping
        if not os.path.exists(path):
            raise apache.SERVER_RETURN(apache.DECLINED)
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

    # return the content
    content = slots.inner.encode("utf-8")
    return content
