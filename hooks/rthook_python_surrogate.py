"""Make the frozen dashAI launcher usable as a Python interpreter.

A PyInstaller bundle ships no ``python`` executable: ``sys.executable`` is the
launcher itself. dashAI installs plugins with ``sys.executable -m pip``, and pip
in turn re-invokes ``sys.executable`` to build isolated wheels, so the launcher
has to honour the two interpreter invocations those paths rely on:

* ``dashAI -m <module> [args...]``   behaves like ``python -m <module> ...``
* ``dashAI <script>.py [args...]``   behaves like ``python <script>.py ...``

Anything else falls through to the normal dashAI CLI.
"""

import runpy
import sys


def _run_as_interpreter():
    arguments = sys.argv[1:]
    if not arguments:
        return

    if arguments[0] == "-m" and len(arguments) > 1:
        module = arguments[1]
        sys.argv = [sys.argv[0], *arguments[2:]]
        runpy.run_module(module, run_name="__main__", alter_sys=True)
        sys.exit(0)

    if arguments[0].endswith(".py"):
        script = arguments[0]
        sys.argv = [script, *arguments[1:]]
        runpy.run_path(script, run_name="__main__")
        sys.exit(0)


_run_as_interpreter()
