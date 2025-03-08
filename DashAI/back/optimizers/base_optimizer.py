"""Base Optimizer abstract class."""

import logging
from abc import ABCMeta, abstractmethod
from typing import Final

import numpy as np
import optuna
import plotly
import plotly.graph_objects as go
from optuna.importance import FanovaImportanceEvaluator

from DashAI.back.config_object import ConfigObject

log = logging.getLogger(__name__)


class BaseOptimizer(ConfigObject, metaclass=ABCMeta):
    """
    Abstract class of all hyperparameter's Optimizers.

    All models must extend this class and implement optimize method.
    """

    TYPE: Final[str] = "Optimizer"

    @abstractmethod
    def optimize(self, model, input, output, parameters, task):
        """
        Optimization process

        Args:
            model (class): class for the model from the current experiment
            dataset (dict): dict with the data to train and validation
            parameters (dict): dict with the information to create the search space

        Returns
        -------
            None
        """
        raise NotImplementedError(
            "Optimization modules must implement optimize method."
        )

    @abstractmethod
    def get_model(self):
        """
        Get the model with the best set of hyperparameters found

        Returns
        -------
            best_model (object): Object from the class model with
                                    the best hyperparameters found.
        """
        raise NotImplementedError(
            "Optimization modules must implement get_model method."
        )

    @abstractmethod
    def get_trials_values(self):
        """
        Get the trial values from the hyperparameter optimization process

        Returns
        -------
            trial_values (list): List with the hyperparameters
                                    values and the goal metric per trial.
        """
        raise NotImplementedError(
            "Optimization modules must implement get_trials_values method."
        )

    def history_objective_plot(self, trials):
        """
        Plot for the goal metric achieved per trial.

        Args:
            trial_values (list): List with the hyperparameters values
                                    and the goal metric per trial.

        Returns
        -------
            fig (json): json with the plot data
        """
        x = list(range(1, len(trials) + 1))
        y = [trial["value"] for trial in trials]
        max_cumulative = np.maximum.accumulate(y)
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=x,
                y=y,
                mode="markers",
                name="Optimization History",
                marker_color="blue",
                marker_size=8,
            )
        )
        fig.add_trace(
            go.Scatter(
                x=x,
                y=max_cumulative,
                mode="lines",
                name="Current Max Value",
                line_color="red",
                line_width=2,
            )
        )
        fig.update_layout(
            title="Optimization History with Current Max Value",
            xaxis_title="Trial",
            yaxis_title="Objective Value",
        )
        return plotly.io.to_json(fig)

    def slice_plot(self, trials):
        """
        Plot that compares the performance in the
        search space of one hyperparameter.

        Args:
            trial_values (list): List with the hyperparameters
                            values and the goal metric per trial.

        Returns
        -------
            fig (json): json with the plot data
        """
        param_names = list(trials[0]["params"].keys())

        traces = []
        for param_name in param_names:
            x_values = [trial["params"][param_name] for trial in trials]
            y_values = [trial["value"] for trial in trials]
            trial_numbers = list(range(1, len(trials) + 1))

            trace = go.Scatter(
                x=x_values,
                y=y_values,
                mode="markers",
                marker={
                    "size": 8,
                    "color": trial_numbers,
                    "colorscale": "Blues",
                    "colorbar": {"title": "Trial Number"},
                    "showscale": True,
                    "line": {"width": 0.2, "color": "black"},
                },
                name=param_name,
                visible=False,
            )
            traces.append(trace)

        traces[0]["visible"] = True

        buttons = []
        for i, param_name in enumerate(param_names):
            buttons.append(
                {
                    "method": "update",
                    "label": param_name,
                    "args": [
                        {"visible": [j == i for j in range(len(param_names))]},
                        {
                            "title": f"Slice plot for {param_name}",
                            "xaxis": {"title": param_name},
                        },
                    ],
                }
            )

        updatemenus = [{"buttons": buttons, "direction": "down", "showactive": True}]

        fig = go.Figure(data=traces)
        fig.update_layout(
            updatemenus=updatemenus,
            title=f"Slice plot for {param_names[0]}",
            xaxis_title=param_names[0],
            yaxis_title="Objective Value",
        )

        return plotly.io.to_json(fig)

    def contour_plot(self, trials):
        """
        Contour plot between two hyperparameters
        and the goal metric achieved in the search space.

        Args:
            trial_values (list): List with the hyperparameters values
                                and the goal metric per trial.

        Returns
        -------
            fig (json): json with the plot data
        """
        param_names = list(trials[0]["params"].keys())
        traces = []
        scatter_traces = []
        for param_x in param_names:
            for param_y in param_names:
                if param_x != param_y:
                    x_values = [
                        trial["params"][param_x]
                        for trial in trials
                        if param_x in trial["params"]
                    ]
                    y_values = [
                        trial["params"][param_y]
                        for trial in trials
                        if param_y in trial["params"]
                    ]
                    z_values = [
                        trial["value"]
                        for trial in trials
                        if param_x in trial["params"] and param_y in trial["params"]
                    ]

                    contour_trace = go.Contour(
                        x=x_values,
                        y=y_values,
                        z=z_values,
                        colorscale="Blues",
                        colorbar={"title": "Objective Value"},
                        showscale=True,
                        name=f"{param_x} vs {param_y}",
                        visible=False,
                    )
                    traces.append(contour_trace)

                    scatter_trace = go.Scatter(
                        x=x_values,
                        y=y_values,
                        mode="markers",
                        marker={
                            "size": 8,
                            "color": z_values,
                            "colorscale": "Blues",
                            "colorbar": {"title": "Objective Value"},
                            "showscale": False,
                            "line": {"width": 0.2, "color": "black"},
                        },
                        name=f"{param_x} vs {param_y} points",
                        visible=False,
                    )
                    scatter_traces.append(scatter_trace)

        traces[0]["visible"] = True
        scatter_traces[0]["visible"] = True

        buttons = []
        for i in range(len(traces)):
            buttons.append(
                {
                    "method": "update",
                    "label": traces[i]["name"],
                    "args": [
                        {
                            "visible": [j == i for j in range(len(traces))]
                            + [j == i for j in range(len(scatter_traces))]
                        },
                        {"title": f'Contour plot for {traces[i]["name"]}'},
                    ],
                }
            )

        updatemenus = [{"buttons": buttons, "direction": "down", "showactive": True}]

        fig = go.Figure(data=traces + scatter_traces)
        fig.update_layout(
            updatemenus=updatemenus,
            title=f'Contour plot for {traces[0]["name"]}',
            xaxis_title=param_names[0],
            yaxis_title=param_names[1],
        )
        return plotly.io.to_json(fig)

    def importance_plot(self, trials):
        """
        Plot to obtain the importance between all the hyperparameters
        involved in hyperparameter optimization.

        Args:
            trial_values (list): List with the hyperparameters values
                                and the goal metric per trial.

        Returns
        -------
            fig (json): json with the plot data
        """
        distributions = {}
        for param, (low, high) in self.parameters.items():
            if isinstance(low, int):
                distributions[param] = optuna.distributions.IntDistribution(low, high)
            elif isinstance(low, float):
                distributions[param] = optuna.distributions.FloatDistribution(low, high)

        study = optuna.create_study(direction="maximize")
        for trial in trials:
            study.add_trial(
                optuna.trial.create_trial(
                    params=trial["params"],
                    distributions=distributions,
                    value=trial["value"],
                    state=optuna.trial.TrialState.COMPLETE,
                )
            )
        evaluator = FanovaImportanceEvaluator()
        importances = evaluator.evaluate(study)
        try:
            evaluator = FanovaImportanceEvaluator()
            importances = evaluator.evaluate(study)
        except RuntimeError:
            importances = {
                param: 1.0 / len(self.parameters) for param in self.parameters
            }
            log.warning(
                "Could not calculate parameter importance using FANOVA. "
                "Using equal importances."
            )

        sorted_items = sorted(importances.items(), key=lambda item: item[1])
        param_names, importance_values = zip(*sorted_items)
        fig = go.Figure(
            data=[
                go.Bar(
                    x=importance_values,
                    y=param_names,
                    orientation="h",
                    text=importance_values,
                    textposition="outside",
                    texttemplate="%{text:.2f}",
                )
            ]
        )

        fig.update_layout(
            title="Hyperparameter importance",
            xaxis_title="Importance",
            yaxis_title="Hyperparameter",
            yaxis={"tickangle": 0},
        )

        return plotly.io.to_json(fig)

    def create_plots(self, trials, run_id, n_params):
        """
        List of available plots.

        Args:
            trials (list): List with the hyperparameters values
                            and the goal metric per trial.
            run_id (int): Number with the id associated to the current run
                            from the experiment.
            n_params (int): Number of the different hyperparameters involved
                            in the process of hyperparameter optimization

        Returns
        -------
            fig (json): json with the plot data
        """
        if n_params >= 2:
            plots_filenames = [
                f"history_objective_plot_{run_id}.pickle",
                f"slice_plot_{run_id}.pickle",
                f"contour_plot_{run_id}.pickle",
                f"importance_plot_{run_id}.pickle",
            ]
            plots_list = [
                self.history_objective_plot(trials),
                self.slice_plot(trials),
                self.contour_plot(trials),
                self.importance_plot(trials),
            ]
            return plots_filenames, plots_list
        else:
            plots_filenames = [
                f"history_objective_plot_{run_id}.pickle",
                f"slice_plot_{run_id}.pickle",
            ]
            plots_list = [self.history_objective_plot(trials), self.slice_plot(trials)]
            return plots_filenames, plots_list
