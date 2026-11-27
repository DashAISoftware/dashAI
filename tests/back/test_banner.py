import io

from DashAI.__main__ import _print_banner


def test_banner_survives_output_without_box_drawing_characters(monkeypatch):
    # Output redirected to a file on Windows is cp1252
    out = io.TextIOWrapper(io.BytesIO(), encoding="cp1252")
    monkeypatch.setattr("sys.stdout", out)

    _print_banner()
