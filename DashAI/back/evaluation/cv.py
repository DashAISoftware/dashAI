from functools import partial

import numpy as np
from kink import di

from DashAI.back.core.enums.metrics import LevelEnum, SplitEnum
from DashAI.back.dependencies.database.models import Metric, Run
from DashAI.back.evaluation.base_evaluation_strategy import BaseEvaluationStrategy
from DashAI.back.models.model_factory import ModelFactory
from DashAI.back.splitters.base_splitter import BaseSplitter


class CrossValidationEvaluationStrategy(BaseEvaluationStrategy):
    def __init__(
        self, model, optimizer, run_optimizable_parameters, goal_metric, **kwargs
    ):
        super().__init__(model, optimizer, run_optimizable_parameters, goal_metric)

    def execute(self, x, y, factory: ModelFactory, run: Run, db):
        plot_paths = []

        # Execute HPO if optimizer and there are parameters to optimize
        if self.optimizer and self.run_optimizable_parameters:
            if run.nested:
                try:
                    registry = di["component_registry"]

                    inner_splits = run.nested
                    splitter_name = inner_splits.get("splitter_name", None)
                    self.inner_splitter: BaseSplitter = registry[splitter_name][
                        "class"
                    ](inner_splits)
                except Exception as e:
                    raise ValueError(
                        f"Error configuring inner splitter for nested CV: {e}"
                    ) from e

                self._nested_cv(run.id, self.model, x, y)

            self._do_hpo(x, y, factory, run, db)
            plot_paths = self._generate_hpo_plots(run)

        # El último fold es el conjunto completo
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

        # Promediar métricas de los folds y guardarlas con level=LAST
        self._aggregate_fold_metrics(
            run_id=run.id, level_to_agg=LevelEnum.FOLD, level_to_save=LevelEnum.LAST
        )

        self.model.train(x[-1]["train"], y[-1]["train"])

        return self.model, plot_paths

    def evaluate(self, model, input_dataset, output_dataset, metric, **kwargs):
        # fold_index es None cuando NO se está haciendo nested CV
        fold_index = kwargs.get("fold_index")
        folds_results = []  # Valores de la métrica objetivo para cada fold
        # Acumuladores de metricas a lo largo de los folds
        train_results = {}
        test_results = {}

        # Validacion cruzada que representa el loop interno en caso de nested CV,
        # o el loop externo en caso de CV simple
        for i in range(len(input_dataset) - 1):
            x_fold = input_dataset[i]
            y_fold = output_dataset[i]

            # Aquí se entrenaría el modelo con x_fold e y_fold y se calcula la métrica
            self.model.x_data = x_fold
            self.model.y_data = y_fold

            model.train(x_fold["train"], y_fold["train"])

            train_scores = model.compute_metrics(split=SplitEnum.TRAIN)
            test_scores = model.compute_metrics(split=SplitEnum.TEST)
            folds_results.append(test_scores[metric.__name__])

            # Acumular metricas solo si no estamos haciendo nested CV
            if fold_index is None:
                for results, scores in [
                    (train_results, train_scores),
                    (test_results, test_scores),
                ]:
                    for metric_name, value in scores.items():
                        if metric_name not in results:
                            results[metric_name] = []
                        results[metric_name].append(value)

        if fold_index is None:
            # Promediar resultados de los folds solo si no estamos haciendo nested CV
            averaged_train_results = {
                metric: np.mean(values) for metric, values in train_results.items()
            }
            averaged_test_results = {
                metric: np.mean(values) for metric, values in test_results.items()
            }

            # Guardar resultados promediados en la base de datos con level=TRIAL
            model._save_metrics(
                results=averaged_train_results,
                split=SplitEnum.TRAIN,
                level=LevelEnum.TRIAL,
            )
            model._save_metrics(
                results=averaged_test_results,
                split=SplitEnum.TEST,
                level=LevelEnum.TRIAL,
            )

        # Retorna el promedio de las métricas de los folds
        return np.mean(folds_results)

    def _nested_cv(self, run_id, model, input_dataset, output_dataset):
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

        # Promediar métricas de los outer folds y guardarlas con level=LAST_OUTER
        self._aggregate_fold_metrics(
            run_id=run_id,
            level_to_agg=LevelEnum.OUTER_FOLD,
            level_to_save=LevelEnum.LAST_OUTER,
        )

    def _aggregate_fold_metrics(
        self, run_id: int, level_to_agg=LevelEnum.FOLD, level_to_save=LevelEnum.LAST
    ):
        """Promediar métricas por fold y guardar como level=LAST.

        Lee todas las métricas con level=level_to_agg, las agrupa por nombre y split,
        calcula el promedio, y las guarda con level=level_to_save.

        Parameters
        ----------
        run_id : int
            ID de la run
        level_to_agg : LevelEnum, optional
            Nivel de las métricas a agregar
        level_to_save : LevelEnum, optional
            Nivel con el que se guardarán las métricas agregadas
        """

        with di["session_factory"]() as db:
            # Obtener todas las métricas con level=level_to_agg para esta run
            fold_metrics = (
                db.query(Metric)
                .filter(Metric.run_id == run_id, Metric.level == level_to_agg)
                .all()
            )

            if not fold_metrics:
                return

            # Agrupar métricas por (split, nombre)
            metrics_by_split_name = {}
            for metric in fold_metrics:
                key = (metric.split, metric.name)
                if key not in metrics_by_split_name:
                    metrics_by_split_name[key] = []
                metrics_by_split_name[key].append(metric.value)

            # Promediar y guardar como level=LAST
            for (split, name), values in metrics_by_split_name.items():
                avg_value = np.mean(values)
                std_value = np.std(values) if len(values) > 1 else 0.0

                # Buscar si ya existe una métrica 'level_to_save' con este nombre
                existing = (
                    db.query(Metric)
                    .filter_by(
                        run_id=run_id, split=split, level=level_to_save, name=name
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
                            level=level_to_save,
                            name=name,
                            value=avg_value,
                            std_value=std_value,
                            step=0,
                        )
                    )

            db.commit()
