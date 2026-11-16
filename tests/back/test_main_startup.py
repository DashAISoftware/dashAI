"""How ``python -m DashAI`` waits for its backend (``DashAI/__main__.py``)."""

import socket
import threading
import time

from DashAI import __main__ as main


def test_the_window_waits_while_the_backend_is_still_starting(monkeypatch):
    # A long plugin repair (large dependencies, slow network) must not make the
    # window give up and close dashAI mid-repair.
    monkeypatch.setattr(main, "_BACKEND_START_SECONDS", 0.5)
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    port = listener.getsockname()[1]

    def backend():
        time.sleep(1.5)  # still repairing when the fixed limit is reached
        listener.listen()

    starting = threading.Thread(target=backend)
    starting.start()
    try:
        assert main._wait_for_backend_server(port=port, starting=starting.is_alive)
    finally:
        starting.join()
        listener.close()
