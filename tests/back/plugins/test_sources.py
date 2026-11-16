"""Trust levels: each source declares its own on the shared tier scale."""

import pytest

from DashAI.back.plugins.sources import (
    needs_ack,
    trust_level,
)
from DashAI.back.plugins.sources.local_source import UNKNOWN


@pytest.mark.parametrize(
    ("name", "asks"),
    [
        ("github_attested", False),
        ("github_source", False),
        ("github_asset", True),
        ("local", True),
        ("unknown", True),
    ],
)
def test_what_asks_to_acknowledge_the_risk(name, asks):
    assert needs_ack(name) is asks


@pytest.mark.parametrize("name", [None, "", "from_a_newer_dashai"])
def test_a_name_no_source_declares_is_unknown(name):
    assert trust_level(name) == UNKNOWN
