from ophelia import oapi


class Navigation(oapi.Namespace):
    """Namespace for navigation info with methods for building menus.

    Registers with the TALES names as "nav".
    """

    def __init__(self, site_prefix, here):
        oapi.getScriptGlobals()["__nav__"] = self
        oapi.getTalesNames().nav = self

        self.site_prefix = site_prefix
        self.here = here
        self.absolute_uri = site_prefix + here

        self.breadcrumbs = []
        self.menu = {}

    def addBreadcrumb(self, title):
        uri = self.getUri()
        self.breadcrumbs.append((uri, title))

    def addMenu(self, entries):
        uri = self.getUri()
        self.menu[uri] = entries

    def conditionalLink(self, href, title):
        if href == self.here:
            return title
        else:
            return '<a href="%s">%s</a>' % (href, title)

    def displayBreadcrumbs(self, sep):
        bc = [self.conditionalLink(href, title)
              for href, title in self.breadcrumbs]
        return sep.join(bc)

    def displayMenu(self, uri=None, depth=3, root=None):
        lines = ["<dl>"]
        if root:
            lines.append("<dt>%s</dt>" % self.conditionalLink(uri, root))
        if uri.endswith('/'):
            uri = uri[:-1]

        def display(uri, deeper):
            for href, title in self.menu[uri]:
                lines.append("<dt>%s</dt>" %
                             self.conditionalLink(href, title))
                if deeper and href in self.menu:
                    lines.append("<dd><dl>")
                    display(href, deeper-1)
                    lines.append("</dl></dd>")
        display(uri or nav.site_prefix, depth-1)

        lines.append("</dl>")
        return '\n'.join(lines)

    def getUri(self):
        traversal = oapi.getTraversal()
        path = traversal.path
        root = traversal.root
        return path.replace(root, self.site_prefix, 1)


def getNav():
    return oapi.getScriptGlobals()["__nav__"]
