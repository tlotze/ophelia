# Copyright (c) 2007 Thomas Lotze
# See also LICENSE.txt

import zope.pagetemplate.pagetemplate


class PageTemplateTracebackSupplement(object):

    def __init__(self, template):
        self.template = template
        self.source_url = template.file_path
        self.warnings = template._v_errors

    def getInfo(self):
        if len(self.template._v_errors) != 2:
            return
        fragments = self.template._v_errors[1].rsplit(',')[-2:]
        if len(fragments) != 2:
            return
        try:
            line = int(fragments[0].split()[-1])
        except ValueError:
            return
        try:
            column = int(fragments[1].split()[-1])
        except ValueError:
            return
        if line >= 5:
            lower = line - 5
            err_line = 5
        else:
            lower = 0
            err_line = line
        text_lines = self.template._text.rstrip().splitlines()[lower:line + 5]
        text_lines = ["%4d: %s" % (lower + i + 1, line)
                      for i, line in enumerate(text_lines)]
        text_lines.insert(err_line, "   -> %s^" % (' ' * column))
        return '\n'.join(text_lines)


class PageTemplate(zope.pagetemplate.pagetemplate.PageTemplate):
    """Page templates with supplemented tracebacks and source tracking.

    Call parameters: the namespace of file context variables
    """

    file_path = None

    def __init__(self, text, file_path=None):
        super(PageTemplate, self).__init__()
        self.file_path = file_path
        self.write(text)

    def _cook(self):
        __traceback_supplement__ = (PageTemplateTracebackSupplement, self)
        super(PageTemplate, self)._cook()
        if self._v_errors:
            raise ValueError("There were errors in the page template text.")

    def pt_getContext(self, args=(), options=None, **ignored):
        context = {"None": None,
                   }
        context.update(args[0])
        return context

    def pt_source_file(self):
        return self.file_path
