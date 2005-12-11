# Python
import os.path

# mod_python
from mod_python import apache

# project
from ophelia.publisher import publish


# generic request handler
def handler(request):
    """generic request handler building pages from TAL templates

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

    # determine the template path
    root = os.path.abspath(request_options["TemplateRoot"])
    path = filename.replace(doc_root, root, 1)

    # get the content
    content = publish(path, root, request)

    # deliver the page
    request.content_type = "text/html; charset=utf-8"
    request.set_content_length(len(content))

    if request.header_only:
        request.write("")
    else:
        request.write(content)

    return apache.OK
