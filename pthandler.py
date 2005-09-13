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
        rval["context"] = options.get("context", {})
        rval["req"] = options.get("req", {})
        return rval


def handler(req):
    """generic request handler """
    # don't interfere with regular delivery (PHP will break, though)
    if os.path.exists(req.filename):
        return apache.DECLINED

    # analyze the file name
    doc_root = os.path.abspath(req.document_root())
    filename = os.path.abspath(req.filename)
    if not filename.startswith(doc_root):
        req.log_error("Requested file %s not in document root %s." %
                      (req.filename, req.document_root()),
                      apache.APLOG_ERR)
        raise apache.SERVER_RETURN(apache.HTTP_INTERNAL_SERVER_ERROR)

    template_root = os.path.abspath(req.get_options()["TemplateRoot"])
    basefile = filename.replace(doc_root, template_root, 1)
    if os.path.isdir(basefile):
        basefile = os.path.join(basefile, "index.html")
    if not os.path.exists(basefile):
        req.log_error("Template for %s not found at %s." %
                      (req.filename, basefile),
                      apache.APLOG_ERR)
        raise apache.SERVER_RETURN(apache.HTTP_NOT_FOUND)

    # set up the environment
    def date_meta():
        return "123"

    context = {
        "absolute_url": req.get_options()["SitePrefix"] + req.uri,
        "imprint": "/impressum.html",
        "date_meta": date_meta,
        }

    # evaluate the innermost template
    template = ContextPTF(basefile)
    context["main_slot"] = template(context=context, req=req)

    # evaluate all outer templates
    dirname = basefile
    while dirname != template_root:
        dirname, ignore = os.path.split(dirname)
        template_name = os.path.join(dirname, ".pt")
        if os.path.exists(template_name):
            template = ContextPTF(template_name)
            context["main_slot"] = template(context=context, req=req)

    # deliver the page
    req.content_type = "text/html"
    req.write(context["main_slot"])
    return apache.OK
