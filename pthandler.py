# Python
import os.path

# Zope
from zope.pagetemplate.pagetemplatefile import PageTemplateFile

# mod_python
from mod_python import apache


class StopTraversal(Exception):
    pass


class Context:
    """Objects which exist only to carry attributes"""

    pass


class ContextPTF(PageTemplateFile):
    """PageTemplateFile with a customized pt_getContext

    All items of a dict passed as context to the PT call are put in the
    top-level namespace.
    """

    def pt_getContext(self, args=(), options={}, **kw):
        rval = PageTemplateFile.pt_getContext(self, args, options)
        for key in ("context", "req", "slots"):
            rval[key] = options.pop(key, {})
        return rval


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
    context = Context()
    context.absolute_url = req.get_options()["SitePrefix"] + req.uri

    slots = {}

    script_globals = {}
    script_globals.update(globals())
    script_globals.update({
            "Context": Context,
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
                req.log_error("%s: template not found %s." % (filename, path),
                              apache.APLOG_ERR)
                raise apache.SERVER_RETURN(apache.HTTP_NOT_FOUND)
            elif os.path.isdir(path):
                pypath = os.path.join(path, ".py")
            else:
                pypath += ".py"
                found_file = True

            if os.path.exists(pypath):
                execfile(pypath, script_globals)

            if not levels and not found_file:
               levels.append(os.path.join(path, "index.html")) 
    except StopTraversal:
        pass

    # evaluate the templates
    while templates:
        path = templates.pop()

        if os.path.isdir(path):
            path = os.path.join(path, ".pt")

        if os.path.exists(path):
            template = ContextPTF(path)
            try:
                slots["main"] = template(
                    context=context,
                    req=req,
                    slots=slots,
                    )
            except Exception:
                req.log_error("%s: template at %s failed." % (filename, path),
                              apache.APLOG_ERR)
                raise

    # deliver the page
    req.content_type = "text/html"
    req.write(slots["main"])
    return apache.OK
