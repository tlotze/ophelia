from urlparse import urljoin

from ophelia import oapi


class Navigation(object):
    """Stores navigation info, builds hierarchical and breadcrumb menus.

    Registers with the TALES names.
    """

    def __init__(self, site_prefix, home=None, tales_name="nav"):
        setattr(oapi.getTalesNames(), tales_name, self)

        self.site_prefix = site_prefix
        self.uri = self.uriFromSite(oapi.getTraversal().path)
        if home is None:
            self.home = self.uriFromSite("/")
        else:
            self.home = home

        self.breadcrumbs = []
        self.menu = {}

    def clearBreadcrumbs(self):
        del self.breadcrumbs[:]

    def addBreadcrumb(self, title):
        self.breadcrumbs.append((self.uriFromCurrent(), title))

    def addMenu(self, entries, root_title=None, root=None):
        self.menu[self.uriFromCurrent(root)] = (
            [(self.uriFromCurrent(href), title) for href, title in entries],
            root_title)

    def conditionalLink(self, href, title):
        if href == self.uri:
            return title
        else:
            return '<a href="%s">%s</a>' % (href, title)

    def displayBreadcrumbs(self, sep):
        bc = [self.conditionalLink(href, title)
              for href, title in self.breadcrumbs]
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
        traversal = oapi.getTraversal()
        uri = urljoin(self.site_prefix, traversal.current)
        if traversal.isdir:
            uri += "/"
        if path is not None:
            uri = urljoin(uri, path)
        return canonicalize(uri)

    def uriFromSite(self, path):
        return canonicalize(urljoin(self.site_prefix, path))

    def uriFromHome(self, path):
        return canonicalize(urljoin(self.home, path))

    def uriFromPage(self, path):
        return canonicalize(urljoin(self.uri, path))


def canonicalize(uri):
    if uri.endswith("/index.html"):
        uri = uri[:-10]
    return uri
