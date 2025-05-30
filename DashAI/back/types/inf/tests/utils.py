from collections import Counter, OrderedDict
import glob
import numpy as np
import pandas as pd
import sys
import os
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
sys.path.insert(0, project_root)

SUPPORTED_TYPES = [
    "integer",
    "string",
    "float",
    "boolean",
    "date",
    "time",
]


def evaluate_model_type(annotations, predictions):
    types = SUPPORTED_TYPES
    type_rates = {t: {"TP": 0, "FP": 0, "TN": 0, "FN": 0} for t in types}

    predictions = [
        prediction.replace("date-eu", "date")
        .replace("date-iso-8601", "date")
        .replace("date-non-std-subtype", "date")
        .replace("date-non-std", "date")
        for prediction in predictions
    ]
    annotations = [
        annotation.replace("date-eu", "date")
            .replace("date-iso-8601", "date")
            .replace("date-non-std-subtype", "date")
            .replace("date-non-std", "date")
        for annotation in annotations
    ]

    # find columns whose types are not supported by ptype
    ignored_columns = np.where(
        (np.array(annotations) != "all identical")
        & (np.array(annotations) != "gender")
        & (np.array(predictions) != "all identical")
        & (np.array(predictions) != "unknown")
    )[0]

    for t in types:
        
        
        y_true = (np.array(annotations) == t)[ignored_columns]
        y_score = (np.array(predictions) == t)[ignored_columns]

        type_rates[t]["TP"] = sum(y_true * y_score)
        type_rates[t]["FP"] = sum(not_vector(y_true) * y_score)
        type_rates[t]["TN"] = sum(not_vector(y_true) * not_vector(y_score))
        type_rates[t]["FN"] = sum(y_true * not_vector(y_score))

    return type_rates


def evaluate_predictions(annotations, type_predictions, methods=["ptype"]):
    # the column type counts of the datasets
    [_, _, total_cols] = get_type_counts(type_predictions, annotations)

    Js, overall_accuracy = get_evaluations(annotations, type_predictions, methods)
    overall_accuracy_to_print = {
        method: {"overall-accuracy": float_2dp(overall_accuracy[method] / total_cols)}
        for method in overall_accuracy
    }
    print("overall accuracy: ", overall_accuracy_to_print)
    print("Jaccard index values: ", {t: Js[t][methods[0]] for t in Js})

    df1 = pd.DataFrame.from_dict(Js, orient="index")
    df2 = pd.DataFrame.from_dict(overall_accuracy_to_print, orient="index").T
    df = pd.concat([df2, df1], ignore_index=True)
    # this could be simplified!
    if methods[0] == "ptype":
        column_type_evaluations = "DashAI/back/types/inf/tests/expected/column_type_evaluations.csv"
    else:
        column_type_evaluations = "DashAI/back/types/inf/tests/expected_cat/column_type_evaluations.csv"

    expected = pd.read_csv(column_type_evaluations, index_col=0)
    if not expected.equals(df):
        df.to_csv(path_or_buf=column_type_evaluations + ".new")
        raise Exception(f"{column_type_evaluations} comparison failed.")


def float_2dp(n: float):
    """Round a float to 2 decimal places, preserving float-hood. Probably a better way to do this."""
    return np.float64("{:.2f}".format(n))


def get_evaluations(_annotations, _predictions, methods):
    dataset_names = list(_predictions.keys())
    types = SUPPORTED_TYPES
    Js = {}
    overall_accuracy = {method: 0 for method in methods}
    for t in types:

        J = {}
        for method in methods:

            tp, fp, fn = 0.0, 0.0, 0.0
            for dataset_name in dataset_names:
                print("dataset_name:", dataset_name)
                temp = evaluate_model_type(
                    _annotations[dataset_name], _predictions[dataset_name].values()
                )
                tp += temp[t]["TP"]
                fp += temp[t]["FP"]
                fn += temp[t]["FN"]

            overall_accuracy[method] += tp
            J[method] = float_2dp(tp / (tp + fp + fn))
        Js[t] = J

    return Js, overall_accuracy


def get_type_counts(predictions, annotations):
    _types = SUPPORTED_TYPES
    dataset_counts = OrderedDict()
    total_test = {t: 0 for t in _types}

    for dataset_name in predictions:
        true_values = annotations[dataset_name]
        ptype_predictions = predictions[dataset_name].values()

        
        true_values = [
            true_value.replace("date-eu", "date")
            .replace("date-iso-8601", "date")
            .replace("date-non-std-subtype", "date")
            .replace("date-non-std", "date")
            for true_value in true_values
        ]
        ptype_predictions = [
            prediction.replace("date-eu", "date")
            .replace("date-iso-8601", "date")
            .replace("date-non-std-subtype", "date")
            .replace("date-non-std", "date")
            for prediction in ptype_predictions
        ]

        ignored_columns = np.where(
            (np.array(true_values) != "all identical")
            & (np.array(true_values) != "gender")
            & (np.array(ptype_predictions) != "all identical")
            & (np.array(ptype_predictions) != "unknown")
        )[0]

        

        counts = Counter(np.array(true_values)[ignored_columns])
        for t in _types:
            if t not in list(counts.keys()):
                counts[t] = 0

        # Counters are unordered, so for deterministic output we sort via a list
        dataset_counts[dataset_name] = dict(sorted(counts.items()))

        total_test = {
            t: total_test[t] + dataset_counts[dataset_name][t] for t in _types
        }

    total_cols = sum(
        [total_test[t] for t in SUPPORTED_TYPES]
    )

    return [total_test, dataset_counts, total_cols]


# added later - needs a pass over
def not_vector(X):
    return np.array([not x for x in X])
