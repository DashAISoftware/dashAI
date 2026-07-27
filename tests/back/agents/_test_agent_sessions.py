# ruff: noqa
from DashAI.back.Agent_tools.tools_datasets import delete_dataset
from tests.back.agents.traces.traces_sessions import (
    build_test_add_model_to_session_output,
    build_test_create_session_output,
    build_test_delete_model_from_session_output,
    build_test_delete_session_output,
    build_test_get_models_execution_metrics_output,
    build_test_get_session_parameters_output,
    build_test_get_sessions_output,
    build_test_run_model_output,
)
from tests.back.agents.utils import (
    assert_evaluations_agent,
    create_model_session,
    create_model_session_with_dataset,
    create_session_with_model,
    load_iris_dataset,
    run_agent_case,
    upload_iris_dataset,
    upload_regression_dataset,
    upload_text_classification_dataset,
    upload_translation_mini_dataset,
)


def test_get_sessions(agent, llm_judge, tool_calling_evaluator, tool_args_evaluator):
    reference_outputs = build_test_get_sessions_output()
    user_input = "Muestra las sesiones de modelos disponibles en DashAI."
    results = run_agent_case(
        agent,
        llm_judge,
        tool_calling_evaluator,
        tool_args_evaluator,
        "test_get_sessions",
        user_input,
        reference_outputs,
        results_file_name="test_agent_sessions_results.json",
    )
    assert_evaluations_agent(results)


def test_get_session_parameters(
    agent, llm_judge, tool_calling_evaluator, tool_args_evaluator
):
    create_model_session_with_dataset(
        dataset_name="iris_sessions_parameters",
        task_name="TabularClassificationTask",
        input_columns=[
            "SepalLengthCm",
            "SepalWidthCm",
            "PetalLengthCm",
            "PetalWidthCm",
        ],
        output_columns=["Species"],
    )
    session_id = 1
    reference_outputs = build_test_get_session_parameters_output(session_id)
    user_input = "Obtén los parámetros de la sesión de modelo del dataset iris."
    results = run_agent_case(
        agent,
        llm_judge,
        tool_calling_evaluator,
        tool_args_evaluator,
        "test_get_session_parameters",
        user_input,
        reference_outputs,
        results_file_name="test_agent_sessions_results.json",
    )
    delete_dataset.invoke({"dataset_id": 1})
    assert_evaluations_agent(results)


def test_delete_session(agent, llm_judge, tool_calling_evaluator, tool_args_evaluator):
    create_model_session_with_dataset(
        dataset_name="iris_sessions_delete",
        task_name="TabularClassificationTask",
        input_columns=[
            "SepalLengthCm",
            "SepalWidthCm",
            "PetalLengthCm",
            "PetalWidthCm",
        ],
        output_columns=["Species"],
    )
    session_id = 1
    reference_outputs = build_test_delete_session_output(session_id)
    user_input = "Elimina la sesión de modelo del dataset iris.  Confirmo la acción, estoy seguro de ejecutarla."
    results = run_agent_case(
        agent,
        llm_judge,
        tool_calling_evaluator,
        tool_args_evaluator,
        "test_delete_session",
        user_input,
        reference_outputs,
        results_file_name="test_agent_sessions_results.json",
    )
    delete_dataset.invoke({"dataset_id": 1})
    assert_evaluations_agent(results)


def test_get_models_execution_metrics(
    agent, llm_judge, tool_calling_evaluator, tool_args_evaluator
):
    create_model_session_with_dataset(
        dataset_name="iris_sessions_metrics",
        task_name="TabularClassificationTask",
        input_columns=[
            "SepalLengthCm",
            "SepalWidthCm",
            "PetalLengthCm",
            "PetalWidthCm",
        ],
        output_columns=["Species"],
    )
    session_id = 1
    reference_outputs = build_test_get_models_execution_metrics_output(session_id)
    user_input = (
        "Obtén las métricas de ejecución de los modelos de la sesión del dataset iris."
    )
    results = run_agent_case(
        agent,
        llm_judge,
        tool_calling_evaluator,
        tool_args_evaluator,
        "test_get_models_execution_metrics",
        user_input,
        reference_outputs,
        results_file_name="test_agent_sessions_results.json",
    )
    delete_dataset.invoke({"dataset_id": 1})
    assert_evaluations_agent(results)


