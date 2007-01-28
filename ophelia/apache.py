# Python
import os.path
import urlparse

# mod_python
from mod_python import apache

# project
from ophelia.publisher import Publisher, NotFound, Redirect


# generic request handler
def handler(request):
    """generic Apache request handler serving pages from Ophelia's publisher

    never raises a 404 but declines instead
    may raise anything else

    The intent is for templates to take precedence, falling back on any static
    content gracefully.
    """
    request_options = request.get_options()

    root = os.path.abspath(request_options["TemplateRoot"])

    # The site URL should be something we can safely urljoin path parts to.
    site = request_options["Site"]
    if not site.endswith('/'):
        site += '/'

    # Determine the path to traverse by the requested URL to the site root
    # URL. We want to catch requests to the site root specified without a
    # trailing slash.
    site_path = urlparse.urlparse(site)[2][:-1]
    if not request.uri.startswith(site_path):
        return apache.DECLINED
    path = request.uri[len(site_path):]

    # get the content
    def log_error(msg):
        request.log_error(msg, apache.APLOG_ERR)

    publisher = Publisher(path, root, site, request, log_error)
    try:
        response_headers, content = publisher()
    except NotFound:
        return apache.DECLINED
    except Redirect, e:
        request.headers_out["Location"] = e.uri
        return apache.HTTP_MOVED_PERMANENTLY

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
