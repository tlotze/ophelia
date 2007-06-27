# Copyright (c) 2007 Thomas Lotze
# See also LICENSE.txt

import zope.pagetemplate.pagetemplate

from ophelia.util import Namespace


class PageTemplateTracebackSupplement(object):

    def __init__(self, template):
        self.template = template

    @property
    def warnings(self):
        return self.template._v_errors


class PageTemplate(zope.pagetemplate.pagetemplate.PageTemplate):
    """Page templates with Ophelia-style namespaces and source tracking.

    Call parameters: the namespace of file context variables
    """

    request = None
    file_path = None

    def __init__(self, request, text, file_path=None):
        super(PageTemplate, self).__init__()
        self.request = request
        self.write(text)
        self.file_path = file_path

    @property
    def macros(self):
        __traceback_supplement__ = (PageTemplateTracebackSupplement, self)
        macros = super(PageTemplate, self).macros
        if self._v_errors:
            raise zope.pagetemplate.pagetemplate.PTRuntimeError(
                "Can't compile template at %s." % self.file_path)
        return macros

    def pt_getContext(self, args=(), options=None, **ignored):
        return Namespace(self.request.tales_namespace(args[0]))

    def pt_source_file(self):
        return self.file_path
