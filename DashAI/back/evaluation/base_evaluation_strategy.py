"""What a run records, declared per strategy.

These classes used to run the training too: ``execute`` took the run row and the
database session and did the fitting, the search, the scoring, the aggregation
and the persistence behind one method. That work is the units' now -- see
``FitModelUnit``, ``FitModelOverFoldsUnit`` and their siblings -- and what is
left here is what was underneath it all along: a declaration of how a run is
carved and which partitions it records a score for.

**They stay registered even though they no longer do anything.** The frontend
reads them in four places, and only one is about metrics:

- the session wizard lists them so the user can choose one, and
  ``ModelSession.evaluation_strategy`` is NOT NULL, so without that listing a
  session cannot be created at all;
- it starts on the first one whose ``kind`` is holdout;
- ``kind`` decides the shape of the splits payload and which controls are shown;
- ``scored_splits`` tells the metric charts which partitions exist to plot.

There is precedent for a class in this codebase that declares and does not
execute: ``BaseSplitter.PARTITIONING`` and ``explainable_partitions`` are read
the same way, by the backend and by the frontend, and nothing calls them to do
work.
"""

from typing import Final, Optional

from DashAI.back.core.enums.metrics import SplitEnum


class BaseEvaluationStrategy:
    """How a run is carved, and what it records.

    Subclasses declare; none of them execute.
    """

    TYPE: Final[str] = "EvaluationStrategy"

    #: Whether this strategy splits the dataset once, into folds, or not at
    #: all. It decides which unit fits the run and which controls the session
    #: wizard offers. The unit that prepares the data is picked from the
    #: splitter's ``PARTITIONING``, so the two have to agree; see below.
    KIND: str = "holdout"

    #: The ``PARTITIONING`` of the splitters this strategy takes, or None when
    #: it takes no splitter. The session API refuses any other splitter,
    #: because the units that prepare a holdout and a fold run publish
    #: different keys and the fitting unit only reads its own: a holdout
    #: strategy with a fold splitter would fail every run with a missing
    #: context key.
    SPLITTER_PARTITIONING: Optional[str] = "holdout"

    #: The partitions a run records a score for. Not the same as which
    #: partitions have metrics configured: a forecaster has training metrics
    #: and still must not be judged on the dates it was fitted on, because an
    #: in-sample fit statistic is not comparable with a forecast. A screen that
    #: offers one control per partition reads this instead of assuming all
    #: three exist.
    SCORED_SPLITS: tuple = (SplitEnum.TRAIN, SplitEnum.VALIDATION, SplitEnum.TEST)

    #: The partition the kept model was fitted on, which is what decides which
    #: partitions of a finished run can still be predicted.
    FINAL_FIT_PARTITIONS: tuple = ("train",)

    #: The splitter a new session starts on, or None for the first one the
    #: task offers among those of ``SPLITTER_PARTITIONING``. Declared so the
    #: wizard does not pick one by name.
    DEFAULT_SPLITTER: Optional[str] = None

    #: The views of a finished run beyond its metrics, which the run screens
    #: show as tabs. ``"fold_metrics"``: a score per fold or origin, served by
    #: ``/fold-metrics``. ``"forecasts"``: the forecasts of every origin,
    #: served by ``/run/{id}/forecasts``. Declared so the frontend does not
    #: infer from ``KIND`` what a run kept.
    RESULT_VIEWS: tuple = ()

    @classmethod
    def get_metadata(cls) -> dict:
        """Describe the strategy for the frontend.

        Returns
        -------
        dict
            Mapping with ``kind``, which says whether this strategy splits the
            dataset once or into folds; ``scored_splits``, the partitions it
            writes metrics for; ``splitter_partitioning`` and
            ``default_splitter``, which splitters it takes and which one a
            session starts on; and ``result_views``, the views a finished run
            offers.
        """
        return {
            "kind": cls.KIND,
            "scored_splits": [split.value for split in cls.SCORED_SPLITS],
            "splitter_partitioning": cls.SPLITTER_PARTITIONING,
            "default_splitter": cls.DEFAULT_SPLITTER,
            "result_views": list(cls.RESULT_VIEWS),
        }
