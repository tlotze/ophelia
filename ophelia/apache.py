# Python
import os.path

# mod_python
from mod_python import apache

# project
from ophelia.publisher import Publisher, NotFound


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
    if doc_root.endswith('/'):
        doc_root = doc_root[:-1]
    if not filename.startswith(doc_root+'/'):
        return apache.DECLINED

    # determine the template root and path, and the site URL
    root = os.path.abspath(request_options["TemplateRoot"])
    path = filename[len(doc_root):]
    site = request_options["Site"]

    # get the content
    def log_error(msg):
        request.log_error(msg, apache.APLOG_ERR)

    publisher = Publisher(path, root, site, request, log_error)
    try:
        response_headers, content = publisher()
    except NotFound:
        return apache.DECLINED

    # deliver the page
    request.content_type = "text/html; charset=%s" % \
                           publisher.response_encoding
    request.set_content_length(len(content))
    request.headers_out.update(response_headers)

    if request.header_only:
        request.write("")
    else:
        request.write(content)

    return apache.OK
