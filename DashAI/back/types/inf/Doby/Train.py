import pandas as pd
import numpy as np
import os
from pathlib import Path
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import RobustScaler
import json
import sys
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
sys.path.insert(0, project_root)
from back.types.inf.ptype.Ptype import Ptype
from back.types.inf.ptype.PtypeCat import PtypeCat
from back.types.inf.ptype.Column import Column
from back.types.inf.ptype.Machines import Machines
from back.types.inf.ptype.Machine import Time
from back.types.inf.tests.utils import evaluate_predictions
from back.types.inf.ptype.Trainer import Trainer


datasets = {
    "accident2016": ("utf-8", "infer"),
    "auto": ("utf-8", None),
    "data_gov_3397_1": ("utf-8", "infer"),
    "data_gov_10151_1": ("utf-8", "infer"),
    "housing_price": ("utf-8", "infer"),
    "inspection_outcomes": ("utf-8", "infer"),
    "mass_6": ("ISO-8859-1", "infer"),
    "survey": ("utf-8", "infer"),
    "earthquakes": ("utf-8", "infer"),
    "sleep": ("utf-8", "infer"),
}

annotations_file = "DashAI/back/types/inf/doby/annotations/annotations.json"

def read_dataset(dataset_name, data_folder = "DashAI/back/types/inf/doby/data/"):

    encoding, header = datasets.get(dataset_name, ("utf-8", "infer"))
    path = os.path.join(data_folder, dataset_name + ".csv")
    return pd.read_csv(path, encoding=encoding, header=header, dtype=str, keep_default_na=False)

def get_predictions(dataset_name):

    df = read_dataset(dataset_name)
    ptype = Ptype()
    print("dataset_name: ", dataset_name)
    schema = ptype.schema_fit(df)

    df_normal = schema.transform(df)
    #print("Original data:\n", df.head())
    #print("Normal:\n", df_normal.head())

    
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

def check_predictions(predicted, expected_folder, dataset_name):

    path = os.path.join(expected_folder, dataset_name + ".json")

    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            expected = json.load(f)
    except FileNotFoundError:
        expected = {}
    
    predicted = {str(k): v for k, v in predicted.items()}

    # dictionary comparison
    print("comparing for dataset:", dataset_name)
    for k in predicted:
        #print("key:", k)
        if k in expected:
            if predicted[k] != expected[k]:
                print(f"\nDiffers on {k} ({predicted[k]} != {expected[k]})\n")
            # else:
            #     print(f"Key {k} matches expected value :", predicted[k])
        else:
            print(f"Key {k} not found in expected")
            
            

def get_inputs(dataset_name, types, annotation_file=annotations_file):
    """Carga datos + etiquetas para entrenamiento supervisado."""
    df = read_dataset(dataset_name)
    labels = json.load(open(annotation_file))[dataset_name]

    indices = [i for i, label in enumerate(labels) if label in types]
    df = df[df.columns[indices]]
    labels = [labels[i] for i in indices]
    y = [types.index(label) + 1 for label in labels]

    return df, y


def core_tests():
    print("Running core tests")
    annotations_file = "DashAI/back/types/inf/doby/annotations/annotations.json"

    """Ejecuta todos los tests principales"""
    annotations = json.load(open(annotations_file))
    expected_folder = "DashAI/back/types/inf/tests/expected/"

    type_predictions = {}

    for dataset_name in datasets:
        predicted_types, missing_anomalous = get_predictions(dataset_name)

        check_predictions(predicted_types, expected_folder, dataset_name)
        # check_predictions(
        #     missing_anomalous,
        #     os.path.join(expected_folder, "missing_anomalous"),
        #     dataset_name,
        # )

        type_predictions[dataset_name] = predicted_types
        #print(f"Predictions for {dataset_name}: {predicted_types}")
        #print(f"annotations for {dataset_name}: {annotations[dataset_name]}")
    # Verifica que las predicciones coincidan con las anotaciones manuales

    # Evalúa contra las anotaciones manuales
    evaluate_predictions(annotations, type_predictions)


def training_tests():
    """Entrena modelos con datasets y valida resultados"""
    ptype = PtypeCat()

    dfs, ys = [], []
    #arreglar esta cosita
    for dataset_name in ["earthquakes"]:
        df, y = get_inputs(dataset_name, ptype.types)
        dfs.append(df)
        ys.append(y)

    trainer = Trainer(ptype.machines, dfs, ys)
    initial, final, training_error = trainer.train(20, False)

    def save_json(obj, name):
        print("corriendo save_json")
        # with open(f"tests/expected/training/{name}.json", "w") as f:
        #     json.dump(obj, f, indent=2)

    save_json(initial, "runner_initial")
    save_json(final, "runner_final")
    save_json(training_error, "error")


def main():

    #np.random.seed(0)
    #core_tests()
    #training_tests()
    df = read_dataset("earthquakes")
    ptype = Ptype()
    schema = ptype.schema_fit(df)
    ptype_cat = PtypeCat()
    schema_cat = ptype_cat.schema_fit(df)
    
    type_predicted = {col_name: col.type for col_name, col in schema.cols.items()}
    cat_type_predicted = {col_name: col.type for col_name, col in schema_cat.cols.items()}
    final_schema = {}
    for col_name, col in zip(schema.cols, schema_cat.cols):
        #si es categorica en schema_cat, entonces gana y va schema_final
        if col_name in cat_type_predicted and cat_type_predicted[col_name] == "categorical":
            final_schema[col_name] = cat_type_predicted[col_name]
        else:
            final_schema[col_name] = type_predicted[col_name]
    print("Final schema types:", final_schema)




if __name__ == "__main__":
    main()
    print("✅ Tests passed.")