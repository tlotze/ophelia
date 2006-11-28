from urlparse import urljoin

import ophelia.publisher


class Navigation(object):
    """Stores navigation info, builds hierarchical and breadcrumb menus.
    """

    def __init__(self, home=None):
        self.publisher = ophelia.publisher.get_publisher()

        self.uri = self.uriFromSite(self.publisher.path)
        if home is None:
            self.home = self.uriFromSite("/")
        else:
            self.home = home

        self.breadcrumbs = {}
        self.menu = {}

        self.alt_langs = {}

    def addMenu(self, entries, root_title=None, root=None):
        self.menu[self.uriFromCurrent(root)] = (
            [(self.uriFromCurrent(href), title) for href, title in entries],
            root_title)

    def setBreadcrumb(self, title):
        self.breadcrumbs[self.uriFromCurrent()] = title

    def iterBreadcrumbs(self):
        menu = {}
        for path in self.publisher.history:
            uri = self.uriFromSite(path)
            title = self.breadcrumbs.get(uri) or menu.get(uri)
            if title:
                yield (uri, title)
            menu = self.menu.get(uri, {})
            if menu:
                menu = dict(menu[0])

    def conditionalLink(self, href, title):
        if href == self.uri:
            return title
        else:
            return '<a href="%s" title="Nav: %s">%s</a>' % \
                   (href, title, title)

    def displayBreadcrumbs(self, sep):
        bc = [self.conditionalLink(href, title)
              for href, title in self.iterBreadcrumbs()]
        return sep.join(bc)

    def displayMenu(self, depth=3, uri=None):
        lines = ["<dl>"]
        if uri is None:
            uri = self.home
        root_title = self.menu[uri][1]
        if root_title:
            lines.append("<dt>%s</dt>" % self.conditionalLink(
                    self.uriFromPage(uri), root_title))

        def display(uri, deeper):
            for href, title in self.menu[uri][0]:
                lines.append("<dt>%s</dt>" %
                             self.conditionalLink(href, title))
                if deeper and href in self.menu:
                    lines.append("<dd><dl>")
                    display(href, deeper-1)
                    lines.append("</dl></dd>")
        display(uri, depth-1)

        lines.append("</dl>")
        return '\n'.join(lines)

    def uriFromCurrent(self, path=None):
        uri = urljoin(self.publisher.site, self.publisher.current)
        if path is not None:
            uri = urljoin(uri, path)
        return canonicalize(uri)

    def uriFromSite(self, path):
        return canonicalize(urljoin(self.publisher.site, path))

    def uriFromHome(self, path):
        return canonicalize(urljoin(self.home, path))

    def uriFromPage(self, path):
        return canonicalize(urljoin(self.uri, path))

    def uriFromUri(self, uri, path):
        return canonicalize(urljoin(uri, path))

    def altLangs(self, **kwargs):
        for lang, path_seg in kwargs.iteritems():
            self.alt_langs[lang] = canonicalize(
                urljoin(self.alt_langs.get(lang, self.uriFromCurrent("")),
                        path_seg))


def canonicalize(uri):
    if uri.endswith("/index.html"):
        uri = uri[:-10]
    return uri
