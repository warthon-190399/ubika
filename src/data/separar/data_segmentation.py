# IMPORT LIBRARIES
import os
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "..",".."))
input_path = os.path.join(BASE_DIR, "data", "processed", "data_preprocessing_eng.csv")
output_path_h = os.path.join(BASE_DIR, "data", "processed", "dataset_h.csv")
output_path_l = os.path.join(BASE_DIR, "data", "processed", "dataset_l.csv")

def main():
    df = pd.read_csv(input_path)

    conteo = df['distrito'].value_counts().sort_values(ascending=True)
    conteo_acum = conteo.cumsum()/conteo.sum()

    print(conteo_acum)

    distritos_inf = conteo[conteo_acum <= 0.5].index

    df_l = df[df["distrito"].isin(distritos_inf)].copy()
    df_h = df[~df["distrito"].isin(distritos_inf)].copy()

    #print(df_l)
    #print(df_h)

    df_l.to_csv(output_path_l, index=False)
    df_h.to_csv(output_path_h, index=False)

if __name__ == "__main__":
    main()