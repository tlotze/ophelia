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
                "basepath": os.path.join(dirname_, ""),
                })

    # initialize the environment
    context = {
        "absolute_url": req.get_options()["SitePrefix"] + req.uri,
        }

    slots = {}

    script_globals = {}
    script_globals.update(globals())
    script_globals.update({
            "context": context,
            "req": req,
            "slots": slots,
            })

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
                    execfile(pypath, script_globals)
                path, ext = os.path.splitext(path)
    except StopTraversal:
        pass

    # evaluate the templates
    while templates:
        info = templates.pop()

        path = info["basepath"]
        ext = True
        while ext:
            ptpath = path + ".pt"
            if os.path.exists(ptpath):
                template = ContextPTF(ptpath)
                try:
                    slots["main"] = template(
                        context=context,
                        req=req,
                        slots=slots,
                        )
                except PTRunTimeError:
                    # resource wasn't found if main slot wasn't filled in time
                    req.log_error("%s: template at %s failed." % 
                                  (filename, ptpath),
                                  apache.APLOG_ERR)
                    raise apache.SERVER_RETURN(apache.HTTP_NOT_FOUND)

            path, ext = os.path.splitext(path)

    # deliver the page
    req.content_type = "text/html"
    req.write(slots["main"])
    return apache.OK
