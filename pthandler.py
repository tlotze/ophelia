# Python
import os.path

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
    """generic request handler

    never raises a 404 but declines instead
    may raise anything else

    The intent is for templates to take precedence, falling back on any static
    content gracefully.
    """
    # is this for us?
    filename = os.path.abspath(req.filename)
    doc_root = os.path.abspath(req.document_root())
    if not filename.startswith(doc_root):
        return apache.DECLINED

    # determine the template path
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

    script_globals = {}
    script_globals.update(globals())
    script_globals.update({
            "Namespace": Namespace,
            "StopTraversal": StopTraversal,
            "context": context,
            "req": req,
            "levels": levels,
            })

    templates = {}
    macros = {}

    # traverse the levels
    outer_template = "" # eek. must start out empty, used in boolean context

    while levels:
        path = levels.pop()

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

        # manipulate the context
        if os.path.exists(pypath):
            try:
                execfile(pypath, script_globals)
            except apache.SERVER_RETURN, e:
                if e[0] is apache.HTTP_NOT_FOUND:
                    return apache.DECLINED
                else:
                    raise
            except StopTraversal:
                del levels[:]

        # compile the templates
        if os.path.exists(ptpath):
            cur_template = outer_template + "_"
            generator = TALGenerator(TALESEngine, xml=False,
                                     source_file=ptpath)
            generator.inMacroDef = 1
            parser = HTMLTALParser(generator)

            try:
                if outer_template:
                    text = file(ptpath).read()
                    parser.parseString("""\
<metal:block use-macro="templates/%s">\
<metal:block fill-slot="inner">""" % outer_template + text + 
"""</metal:block></metal:block>""")
                else:
                    parser.parseFile(ptpath)
            except:
                req.log_error("%s: can't compile template %s." %
                              (filename, ptpath),
                              apache.APLOG_ERR)
                raise

            program, _macros = parser.getCode()
            templates[cur_template] = program
            macros.update(_macros)
            outer_template = cur_template

    # evaluate the last compiled program and deliver the page
    engine_ns = {
        "apache": apache,
        "req": req,
        "context": context,
        "macros": macros,
        "templates": templates,
        }
    engine_ns.update(TALESEngine.getBaseNames())
    engine_context = TALESEngine.getContext(engine_ns)

    req.content_type = "text/html"

    try:
        TALInterpreter(program, macros, engine_context, req,
                       strictinsert=False)()
    except:
        req.log_error("%s: can't interpret template." % filename,
                          apache.APLOG_ERR)
        raise

    return apache.OK
