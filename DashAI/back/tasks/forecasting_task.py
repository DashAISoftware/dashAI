from DashAI.back.tasks.base_task import BaseTask


class ForecastingTask(BaseTask):
    """The family of tasks that forecast a series forward in time.

    A forecasting task has a time index, and predicts forward from the end of
    the history it was given. That much holds for every kind of forecasting,
    and it is all this class says. The concrete tasks inherit from it and
    declare everything else, because that is where the kinds differ: how many
    series there are, whether they form a hierarchy, whether the dates sit on a
    regular grid. Roles, preparation, splitters, strategies, models and
    metrics all depend on that structure.

    The family is never registered. A component that names it would hold a
    relationship nobody queries, because the registry resolves compatibility
    by exact name: name the concrete task instead. Something every kind needs
    would be declared here, in this class's own ``COMPATIBLE_COMPONENTS``,
    which the registry collects through the concrete task's MRO.

    Two routes lead to a forecast in DashAI, and this family is one of them.
    The other is ``TimeSeriesWindowConverter``, which reshapes a series into
    lag columns and hands it to ``RegressionTask``, making every existing
    regressor usable.
    """

    PREDICTS_FORWARD_ONLY: bool = True
