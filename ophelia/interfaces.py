# Copyright (c) 2007 Thomas Lotze
# See also LICENSE.txt

"""Public interfaces used in Ophelia.
"""

import zope.interface


class IRequestAPI(zope.interface.Interface):
    """HTTP request API for use in scripts and TALES expressions.
    """

    # Basic parameters which don't have defaults, not meant to be changed.

    path = zope.interface.Attribute(
        """URI path portion to traverse from the site root.

        String with path segments separated by '/', doesn't start with '/' if
        the requested URI was canonical.
        """)

    template_root = zope.interface.Attribute(
        """Absolute file system path to the templates' root directory.
        """)

    site = zope.interface.Attribute(
        """Absolute URI of the site root.

        String, the URI which corresponds to an empty path.
        """)

    env = zope.interface.Attribute(
        """Compound environment namespace.

        - site configuration options (PythonOption setting if running
          mod_python, application configuration if using WSGI)
        - the CGI or WSGI environment variables passed by the server
        - if running mod_python, the Apache request object as apache_request
        """)

    # Further configuration, may be modified by scripts.

    response_encoding = zope.interface.Attribute(
        """Name of the character encoding used for the HTTP response.

        String, defaults to "utf-8".
        """)

    index_name = zope.interface.Attribute(
        """File name to access if a URI refers to a bare directory.

        String, defaults to "index.html".
        """)

    redirect_index = zope.interface.Attribute(
        """Whether to redirect requests for index pages to directory URIs.

        Bool, defaults to False. A request for an index page is one that maps
        to a file named like the index_name.
        """)

    # Components.

    splitter = zope.interface.Attribute(
        """Splits input files into scripts and templates.

        Implements ophelia.interfaces.ISplitter.
        """)

    # Traversal and rendering state meant for use in scripts and expressions.

    context = zope.interface.Attribute(
        """Namespace for executing scripts and evaluating TALES expressions.
        """)

    macros = zope.interface.Attribute(
        """Namespace of compiled macros.
        """)

    innerslot = zope.interface.Attribute(
        """Unicode content to put in the template's inner slot.

        None during traversal, assigned to after each template on the stack
        has been rendered, starting with the innermost one. Thus, this value
        can't be directly used by scripts but may be used by functions placed
        in the context.
        """)

    response_headers = zope.interface.Attribute(
        """Mapping of header names to TALES expressions.

        Expressions will be evaluated in the usual TALES context after all
        templates have been rendered.
        """)

    content = zope.interface.Attribute(
        """Encoded HTTP response after the response body is complete.

        None during traversal and template rendering. After that, consists of
        an XML declaration and the encoded current innerslot value.
        """)

    # Traversal and rendering state meant for use by those who know what
    # they're doing.

    current = zope.interface.Attribute(
        """URI traversed so far, starting with the site root URI.

        String, ends with '/' if a directory's __init__ is currently being
        processed.
        """)

    history = zope.interface.Attribute(
        """List of all past values of the "current" attribute.
        """)

    dir_path = zope.interface.Attribute(
        """Absolute file system path to the current directory.

        String. The current directory is the one which directly contains the
        file currently being processed.
        """)

    tail = zope.interface.Attribute(
        """List of path segments yet to traverse.

        List of strings, the last one being empty if the requested URI refers
        to a directory.
        """)

    stack = zope.interface.Attribute(
        """Stack of file contexts to process when rendering the response body.

        List of namespaces holding the file path, template text, and page
        template for any non-empty page template encountered so far (during
        traversal) or to be rendered yet (when building the response). The
        outermost template is at the bottom of the stack (i.e. at index 0).
        """)

    # Methods for processing further files.

    def load_macros(name):
        """Process a file, only executing the script and loading the macros.

        Only the macros defined by the template in the file are used; the
        template itself will be thrown away.

        name: str, file name to process, relative to the current dir_path

        Returns nothing.
        """

    def insert_template(name):
        """Process a file, pushing the template onto the stack.

        The script contained in the file given will be executed, the macros
        defined by the template will be loaded, and the template will be
        stacked on top of the one from the file whose script called this
        method.

        name: str, file name to process, relative to the current dir_path

        Returns nothing.
        """

    def load_macros(name):
        """Process a file, rendering its template.

        The script contained in the file given will be executed, the macros
        defined by the template will be loaded, and the template will be
        rendered in the TALES context as it is at the moment this method is
        called.

        name: str, file name to process, relative to the current dir_path

        Returns unicode, the rendered template contained in the file.
        """


class ISplitterAPI(zope.interface.Interface):
    """Input splitter API for use in scripts and TALES expressions.
    """

    script_encoding = zope.interface.Attribute(
        """Name of the character encoding for reading Python scripts.

        String, defaults to "ascii".
        """)

    template_encoding = zope.interface.Attribute(
        """Name of the character encoding for reading TAL templates.

        String, defaults to "ascii".
        """)