def test_create_session(agent, llm_judge, tool_calling_evaluator, tool_args_evaluator):
    load_iris_dataset("iris_create_session")
    reference_outputs = build_test_create_session_output(
        1,
        "TabularClassificationTask",
        "session_tabular_classification",
        ["SepalLengthCm", "SepalWidthCm", "PetalLengthCm", "PetalWidthCm"],
        ["Species"],
        {
            "train": 0.6,
            "validation": 0.2,
            "test": 0.2,
            "shuffle": True,
            "stratify": True,
            "seed": 42,
            "splitType": "random",
        },
    )
    user_input = (
        "Crea una sesión de modelo para el dataset iris con task_name TabularClassificationTask, "
        "name session_tabular_classification, input_columns SepalLengthCm, SepalWidthCm, PetalLengthCm, PetalWidthCm, output_columns Species y splits aleatorios con train 0.6, "
        "validation 0.2, test 0.2, shuffle true, stratify true y seed 42."
    )
    results = run_agent_case(
        agent,
        llm_judge,
        tool_calling_evaluator,
        tool_args_evaluator,
        "test_create_session",
        user_input,
        reference_outputs,
        results_file_name="test_agent_sessions_results.json",
    )
    delete_dataset.invoke({"dataset_id": 1})
    assert_evaluations_agent(results)


def test_add_model_knn_neighbors(
    agent, llm_judge, tool_calling_evaluator, tool_args_evaluator
):
    create_model_session(
        upload_iris_dataset,
        "iris_add_model",
        "TabularClassificationTask",
        ["SepalLengthCm", "SepalWidthCm", "PetalLengthCm", "PetalWidthCm"],
        ["Species"],
    )
    reference_outputs = build_test_add_model_to_session_output(
        1,
        "KNeighborsClassifier",
        "iris_knn_run",
        {"n_neighbors": 3, "weights": "uniform", "algorithm": "auto"},
        "",
        None,
        "",
        "",
    )
    user_input = (
        "Agrega un modelo KNeighborsClassifier a la sesión del dataset iris.  Debes buscar la única sesión de model existente. "
        "con run_name iris_knn_run, parámetros n_neighbors 3, weights uniform y algorithm auto."
    )
    results = run_agent_case(
        agent,
        llm_judge,
        tool_calling_evaluator,
        tool_args_evaluator,
        "test_add_model_knn_neighbors",
        user_input,
        reference_outputs,
        results_file_name="test_agent_sessions_results.json",
    )
    delete_dataset.invoke({"dataset_id": 1})
    assert_evaluations_agent(results)


def test_add_model_opus_mt_en_es(
    agent, llm_judge, tool_calling_evaluator, tool_args_evaluator
):
    create_model_session(
        upload_translation_mini_dataset,
        "translation_add_model",
        "TranslationTask",
        ["english"],
        ["spanish"],
    )
    reference_outputs = build_test_add_model_to_session_output(
        1,
        "OpusMtEnESTransformer",
        "translation_transformer_run",
        {
            "num_train_epochs": 1,
            "batch_size": 4,
            "learning_rate": 2e-5,
            "device": "CPU",
            "weight_decay": 0.01,
        },
        "",
        None,
        "",
        "",
    )
    user_input = (
        "Agrega un modelo OpusMtEnESTransformer a la sesión del dataset de traducción.  Debes buscar la única sesión de model existente "
        "con run_name translation_transformer_run, parámetros num_train_epochs 1, batch_size 4, learning_rate 2e-5 y device CPU."
    )
    results = run_agent_case(
        agent,
        llm_judge,
        tool_calling_evaluator,
        tool_args_evaluator,
        "test_add_model_opus_mt_en_es",
        user_input,
        reference_outputs,
        results_file_name="test_agent_sessions_results.json",
    )
    delete_dataset.invoke({"dataset_id": 1})
    assert_evaluations_agent(results)


def test_add_model_linear_regression(
    agent, llm_judge, tool_calling_evaluator, tool_args_evaluator
):
    create_model_session(
        upload_regression_dataset,
        "regression_add_model",
        "RegressionTask",
        ["x"],
        ["y"],
    )
    reference_outputs = build_test_add_model_to_session_output(
        1,
        "LinearRegression",
        "regression_linear_run",
        {"fit_intercept": True, "copy_X": True, "n_jobs": None, "positive": False},
        "",
        None,
        "",
        "",
    )
    user_input = (
        "Agrega un modelo LinearRegression a la sesión del dataset de regresión.  Debes buscar la única sesión de model existente "
        "con run_name regression_linear_run, parámetros fit_intercept true, copy_X true, n_jobs none y positive false."
    )
    results = run_agent_case(
        agent,
        llm_judge,
        tool_calling_evaluator,
        tool_args_evaluator,
        "test_add_model_linear_regression",
        user_input,
        reference_outputs,
        results_file_name="test_agent_sessions_results.json",
    )
    delete_dataset.invoke({"dataset_id": 1})
    assert_evaluations_agent(results)


