# Copyright (c) 2007 Thomas Lotze
# See also LICENSE.txt

"""A WSGI application running Ophelia, and an optional wsgiref server running
this application.
"""

import sys
import os.path

import zope.exceptions.exceptionformatter

import ophelia.request
from ophelia.util import Namespace


class Application(object):

    def __init__(self, options):
        self.options = options

    def __call__(self, environ, start_response):
        self.start_response = start_response

        self.env = env = Namespace(self.options)
        env.update(environ)

        path = env.PATH_INFO
        if path.startswith('/'):
            path = path[1:]

        request = ophelia.request.Request(
            path, env.template_root, env.site, env)

        try:
            response_headers, body = request()
        except ophelia.request.Redirect, e:
            return self.error_response(
                "301 Moved permanently",
                'The resource you were trying to access '
                'has moved permanently to <a href="%(uri)s">%(uri)s</a>',
                {"location": e.uri})
        except ophelia.request.NotFound, e:
            return self.error_response(
                "404 Not found",
                "The resource you were trying to access could not be found.")
        except Exception, e:
            exc_info = sys.exc_info()
            msg = "".join(zope.exceptions.exceptionformatter.format_exception(
                with_filenames=True, *exc_info))
            print msg
            return self.error_response(
                "500 Internal server error",
                "<pre>\n%s\n</pre>" % msg,
                exc_info=sys.exc_info())
        else:
            start_response("200 OK", response_headers.items())
            return [body]

    def error_response(self, status, text,
                       response_headers=None, exc_info=None):
        if response_headers is None:
            response_headers = {}
        response_headers.setdefault("Content-Type", "text/html")
        self.start_response(status, response_headers.items(), exc_info)

        if self.env.REQUEST_METHOD == "GET":
            return [ERROR_BODY % {"status": status, "text": text}]
        else:
            return []


ERROR_BODY = """\
<html>
  <head>
    <title>%(status)s</title>
  </head>
  <body>
    <h1>%(status)s</h1>
    <p>
      %(text)s
    </p>
  </body>
</html>
"""


def wsgiref_server():
    import optparse
    import ConfigParser
    import wsgiref.simple_server

    oparser = optparse.OptionParser()
    oparser.add_option("-c", dest="config_file")
    oparser.add_option("-s", dest="section", default="DEFAULT")
    cmd_options, args = oparser.parse_args()

    config = ConfigParser.ConfigParser()
    config.read(cmd_options.config_file)
    options = Namespace((key.replace('-', '_'), value)
                        for key, value in config.items(cmd_options.section))

    httpd = wsgiref.simple_server.make_server(
        options.host, int(options.port), Application(options))
    httpd.serve_forever()
