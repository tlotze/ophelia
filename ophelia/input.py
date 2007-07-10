# Copyright (c) 2006-2007 Thomas Lotze
# See also LICENSE.txt

import re

import zope.interface

import ophelia.interfaces


XML_DECLARATION = re.compile("<\?xml([^<>]*)\?>")
CODING_PATTERN = re.compile("coding[=:]\s*\"?\s*([-\w.]+)\s*\"?")


class Splitter(object):
    """Splitter decomposing a file into Python script and template.

    Instantiate as Splitter(**options).
    """

    zope.interface.implements(ophelia.interfaces.ISplitterAPI)

    script_encoding = None
    template_encoding = None

    def __init__(self, **options):
        self.script_encoding = options.get("script_encoding", "ascii")
        self.template_encoding = options.get("template_encoding", "ascii")

    def __call__(self, content):
        """Split file content into Python script and template.

        content: str

        returns (unicode, unicode): Python script and template

        may raise ValueError if <?xml ... ?> is not closed
        """
        parts = XML_DECLARATION.split(content, 1)
        if len(parts) == 1:
            script, xml_options, template = "", "", content
        else:
            script, xml_options, template = parts

        template_encoding = self.template_encoding
        coding_match = CODING_PATTERN.search(xml_options)
        if coding_match:
            template_encoding = coding_match.group(1)

        template = template.decode(template_encoding)

        script_encoding = self.script_encoding
        script = script.strip()
        if script.startswith("#"):
            lines = script.splitlines(True)
            coding_match = CODING_PATTERN.search(lines[0])
            if coding_match:
                script_encoding = coding_match.group(1)
                del lines[0]
            script = "".join(lines)

        script = script.decode(script_encoding)

        return script, template
