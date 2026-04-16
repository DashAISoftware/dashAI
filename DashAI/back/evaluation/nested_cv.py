from DashAI.back.evaluation.base_evaluation_strategy import BaseEvaluationStrategy


class NestedCrossValidationStrategy(BaseEvaluationStrategy):
    def __init__(
        self, model, optimizer, run_optimizable_parameters, goal_metric, **kwargs
    ):
        super().__init__(model, optimizer, run_optimizable_parameters, goal_metric)

        self.inner_splitter = kwargs.get("inner_splitter")
