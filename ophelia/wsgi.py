# Copyright (c) 2007-2011 Thomas Lotze
# See also LICENSE.txt

"""A WSGI application running Ophelia, and an optional wsgiref server running
this application.
"""

import sys

import zope.exceptions.exceptionformatter

import ophelia.request


class Application(object):
    """Ophelia's WSGI application.
    """

    def __call__(self, env, start_response):
        path = env["PATH_INFO"]
        if path.startswith('/'):
            path = path[1:]

        context = env.get("ophelia.context", {})

        request = ophelia.request.Request(
            path, env.pop("template_root"), env.pop("site"), **env)

        response_headers = {"Content-Type": "text/html"}
        body = None
        exc_info = None

        try:
            response_headers, body = request(**context)
        except ophelia.request.Redirect, e:
            status = "301 Moved permanently"
            text = ('The resource you were trying to access '
                    'has moved permanently to <a href="%(uri)s">%(uri)s</a>')
            response_headers["location"] = e.uri
        except ophelia.request.NotFound, e:
            status = "404 Not found"
            text = "The resource you were trying to access could not be found."
        except Exception, e:
            status = "500 Internal server error"
            exc_info = sys.exc_info()
            msg = "".join(zope.exceptions.exceptionformatter.format_exception(
                with_filenames=True, *exc_info))
            if isinstance(msg, unicode):
                msg = msg.encode('utf-8')
            text = "<pre>\n%s\n</pre>" % msg
            self.report_exception(env, msg)
        else:
            status = "200 OK"

        response_headers = [(key, str(value))
                            for key, value in response_headers.iteritems()]
        start_response(status, response_headers, exc_info)

        if env["REQUEST_METHOD"] == "GET":
            if body is None:
                body = self.error_body % {"status": status, "text": text}
            return [body]
        else:
            return []

    def report_exception(self, env, msg):
        sys.stderr.write(msg)

    error_body = """\
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
        """.replace(" ", "")


def wsgiref_server(config_file="", section="DEFAULT"):
    import optparse
    import ConfigParser
    import wsgiref.simple_server

    oparser = optparse.OptionParser()
    oparser.add_option("-c", dest="config_file", default=config_file)
    oparser.add_option("-s", dest="section", default=section)
    cmd_options, args = oparser.parse_args()

    config = ConfigParser.ConfigParser()
    config.read(cmd_options.config_file)
    options = dict((key.replace('-', '_'), value)
                   for key, value in config.items(cmd_options.section))

    app = Application()

    def configured_app(environ, start_response):
        environ.update(options)
        return app(environ, start_response)

    httpd = wsgiref.simple_server.make_server(
        options.pop("host"), int(options.pop("port")), configured_app)
    httpd.serve_forever()
