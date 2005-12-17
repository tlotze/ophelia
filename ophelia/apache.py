# Python
import os.path

# mod_python
from mod_python import apache

# project
from ophelia.publisher import publish, NotFound


# generic request handler
def handler(request):
    """generic Apache request handler serving pages from Ophelia's publisher

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

    # determine the template root and path
    root = os.path.abspath(request_options["TemplateRoot"])
    path = filename[len(doc_root):]

    # get the content
    def log_error(msg):
        request.log_error(msg, apache.APLOG_ERR)

    try:
        content = publish(path, root, request, log_error)
    except NotFound:
        return apache.DECLINED

    # deliver the page
    request.content_type = "text/html; charset=utf-8"
    request.set_content_length(len(content))

    if request.header_only:
        request.write("")
    else:
        request.write(content)

    return apache.OK
