import os, os.path


class ApacheRoot(object):

    def __init__(self, buildout, name, options):
        self.buildout = buildout
        self.name = name
        self.options = options

        options["location"] = os.path.join(
            buildout["buildout"]["parts-directory"], name)

    def install(self):
        location = self.options["location"]
        os.mkdir(location)

        return [location,
                ]

    def update(self):
        pass
