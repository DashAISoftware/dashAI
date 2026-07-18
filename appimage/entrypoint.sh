#!/bin/bash
# Run the dashai console script installed by pip into the embedded Python.
# Starts the FastAPI server, the Huey consumer, and opens the browser.

# When launched from a file manager (double-click) there is no terminal, so
# the server logs would be invisible. Relaunch inside a terminal emulator in
# that case. If none is available, fall through and run headless (the browser
# still opens). DASHAI_IN_TERMINAL guards against an infinite relaunch loop.
if [ ! -t 1 ] && [ -z "${DASHAI_IN_TERMINAL}" ]; then
    export DASHAI_IN_TERMINAL=1
    if command -v x-terminal-emulator >/dev/null 2>&1; then
        exec x-terminal-emulator -e "$0" "$@"
    elif command -v gnome-terminal >/dev/null 2>&1; then
        exec gnome-terminal -- "$0" "$@"
    elif command -v konsole >/dev/null 2>&1; then
        exec konsole -e "$0" "$@"
    elif command -v xfce4-terminal >/dev/null 2>&1; then
        exec xfce4-terminal -e "$0" "$@"
    elif command -v xterm >/dev/null 2>&1; then
        exec xterm -e "$0" "$@"
    fi
fi

exec "{{ python-executable }}" "${APPDIR}/opt/python{{ python-version }}/bin/dashai" "$@"
