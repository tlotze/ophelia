===================
Overview of Ophelia
===================

Ophelia creates XHTML pages from templates written in TAL, the Zope Template
Attribute Language. It is designed to reduce code repetition to zero.

The package contains both a WSGI application running Ophelia as well as a
request handler for mod_python, the Python module for the Apache2 web server.

Documentation files cited below can be found inside the package directory,
along with a number of doctests for the modules.


Entry points
============

After you installed Ophelia and wrote some templates, how can you make it
render web pages?

Use Ophelia with Apache
    The Python package contains a module ``ophelia.modpython`` that provides a
    request handler for the mod_python Apache module.

Use Ophelia as a WSGI application
    Ophelia defines an application class compliant with the WSGI standard,
    :PEP:`333`: ``ophelia.wsgi.Application``. You can either try it by running
    Ophelia's own wsgiref-based HTTP server or run it by any WSGI server you
    might care to use.

    The wsgiref-based server is installed as the ``ophelia-wsgiref``
    executable if Ophelia is installed as an egg with the "wsgiref" extra
    enabled. Its script entry point is ``ophelia.wsgi.wsgiref_server``.

Dump single pages to stdout
    An executable which is always installed with the ophelia egg is
    ``ophelia-dump``. This script has Ophelia render the response
    corresponding to the path you specify, and prints it to ``sys.stdout``,
    optionally with HTTP headers. The script's entry point is
    ``ophelia.dump.dump``.

Both scripts provide some usage instructions when called with the ``--help``
option. They read a configuration file; see CONFIGURATION.txt for details.


What kind of sites is Ophelia good for?
=======================================

Static content
--------------

Consider Ophelia as SSI on drugs. It's not fundamentally different, just a
lot friendlier and more capable.

Use Ophelia for sites where you basically write your HTML yourself, except
that you need write the recurring stuff only once. Reducing repetition to zero
comes at a price: your site must follow a pattern for Ophelia to combine your
templates the right way.

Consider your site's layout to be hierarchical: there's a common look to all
your pages, sections have certain characteristics, and each page has unique
content. It's crucial to Ophelia that this hierarchy reflect in the file
system organization of your documents; how templates combine is deduced from
their places in the hierarchy of directories.

Dynamic content
---------------

Ophelia makes the Python language available for including dynamic content.
Each template file may include a Python script. Python scripts and templates
contributing to a page share a common set of variables to modify and use.

Ophelia's content model is very simple and works best if each content object
you publish is its own view: the page it is represented on. If you get content
from external resources anyway (e.g. a database or a version control
repository), it's still OK to use Ophelia even with multiple views per content
object as long as an object's views don't depend on the object's type or even
the object itself.

Trying to use Ophelia on a more complex site will lead to an ugly entanglement
of logic and presentation. Don't use Ophelia for sites that are actually web
interfaces to applications, content management systems and the like.


How Ophelia works
=================

Template files
--------------

For each request, Ophelia looks for a number of template files. It takes one
file named "__init__" from each directory on the path from the site root to
the page, and a final one for the page itself. The request is served by
Ophelia if that final template is found.

When building the page, the page's template is evaluated and its content
stored in what is called the inner slot. Then each template on the way back
from the page to the root is evaluated in turn and may include the current
content of the inner slot. The result is stored in the inner slot after each
step.

The result of processing the root template is served as the page.

Python scripts
--------------

Each template file may start with a Python script. In that case, the script is
separated from the template by the first occurrence of an "<?xml?>" tag on a
line of its own (except for whitespace left or right). If the template file
contains only a Python script but not actually a template, put "<?xml?>" in
its last line.

Python scripts are executed in order while traversing from the site root to
the page. They are run in the same namespace of variables that is later used
as the evaluation context of the templates. Variables that are set by a Python
script may be used and modified by any scripts run later, as well as by TALES
expressions used in the templates.

The namespace is initialized by Ophelia with a single variable, __request__,
that references the request object. Thus, scripts have access to request
details and traversal internals. In addition to setting variables, scripts may
also import modules, define functions, access the file system, and generally
do anything a Python program can do.


How Ophelia behaves
===================

URL canonicalization and redirection
------------------------------------

If Ophelia encounters a URL that corresponds to a directory it behaves
similarly to Apache in its default configuration: If the URL doesn't end with
a slash, it will redirect the browser to add the slash. If the slash is there,
it will try to find a template named index.html by default, and render it as
the directory "index".

Depending on configuration, explicit requests for directory index pages may be
redirected to bare directory URLs without the final path segment. This would
turn <http://www.example.com/index.html> into <http://www.example.com/>.

Additionally, Ophelia canonicalizes URLs containing path segments "." and ".."
according to :RFC:`3986` on generic URI syntax, and removes empty path
segments which are not at the end of the path. If the URL is changed by these
rules, Ophelia redirects the browser accordingly.

The mod_python handler
----------------------

Apache2 processes a request in phases, each of which can be handled by modules
such as mod_python. Ophelia provides a mod_python handler for the content
generation phase. If a requested URL is configured to be handled by Ophelia,
the handler tries to find appropriate templates in the file system, and build
a page from them.

Ophelia's mod_python handler never causes a File Not Found HTTP error.
Instead, it passes control back to Apache and other modules if it finds it
can't build a particular resource. Apache falls back to serving static content
from disk in that case. Ophelia can thus be installed on top of a static site
to handle just those requests for which templates exist in the template
directory.


Languages and APIs used in templates and scripts
================================================

For the Python language, see <http://docs.python.org/>.

For Zope page templates, see
<http://www.zope.org/Documentation/Books/ZopeBook/2_6Edition/AppendixC.stx>.

For WSGI, the web server gateway interface, see
<http://www.python.org/dev/peps/pep-0333/>.

For the mod_python API, see
<http://www.modpython.org/live/current/doc-html/>.

For the Ophelia API and predefined script and template variables, see API.txt.


.. Local Variables:
.. mode: rst
.. End:
