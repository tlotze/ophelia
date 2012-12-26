# coding: utf-8
# Copyright (c) 2012 Thomas Lotze
# See also LICENSE.txt

import os
import os.path
import tl.pkg.sphinxconf


_year_started = 2006
_bitbucket_name = 'ophelia'

# XXX We need to hack around the assumption of a namespaced package made by
# tl.pkg 0.1.

tl.pkg.sphinxconf.link_text_files_from_source = lambda project: None

tl.pkg.sphinxconf.set_defaults()

for name in os.listdir(os.path.join('..', project)):
    if not name.endswith('txt'):
        continue
    os.symlink(os.path.join('..', project, name),
               '%s-%s' % (project, name))

# XXX hack ends here

extensions.append('repoze.sphinx.autointerface')
