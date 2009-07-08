# Copyright (c) 2006-2009 Thomas Lotze
# See also LICENSE.txt

try:
    from mod_python import apache, util
except:
    # Allow the sphinx autosummary extension to import this module.
    pass

import sys
import os.path
import urlparse

import zope.exceptions.exceptionformatter

from ophelia.request import Request, NotFound, Redirect
from ophelia.util import Namespace


# fix-up request handler
def fixuphandler(apache_request):
    """Fix-up handler setting up the Ophelia content handler iff applicable.

    This handler has the Ophelia request traverse the requested URL and
    registers the generic content handler if and only if traversal is possible
    and the requested resource can actually be served by Ophelia. This is to
    prevent clobbering Apache's default generic handler chain if it's needed.

    never raises a 404 but declines instead
    may raise anything else

    The intent is for templates to take precedence, falling back on any static
    content gracefully.
    """
    env = Namespace(apache_request.get_options())

    template_root = os.path.abspath(env.pop("template_root"))

    # The site URL should be something we can safely urljoin path parts to.
    site = env.pop("site")
    if not site.endswith('/'):
        site += '/'

    # Determine the path to traverse by the requested URL to the site root
    # URL. We want to catch requests to the site root specified without a
    # trailing slash.
    site_path = urlparse.urlparse(site)[2]
    if not (apache_request.uri == site_path[:-1] or
            apache_request.uri.startswith(site_path)):
        return apache.DECLINED
    path = apache_request.uri[len(site_path):]

    # Apache already maps multiple HTTP headers to a comma-separated single
    # header according to RfC 2068, section 4.2.
    env.update(apache.build_cgi_env(apache_request))
    env.setdefault('wsgi.input', InputStream(apache_request))
    env.apache_request = apache_request

    # Response headers may already have been set during earlier phases of
    # Apache request processing.
    env['ophelia.response_headers'] = Namespace(apache_request.headers_out)
    request = Request(path, template_root, site, **env)
    try:
        request.traverse()
    except NotFound:
        return apache.DECLINED
    except Redirect, e:
        apache_request.handler = "mod_python"
        apache_request.add_handler("PythonHandler",
                                   "ophelia.modpython::redirect")
        apache_request.__ophelia_location__ = e.uri
    except:
        report_exception(apache_request)
    else:
        apache_request.handler = "mod_python"
        apache_request.add_handler("PythonHandler", "ophelia.modpython")
        apache_request.__ophelia_request__ = request

    return apache.OK


# generic request handler
def redirect(apache_request):
    """Generic Apache request handler doing an Ophelia traversal's redirect.

    Under certain circumstances, Apache writes to the request during the
    fix-up phase so calling modpython.util.redirect() in the fix-up handler
    may result in an IOError since headers have supposedly already been sent.
    The generic handler gets a new chance to do redirection, so we defer it
    until then, using this handler.
    """
    util.redirect(apache_request, apache_request.__ophelia_location__,
                  permanent=True)


def handler(apache_request):
    """Generic Apache request handler serving pages from Ophelia's request.

    This handler is called only after it is known that the requested resource
    can actually be served by Ophelia.

    may raise anything
    """
    request = apache_request.__ophelia_request__
    try:
        response_headers, content = request.build()
    except Redirect, e:
        util.redirect(apache_request, e.uri, permanent=True)
    except:
        report_exception(apache_request)

    # deliver the page
    apache_request.content_type = request.compiled_headers["Content-Type"]
    apache_request.set_content_length(len(content))
    apache_request.headers_out.update(response_headers)

    if apache_request.header_only:
        apache_request.write("")
    else:
        apache_request.write(content)

    return apache.OK


# helpers
def report_exception(apache_request):
    exc_type, exc_value, traceback_info = sys.exc_info()

    if apache_request.get_config().get("PythonDebug") != "1":
        raise exc_value

    msg = zope.exceptions.exceptionformatter.format_exception(
        exc_type, exc_value, traceback_info, with_filenames=True)

    apache_request.status = apache.HTTP_INTERNAL_SERVER_ERROR
    apache_request.content_type = "text/plain"
    apache_request.write("".join(msg).encode("utf-8"))

    for entry in msg:
        for line in entry.splitlines():
            apache_request.log_error(line, apache.APLOG_ERR)

    raise apache.SERVER_RETURN(apache.DONE)


class InputStream(object):
    """Wrapper for the Apache request that implements the minimal API required
    of a WSGI-compliant input stream.
    """

    def __init__(self, apache_request):
        self.read = apache_request.read
        self.readline = apache_request.readline
        self.readlines = apache_request.readlines

    def __iter__(self):
        while True:
            line = self.readline()
            if not line:
                break
            yield line
