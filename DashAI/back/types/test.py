from ptype.Ptype import Ptype
from ptype.PtypeCat import PtypeCat
import pandas as pd


def main():
    df = pd.read_csv(r'C:\\Users\\dfaun\\OneDrive\\Escritorio\\titulo\\DashAI\\DashAI\\back\\example_datasets\\diabetes_small.csv', dtype=str)
    #df = pd.read_json(r'C:\\Users\\dfaun\\OneDrive\\Escritorio\\titulo\\DashAI\\DashAI\\back\\example_datasets\\random_text.json')
    #df = df["data"].apply(pd.Series)
    ptype_cat = PtypeCat()
    schema = ptype_cat.schema_fit(df)
    
    # Mostrar el esquema general
    print(schema.show())

        # Imprimir las probabilidades y la cantidad de valores únicos por columna
    for col_name, column_object in schema.cols.items():
        print(f"\nColumna: '{col_name}'")
        
        # Imprimir las probabilidades para la columna
        print("Probabilidades por tipo de columna:")
        print(column_object.p_t)
        
        # Imprimir la cantidad de valores únicos para la columna
        unique_vals_count = len(column_object.unique_vals)
        print(f"Cantidad de valores únicos: {unique_vals_count}")

if __name__ == "__main__":
    main()