pthandler
=========

pthandler is a request handler for the Apache2 web server. It creates HTML
pages from templates written in TAL, the Zope Template Attribute Language.

See INSTALL.txt for installation and configuration issues.


What kind of sites is pthandler good for?
+++++++++++++++++++++++++++++++++++++++++

Static content
--------------

Consider pthandler as SSI on drugs. It's not fundamentally different, just a
lot friendlier and more capable.

Use pthandler for sites where you basically write your HTML yourself, except
that you can leave out the repetitive stuff. Leaving all of it out comes at a
price: your site must follow a pattern for pthandler to combine your templates
the right way.

Consider your site's layout to be hierarchical: there's a common look to all
your pages, sections have certain characteristics, and each page has unique
content. It's crucial to pthandler that this hierarchy reflects in the file
system organization of your documents.

Dynamic content
---------------

pthandler makes the Python language available for including dynamic content.

pthandler's content model works best if for each content object you publish,
there is exactly one view: the page it is represented on. If you get content
from external resources anyway (e.g. a database or a version control
repository), it's still OK to use pthandler if there are multiple views per
content object as long as the views of an object don't depend on the type of
the object or even the object itself.

Trying to use pthandler on a more complex site leads to applications that
might just as well be written in PHP (except that Python is still the more
beautiful language). Don't use pthandler for sites that are actually web
interfaces to applications, content management systems and the like.


How pthandler behaves
+++++++++++++++++++++

In Apache2, a request is handled in phases, each of which can be handled by
one or more modules. pthandler provides a handler for the content generation
phase, passing control back to Apache and other modules if it finds it can't
build a particular resource. pthandler never causes a File Not Found HTTP
error. This means that pthandler can be installed on top of a static site,
handling just some of the requests to HTML pages and letting Apache serve
static files for all others.


How pthandler works
+++++++++++++++++++

Static templates
----------------

For each request, pthandlers looks for a number of templates. It takes one
template named "pt" from each directory on the path from the site root to the
page, and a final one for the page itself. The request is served if that final
template is found, otherwise control is given back to Apache.

The page is built by first putting the content of the page's template into a
slot called "inner". Then each template on the way back from the page to the
root is evaluated in turn, making the inner slot availably in the evaluation
context and replacing it with the result after each step.

The result of processing the root template is served as the page.

Dynamic templates
-----------------

The description of static templates was a bit simplistic in that even the most
specific template, corresponding to the page itself, is evaluated as a
template. The inner slot is empty in the beginning, but there may be other
evaluation context already. Some is initialized by pthandler itself. The rest
can be set by Python scripts put in the template directory tree.

On the way forward from the site root to the page, pthandler tries to execute
a Python script named "py" in each directory, and finally one for the page.
Each is passed some information about the request and allowed to modify the
template context. Each script may also import module, define functions and set
values other than the context. They will be available to all scripts executed
later.

On the way back from the page to the root, templates can use the values stored
in the context through TALES expressions.

Controlling traversal
---------------------

This is at the edge of what is in pthandler's scope.

There are two exception classes defined by pthandler and made available to
scripts as spi.StopTraversal and spi.ResetTraversal (spi being the namespace
for the script programmers' interface). Raising spi.StopTraversal in a script
prevents more specific scripts from being executed and more specific templates
from being evaluated. The raising script is responsible for filling the inner
slot, possibly using the rest of the URL as input.

Raising spi.ResetTraversal causes more general templates to be ignored, making
the template corresponding to the script responsible for providing the outer
HTML structure. This allows for switching the layout completely in the middle
of traversal while using the context manipulations made so far.
