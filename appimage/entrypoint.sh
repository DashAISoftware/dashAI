#!/bin/bash
# Run the dashAI app via the installed package. Starts the FastAPI server,
# the Huey consumer, and opens the browser at http://localhost:8000/.
{{ python-executable }} -m DashAI "$@"
