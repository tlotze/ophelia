# Python
import os.path

# Zope
from zope.pagetemplate.pagetemplatefile import PageTemplateFile

# mod_python
from mod_python import apache, util


class StopTraversal(Exception):
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
    if os.path.isdir(template_path):
        template_path = os.path.join(template_path, "index.html")

    # create a stack of levels to walk
    dirname, basename = os.path.split(template_path)
    levels = [{
            "basename": basename,
            "path": template_path,
            "basepath": template_path,
            }]

    while basename:
        dirname_ = dirname
        if dirname == template_root:
            basename = ""
        else:
            dirname, basename = os.path.split(dirname_)
        levels.append({
                "basename": basename,
                "path": os.path.join(dirname_, ".pt"),
                "basepath": os.path.join(dirname_, ""),
                })

    # initialize the environment
    def date_meta():
        return "123"

    context = {
        "absolute_url": req.get_options()["SitePrefix"] + req.uri,
        "imprint": "/impressum.html",
        "date_meta": date_meta,
        }

    slots = {}

    locals = {
        "context": context,
        "slots": slots,
        "req": req,
        }

    # traverse the levels to manipulate the context
    templates = []

    try:
        while levels:
            info = levels.pop()
            templates.append(info)

            path = info["basepath"]
            ext = True
            while ext:
                pypath = path + ".py"
                if os.path.exists(pypath):
                    execfile(pypath, globals(), locals)
                path, ext = os.path.splitext(path)

        # fail if the innermost template doesn't exist
        if not os.path.exists(template_path):
            req.log_error("Template for %s not found at %s." %
                          (filename, template_path),
                          apache.APLOG_ERR)
            raise apache.SERVER_RETURN(apache.HTTP_NOT_FOUND)
    except StopTraversal:
        pass

    # evaluate the templates
    while templates:
        info = templates.pop()
        if os.path.exists(info["path"]):
            template = ContextPTF(info["path"])
            slots["main"] = template(
                context=context,
                req=req,
                slots=slots,
                )

    # deliver the page
    req.content_type = "text/html"
    req.write(slots["main"])
    return apache.OK
