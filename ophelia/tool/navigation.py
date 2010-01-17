# Copyright (c) 2006-2010 Thomas Lotze
# See also LICENSE.txt

from urlparse import urljoin

import ophelia.request
import ophelia.util


class Navigation(object):
    """Stores navigation info, builds hierarchical and breadcrumb menus.
    """

    chapter = None
    chapter_title = None

    @property
    def current(self):
        return self.request.current

    def __init__(self, home=None):
        self.request = ophelia.request.get_request()

        self.site = self.request.site
        self.uri = self.site + self.request.path
        if home is None:
            self.home = self.site
        else:
            self.home = home

        self.breadcrumbs = {}
        self.menu = ophelia.util.Namespace()

        self.alt_lang_uris = {}

    def set_chapter(self, title):
        self.chapter = self.current
        self.chapter_title = title

    def add_menu(self, entries, root_title=None, root=None):
        root = urljoin(self.current, root)
        self.menu[root] = ophelia.util.Namespace(
            url=root,
            root_title=root_title,
            entry_pairs=[(urljoin(root, href), title)
                         for href, title in entries],
            entries=[dict(url=urljoin(root, href),
                          title=title) for href, title in entries],
            )

    def set_breadcrumb(self, title):
        self.breadcrumbs[self.current] = title

    def iter_breadcrumbs(self):
        menu = {}
        for uri in self.request.history:
            title = self.breadcrumbs.get(uri) or menu.get(uri)
            if title:
                yield (uri, title)
            menu = self.menu.get(uri, {})
            if menu:
                menu = dict(menu.entry_pairs)

    def conditional_link(self, href, title):
        if href == self.uri:
            return title
        else:
            return '<a href="%s" title="Nav: %s">%s</a>' % \
                   (href, title, title)

    def display_breadcrumbs(self, sep):
        bc = [self.conditional_link(href, title)
              for href, title in self.iter_breadcrumbs()]
        return sep.join(bc)

    def display_menu(self, depth=3, uri=None):
        lines = ["<dl>"]
        if uri is None:
            uri = self.home
        root_title = self.menu[uri].root_title
        if root_title:
            lines.append("<dt>%s</dt>" % self.conditional_link(
                    urljoin(self.uri, uri), root_title))

        def display(uri, deeper):
            for href, title in self.menu[uri].entry_pairs:
                if not title:
                    lines.append("</dl><dl>")
                    continue
                lines.append("<dt>%s</dt>" %
                             self.conditional_link(href, title))
                if deeper and href in self.menu:
                    lines.append("<dd><dl>")
                    display(href, deeper-1)
                    lines.append("</dl></dd>")
        display(uri, depth-1)

        lines.append("</dl>")
        return '\n'.join(lines)

    def alt_langs(self, **kwargs):
        for lang, path_seg in kwargs.iteritems():
            self.alt_lang_uris[lang] = urljoin(
                self.alt_lang_uris.get(lang, self.current),
                path_seg)
