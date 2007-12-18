# Copyright (c) 2007 Thomas Lotze
# See also LICENSE.txt

import zope.pagetemplate.pagetemplate


class PageTemplateTracebackSupplement(object):

    def __init__(self, template):
        self.template = template
        self.source_url = template.file_path
        self.warnings = template._v_errors


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
        return args[0]

    def pt_source_file(self):
        return self.file_path