def test_add_model_distil_bert(
    agent, llm_judge, tool_calling_evaluator, tool_args_evaluator
):
    create_model_session(
        upload_text_classification_dataset,
        "corona_add_model",
        "TextClassificationTask",
        ["OriginalTweet"],
        ["Sentiment"],
    )
    reference_outputs = build_test_add_model_to_session_output(
        1,
        "DistilBertTransformer",
        "corona_transformer_run",
        {
            "num_train_epochs": 1,
            "batch_size": 16,
            "learning_rate": 3e-5,
            "device": "CPU",
            "weight_decay": 0.01,
        },
        "",
        None,
        "",
        "",
    )
    user_input = (
        "Agrega un modelo DistilBertTransformer a la sesión del dataset de clasificación de texto.  Debes buscar la única sesión de model existente "
        "con run_name corona_transformer_run, parámetros num_train_epochs 1, batch_size 16, learning_rate 3e-5 y device CPU."
    )
    results = run_agent_case(
        agent,
        llm_judge,
        tool_calling_evaluator,
        tool_args_evaluator,
        "test_add_model_distil_bert",
        user_input,
        reference_outputs,
        results_file_name="test_agent_sessions_results.json",
    )
    delete_dataset.invoke({"dataset_id": 1})
    assert_evaluations_agent(results)


def test_add_model_svc(agent, llm_judge, tool_calling_evaluator, tool_args_evaluator):
    create_model_session(
        upload_iris_dataset,
        "iris_svc_add_model",
        "TabularClassificationTask",
        ["SepalLengthCm", "SepalWidthCm", "PetalLengthCm", "PetalWidthCm"],
        ["Species"],
    )
    reference_outputs = build_test_add_model_to_session_output(
        1,
        "SVC",
        "iris_svc_run",
        {
            "C": 1.0,
            "coef0": 1.0,
            "degree": 1.0,
            "gamma": "scale",
            "kernel": "rbf",
            "max_iter": -1,
            "shrinking": True,
            "tol": 1.0,
        },
        "",
        None,
        "",
        "",
    )
    user_input = (
        "Agrega un modelo SVC a la sesión del dataset iris. Debes buscar la única sesión de model existente "
        "con run_name iris_svc_run, parámetros C 1.0, coef0 1.0, degree 1.0, gamma scale, kernel rbf, max_iter -1, shrinking true y tol 1.0."
    )
    results = run_agent_case(
        agent,
        llm_judge,
        tool_calling_evaluator,
        tool_args_evaluator,
        "test_add_model_svc",
        user_input,
        reference_outputs,
        results_file_name="test_agent_sessions_results.json",
    )
    delete_dataset.invoke({"dataset_id": 1})
    assert_evaluations_agent(results)


def test_add_model_decision_tree_classifier(
    agent, llm_judge, tool_calling_evaluator, tool_args_evaluator
):
    create_model_session(
        upload_iris_dataset,
        "iris_dt_add_model",
        "TabularClassificationTask",
        ["SepalLengthCm", "SepalWidthCm", "PetalLengthCm", "PetalWidthCm"],
        ["Species"],
    )
    reference_outputs = build_test_add_model_to_session_output(
        1,
        "DecisionTreeClassifier",
        "iris_dt_run",
        {
            "criterion": "gini",
            "max_depth": 3,
            "min_samples_split": 2,
            "min_samples_leaf": 1,
            "max_features": None,
        },
        "",
        None,
        "",
        "",
    )
    user_input = (
        "Agrega un modelo DecisionTreeClassifier a la sesión del dataset iris. Debes buscar la única sesión de model existente "
        "con run_name iris_dt_run, parámetros criterion gini, max_depth 3, min_samples_split 2, min_samples_leaf 1 y max_features none."
    )
    results = run_agent_case(
        agent,
        llm_judge,
        tool_calling_evaluator,
        tool_args_evaluator,
        "test_add_model_decision_tree_classifier",
        user_input,
        reference_outputs,
        results_file_name="test_agent_sessions_results.json",
    )
    delete_dataset.invoke({"dataset_id": 1})
    assert_evaluations_agent(results)


