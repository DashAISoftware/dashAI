============
DashAI
============

.. image:: https://img.shields.io/pypi/v/dashai.svg
        :target: https://pypi.python.org/pypi/dashai

.. image:: https://readthedocs.org/projects/dashai/badge/?version=latest
        :target: https://dashai.readthedocs.io/en/latest/?version=latest
        :alt: Documentation Status


A graphical toolbox for training, evaluating and deploying state-of-the-art
AI models

.. image:: ./images/DashAI_banner.png
   :alt: DashAI Logo

Quick installation (Pypi)
=========================


DashAI needs Python 3.10 or greater to be installed. Once that requirement is satisfied, you can install DashAI via pip:

.. code:: bash

    $ pip install dashai

Then, to initialize the server and the graphical interface, run:

.. code:: bash

    $ dashai

Finally, go to `http://localhost:3000/ <http://localhost:3000/>`_ in your browser to access to the DashAI graphical interface.


Test datasets
=============

Some datasets you can use to try DashAI are available `here <https://github.com/DashAISoftware/DashAI_Datasets>`_.


Development
===========


To download and run the development version of DashAI, first, download the repository
and switch to the developing branch:

.. code:: bash

    $ git clone https://github.com/DashAISoftware/DashAI.git
    $ git checkout develop


Frontend
--------

.. warning::

    All commands executed in this section must be run
    from `DashAI/front`. To move there, run:

    .. code::

        $ cd DashAI/front


Prepare the environment
~~~~~~~~~~~~~~~~~~~~~~~

1. `Install the LTS node version <https://nodejs.org/en>`_.

2. Install `Yarn` package manager following the instructions located on the
   `yarn getting started <https://yarnpkg.com/getting-started>`_ page.

3. Move to `DashAI/front` and Install the project packages
   using yarn:

.. code:: bash

    $ cd DashAI/front
    $ yarn install


Running the frontend
~~~~~~~~~~~~~~~~~~~~~~

Move to DashAI/front if you are not on that route:

.. code:: bash

    $ cd DashAI/front

Then, launch the front-end development server by running the following command:

.. code:: bash

    $ yarn start


Backend
-------


Prepare the environment
~~~~~~~~~~~~~~~~~~~~~~~

First, set the python enviroment, for that you can use
`conda <https://docs.conda.io/en/latest/miniconda.html>`_:

.. code: bash

    $ conda create -n dashai python=3.10
    $ conda activate dashai

Later, install the requirements:

.. code:: bash

    $ pip install -r requirements.txt
    $ pip install -r requirements-dev.txt
    $ pre-commit install

Running the Backend
~~~~~~~~~~~~~~~~~~~

There are two ways to run DashAI:

1. By executing DashAI as a module from the root of the repository:

.. code:: bash

    $ python -m DashAI

2. Or,  installing the default build:

.. code:: bash

    $ pip install . -e
    $ dashai


Optional Flags
==============

**Setting the local execution path**

With the `--local-path` (alias `-lp`) option you can determine where DashAI will save its local
files, such as datasets, experiments, runs and others.
The following example shows how to set the folder in the local `.DashAI` directory:

.. code:: bash

    $ python -m DashAI --local-path "~/.DashAI"


**Setting the logging level**

Through the `--logging-level` (alias `-ll`) parameter, you can set which logging level the DashAI
backend server will have.

.. code:: bash

    $ python -m DashAI --logging-level INFO

The possible levels available are: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`.

Note that the `--logging-level` not only affects the DashAI loggers, but also
the datasets (which is set to the same level as DashAI) and the
SQLAlchemy (which is only activated when logging level is DEBUG).


**Disabling automatic browser opening**

By default, DashAI will open a browser window pointing to the application
after starting. If you prefer to disable this behavior, you can use the
`--no-browser` (alias `-nb`) flag:

.. code:: bash

    $ python -m DashAI --no-browser


**Checking Available Options**

You can check all available options through the command:

.. code:: bash

    $ python -m DashAI --help


Database Migrations
==================

Migrations are managed through `Alembic <https://alembic.sqlalchemy.org/en/latest/>`_.

They are automatically executed when starting DashAI. However, if you want to
run them manually, you can do so using the following command (inside the
`DashAI/` folder):

.. code-block:: bash

    $ alembic upgrade head

This command applies all pending migrations up to the latest revision.

---

Creating a New Migration
------------------------

After modifying the database models, a new migration can be generated using:

.. code-block:: bash

    $ alembic revision --autogenerate -m "<<Your message here>>"

Where ``<<Your message here>>`` is a brief description of the changes introduced
(e.g., *add model metadata table*, *update dataset schema*).

Generated migrations are located in the ``alembic/versions`` directory and
**must be committed to the repository**.

It is strongly recommended to review the autogenerated migration file before
applying it, as Alembic may not always detect complex changes correctly.

---

Applying Migrations
-------------------

To apply all pending migrations:

.. code-block:: bash

    $ alembic upgrade head

To upgrade to a specific revision:

.. code-block:: bash

    $ alembic upgrade <revision_id>

---

Downgrading Migrations
----------------------

If you need to revert database changes, migrations can be downgraded using:

.. code-block:: bash

    $ alembic downgrade -1

This command reverts the last applied migration.

To downgrade to a specific revision:

.. code-block:: bash

    $ alembic downgrade <revision_id>

---

Checking Migration Status
-------------------------

To view the current migration applied to the database:

.. code-block:: bash

    $ alembic current

To list the full migration history:

.. code-block:: bash

    $ alembic history

---


Testing
=======

Execute tests
-------------

DashAI uses `pytest <https://docs.pytest.org/>`_ to perform the backend
tests.
To execute the backend tests

1. Move to `DashAI/back`

.. code:: bash

    $ cd DashAI/back

2. Run:

.. code:: bash

    $ pytest tests/

.. note::

    The database session is parametrized in every endpoint as
    ``db: Session = Depends(get_db)`` so we can test endpoints on a test database
    without making changes to the main database.



Acknowledgments
===============

This project is sponsored by the `National Center for Artificial Intelligence - CENIA <https://cenia.cl/en/>`_ (FB210017), and the `Millennium Institute for Foundational Data Research - IMFD <https://imfd.cl/en/>`_ (ICN17_002).

The core of the development is carried out by students from the Computer Science Department of the University of Chile and the Federico Santa Maria Technical University.

To see the full list of contributors, visit in `Contributors <https://github.com/DashAISoftware/DashAI/graphs/contributors>`_ the DashAI repository on Github.

.. image:: ./images/logos.png
   :alt: Collaboration Logos
