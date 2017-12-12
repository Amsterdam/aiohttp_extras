.. reference this page as :ref:`index` (from which it's included)

Datapunt OAuth2 Services
========================

.. image:: https://img.shields.io/badge/python-3.6-blue.svg
   :target: https://www.python.org/

.. image:: https://img.shields.io/badge/license-MPLv2.0-blue.svg
   :target: https://www.mozilla.org/en-US/MPL/2.0/

The latest published documentation for this project can be found *here*.

.. todo::

   Publish the documentation somewhere (ReadTheDocs?) and insert a link in the
   sentence above.


Conventions
===========

*   The project top-level directory is also the source root.
*   We use PyTest for tests.
*   PyTest can be integrated with SetupTools (see
    https://docs.pytest.org/en/latest/goodpractices.html). We don’t do this.
*   Common commands for builds, distributing, packaging, documentation etcetera
    are in :file:`Makefile` and :file:`docs/Makefile`.
*   RST-files and -docstrings are indented with 4 spaces.
*   Globals must be immutable.
*   Docstrings are formatted like this:

    .. code-block:: python

        """This is a one-line docstring."""
        """One line description, terminated with a period.

        More info, with a trailing empty line.

        """


Getting Started
===============

.. code-block:: bash

    # Clone the repository:
    git clone git@github.com:Amsterdam/aiohttp_extras.git
    cd aiohttp_extras
    # Create a virtual environment:
    python3.6 -m venv --copies --prompt oauth2 .venv
    pip install -e .[docs,test]
    # Start a database server (required for all sub-services):
    docker-compose up -d database

    # To start a documentation server:
    make -C docs server
