from urlparse import urljoin

import ophelia.publisher


class Navigation(object):
    """Stores navigation info, builds hierarchical and breadcrumb menus.
    """

    chapter = None
    chapter_title = None

    def __init__(self, home=None):
        self.publisher = ophelia.publisher.get_publisher()

        self.uri = self.uri_from_site(self.publisher.path)
        if home is None:
            self.home = self.uri_from_site("/")
        else:
            self.home = home

        self.breadcrumbs = {}
        self.menu = {}

        self.alt_langs = {}

    def set_chapter(self, title):
        self.chapter = self.uri_from_current()
        self.chapter_title = title

    def add_menu(self, entries, root_title=None, root=None):
        self.menu[self.uri_from_current(root)] = (
            [(self.uri_from_current(href), title) for href, title in entries],
            root_title)

    def set_breadcrumb(self, title):
        self.breadcrumbs[self.uri_from_current()] = title

    def iter_breadcrumbs(self):
        menu = {}
        for path in self.publisher.history:
            uri = self.uri_from_site(path)
            title = self.breadcrumbs.get(uri) or menu.get(uri)
            if title:
                yield (uri, title)
            menu = self.menu.get(uri, {})
            if menu:
                menu = dict(menu[0])

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
        root_title = self.menu[uri][1]
        if root_title:
            lines.append("<dt>%s</dt>" % self.conditional_link(
                    self.uri_from_page(uri), root_title))

        def display(uri, deeper):
            for href, title in self.menu[uri][0]:
                lines.append("<dt>%s</dt>" %
                             self.conditional_link(href, title))
                if deeper and href in self.menu:
                    lines.append("<dd><dl>")
                    display(href, deeper-1)
                    lines.append("</dl></dd>")
        display(uri, depth-1)

        lines.append("</dl>")
        return '\n'.join(lines)

    def uri_from_current(self, path=None):
        uri = urljoin(self.publisher.site, self.publisher.current)
        if path is not None:
            uri = urljoin(uri, path)
        return uri

    def uri_from_site(self, path):
        return urljoin(self.publisher.site, path)

    def uri_from_home(self, path):
        return urljoin(self.home, path)

    def uri_from_page(self, path):
        return urljoin(self.uri, path)

    def uri_from_uri(self, uri, path):
        return urljoin(uri, path)

    def alt_langs(self, **kwargs):
        for lang, path_seg in kwargs.iteritems():
            self.alt_langs[lang] = urljoin(
                self.alt_langs.get(lang, self.uri_from_current("")), path_seg)
