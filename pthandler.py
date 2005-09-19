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
    pass


class Namespace:
    """Objects which exist only to carry attributes"""

    pass


def handler(req):
    """generic request handler """
    # don't interfere with regular delivery (PHP will break, though)
    if os.path.exists(req.filename):
        return apache.DECLINED

    # determine the template path
    doc_root = os.path.abspath(req.document_root())
    filename = os.path.abspath(req.filename)
    if not filename.startswith(doc_root):
        req.log_error("Requested file %s not in document root %s." %
                      (req.filename, req.document_root()),
                      apache.APLOG_ERR)
        raise apache.SERVER_RETURN(apache.HTTP_INTERNAL_SERVER_ERROR)

    template_root = os.path.abspath(req.get_options()["TemplateRoot"])
    template_path = filename.replace(doc_root, template_root, 1)

    # create a stack of levels to walk
    path = template_path
    levels = [path]
    while path != template_root:
        path, ignored = os.path.split(path)
        levels.append(path)

    # initialize the environment
    context = Namespace()
    context.absolute_url = req.get_options()["SitePrefix"] + req.uri

    slots = Namespace()

    script_globals = {}
    script_globals.update(globals())
    script_globals.update({
            "Namespace": Namespace,
            "context": context,
            "req": req,
            "levels": levels,
            "slots": slots,
            })

    # traverse the levels to manipulate the context
    templates = []
    found_file = False

    try:
        while levels:
            path = levels.pop()
            templates.append(path)

            if not os.path.exists(path):
                req.log_error("%s template not found: %s." % (filename, path),
                              apache.APLOG_ERR)
                raise apache.SERVER_RETURN(apache.HTTP_NOT_FOUND)
            elif os.path.isdir(path):
                pypath = os.path.join(path, ".py")
            else:
                pypath = path + ".py"
                found_file = True

            if os.path.exists(pypath):
                execfile(pypath, script_globals)

            if not levels and not found_file:
               levels.append(os.path.join(path, "index.html")) 
    except StopTraversal:
        pass

    # evaluate the templates
    engine_ns = {
        "req": req,
        "context": context,
        "slots": slots,
        }
    engine_ns.update(TALESEngine.getBaseNames())
    engine_context = TALESEngine.getContext(engine_ns)
    out = StringIO(u"")

    while templates:
        path = templates.pop()

        if os.path.isdir(path):
            path = os.path.join(path, ".pt")

        if os.path.exists(path):
            out.truncate(0)
            try:
                generator = TALGenerator(TALESEngine, xml=False,
                                         source_file=path)
                parser = HTMLTALParser(generator)
                parser.parseFile(path)
                program, macro_programs = parser.getCode()
                TALInterpreter(program, macro_programs, engine_context, out,
                               strictinsert=False)()
            except:
                req.log_error("%s: template %s failed." % (filename, path),
                              apache.APLOG_ERR)
                raise
            else:
                slots.main = out.getvalue()

    # deliver the page
    req.content_type = "text/html"
    req.write(slots.main)
    return apache.OK