def test_add_model_dummy_classifier(
    agent, llm_judge, tool_calling_evaluator, tool_args_evaluator
):
    create_model_session(
        upload_iris_dataset,
        "iris_dummy_add_model",
        "TabularClassificationTask",
        ["SepalLengthCm", "SepalWidthCm", "PetalLengthCm", "PetalWidthCm"],
        ["Species"],
    )
    reference_outputs = build_test_add_model_to_session_output(
        1,
        "DummyClassifier",
        "iris_dummy_run",
        {"strategy": "prior"},
        "",
        None,
        "",
        "",
    )
    user_input = (
        "Agrega un modelo DummyClassifier a la sesión del dataset iris. Debes buscar la única sesión de model existente "
        "con run_name iris_dummy_run, parámetro strategy prior."
    )
    results = run_agent_case(
        agent,
        llm_judge,
        tool_calling_evaluator,
        tool_args_evaluator,
        "test_add_model_dummy_classifier",
        user_input,
        reference_outputs,
        results_file_name="test_agent_sessions_results.json",
    )
    delete_dataset.invoke({"dataset_id": 1})
    assert_evaluations_agent(results)


def test_add_model_hist_gradient_boosting_classifier(
    agent, llm_judge, tool_calling_evaluator, tool_args_evaluator
):
    create_model_session(
        upload_iris_dataset,
        "iris_hist_gb_add_model",
        "TabularClassificationTask",
        ["SepalLengthCm", "SepalWidthCm", "PetalLengthCm", "PetalWidthCm"],
        ["Species"],
    )
    reference_outputs = build_test_add_model_to_session_output(
        1,
        "HistGradientBoostingClassifier",
        "iris_hist_gb_run",
        {
            "learning_rate": 0.1,
            "max_iter": 100,
            "max_depth": 1,
            "max_leaf_nodes": 31,
            "min_samples_leaf": 20,
            "l2_regularization": 0.0,
        },
        "",
        None,
        "",
        "",
    )
    user_input = (
        "Agrega un modelo HistGradientBoostingClassifier a la sesión del dataset iris. Debes buscar la única sesión de model existente "
        "con run_name iris_hist_gb_run, parámetros learning_rate 0.1, max_iter 100, max_depth 1, max_leaf_nodes 31, min_samples_leaf 20 y l2_regularization 0.0."
    )
    results = run_agent_case(
        agent,
        llm_judge,
        tool_calling_evaluator,
        tool_args_evaluator,
        "test_add_model_hist_gradient_boosting_classifier",
        user_input,
        reference_outputs,
        results_file_name="test_agent_sessions_results.json",
    )
    delete_dataset.invoke({"dataset_id": 1})
    assert_evaluations_agent(results)


def test_add_model_logistic_regression(
    agent, llm_judge, tool_calling_evaluator, tool_args_evaluator
):
    create_model_session(
        upload_iris_dataset,
        "iris_logistic_add_model",
        "TabularClassificationTask",
        ["SepalLengthCm", "SepalWidthCm", "PetalLengthCm", "PetalWidthCm"],
        ["Species"],
    )
    reference_outputs = build_test_add_model_to_session_output(
        1,
        "LogisticRegression",
        "iris_logistic_run",
        {"penalty": "l2", "tol": 0.0, "C": 1.0, "max_iter": 100},
        "",
        None,
        "",
        "",
    )
    user_input = (
        "Agrega un modelo LogisticRegression a la sesión del dataset iris. Debes buscar la única sesión de model existente "
        "con run_name iris_logistic_run, parámetros penalty l2, tol 0.0, C 1.0 y max_iter 100."
    )
    results = run_agent_case(
        agent,
        llm_judge,
        tool_calling_evaluator,
        tool_args_evaluator,
        "test_add_model_logistic_regression",
        user_input,
        reference_outputs,
        results_file_name="test_agent_sessions_results.json",
    )
    delete_dataset.invoke({"dataset_id": 1})
    assert_evaluations_agent(results)


