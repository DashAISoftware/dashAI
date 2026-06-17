#!/bin/bash
# Run the dashai console script installed by pip into the embedded Python.
# Starts the FastAPI server, the Huey consumer, and opens the browser.
{{ python-executable }} "${APPDIR}/opt/python{{ python-version }}/bin/dashai" "$@"
