"""Translation Metrics Tests."""

import pytest
from datasets import Dataset

from DashAI.back.metrics.translation.bleu import Bleu
from DashAI.back.metrics.translation.ter import Ter


@pytest.fixture(scope="module", name="metric_input")
def fixture_metric_input() -> dict:
    return {
        "true_sentences": Dataset.from_list(
            [{"foo": "Tuve que hacerlo"}, {"foo": "Quiero que suspendas la pelea."}]
        ),
        "pred_sentences": ["Tuve que hacerlo", "Quiero que suspendas la pelea."],
        "wrong_size_sentences": ["Tuve que hacerlo"],
    }


def test_bleu(metric_input: dict):
    score = Bleu.score(metric_input["true_sentences"], metric_input["pred_sentences"])

    assert isinstance(score, float)
    assert score >= 0.0
    assert score <= 1.0


def test_ter(metric_input: dict):
    score = Ter.score(metric_input["true_sentences"], metric_input["pred_sentences"])

    assert isinstance(score, float)
    assert score >= 0.0
    assert score <= 1.0


def test_metrics_different_input_sizes(metric_input: dict):
    with pytest.raises(ValueError) as excinfo:
        Bleu.score(metric_input["true_sentences"], metric_input["wrong_size_sentences"])
    err_msg = str(excinfo.value)
    assert "length of the true labels" in err_msg
    assert "must be equal" in err_msg

    with pytest.raises(ValueError) as excinfo:
        Ter.score(metric_input["true_sentences"], metric_input["wrong_size_sentences"])
    err_msg = str(excinfo.value)
    assert "length of the true labels" in err_msg
    assert "must be equal" in err_msg
