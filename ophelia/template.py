import re, string

XML_START = re.compile("^\s*<\?xml\s*", re.MULTILINE)
XML_END = re.compile("\s*\?>\s*$", re.MULTILINE)
CODING_PATTERN = re.compile("coding[=:]\s*\"?\s*([-\w.]+)\s*\"?")

def split(content, traversal):
    """split file content into Python script and template

    content: str
    traversal: traversal namespace from script_globals

    returns (unicode, unicode): Python script and template

    may raise ValueError if <?xml ... ?> is not closed
    """
    template_encoding = getattr(traversal, "template_encoding", "ascii")
    parts = XML_START.split(content, 1)
    if len(parts) == 1:
        script, template = "", content
    else:
        script = parts[0]
        xml_declaration, template = XML_END.split(parts[1], 1)
        coding_match = CODING_PATTERN.search(xml_declaration)
        if coding_match:
            template_encoding = coding_match.group(1)
            if type(template_encoding) == tuple:
                template_encoding = template_encoding[0]

    template = template.decode(template_encoding)

    script_encoding = getattr(traversal, "script_encoding", "ascii")
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
