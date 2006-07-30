Ophelia
=======

Ophelia creates XHTML pages from templates written in TAL, the Zope Tag
Attribute Language. It is designed to reduce code repetition to zero.

At present, Ophelia contains a request handler for the Apache2 web server.

See INSTALL.txt for installation and configuration issues.


What kind of sites is Ophelia good for?
+++++++++++++++++++++++++++++++++++++++

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
content. It's crucial to Ophelia that this hierarchy reflects in the file
system organization of your documents; how templates are nested is deduced
from their places in the hierarchy of directories.

Dynamic content
---------------

Ophelia makes the Python language available for including dynamic content.
Each template file may include a Python script. Python scripts and templates
contributing to a page share a common set of variables to modify and use.

Ophelia's content model is very simple and works best if each content object
you publish is its own view: the page it is represented on. If you get content
from external resources anyway (e.g. a database or a version control
repository), it's still OK to use Ophelia even with multiple views per content
object as long as an object's views doesn't depend on the object's type or
even the object itself.

Trying to use Ophelia on a more complex site will lead to an ugly entanglement
of logic and presentation. Don't use Ophelia for sites that are actually web
interfaces to applications, content management systems and the like.


Languages and APIs used in templates and scripts
++++++++++++++++++++++++++++++++++++++++++++++++

For the Python language, see <http://docs.python.org/>.

For Zope page templates, see
<http://www.zope.org/Documentation/Books/ZopeBook/2_6Edition/AppendixC.stx>.

For the mod_python API parts of which are accessible from templates and
scripts, see <http://www.modpython.org/live/current/doc-html/>.

For the Ophelia API and predefined script and template variables, see API.txt.


How Ophelia behaves
+++++++++++++++++++

In Apache2, a request is handled in phases, each of which can be handled by
one or more modules. Ophelia provides a handler for the content generation
phase, passing control back to Apache and other modules if it finds it can't
build a particular resource. Ophelia never causes a File Not Found HTTP
error. This means that Ophelia can be installed on top of a static site,
handling just some of the requests to HTML pages and letting Apache serve
static files for all others.

Caveat: For some reason, PHP files are not parsed correctly after Apache got
        control back from Ophelia.


How Ophelia works
+++++++++++++++++

Template files
--------------

For each request, Ophelia looks for a number of template files. It takes one
file named "__init__" from each directory on the path from the site root to
the page, and a final one for the page itself. The request is served if that
final template is found, otherwise control is given back to Apache.

The page is built by first putting the content of the page's template into the
inner slot. Then each template on the way back from the page to the root is
evaluated in turn, making the inner slot available in the evaluation context
and replacing it with the result after each step.

The result of processing the root template is served as the page.

In general, the inner slot is empty in the beginning, but there may be other
evaluation context already. Some is initialized by Ophelia itself. The rest
can be set by Python scripts included in the template files.

Character encoding and Python scripts
-------------------------------------

A template file may start with a Python script. In that case, the script is
separated from the template by the first occurrence of an "<?xml?>" tag on a
line of its own (except for whitespace left or right). If the template file
contains only a Python script but not actually a template, put "<?xml?>" in
its last line.

You can declare a character encoding both for the Python script and the
template, and the two encodings may differ. To specify the Python encoding,
just start the script with a Python style encoding declaration like this:
# -*- coding: utf-8 -*-
The template's encoding is determined by looking at the "<?xml?>" tag:
<?xml coding="utf-8" ?>
specifies UTF-8 encoding for the template. The tag itself will be stripped
from the template and will not appear in the rendered page.

You may also specify a default encoding for any scripts and templates to be
read later during traversal. In a Python script, just do something like
traversal.script_encoding = "utf-8"
traversal.template_encoding = "utf-8"
Failing such settings, the default encoding will be 7-bit ASCII.

Each script is passed some information about the request and traversal
internals and allowed to modify the template context and macros. Scripts may
also import modules and define functions and arbitrary variables. Those will
be available to all scripts executed later.

On the way back from the page to the root, templates can use the values stored
in the context through TALES expressions.

Controlling traversal
---------------------

This is at the edge of Ophelia's scope.

There is an exception class defined by Ophelia and made available to scripts
as oapi.StopTraversal (oapi being the namespace for Ophelia's programmers'
interface). Raising oapi.StopTraversal in a script prevents more specific
scripts from being executed and the current as well as more specific templates
from being evaluated. The exception accepts two optional parameters:

* content: str, used to fill the inner slot

* use_template: bool, whether to use the current template, defaults to False
