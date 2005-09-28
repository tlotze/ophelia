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


class StopTraversal(Exception):
    """Flow control device for scripts to stop directory traversal."""
    pass

class ResetTraversal(Exception):
    """Flow control device for scripts to throw away out templates."""
    pass


class Namespace:
    """Objects which exist only to carry attributes"""
    pass


# script programmer's interface
spi = Namespace()
for item in [
    StopTraversal,
    ResetTraversal,
    Namespace,
    ]:
    setattr(spi, item.__name__, item)


# generic request handler
def handler(req):
    """generic request handler building pages from TAL templates

    never raises a 404 but declines instead
    may raise anything else

    The intent is for templates to take precedence, falling back on any static
    content gracefully.
    """
    req_options = req.get_options()

    # is this for us?
    filename = os.path.abspath(req.filename)
    doc_root = os.path.abspath(req_options.get("DocumentRoot") or
                               req.document_root())
    if not filename.startswith(doc_root):
        return apache.DECLINED

    # determine the template path
    template_root = os.path.abspath(req_options["TemplateRoot"])
    template_path = filename.replace(doc_root, template_root, 1)

    # create a stack of levels to walk
    path = template_path
    tail = ()
    levels = [(path, tail)]
    while path != template_root:
        path, next = os.path.split(path)
        tail = (next, ) + tail
        levels.insert(0, (path, tail))

    # initialize the environment
    context = Namespace()
    site_prefix = req_options["SitePrefix"]
    context.site_prefix = site_prefix
    context.absolute_url = site_prefix + req.uri

    slots = Namespace()
    macros = {}

    # traverse the levels
    script_globals = {}
    script_globals.update(globals())
    script_globals.update({
            "apache": apache,
            "spi": spi,
            "context": context,
            "req": req,
            })

    template_levels = []

    for path, tail in levels:
        # some path house-keeping
        if not os.path.exists(path):
            return apache.DECLINED
        elif os.path.isdir(path):
            pypath = os.path.join(path, "py")
            ptpath = os.path.join(path, "pt")
            if not levels:
                levels.append(os.path.join(path, "index.html")) 
        else:
            pypath = path + ".py"
            ptpath = path
        template_levels.append(ptpath)

        # manipulate the context
        if os.path.exists(pypath):
            spi.path = path
            spi.tail = tail
            try:
                execfile(pypath, script_globals)
            except apache.SERVER_RETURN, e:
                if e[0] is apache.HTTP_NOT_FOUND:
                    return apache.DECLINED
                else:
                    raise
            except ResetTraversal:
                del template_levels[:-1]
            except StopTraversal:
                break

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
                req.log_error("%s: can't compile template %s." %
                              (filename, ptpath),
                              apache.APLOG_ERR)
                raise

            program, _macros = parser.getCode()
            templates.append((path, program))
            macros.update(_macros)

    # interpret the templates
    engine_ns = {
        "apache": apache,
        "req": req,
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
            req.log_error("%s: can't interpret template at %s." %
                          (filename, path),
                          apache.APLOG_ERR)
            raise
        else:
            slots.inner = out.getvalue()

    # deliver the page
    req.content_type = "text/html; charset=utf-8"
    req.write(slots.inner.encode("utf-8"))
    return apache.OK