def test_add_model_random_forest_classifier(
    agent, llm_judge, tool_calling_evaluator, tool_args_evaluator
):
    create_model_session(
        upload_iris_dataset,
        "iris_rf_add_model",
        "TabularClassificationTask",
        ["SepalLengthCm", "SepalWidthCm", "PetalLengthCm", "PetalWidthCm"],
        ["Species"],
    )
    reference_outputs = build_test_add_model_to_session_output(
        1,
        "RandomForestClassifier",
        "iris_rf_run",
        {
            "n_estimators": 100,
            "max_depth": 2,
            "min_samples_split": 2,
            "min_samples_leaf": 1,
            "max_leaf_nodes": 2,
            "random_state": 0,
        },
        "",
        None,
        "",
        "",
    )
    user_input = (
        "Agrega un modelo RandomForestClassifier a la sesión del dataset iris. Debes buscar la única sesión de model existente "
        "con run_name iris_rf_run, parámetros n_estimators 100, max_depth 2, min_samples_split 2, min_samples_leaf 1, max_leaf_nodes 2 y random_state 0."
    )
    results = run_agent_case(
        agent,
        llm_judge,
        tool_calling_evaluator,
        tool_args_evaluator,
        "test_add_model_random_forest_classifier",
        user_input,
        reference_outputs,
        results_file_name="test_agent_sessions_results.json",
    )
    delete_dataset.invoke({"dataset_id": 1})
    assert_evaluations_agent(results)


def test_add_model_gradient_boosting_r(
    agent, llm_judge, tool_calling_evaluator, tool_args_evaluator
):
    create_model_session(
        upload_regression_dataset,
        "regression_gb_add_model",
        "RegressionTask",
        ["x"],
        ["y"],
    )
    reference_outputs = build_test_add_model_to_session_output(
        1,
        "GradientBoostingR",
        "regression_gb_run",
        {
            "loss": "squared_error",
            "learning_rate": 0.1,
            "n_estimators": 100,
            "subsample": 1.0,
            "criterion": "friedman_mse",
            "min_samples_split": 0.5,
            "min_samples_leaf": 1,
            "min_weight_fraction_leaf": 0.0,
            "max_depth": 3,
            "min_impurity_decrease": 0.0,
            "random_state": None,
            "max_features": "sqrt",
            "alpha": 0.9,
            "verbose": 0,
            "max_leaf_nodes": None,
            "warm_start": False,
            "validation_fraction": 0.1,
            "n_iter_no_change": None,
            "tol": 0.0001,
            "ccp_alpha": 0.0,
        },
        "",
        None,
        "",
        "",
    )
    user_input = (
        "Agrega un modelo GradientBoostingR a la sesión del dataset de regresión. Debes buscar la única sesión de model existente "
        "con run_name regression_gb_run, parámetros loss squared_error, learning_rate 0.1, n_estimators 100, subsample 1.0 y criterion friedman_mse."
    )
    results = run_agent_case(
        agent,
        llm_judge,
        tool_calling_evaluator,
        tool_args_evaluator,
        "test_add_model_gradient_boosting_r",
        user_input,
        reference_outputs,
        results_file_name="test_agent_sessions_results.json",
    )
    delete_dataset.invoke({"dataset_id": 1})
    assert_evaluations_agent(results)


def test_add_model_mlp_regression(
    agent, llm_judge, tool_calling_evaluator, tool_args_evaluator
):
    create_model_session(
        upload_regression_dataset,
        "regression_mlp_add_model",
        "RegressionTask",
        ["x"],
        ["y"],
    )
    reference_outputs = build_test_add_model_to_session_output(
        1,
        "MLPRegression",
        "regression_mlp_run",
        {
            "hidden_size": 5,
            "activation": "relu",
            "learning_rate": 0.001,
            "epochs": 5,
            "batch_size": 32,
            "device": "CPU",
        },
        "",
        None,
        "",
        "",
    )
    user_input = (
        "Agrega un modelo MLPRegression a la sesión del dataset de regresión. Debes buscar la única sesión de model existente "
        "con run_name regression_mlp_run, parámetros hidden_size 5, activation relu, learning_rate 0.001, epochs 5, batch_size 32 y device CPU."
    )
    results = run_agent_case(
        agent,
        llm_judge,
        tool_calling_evaluator,
        tool_args_evaluator,
        "test_add_model_mlp_regression",
        user_input,
        reference_outputs,
        results_file_name="test_agent_sessions_results.json",
    )
    delete_dataset.invoke({"dataset_id": 1})
    assert_evaluations_agent(results)


