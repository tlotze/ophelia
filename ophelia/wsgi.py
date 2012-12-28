# Copyright (c) 2007-2012 Thomas Lotze
# See also LICENSE.txt

"""A WSGI application running Ophelia, and an optional wsgiref server running
this application.
"""

import ConfigParser
import logging
import ophelia.request
import ophelia.util
import os.path
import sys
import wsgiref.simple_server
import xsendfile
import zope.exceptions.exceptionformatter


logger = logging.getLogger('ophelia')
logger.addHandler(logging.StreamHandler())


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

            if (env.get('redirect_index') and parts[-1] == index_name):
                raise ophelia.request.Redirect(path=path[:-len(index_name)])

            fs_path = os.path.join(document_root, *parts)
            if os.path.isdir(fs_path):
                if not path.endswith('/'):
                    raise ophelia.request.Redirect(path=path + '/')

                path = '%s/%s' % (path.rstrip('/'), index_name)

            raise ophelia.request.NotFound(path)


class Application(object):
    """Ophelia's WSGI application.
    """

    def __init__(self, options=None):
        self.options = options or {}

    @classmethod
    def paste_app_factory(cls, global_conf, **local_conf):
        options = global_conf.copy()
        options.update(local_conf)
        options = dict((key.replace('-', '_'), value)
                       for key, value in options.items())
        return cls(options)

    def __call__(self, env, start_response):
        env = ophelia.util.Namespace(self.options, **env)
        path = env["PATH_INFO"].lstrip('/')
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
        except Exception, e:
            status = "500 Internal server error"
            exc_info = sys.exc_info()
            msg = "".join(zope.exceptions.exceptionformatter.format_exception(
                with_filenames=True, *exc_info))
            if isinstance(msg, unicode):
                msg = msg.encode('utf-8')
            logger.error(msg)
            if boolean(env.get('debug', False)):
                text = '<pre>\n%s\n</pre>' % msg
            else:
                text = 'Something went wrong with the server software.'
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


def boolean(value):
    if isinstance(value, basestring):
        return value.lower() in ("on", "true", "yes")
    else:
        return bool(value)


def paste_app_factory(global_conf, **local_conf):
    options = global_conf.copy()
    options.update(local_conf)
    options = dict((key.replace('-', '_'), value)
                   for key, value in options.items())
    return Application(options)


def wsgiref_server():
    config_file = sys.argv[1]

    config = ConfigParser.ConfigParser()
    config.read(config_file)
    options = dict((key.replace('-', '_'), value)
                   for key, value in config.items('DEFAULT'))

    configured_app = Application(options)

    httpd = wsgiref.simple_server.make_server(
        options.pop("host"), int(options.pop("port")), configured_app)
    httpd.serve_forever()
