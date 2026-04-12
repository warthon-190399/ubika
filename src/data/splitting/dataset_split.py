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

    top_district = df['distrito'].value_counts().idxmax()

    df_h = df[df['distrito']==top_district].copy()
    df_l = df[df['distrito']!=top_district].copy()

    df_h.to_csv(output_path_h, index=False)
    df_l.to_csv(output_path_l, index=False)

if __name__ == "__main__":
    main()