Ophelia
=======

Ophelia creates HTML pages from templates written in TAL, the Zope Template
Attribute Language. It contains a request handler for the Apache2 web server.

See INSTALL.txt for installation and configuration issues.


What kind of sites is Ophelia good for?
+++++++++++++++++++++++++++++++++++++++

Static content
--------------

Consider Ophelia as SSI on drugs. It's not fundamentally different, just a
lot friendlier and more capable.

Use Ophelia for sites where you basically write your HTML yourself, except
that you can leave out the repetitive stuff. Leaving all of it out comes at a
price: your site must follow a pattern for Ophelia to combine your templates
the right way.

Consider your site's layout to be hierarchical: there's a common look to all
your pages, sections have certain characteristics, and each page has unique
content. It's crucial to Ophelia that this hierarchy reflects in the file
system organization of your documents.

Dynamic content
---------------

Ophelia makes the Python language available for including dynamic content.

Ophelia's content model works best if for each content object you publish,
there is exactly one view: the page it is represented on. If you get content
from external resources anyway (e.g. a database or a version control
repository), it's still OK to use Ophelia if there are multiple views per
content object as long as the views of an object don't depend on the type of
the object or even the object itself.

Trying to use Ophelia on a more complex site leads to applications that
might just as well be written in PHP (except that Python is still the more
beautiful language). Don't use Ophelia for sites that are actually web
interfaces to applications, content management systems and the like.


How to write templates and scripts
++++++++++++++++++++++++++++++++++

For the Python language, see <http://docs.python.org/>.

For Zope page templates, see
<http://www.zope.org/Documentation/Books/ZopeBook/2_6Edition/AppendixC.stx>.

For the mod_python API parts of which are accessible from templates and
scripts, see <http://www.modpython.org/live/current/doc-html/>.

Page template context
---------------------

The context of a page template, i.e. the set of variables that can be accessed
by TALES expressions, contains:

* context: application-level context variables, modified by any relevant
           scripts, both more and less specific

* macros: macros defined by any relevant templates and scripts, both more and
          less specific

* innerslot: the "magic" slot filled by evaluating the next more specific
             template. Example use: <div tal:content="structure innerslot">

             Making this slot magic avoids writing any boiler-plate code at
             all in run-of-the-mill templates and pages.

Script context
--------------

* context: see above

* macros: namespace of str, compiled macros encountered so far

* request: the request object passed by mod_python

* traversal: traversal context, a namespace carrying some variables internally
             used by Ophelia's traversal mechanism:

             path: str, path traversed so far

             tail: list of str, path segments yet to traverse from here

             stack: list of str pairs, compiled templates encountered so far,
                                       together with their file paths

             template: unicode, the decoded source of the current template

After running all scripts, the ophelia namespace will also hold the inner slot
as it is built while interpreting the template stack. It will be a unicode
string under the name "innerslot". This is so it may be accessed at
interpretation time by functions put in the context.


Ophelia's application programmers' interface
--------------------------------------------

(This is a slight misnomer as you don't actually build applications with
Ophelia. But "API" is a rather common term, let's use it to mean the end
users' programming interface.)

To use the interface in a script or Python module, do:

from ophelia import oapi

The interface contains the following members:

* StopTraversal: exception, see "controlling traversal" below

* NotFound: exception signalling that some file needed to respond to the
            request was not found

* Namespace: class whose instances do nothing but carry attributes

             Not using dictionaries here makes for more aesthetic code if
             nothing else.

* getScriptGlobals: function returning the global namespace in which Ophelia
                    executes all Python scripts of the current request

* getContext: function returning the application-level context as available in
              templates and scripts

* getMacros: function returning the template macros as available in templates
             and scripts

* getRequest: function returning the request

* getTraversal: function returning the traversal context as available in
                templates and scripts


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

If a template file starts with the marker "<?ophelia", the following line or
lines are examined. If the first line contains a Python-style encoding
declaration, the encoding is assumed for both the script and the template in
that file. Anything else on that line is ignored and the encoding defaults to
iso-8859-15 (a.k.a. latin-9) if none is given.

The region ends with the marker "?>" which may either end the first line of
the file or start an otherwise empty line farther down the file. In the latter
case, the region between the starting and ending lines is taken to be a Python
script, and executed. Trailing whitespace on the ending line is dropped; there
may, however, be no leading whitespace.

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
