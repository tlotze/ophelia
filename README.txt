===================================================================
Ophelia – build a web site from templates with zero code repetition
===================================================================

Ophelia creates XHTML pages from templates written in TAL, the Zope Template
Attribute Language. It is designed to reduce code repetition to zero.

Ophelia is a WSGI application. The package includes a wsgiref-based server
configured to run Ophelia as well as an application factory for use with
paster.

The package requires Python 2.6 or 2.7.

Documentation files cited below can be found inside the package directory,
along with a number of doctests for the modules.


Entry points
============

After you installed Ophelia and wrote some templates, how can you make it
render web pages?

Use Ophelia as a WSGI application
    Ophelia defines an application class compliant with the WSGI standard,
    :PEP:`333`: ``ophelia.wsgi.Application``. You can either try it by running
    Ophelia's own wsgiref-based HTTP server or run it by any WSGI server you
    might care to use.

Try the wsgiref-based server that comes with Ophelia
    A rather simplistic and non-production-ready wsgiref-based server set up
    to use the provided WSGI application is installed as the
    ``ophelia-wsgiref`` executable. Its script entry point is
    ``ophelia.wsgi.wsgiref_server``.

    The script provides some usage instructions when called with the
    ``--help`` option. It reads a configuration file; see CONFIGURATION.txt
    for details.

Use paster to plug the application into a WSGI server
    Ophelia provides a ``paste.app_factory#main`` entry point at
    ``ophelia.wsgi.Application.paste_app_factory``. This can be used to run
    Ophelia inside any WSGI server that can read paste "ini" files. See
    CONFIGURATION.txt for an example.


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

Documents on disk
-----------------

Generally, a site will include documents that cannot be assembled from
templates as described above. These are assets like images, javascript files
and style sheets as well as pages that, e.g., may have been exported by some
other system such as a source-code documentation generator.

In order to mix such content into the URL space of an Ophelia-generated site,
the template hierarchy must omit the relevant paths and a second directory
hierarchy which directly corresponds to the URL-space needs to contain the
documents to be delivered from disk. If Ophelia then finds that it cannot
serve a request using the templates, it will fall back to the on-disk
documents. Only if the latter do not include a file corresponding to the
requested URL will a "404 Not found" error response be sent.


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


Languages and APIs used in templates and scripts
================================================

For the Python language, see <http://docs.python.org/>.

For the Template attribute language, see
<http://wiki.zope.org/ZPT/TAL>.

For WSGI, the web server gateway interface, see
<http://www.python.org/dev/peps/pep-0333/>.

For the Ophelia API and predefined script and template variables, see API.txt.


.. Local Variables:
.. mode: rst
.. End:
