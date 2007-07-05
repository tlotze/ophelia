# Copyright (c) 2006-2007 Thomas Lotze
# See also LICENSE.txt

import re

import zope.interface

import ophelia.interfaces


XML_START = re.compile("^\s*<\?xml\s*", re.MULTILINE)
XML_END = re.compile("\s*\?>\s*$", re.MULTILINE)
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
        template_encoding = self.template_encoding
        parts = XML_START.split(content, 1)
        if len(parts) == 1:
            script, template = "", content
        else:
            script = parts[0]
            try:
                xml_declaration, template = XML_END.split(parts[1], 1)
            except ValueError:
                raise ValueError("Broken <?xml ?> declaration.")
            coding_match = CODING_PATTERN.search(xml_declaration)
            if coding_match:
                template_encoding = coding_match.group(1)
                if type(template_encoding) == tuple:
                    template_encoding = template_encoding[0]

        template = template.decode(template_encoding)

        script_encoding = self.script_encoding
        script = script.strip()
        if script.startswith("#"):
            lines = script.splitlines(True)
            coding_match = CODING_PATTERN.search(lines[0])
            if coding_match:
                script_encoding = coding_match.group(1)
                if type(script_encoding) == tuple:
                    script_encoding = script_encoding[0]
                del lines[0]
            script = "".join(lines)

        script = script.decode(script_encoding)

        return script, template
