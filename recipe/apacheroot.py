#!/usr/bin/env python
#
# Copyright (c) 2007 Thomas Lotze
# See also LICENSE.txt

import os, os.path
import stat
import ConfigParser


CONFIGFILE = "apacheroot.cfg"


def relative_path(filename):
    return os.path.join(os.path.dirname(__file__), filename)


class ApacheRoot(object):
    """Recipe to create an Apache HTTP server root and apachectl script.
    """

    def __init__(self, buildout, name, options):
        self.buildout = buildout
        self.name = name
        self.options = options

        config_path = relative_path(CONFIGFILE)
        config = ConfigParser.ConfigParser()
        config.read(config_path)
        for key, value in config.items("defaults"):
            options.setdefault(key, value)

        parts = buildout["buildout"]["parts-directory"]
        location = os.path.join(parts, name)
        conf_path = os.path.join(location, options["conf-dir"], "httpd.conf")
        options.update({
            "location": location,
            "conf-path": conf_path,
            "serverroot": location,
            }) 

        base = buildout["buildout"]["directory"]
        options["htdocs"] = os.path.join(base, options["htdocs"])
        options["cgi-bin"] = os.path.join(base, options["cgi-bin"])

    def install(self):
        options = self.options
        location = options["location"]

        for sub in ("",
                    options["conf-dir"],
                    options["lock-dir"],
                    options["log-dir"],
                    options["runtime-dir"],
                    ):
            path = os.path.join(location, sub)
            if not os.path.exists(path):
                os.mkdir(path)
            else:
                assert os.path.isdir(path)

        conf_path = options["conf-path"]
        conf_in_path = relative_path("httpd.conf.in")
        open(conf_path, "w").write(open(conf_in_path).read() % options)

        bin_dir = self.buildout["buildout"]["bin-directory"]
        ctl_path = os.path.join(bin_dir, "apachectl")
        ctl_in_path = relative_path("apachectl.in")
        open(ctl_path, "w").write(open(ctl_in_path).read() % options)
        os.chmod(ctl_path, (os.stat(ctl_path).st_mode |
                            stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH))

        return [location,
                ]

    def update(self):
        pass