def test_add_model_random_forest_regression(
    agent, llm_judge, tool_calling_evaluator, tool_args_evaluator
):
    create_model_session(
        upload_regression_dataset,
        "regression_rf_add_model",
        "RegressionTask",
        ["x"],
        ["y"],
    )
    reference_outputs = build_test_add_model_to_session_output(
        1,
        "RandomForestRegression",
        "regression_rf_run",
        {
            "n_estimators": 100,
            "criterion": "squared_error",
            "max_depth": 2,
            "min_samples_split": 2,
            "min_samples_leaf": 1,
            "min_weight_fraction_leaf": 0.0,
            "max_features": "sqrt",
            "max_leaf_nodes": None,
            "min_impurity_decrease": 0.0,
            "bootstrap": True,
            "oob_score": False,
            "n_jobs": None,
            "random_state": None,
            "warm_start": False,
            "ccp_alpha": 0.0,
            "max_samples": None,
        },
        "",
        None,
        "",
        "",
    )
    user_input = (
        "Agrega un modelo RandomForestRegression a la sesión del dataset de regresión. Debes buscar la única sesión de model existente "
        "con run_name regression_rf_run, parámetros n_estimators 100, criterion squared_error, max_depth 2, min_samples_split 2, min_samples_leaf 1 y bootstrap true."
    )
    results = run_agent_case(
        agent,
        llm_judge,
        tool_calling_evaluator,
        tool_args_evaluator,
        "test_add_model_random_forest_regression",
        user_input,
        reference_outputs,
        results_file_name="test_agent_sessions_results.json",
    )
    delete_dataset.invoke({"dataset_id": 1})
    assert_evaluations_agent(results)


def test_add_model_ridge_regression(
    agent, llm_judge, tool_calling_evaluator, tool_args_evaluator
):
    create_model_session(
        upload_regression_dataset,
        "regression_ridge_add_model",
        "RegressionTask",
        ["x"],
        ["y"],
    )
    reference_outputs = build_test_add_model_to_session_output(
        1,
        "RidgeRegression",
        "regression_ridge_run",
        {
            "alpha": 1,
            "fit_intercept": True,
            "copy_X": True,
            "max_iter": 100,
            "tol": 0.001,
            "solver": "auto",
            "positive": False,
            "random_state": None,
        },
        "",
        None,
        "",
        "",
    )
    user_input = (
        "Agrega un modelo RidgeRegression a la sesión del dataset de regresión. Debes buscar la única sesión de model existente "
        "con run_name regression_ridge_run, parámetros alpha 1, fit_intercept true, copy_X true, max_iter 100, tol 0.001, solver auto y positive false."
    )
    results = run_agent_case(
        agent,
        llm_judge,
        tool_calling_evaluator,
        tool_args_evaluator,
        "test_add_model_ridge_regression",
        user_input,
        reference_outputs,
        results_file_name="test_agent_sessions_results.json",
    )
    delete_dataset.invoke({"dataset_id": 1})
    assert_evaluations_agent(results)


def test_add_model_linear_svr(
    agent, llm_judge, tool_calling_evaluator, tool_args_evaluator
):
    create_model_session(
        upload_regression_dataset,
        "regression_svr_add_model",
        "RegressionTask",
        ["x"],
        ["y"],
    )
    reference_outputs = build_test_add_model_to_session_output(
        1,
        "LinearSVR",
        "regression_svr_run",
        {
            "epsilon": 0.0,
            "tol": 0.0001,
            "C": 1,
            "loss": "epsilon_insensitive",
            "fit_intercept": True,
            "intercept_scaling": 1.0,
            "dual": True,
            "verbose": 0,
            "random_state": None,
            "max_iter": 1000,
        },
        "",
        None,
        "",
        "",
    )
    user_input = (
        "Agrega un modelo LinearSVR a la sesión del dataset de regresión. Debes buscar la única sesión de model existente "
        "con run_name regression_svr_run, parámetros epsilon 0.0, tol 0.0001, C 1, loss epsilon_insensitive, fit_intercept true, dual true y verbose 0."
    )
    results = run_agent_case(
        agent,
        llm_judge,
        tool_calling_evaluator,
        tool_args_evaluator,
        "test_add_model_linear_svr",
        user_input,
        reference_outputs,
        results_file_name="test_agent_sessions_results.json",
    )
    delete_dataset.invoke({"dataset_id": 1})
    assert_evaluations_agent(results)


