from functools import partial

import numpy as np
from kink import di

from DashAI.back.core.enums.metrics import LevelEnum, SplitEnum
from DashAI.back.dependencies.database.models import Metric, Run
from DashAI.back.evaluation.cv import CrossValidationEvaluationStrategy
from DashAI.back.models.model_factory import ModelFactory
from DashAI.back.splitters.fold_splitter import FoldSplitter


class NestedCrossValidationStrategy(CrossValidationEvaluationStrategy):
    def __init__(
        self, model, optimizer, run_optimizable_parameters, goal_metric, **kwargs
    ):
        super().__init__(model, optimizer, run_optimizable_parameters, goal_metric)
        self.inner_splitter: FoldSplitter = kwargs.get("inner_splitter")

    def execute(self, x, y, factory: ModelFactory, run: Run, db):
        plot_paths = []

        self.nested_cv(self.model, x, y)
        self._do_hpo(x, y, factory, run, db)

        # Suponiendo que el último fold es el conjunto completo
        for i in range(len(x) - 1):
            x_fold = x[i]
            y_fold = y[i]

            self.model.x_data = x_fold
            self.model.y_data = y_fold

            self.model.train(x_fold["train"], y_fold["train"])

            self.model.calculate_metrics(
                split=SplitEnum.TRAIN, level=LevelEnum.FOLD, fold_index=i
            )
            self.model.calculate_metrics(
                split=SplitEnum.TEST, level=LevelEnum.FOLD, fold_index=i
            )

        self.model.train(x[-1]["train"], y[-1]["train"])

        # Agregar métricas de folds y outer folds
        self._aggregate_fold_metrics(run.id)
        self._aggregate_outer_fold_metrics(run.id)

        return self.model, plot_paths

    def nested_cv(self, model, input_dataset, output_dataset):
        # Implement the logic to evaluate the model using nested cross-validation
        # This will involve using self.inner_splitter
        # to create inner folds and evaluating the model on those folds

        for i in range(len(input_dataset) - 1):
            x_outer = input_dataset[i]
            y_outer = output_dataset[i]

            # Use inner_splitter to create inner folds
            inner_x, inner_y, _ = self.inner_splitter.split(
                x_outer["train"], y_outer["train"]
            )

            strategy_with_context = partial(self.evaluate, fold_index=i)
            # Evaluate the model on the inner folds
            # best model is the best model obtained from the inner fold in all trials
            self.model, _ = self.optimizer.optimize(
                model,
                inner_x,
                inner_y,
                self.run_optimizable_parameters,
                self.goal_metric,
                strategy=strategy_with_context,
            )

            self.model.x_data = x_outer
            self.model.y_data = y_outer

            self.model.train(x_outer["train"], y_outer["train"])

            self.model.calculate_metrics(
                split=SplitEnum.TEST, level=LevelEnum.OUTER_FOLD, fold_index=i
            )
            self.model.calculate_metrics(
                split=SplitEnum.TRAIN, level=LevelEnum.OUTER_FOLD, fold_index=i
            )

    def _aggregate_outer_fold_metrics(self, run_id: int):
        """Promediar métricas de outer folds y guardar como level=LAST.

        Lee todas las métricas con level=OUTER_FOLD, las agrupa por nombre y split,
        calcula el promedio y desviación estándar, y las guarda con level=LAST.

        Parameters
        ----------
        run_id : int
            ID de la run
        """

        with di["session_factory"]() as db:
            # Obtener todas las métricas con level=OUTER_FOLD
            outer_fold_metrics = (
                db.query(Metric)
                .filter(Metric.run_id == run_id, Metric.level == LevelEnum.OUTER_FOLD)
                .all()
            )

            if not outer_fold_metrics:
                return

            # Agrupar métricas por (split, nombre)
            metrics_by_split_name = {}
            for metric in outer_fold_metrics:
                key = (metric.split, metric.name)
                if key not in metrics_by_split_name:
                    metrics_by_split_name[key] = []
                metrics_by_split_name[key].append(metric.value)

            # Promediar y guardar como level=LAST
            for (split, name), values in metrics_by_split_name.items():
                avg_value = np.mean(values)
                std_value = np.std(values) if len(values) > 1 else 0.0

                # Buscar si ya existe una métrica LAST con este nombre
                existing = (
                    db.query(Metric)
                    .filter_by(
                        run_id=run_id, split=split, level=LevelEnum.LAST, name=name
                    )
                    .first()
                )

                if existing:
                    # Actualizar con el promedio y desviación estándar
                    existing.value = avg_value
                    existing.std_value = std_value
                else:
                    # Crear nueva métrica
                    db.add(
                        Metric(
                            run_id=run_id,
                            split=split,
                            level=LevelEnum.LAST,
                            name=name,
                            value=avg_value,
                            std_value=std_value,
                            step=0,
                        )
                    )

            db.commit()
