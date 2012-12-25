# Copyright (c) 2007-2012 Thomas Lotze
# See also LICENSE.txt

import ophelia.wsgi
import os.path
import pkg_resources
import unittest
import webtest


FIXTURES = pkg_resources.resource_filename('ophelia', 'tests/fixtures')


def fixture(*parts):
    return os.path.join(FIXTURES, *parts)


class BasicApplicationTest(unittest.TestCase):

    def setUp(self):
        self.app = webtest.TestApp(
            ophelia.wsgi.Application(),
            extra_environ={
                'site': 'http://localhost/',
                'template_root': fixture('templates'),
                'document_root': fixture('documents'),
                })

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
