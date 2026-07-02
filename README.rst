============
dashAI
============

.. image:: https://img.shields.io/pypi/v/dashai.svg
        :target: https://pypi.python.org/pypi/dashai

.. image:: https://readthedocs.org/projects/dashai/badge/?version=latest
        :target: https://docs.dash-ai.com/
        :alt: Documentation Status


A graphical toolbox for training, evaluating and deploying state-of-the-art
AI models

.. image:: ./images/dashai-logo.svg
   :alt: dashAI Logo

Desktop installers (Windows / macOS / Linux)
=============================================

The easiest way to get started. Desktop installers, ready to use, are
published with every release. They are **CPU only** and bundle everything you
need, so no Python or extra setup is required.

Download the file for your system from the
`latest release <https://github.com/DashAISoftware/DashAI/releases/latest>`_:

* **Windows (x64):** ``dashAI-<version>-x64-windows.exe``
* **macOS (Apple Silicon):** ``dashAI-<version>-arm-osx.dmg``
* **macOS (Intel):** ``dashAI-<version>-x64-osx.dmg``
* **Linux (x64):** ``dashAI-<version>-x64-linux.AppImage``

On Windows and macOS, run the installer, launch dashAI, and the graphical
interface opens automatically.

On Linux, make the AppImage executable and run it:

.. code:: bash

    $ chmod +x dashAI-<version>-x64-linux.AppImage
    $ ./dashAI-<version>-x64-linux.AppImage

The AppImage bundles its own Python, so nothing needs to be installed. It
requires glibc 2.35 or newer (Ubuntu 22.04+, Debian 12+, Fedora 36+, and most
distributions from 2022 on) and FUSE 2 to mount. If FUSE is missing, run it
with ``./dashAI-<version>-x64-linux.AppImage --appimage-extract-and-run``.

When double clicked, the AppImage opens a terminal window to show the server
logs. This needs a terminal emulator, which every standard desktop (GNOME, KDE,
XFCE, and others) already provides, so no setup is required. On a minimal system
with no terminal emulator the log window is skipped, but the app still starts
and opens the browser as usual.

**Note:** the desktop installers ship with CPU only PyTorch and
``llama-cpp-python``. For NVIDIA (CUDA) or AMD (ROCm) GPU acceleration, use the
pip installation below.


Installation (PyPI)
===================

dashAI needs Python 3.10 or greater. We strongly recommend installing it inside
an isolated environment (``venv`` or ``conda``) to avoid clashes with other
packages.

Installing dashAI also installs PyTorch with the default build for your
platform, which works out of the box on CPU. To enable GPU acceleration (NVIDIA
CUDA or AMD ROCm), or to force a CPU only build, reinstall PyTorch from the
matching index as shown in step 3. ``llama-cpp-python`` is required to run LLM
models (GGUF / Llama, Mistral, Qwen, and similar) inside the app, but it is
never installed automatically, so install it in step 3 if you need those models.


1. Create an environment
-------------------------

**Linux / macOS (venv)**

.. code:: bash

    $ python3 -m venv .venv
    $ source .venv/bin/activate

**Windows (venv, PowerShell)**

.. code:: powershell

    > python -m venv .venv
    > .venv\Scripts\Activate.ps1

**Any OS (conda)**

.. code:: bash

    $ conda create -n dashai python=3.12
    $ conda activate dashai


2. Install dashAI
-----------------

With the environment active:

.. code:: bash

    $ pip install dashai


3. Select a PyTorch build and (optional) llama-cpp
--------------------------------------------------

This step is optional on CPU (step 2 already installed a working PyTorch).
Run the section below that matches your hardware to pick a specific build.

CPU only (Linux / macOS / Windows)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

On Linux the default PyTorch ships the large CUDA build; reinstall from the CPU
index if you want a smaller CPU only install:

.. code:: bash

    $ pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu --force-reinstall --no-cache-dir

    # Optional, for GGUF / Llama models (precompiled CPU wheel, no build tools):
    $ pip install llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu --force-reinstall --no-cache-dir

NVIDIA GPU (CUDA 12.8)
~~~~~~~~~~~~~~~~~~~~~~~

.. code:: bash

    # Torch CUDA 12.8 (prebuilt wheels)
    $ pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128 --force-reinstall --no-cache-dir

    # Llama compiled with CUDA offload (requires build tools, see below)
    $ pip install llama-cpp-python -C cmake.args="-DGGML_CUDA=on" --force-reinstall --no-cache-dir --verbose

AMD GPU (ROCm 6.4)
~~~~~~~~~~~~~~~~~~

.. code:: bash

    # Torch ROCm (prebuilt wheels)
    $ pip install torch torchvision --index-url https://download.pytorch.org/whl/rocm6.4 --force-reinstall --no-cache-dir

    # Llama compiled with HIP/ROCm offload (requires build tools, see below)
    $ pip install llama-cpp-python -C cmake.args="-DGGML_HIP=on" --force-reinstall --no-cache-dir --verbose


Build tools for GPU llama-cpp
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``-C cmake.args=...`` commands above compile ``llama-cpp-python`` from
source. They require:

* `CMake <https://cmake.org/>`_ (required to drive the build)
* A C compiler:

  * **Linux:** ``gcc`` or ``clang``
  * **Windows:** Visual Studio (C++ build tools / MSVC) or MinGW
  * **macOS:** Xcode

* **NVIDIA (CUDA):** NVIDIA drivers and the NVIDIA CUDA Toolkit. Use version
  ``>=12.8`` for RTX 5000 series GPUs to work.
* **AMD (ROCm):** the ROCm / HIP SDK and AMD drivers.

