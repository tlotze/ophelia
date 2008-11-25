# Copyright (c) 2007-2008 Thomas Lotze
# See also LICENSE.txt

"""A script entry point for dumping a page built by Ophelia to stdout.
"""

import sys
import optparse
import ConfigParser

import zope.exceptions.exceptionformatter

import ophelia.request


def dump(config_file="", section="DEFAULT"):
    oparser = optparse.OptionParser("usage: %prog [options] path")
    oparser.add_option("-c", dest="config_file", default=config_file)
    oparser.add_option("-s", dest="section", default=section)
    oparser.add_option("-v", dest="verbose",
                       action="store_true", default=False,
                       help="verbose, print response headers")
    cmd_options, args = oparser.parse_args()

    if len(args) != 1:
        sys.stderr.write("Exactly one path must be requested.")
        return 1
    path = args[0]

    config = ConfigParser.ConfigParser()
    config.read(cmd_options.config_file)
    env = dict((key.replace('-', '_'), value)
               for key, value in config.items(cmd_options.section))
    env.setdefault('wsgi.input', sys.stdin)

    if path.startswith('/'):
        path = path[1:]
    if '?' in path:
        path, env["QUERY_STRING"] = path.split('?', 1)

    request = ophelia.request.Request(
        path, env.pop("template_root"), env.pop("site"), **env)
    try:
        headers, body = request()
    except:
        msg = "".join(zope.exceptions.exceptionformatter.format_exception(
            with_filenames=True, *sys.exc_info()))
        sys.stderr.write(msg)
        return 1

    if cmd_options.verbose:
        sys.stdout.write(
            '\n'.join("%s: %s" % item for item in headers.items()) +
            "\n\n")
    sys.stdout.write(body)