def test_add_model_modern_bert(
    agent, llm_judge, tool_calling_evaluator, tool_args_evaluator
):
    create_model_session(
        upload_text_classification_dataset,
        "corona_modern_bert_add_model",
        "TextClassificationTask",
        ["OriginalTweet"],
        ["Sentiment"],
    )
    reference_outputs = build_test_add_model_to_session_output(
        1,
        "ModernBertTransformer",
        "corona_modern_bert_run",
        {
            "num_train_epochs": 1,
            "batch_size": 16,
            "learning_rate": 3e-5,
            "device": "CPU",
            "weight_decay": 0.01,
        },
        "",
        None,
        "",
        "",
    )
    user_input = (
        "Agrega un modelo ModernBertTransformer a la sesión del dataset de clasificación de texto. Debes buscar la única sesión de model existente "
        "con run_name corona_modern_bert_run, parámetros num_train_epochs 1, batch_size 16, learning_rate 3e-5 y device CPU."
    )
    results = run_agent_case(
        agent,
        llm_judge,
        tool_calling_evaluator,
        tool_args_evaluator,
        "test_add_model_modern_bert",
        user_input,
        reference_outputs,
        results_file_name="test_agent_sessions_results.json",
    )
    delete_dataset.invoke({"dataset_id": 1})
    assert_evaluations_agent(results)


def test_add_model_deberta_v3(
    agent, llm_judge, tool_calling_evaluator, tool_args_evaluator
):
    create_model_session(
        upload_text_classification_dataset,
        "corona_deberta_add_model",
        "TextClassificationTask",
        ["OriginalTweet"],
        ["Sentiment"],
    )
    reference_outputs = build_test_add_model_to_session_output(
        1,
        "DebertaV3Transformer",
        "corona_deberta_run",
        {
            "num_train_epochs": 1,
            "batch_size": 16,
            "learning_rate": 3e-5,
            "device": "CPU",
            "weight_decay": 0.01,
        },
        "",
        None,
        "",
        "",
    )
    user_input = (
        "Agrega un modelo DebertaV3Transformer a la sesión del dataset de clasificación de texto. Debes buscar la única sesión de model existente "
        "con run_name corona_deberta_run, parámetros num_train_epochs 1, batch_size 16, learning_rate 3e-5 y device CPU."
    )
    results = run_agent_case(
        agent,
        llm_judge,
        tool_calling_evaluator,
        tool_args_evaluator,
        "test_add_model_deberta_v3",
        user_input,
        reference_outputs,
        results_file_name="test_agent_sessions_results.json",
    )
    delete_dataset.invoke({"dataset_id": 1})
    assert_evaluations_agent(results)


def test_add_model_bag_of_words_text_classification(
    agent, llm_judge, tool_calling_evaluator, tool_args_evaluator
):
    create_model_session(
        upload_text_classification_dataset,
        "corona_bow_add_model",
        "TextClassificationTask",
        ["OriginalTweet"],
        ["Sentiment"],
    )
    reference_outputs = build_test_add_model_to_session_output(
        1,
        "BagOfWordsTextClassificationModel",
        "corona_bow_run",
        {
            "tabular_classifier": {
                "component": "TabularClassificationModel",
                "params": {
                    "component": "SVC",
                    "params": {
                        "C": 1.0,
                        "coef0": 1.0,
                        "degree": 1.0,
                        "gamma": "scale",
                        "kernel": "rbf",
                        "max_iter": -1,
                        "shrinking": True,
                        "tol": 1.0,
                    },
                },
            },
            "ngram_min_n": 1,
            "ngram_max_n": 1,
        },
        "",
        None,
        "",
        "",
    )
    user_input = (
        "Agrega un modelo BagOfWordsTextClassificationModel a la sesión del dataset de clasificación de texto. Debes buscar la única sesión de model existente "
        "con run_name corona_bow_run, parámetros tabular_classifier con componente SVC, ngram_min_n 1 y ngram_max_n 1."
    )
    results = run_agent_case(
        agent,
        llm_judge,
        tool_calling_evaluator,
        tool_args_evaluator,
        "test_add_model_bag_of_words_text_classification",
        user_input,
        reference_outputs,
        results_file_name="test_agent_sessions_results.json",
    )
    delete_dataset.invoke({"dataset_id": 1})
    assert_evaluations_agent(results)


