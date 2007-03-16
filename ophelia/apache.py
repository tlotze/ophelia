# Copyright (c) 2006-2007 Thomas Lotze
# See also LICENSE.txt

import os.path
import urlparse

from mod_python import apache, util

from ophelia.publisher import Publisher, NotFound, Redirect


# fix-up request handler
def fixuphandler(request):
    """Fix-up handler setting up the Ophelia content handler iff applicable.

    This handler has the Ophelia publisher traverse the requested URL and
    registers the generic content handler if and only if traversal is possible
    and the requested resource can actually be served by Ophelia. This is to
    prevent clobbering Apache's default generic handler chain if it's needed.

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
    site_path = urlparse.urlparse(site)[2]
    if not (request.uri == site_path[:-1] or
            request.uri.startswith(site_path)):
        return apache.DECLINED
    path = request.uri[len(site_path):]

    # get the content
    def log_error(msg):
        request.log_error(msg, apache.APLOG_ERR)

    publisher = Publisher(path, root, site, request, log_error)
    try:
        publisher.traverse()
    except NotFound:
        return apache.DECLINED
    except Redirect, e:
        request.handler = "mod_python"
        request.add_handler("PythonHandler", "ophelia.apache::redirect")
        request.__ophelia_location__ = e.uri
    else:
        request.handler = "mod_python"
        request.add_handler("PythonHandler", "ophelia.apache")
        request.__ophelia_publisher__ = publisher

    return apache.OK


# generic request handler
def redirect(request):
    """Generic Apache request handler doing an Ophelia traversal's redirect.

    Under certain circumstances, Apache writes to the request during the
    fix-up phase so calling modpython.util.redirect() in the fix-up handler
    may result in an IOError since headers have supposedly already been sent.
    The generic handler gets a new chance to do redirection, so we defer it
    until then, using this handler.
    """
    util.redirect(request, request.__ophelia_location__, permanent=True)


def handler(request):
    """Generic Apache request handler serving pages from Ophelia's publisher.

    This handler is called only after it is known that the requested resource
    can actually be served by Ophelia.

    may raise anything
    """
    publisher = request.__ophelia_publisher__
    try:
        response_headers, content = publisher.build()
    except Redirect, e:
        util.redirect(request, e.uri, permanent=True)

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
