import json
import jsonpickle
import numpy as np
import os
import pandas as pd
import sys
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
sys.path.insert(0, project_root)
from back.types.inf.ptype.Ptype import Ptype
from back.types.inf.ptype.PtypeCat import PtypeCat
from back.types.inf.ptype.Trainer import Trainer
from back.types.inf.tests.utils import evaluate_predictions


# Associate each dataset with file prefix, encoding and header setting for Pandas read_csv.
datasets_cat = {
    "autos": ("utf-8", "infer"),
}


def get_predictions(dataset_name, data_folder, method=Ptype()):
    df = read_dataset(dataset_name, data_folder)

    schema = method.schema_fit(df)

    return (
        {col_name: col.type for col_name, col in schema.cols.items()},
        {
            col_name: {
                "missing_values": col.get_na_values(),
                "anomalous_values": col.get_an_values(),
            }
            for col_name, col in schema.cols.items()
        },
    )


def check_predictions(type_predictions, expected_folder, dataset_name):
    expected_file = expected_folder + "/" + os.path.splitext(dataset_name)[0]
    try:
        with open(expected_file + ".json", "r", encoding="utf-8-sig") as read_file:
            expected = json.load(read_file)
    except FileNotFoundError:
        expected = {}

    # JSON doesn't support integer keys
    type_predictions = {str(k): v for k, v in type_predictions.items()}
    if not (type_predictions == expected):  # dictionary comparison
        for k in type_predictions:
            if k in expected:
                if type_predictions[k] != expected[k]:
                    print(f"Differs on {k} ({type_predictions[k]} != {expected[k]})")
            else:
                print(f"Key {k} not expected")
        # prettyprint new JSON, omitting optional BOM char
        with open(expected_file + ".new.json", "w", encoding="utf-8-sig") as write_file:
            json.dump(
                type_predictions,
                write_file,
                indent=2,
                sort_keys=True,
                ensure_ascii=False,
            )
        raise Exception(f"{expected_file + '.json'} comparison failed.")


def read_dataset(dataset_name, data_folder):
    filename = data_folder + dataset_name + ".csv"
    if dataset_name in datasets_cat:
        encoding, header = datasets_cat[dataset_name]
        return pd.read_csv(
            filename,
            sep=",",
            dtype=str,
            encoding=encoding,
            keep_default_na=False,
            skipinitialspace=True,
            header=header,
        )
    else:
        raise Exception(f"{filename} not known.")


def get_inputs(
    dataset_name,
    types,
    annotations_file="annotations/annotations.json",
    data_folder="data/",
):
    annotations = json.load(open(annotations_file))
    df = read_dataset(dataset_name, data_folder)
    labels = annotations[dataset_name]

    # discard labels other than initialized 'types'
    indices = [i for i, label in enumerate(labels) if label in types]
    df = df[df.columns[np.array(indices)]]
    labels = [labels[index] for index in indices]

    # find the integer labels for the types
    y = [types.index(label) + 1 for label in labels]

    return df, y


def core_tests():
    expected_folder = "tests/expected_cat"
    data_folder = "data/"
    annotations = json.load(open("annotations/annotations_cat.json"))

    type_predictions = {}
    for dataset_name in datasets_cat:
        col_predictions, missing_anomalous = get_predictions(dataset_name, data_folder, PtypeCat())

        check_predictions(col_predictions, expected_folder, dataset_name)
        check_predictions(
            missing_anomalous, expected_folder + "/missing_anomalous", dataset_name
        )

        type_predictions[dataset_name] = col_predictions

    evaluate_predictions(annotations, type_predictions, methods=["ptype-cat"])


def check_expected(actual, filename):
    filename_ = filename + ".json"
    with open(filename_, "r") as file:
        expected_str = file.read()
    actual_str = jsonpickle.encode(actual, indent=2, unpicklable=False)
    if expected_str != actual_str:  # deep comparison
        with open(filename_, "w") as file:
            file.write(actual_str)
        print("Result of 'git diff':")
        stream = os.popen(f"git diff {filename_}")
        output = stream.read()
        print(output)
        print(f"{filename_} comparison failed.")
        return False
    return True


def main():
    np.random.seed(0)
    core_tests()


if __name__ == "__main__":
    main()
    print("Tests passed.")
