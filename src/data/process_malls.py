#%% IMPORT LIBRARIES
import os
import pandas as pd
import warnings
warnings.simplefilter("ignore")

# %% FILES LOCATION
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", ".."))

input_path = os.path.join(BASE_DIR, "data", "raw", "osm_malls.csv")
output_path = os.path.join(BASE_DIR, "data", "processed", "malls_processed.csv")
#%%
df = pd.read_csv(input_path, sep=None, engine="python", encoding="utf-8-sig")
df = df[["name","@lat","@lon"]]

# RENAME COLUMNS
df.rename(columns = {"name":"nombre","@lat":"latitud","@lon":"longitud"}, inplace=True)
df

#%% EXPORT CSV
df.to_csv(output_path, index=False)
# %%
