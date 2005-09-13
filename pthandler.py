# Python
import os.path

# Zope
from zope.pagetemplate.pagetemplatefile import PageTemplateFile

# mod_python
from mod_python import apache, util


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
            }]

    while dirname != template_root:
        dirname_ = dirname
        dirname, basename = os.path.split(dirname_)
        levels.append({
                "basename": basename,
                "path": os.path.join(dirname, ".pt"),
                })

    # initialize the context
    def date_meta():
        return "123"

    context = {
        "absolute_url": req.get_options()["SitePrefix"] + req.uri,
        "imprint": "/impressum.html",
        "date_meta": date_meta,
        }

    slots = {}

    # walk the levels to manipulate the context
    levels.reverse()
    templates = levels

    # fail if the innermost template doesn't exist
    if not os.path.exists(template_path):
        req.log_error("Template for %s not found at %s." %
                      (filename, template_path),
                      apache.APLOG_ERR)
        raise apache.SERVER_RETURN(apache.HTTP_NOT_FOUND)

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