If you want to skip compilation, precompiled ``llama-cpp-python`` wheels are
available for CPU and CUDA:

.. code:: bash

    $ pip install llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu --force-reinstall --no-cache-dir
    $ pip install llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/<cuda-version> --force-reinstall --no-cache-dir

Replace ``<cuda-version>`` with your CUDA tag. Prebuilt wheels are published for
``cu118``, ``cu121``, ``cu122``, ``cu123``, ``cu124``, ``cu125``, ``cu130`` and
``cu132`` (for example ``cu124``). See the
`llama-cpp-python installation docs <https://llama-cpp-python.readthedocs.io/en/latest/>`_
for the available wheels and other backend options.


1. Run dashAI
-------------

Start the server and graphical interface with:

.. code:: bash

    $ dashai

Then open `http://localhost:8000/ <http://localhost:8000/>`_ in your browser to
access the dashAI graphical interface.


Docker
======

dashAI can also run inside a container. Two Dockerfiles are provided at the
repository root.

CPU image
---------

``Dockerfile`` builds a CPU only image (CPU PyTorch). Build and run it with:

.. code:: bash

    $ docker build -t dashai .
    $ docker run -p 8000:8000 dashai

NVIDIA GPU image (CUDA)
-----------------------

``Dockerfile.cuda`` builds a CUDA enabled image (CUDA 12.8 PyTorch and
``llama-cpp-python`` compiled with CUDA offload). Build and run it with:

.. code:: bash

    $ docker build -t dashai:cuda -f Dockerfile.cuda .
    $ docker run --gpus all -p 8000:8000 dashai:cuda

Then open `http://localhost:8000/ <http://localhost:8000/>`_ in your browser.

To pass the host GPU into the container with ``--gpus all`` you need the NVIDIA
drivers plus the runtime that wires the GPU into Docker. How you get that
runtime depends on your setup:

* **Native Linux Docker:** install the
  `NVIDIA Container Toolkit <https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html>`_
  on the host.
* **Docker Desktop (Windows / macOS):** the GPU runtime is bundled with the
  WSL 2 backend, so you only install the NVIDIA driver on Windows and enable the
  WSL 2 backend. See the
  `Docker Desktop GPU docs <https://docs.docker.com/desktop/features/gpu/>`_.
* **Docker Engine inside a WSL 2 distro (without Docker Desktop):** install the
  NVIDIA Container Toolkit inside the WSL distro, following the
  `CUDA on WSL guide <https://docs.nvidia.com/cuda/wsl-user-guide/index.html>`_.


Test datasets
=============

Some datasets you can use to try dashAI are available `here <https://github.com/DashAISoftware/DashAI_Datasets>`_.


Development
===========


To download and run the development version of dashAI, first, download the repository
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

    $ conda create -n dashai python=3.12
    $ conda activate dashai

Later, install the requirements:

.. code:: bash

    $ pip install -r requirements.txt
    $ pip install -r requirements-dev.txt
    $ pre-commit install

Running the Backend
~~~~~~~~~~~~~~~~~~~

There are two ways to run dashAI:

1. By executing dashAI as a module from the root of the repository:

.. code:: bash

    $ python -m DashAI

2. Or,  installing the default build:

.. code:: bash

    $ pip install . -e
    $ dashai


Optional Flags
==============

**Setting the local execution path**

With the `--local-path` (alias `-lp`) option you can determine where dashAI will save its local
files, such as datasets, experiments, runs and others.
The following example shows how to set the folder in the local `.DashAI` directory:

.. code:: bash

    $ python -m DashAI --local-path "~/.DashAI"


**Setting the logging level**

Through the `--logging-level` (alias `-ll`) parameter, you can set which logging level the dashAI
backend server will have.

.. code:: bash

    $ python -m DashAI --logging-level INFO

The possible levels available are: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`.

Note that the `--logging-level` not only affects the dashAI loggers, but also
the datasets (which is set to the same level as dashAI) and the
SQLAlchemy (which is only activated when logging level is DEBUG).


**Disabling automatic browser opening**

By default, dashAI will open a browser window pointing to the application
after starting. If you prefer to disable this behavior, you can use the
`--no-browser` (alias `-nb`) flag:

.. code:: bash

    $ python -m DashAI --no-browser


**Checking Available Options**

You can check all available options through the command:

.. code:: bash

    $ python -m DashAI --help


Database Migrations
===================

Migrations are managed through `Alembic <https://alembic.sqlalchemy.org/en/latest/>`_.

They are automatically executed when starting dashAI. However, if you want to
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

dashAI uses `pytest <https://docs.pytest.org/>`_ to perform the backend
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

.. INSTITUTIONS-BLOCK:START

.. This block is auto-generated from docs/static/institutions/institutions.json.
   Edit that file and run ``python scripts/render_institutions.py``. Do not edit by hand.

This project is developed in collaboration with:

* `University of Chile <https://uchile.cl/>`_ - Leading Institution
* `Fcfm <https://www.fcfm.uchile.cl/>`_ - Leading Institution
* `CENIA <https://www.cenia.cl/>`_ - Associated Institution
* `IMFD <https://imfd.cl/en/>`_ - Collaborator
* `Unholster <https://unholster.com/>`_ - Industry Partner

Supported by ANID through Fondef IDEA ID25I10330, Fondef VIU23P 0110, and grants supporting the centers CENIA (FB210017) and IMFD (ICN17_002). Developed by students of DCC UChile and UTFSM.

.. image:: images/logos.png
   :alt: Logos of collaborating institutions

.. INSTITUTIONS-BLOCK:END

To see the full list of contributors, visit in `Contributors <https://github.com/DashAISoftware/DashAI/graphs/contributors>`_ the dashAI repository on Github.
