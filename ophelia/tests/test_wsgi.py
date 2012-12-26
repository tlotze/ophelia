# Copyright (c) 2012 Thomas Lotze
# See also LICENSE.txt

import logging
import ophelia.wsgi
import os.path
import pkg_resources
import webtest

try:
    import unittest2 as unittest
except ImportError:
    import unittest


FIXTURES = pkg_resources.resource_filename('ophelia', 'tests/fixtures')


def fixture(*parts):
    return os.path.join(FIXTURES, *parts)


class BasicApplicationTest(unittest.TestCase):

    def setUp(self):
        self.app = webtest.TestApp(ophelia.wsgi.Application({
                    'site': 'http://localhost/',
                    'template_root': fixture('templates'),
                    }))
        logger = logging.getLogger('ophelia')
        for handler in list(logger.handlers):
            if isinstance(handler, logging.StreamHandler):
                logger.removeHandler(handler)

    def test_smoke(self):
        r = self.app.get('/smoke.html', status=200)
        self.assertEqual(
            'text/html; charset=utf-8', r.headers['content-type'])
        self.assertIn('<p>bar</p>', r.body)

    def test_redirect(self):
        r = self.app.get('/redirect.html', status=301)
        self.assertEqual('http://localhost/smoke.html', r.headers['location'])
        self.assertEqual('text/html', r.headers['content-type'])
        self.assertIn('<a href="http://localhost/smoke.html">'
                      'http://localhost/smoke.html</a>', r.body)

    def test_debug_mode_is_off_by_default(self):
        r = self.app.get('/raise.html', status=500)
        self.assertNotIn('message', r.body)

    def test_debug_mode_switched_on(self):
        r = self.app.get(
            '/raise.html', status=500, extra_environ={'debug': 'on'})
        self.assertIn('message', r.body)


class OnDiskDocumentsTest(unittest.TestCase):

    def setUp(self):
        self.app = webtest.TestApp(ophelia.wsgi.Application({
                    'site': 'http://localhost/',
                    'template_root': fixture('templates'),
                    'document_root': fixture('documents'),
                    }))

    def test_smoke_document(self):
        r = self.app.get('/smoke-document.html', status=200)
        self.assertEqual('text/html', r.headers['content-type'])
        self.assertIn('<p tal:content="foo" />', r.body)

    def test_on_disk_default_index_name(self):
        r = self.app.get('/', status=200)
        self.assertIn('<p>Root index</p>', r.body)

    def test_redirect_on_disk_directory_without_trailing_slash(self):
        r = self.app.get('/folder', status=301)
        self.assertEqual('http://localhost/folder/', r.headers['location'])

    def test_no_redirect_on_disk_directory_with_index_name(self):
        r = self.app.get('/folder/index.html', status=200)
        self.assertIn('<p>Folder index</p>', r.body)

    def test_redirect_on_disk_directory_with_index_name(self):
        r = self.app.get('/folder/index.html',
                         extra_environ={'redirect_index': 'on'},
                         status=301)
        self.assertEqual('http://localhost/folder/', r.headers['location'])

    def test_on_disk_index_name_is_configurable(self):
        r = self.app.get('/',
                         extra_environ={'index_name': 'smoke-document.html'},
                         status=200)
        self.assertEqual('text/html', r.headers['content-type'])
        self.assertIn('<p tal:content="foo" />', r.body)

    def test_x_sendfile_header(self):
        r = self.app.get('/smoke-document.html',
                         extra_environ={'xsendfile': 'standard'},
                         status=200)
        self.assertEqual(fixture('documents', 'smoke-document.html'),
                         r.headers['x-sendfile'])
        self.assertEqual('', r.body)

    def test_x_accel_redirect_header(self):
        r = self.app.get('/smoke-document.html',
                         extra_environ={'xsendfile': 'nginx'},
                         status=200)
        self.assertEqual('/-internal-/smoke-document.html',
                         r.headers['x-accel-redirect'])
        self.assertEqual('', r.body)