def test_add_model_opus_mt_es_en(
    agent, llm_judge, tool_calling_evaluator, tool_args_evaluator
):
    create_model_session(
        upload_translation_mini_dataset,
        "translation_opus_mt_es_en_add_model",
        "TranslationTask",
        ["english"],
        ["spanish"],
    )
    reference_outputs = build_test_add_model_to_session_output(
        1,
        "OpusMtEsENTransformer",
        "translation_opus_mt_es_en_run",
        {
            "num_train_epochs": 1,
            "batch_size": 4,
            "learning_rate": 2e-5,
            "device": "CPU",
            "weight_decay": 0.01,
        },
        "",
        None,
        "",
        "",
    )
    user_input = (
        "Agrega un modelo OpusMtEsENTransformer a la sesión del dataset de traducción. Debes buscar la única sesión de model existente "
        "con run_name translation_opus_mt_es_en_run, parámetros num_train_epochs 1, batch_size 4, learning_rate 2e-5 y device CPU."
    )
    results = run_agent_case(
        agent,
        llm_judge,
        tool_calling_evaluator,
        tool_args_evaluator,
        "test_add_model_opus_mt_es_en",
        user_input,
        reference_outputs,
        results_file_name="test_agent_sessions_results.json",
    )
    delete_dataset.invoke({"dataset_id": 1})
    assert_evaluations_agent(results)


def test_add_model_nllb_transformer(
    agent, llm_judge, tool_calling_evaluator, tool_args_evaluator
):
    create_model_session(
        upload_translation_mini_dataset,
        "translation_nllb_add_model",
        "TranslationTask",
        ["english"],
        ["spanish"],
    )
    reference_outputs = build_test_add_model_to_session_output(
        1,
        "NllbTransformer",
        "translation_nllb_run",
        {
            "num_train_epochs": 1,
            "batch_size": 4,
            "learning_rate": 2e-5,
            "device": "CPU",
            "weight_decay": 0.01,
            "source_language": "spa_Latn",
            "target_language": "eng_Latn",
        },
        "",
        None,
        "",
        "",
    )
    user_input = (
        "Agrega un modelo NllbTransformer a la sesión del dataset de traducción. Debes buscar la única sesión de model existente "
        "con run_name translation_nllb_run, parámetros num_train_epochs 1, batch_size 4, learning_rate 2e-5, device CPU, source_language spa_Latn y target_language eng_Latn."
    )
    results = run_agent_case(
        agent,
        llm_judge,
        tool_calling_evaluator,
        tool_args_evaluator,
        "test_add_model_nllb_transformer",
        user_input,
        reference_outputs,
        results_file_name="test_agent_sessions_results.json",
    )
    delete_dataset.invoke({"dataset_id": 1})
    assert_evaluations_agent(results)


def test_delete_model_from_session(
    agent, llm_judge, tool_calling_evaluator, tool_args_evaluator
):
    create_session_with_model(
        upload_iris_dataset,
        "iris_delete_model",
        "TabularClassificationTask",
        ["SepalLengthCm", "SepalWidthCm", "PetalLengthCm", "PetalWidthCm"],
        ["Species"],
        "KNeighborsClassifier",
        "iris_delete_run",
        {"n_neighbors": 3, "weights": "uniform", "algorithm": "auto"},
    )
    reference_outputs = build_test_delete_model_from_session_output(1)
    user_input = "Elimina el único modelo que hay en la sesión del dataset iris."
    results = run_agent_case(
        agent,
        llm_judge,
        tool_calling_evaluator,
        tool_args_evaluator,
        "test_delete_model_from_session",
        user_input,
        reference_outputs,
        results_file_name="test_agent_sessions_results.json",
    )
    delete_dataset.invoke({"dataset_id": 1})
    assert_evaluations_agent(results)


def test_run_model(agent, llm_judge, tool_calling_evaluator, tool_args_evaluator):
    create_session_with_model(
        upload_iris_dataset,
        "iris_run_model",
        "TabularClassificationTask",
        ["SepalLengthCm", "SepalWidthCm", "PetalLengthCm", "PetalWidthCm"],
        ["Species"],
        "KNeighborsClassifier",
        "iris_run_model_run",
        {"n_neighbors": 3, "weights": "uniform", "algorithm": "auto"},
    )
    reference_outputs = build_test_run_model_output(1)
    user_input = "Ejecuta el único modelo que hay en la sesión del dataset iris."
    results = run_agent_case(
        agent,
        llm_judge,
        tool_calling_evaluator,
        tool_args_evaluator,
        "test_run_model",
        user_input,
        reference_outputs,
        results_file_name="test_agent_sessions_results.json",
    )
    delete_dataset.invoke({"dataset_id": 1})
    assert_evaluations_agent(results)
