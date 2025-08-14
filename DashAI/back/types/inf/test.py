from ptype.PtypeCat import PtypeCat

import pandas as pd
import os
import sys
import json
#import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))
from inference_methods import DashAIPtype

def test_inference():
    ptype = DashAIPtype()
    # Add your test cases here

    current_dir = os.path.dirname(__file__)
    file_path = os.path.join(current_dir, "twitterDataset.json")

    df = pd.read_json(file_path)

    df = pd.DataFrame(df["data"].tolist()) 

    #schema = ptype.infer_types(df)
    schema = ptype.infer_types(df)
    print("Schema:")
    #print(schema.show())
    print(schema)
    # for col_name, column_object in schema.cols.items():
    #     print(f"\nColumna: '{col_name}'")
        
    #     # Imprimir las probabilidades para la columna
    #     print("Probabilidades por tipo de columna:")
    #     print(column_object.p_t)
        
    #     # Imprimir la cantidad de valores únicos para la columna
    #     unique_vals_count = len(column_object.unique_vals)
    #     print(f"Cantidad de valores únicos: {unique_vals_count}")
if __name__ == "__main__":
    test_inference()
    # Run the test function