import os
import pickle

import numpy as np
from kink import di

from DashAI.back.core.enums.metrics import LevelEnum, SplitEnum
from DashAI.back.dependencies.database.models import Metric, Run
from DashAI.back.evaluation.base_evaluation_strategy import BaseEvaluationStrategy
from DashAI.back.models.model_factory import ModelFactory


class CrossValidationEvaluationStrategy(BaseEvaluationStrategy):
    def __init__(
        self, model, optimizer, run_optimizable_parameters, goal_metric, **kwargs
    ):
        super().__init__(model, optimizer, run_optimizable_parameters, goal_metric)

    def execute(self, x, y, factory: ModelFactory, run: Run, db):
        config = di["config"]
        plot_paths = []

        # Execute HPO if optimizer and there are parameters to optimize
        if self.optimizer and self.run_optimizable_parameters:
            self._do_hpo(x, y, factory, run, db)

            # Generate hyperparameter plot
            trials = self.optimizer.get_trials_values()
            plot_filenames, plots = self.optimizer.create_plots(
                trials,
                run.id,
                n_params=len(self.run_optimizable_parameters),
                goal_metric=self.goal_metric,
            )
            for filename, plot in zip(plot_filenames, plots):
                plot_path = os.path.join(config["RUNS_PATH"], filename)
                with open(plot_path, "wb") as file:
                    pickle.dump(plot, file)
                    plot_paths.append(plot_path)

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

        # Promediar métricas de los folds y guardarlas con level=LAST
        self._aggregate_fold_metrics(run.id)

        return self.model, plot_paths

    def _aggregate_fold_metrics(self, run_id: int):
        """Promediar métricas por fold y guardar como level=LAST.

        Lee todas las métricas con level=FOLD, las agrupa por nombre y split,
        calcula el promedio, y las guarda con level=LAST.

        Parameters
        ----------
        run_id : int
            ID de la run
        """

        with di["session_factory"]() as db:
            # Obtener todas las métricas con level=FOLD
            fold_metrics = (
                db.query(Metric)
                .filter(Metric.run_id == run_id, Metric.level == LevelEnum.FOLD)
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

                # Buscar si ya existe una métrica LAST con este nombre
                existing = (
                    db.query(Metric)
                    .filter_by(
                        run_id=run_id, split=split, level=LevelEnum.LAST, name=name
                    )
                    .first()
                )

                if existing:
                    # Actualizar con el promedio
                    existing.value = avg_value
                else:
                    # Crear nueva métrica
                    db.add(
                        Metric(
                            run_id=run_id,
                            split=split,
                            level=LevelEnum.LAST,
                            name=name,
                            value=avg_value,
                            step=0,
                        )
                    )

            db.commit()

    def evaluate(self, model, input_dataset, output_dataset, metric, **kwargs):
        fold_index = kwargs.get("fold_index")
        folds_results = []

        # Suponiendo que el último fold es el conjunto completo
        for i in range(len(input_dataset) - 1):
            x_fold = input_dataset[i]
            y_fold = output_dataset[i]

            # Aquí se entrenaría el modelo con x_fold e y_fold y se calcula la métrica
            self.model.x_data = x_fold
            self.model.y_data = y_fold

            model.train(x_fold["train"], y_fold["train"])

            y_pred = model.predict(x_fold["test"])

            output_dataset_transformed = model.prepare_output(
                y_fold["test"], is_fit=False
            )

            if fold_index is None:
                model.calculate_metrics(
                    split=SplitEnum.TRAIN, level=LevelEnum.TRIAL, fold_index=i
                )
                model.calculate_metrics(
                    split=SplitEnum.TEST, level=LevelEnum.TRIAL, fold_index=i
                )
            else:
                model.calculate_metrics(
                    split=SplitEnum.TRAIN,
                    level=LevelEnum.TRIAL,
                    fold_index=fold_index,
                    inner_fold_index=i,
                )
                model.calculate_metrics(
                    split=SplitEnum.TEST,
                    level=LevelEnum.TRIAL,
                    fold_index=fold_index,
                    inner_fold_index=i,
                )

            score = metric.score(output_dataset_transformed, y_pred)
            folds_results.append(score)

        # Retorna el promedio de las métricas de los folds
        return np.mean(folds_results)
