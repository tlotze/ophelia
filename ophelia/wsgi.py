# Copyright (c) 2007-2012 Thomas Lotze
# See also LICENSE.txt

"""A WSGI application running Ophelia, and an optional wsgiref server running
this application.
"""

import ophelia.request
import os.path
import sys
import xsendfile
import zope.exceptions.exceptionformatter


class Request(ophelia.request.Request):

    @ophelia.request.push_request
    def __call__(self):
        try:
            return super(Request, self).__call__()
        except ophelia.request.NotFound:
            env = self.env
            document_root = env.get('document_root')
            if not document_root:
                raise

            path = env['PATH_INFO']
            parts = path.split('/')
            index_name = env.get('index_name', 'index.html')

            fs_path = os.path.join(document_root, *parts)
            if os.path.isdir(fs_path):
                path = '%s/%s' % (path.rstrip('/'), index_name)

            raise ophelia.request.NotFound(path)


class Application(object):
    """Ophelia's WSGI application.
    """

    def __call__(self, env, start_response):
        path = env["PATH_INFO"]
        if path.startswith('/'):
            path = path[1:]

        context = env.get("ophelia.context", {})

        request = Request(
            path, env.pop("template_root"), env.pop("site"), **env)

        response_headers = {"Content-Type": "text/html"}
        body = None
        exc_info = None

        try:
            try:
                response_headers, body = request(**context)
            except ophelia.request.NotFound, e:
                env['PATH_INFO'] = e.args[0]
                return self.sendfile(env, start_response)
        except ophelia.request.Redirect, e:
            status = "301 Moved permanently"
            text = ('The resource you were trying to access '
                    'has moved permanently to <a href="%(uri)s">%(uri)s</a>' %
                    dict(uri=e.uri))
            response_headers["location"] = e.uri
        except ophelia.request.NotFound, e:
            return self.sendfile(env, start_response)
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

    def sendfile(self, env, start_response):
        xsendfile_app = xsendfile.XSendfileApplication(
            env['document_root'], env.get('xsendfile', 'serve'))
        return xsendfile_app(env, start_response)

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
