# %%
import pandas as pd
import numpy as np
import os
from sklearn.tree import DecisionTreeClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
import matplotlib.pyplot as plt

# %%

# Función para imputar
def imputar_con_medianas_zona(row):
    for col in cols_impute:
        if pd.isna(row[col]):
            zona = row['zona_apeim']
            if zona in medianas_zona.index:
                valor = medianas_zona.loc[zona, col]
                if not pd.isna(valor):
                    row[col] = valor
    return row

#%%
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", ".."))
input_path = os.path.join(BASE_DIR, "data", "processed", "data_preprocessing.csv")
output_path = os.path.join(BASE_DIR, "data", "processed", "data_preprocessing_eng.csv")
 
df = pd.read_csv(input_path)
df_processed = df.copy()
df.columns
# %%
df_processed['num_estac'] = df_processed['num_estac'].fillna(0)

df_processed['total_ambientes'] = df_processed['num_dorm'] + df_processed['num_banios']

df_processed['total_servicios_prox'] = (
    df_processed['num_colegios_aprox'] + df_processed['num_hospitales_aprox'] +
    df_processed['num_tren_est_aprox'] + df_processed['num_metro_est_aprox'] +
    df_processed['num_comisarias_aprox']
)

df_processed['total_transporte_aprox'] = df_processed['num_tren_est_aprox'] + df_processed['num_metro_est_aprox']

df_processed['flg_estac'] = (df_processed['num_estac'] > 0).astype(int)

df_processed["flg_tren"] = (df_processed["num_tren_est_aprox"] > 0).astype(int)

df_processed["flg_metro"] = (df_processed["num_metro_est_aprox"] > 0).astype(int)

#%%

df_processed['precio_por_m2'] = df_processed['precio_pen'] / df_processed['area_m2']

df_processed['costo_total_mensual'] = df_processed['precio_pen'] + df_processed['mantenimiento_soles']  # Asumiendo 0.8% mensual

df_processed['score_ubicacion'] = (df_processed['total_servicios_prox'] * 0.6 + df_processed['total_transporte_aprox'] * 0.4)

df_processed['categoria_precio'] = pd.cut(df_processed['precio_pen'], bins=5, labels=['Muy Bajo', 'Bajo', 'Medio', 'Alto', 'Muy Alto'])

df_processed['decada_construccion'] = (2025 - df['antiguedad']) // 10 * 10


# %% 
dict_zona_apeim = {
    'puente piedra': 'zona 1', 'comas': 'zona 1', 'carabayllo': 'zona 1',
    'callao': 'zona 1', 'bellavista': 'zona 1', 'la perla': 'zona 1',
    'la punta': 'zona 1', 'carmen de la legua': 'zona 1', 'ventanilla': 'zona 1',
    'independencia': 'zona 2', 'los olivos': 'zona 2', 'san martin de porres': 'zona 2', 'smp': 'zona 2',
    'san juan de lurigancho': 'zona 3', 'sjl': 'zona 3',
    'lima cercado': 'zona 4', 'rimac': 'zona 4', 'brena': 'zona 4', 'la victoria': 'zona 4',
    'ate': 'zona 5', 'chaclacayo': 'zona 5', 'lurigancho': 'zona 5',
    'santa anita': 'zona 5', 'san luis': 'zona 5', 'el agustino': 'zona 5',
    'jesus maria': 'zona 6', 'lince': 'zona 6', 'pueblo libre': 'zona 6',
    'magdalena': 'zona 6', 'san miguel': 'zona 6',
    'miraflores': 'zona 7', 'san isidro': 'zona 7', 'san borja': 'zona 7',
    'surco': 'zona 7', 'la molina': 'zona 7',
    'surquillo': 'zona 8', 'barranco': 'zona 8', 'chorrillos': 'zona 8',
    'san juan de miraflores': 'zona 8', 'sjm': 'zona 8',
    'villa el salvador': 'zona 9', 'ves': 'zona 9', 'villa maria del triunfo': 'zona 9',
    'vmt': 'zona 9', 'lurin': 'zona 9', 'pachacamac': 'zona 9',
    'punta hermosa': 'zona 10', 'san bartolo': 'zona 10', 'cieneguilla': 'zona 10', 'punta negra': 'zona 10', 'ancon': 'zona 10',
    'santa maria del mar': 'zona 10', 'pucusana': 'zona 10'
}
df_processed['zona_apeim'] = df_processed['distrito'].map(dict_zona_apeim)
df_processed['zona_apeim_cod'] = df_processed['zona_apeim'].map({f'zona {i}': i for i in range(1, 11)})

#%%

# Imputación por zona
cols_impute = ['num_dorm', 'num_banios', 'antiguedad']
df_train = df_processed[df_processed["set"] == "train"]
medianas_zona = df_train.groupby('zona_apeim')[cols_impute].median()
df_processed = df_processed.apply(imputar_con_medianas_zona, axis=1)

#%%
# Variables categóricas
df_processed["tamano"] = pd.cut(df_processed["area_m2"],
                                bins=[0, 50, 100, float("inf")],
                                labels=["pequeno", "mediano", "grande"]
                                )

df_processed['antiguedad_categoria'] = pd.cut(df_processed['antiguedad'],
                                              bins=[-1, 5, 20, float('inf')],
                                              labels=['nuevo', 'seminuevo', 'antiguo']
                                              )
df_processed['tamano_cod'] = df_processed['tamano'].map({'pequeno': 1,
                                                         'mediano': 2,
                                                         'grande': 3}).astype(float)
df_processed['antiguedad_cod'] = df_processed['antiguedad_categoria'].map({'nuevo': 1,
                                                                           'seminuevo': 2,
                                                                           'antiguo': 3}).astype(float)
df_processed['nivel_socioeconomico_cod'] = df_processed['nivel_socioeconomico'].map({'A': 1, 'B': 2, 'C': 3, 'D': 4}).astype(float)
#%%

df_train_tree = df_train[['num_delitos_aprox', 'zona_apeim_cod']]

X = df_train_tree[['num_delitos_aprox']]
y = df_train_tree['zona_apeim_cod']

tree = DecisionTreeClassifier(max_leaf_nodes=4, random_state=42)
tree.fit(X, y)
thresholds = np.sort(tree.tree_.threshold[tree.tree_.threshold != -2])

bins = [-1] + list(thresholds) + [float("inf")]

labels = [f'nivel_{i+1}' for i in range(len(bins) - 1)]

df_processed['categoria_crimenes'] = pd.cut(df_processed['num_delitos_aprox'], bins=bins, labels=labels)
df_processed['categoria_crimenes_cod'] = df_processed['categoria_crimenes'].cat.codes + 1

#%%

# KMeans
cols_cluster = [
                'area_m2',
                'num_dorm',
                'num_banios',
                'num_estac',
                'categoria_crimenes_cod',
                'zona_apeim_cod',
                'antiguedad_cod',
                'tamano_cod']

scaler = StandardScaler()
X_cluster = df_processed[cols_cluster].fillna(0)  # aseguramos que no haya NaN
X_scaled = scaler.fit_transform(X_cluster)
kmeans = KMeans(n_clusters=3, random_state=42)
df_processed['tipo_vivienda_cod'] = kmeans.fit_predict(X_scaled)


#%%
pca = PCA(n_components=2)
X_pca = pca.fit_transform(X_scaled)
plt.scatter(X_pca[:, 0], X_pca[:, 1], c=df_processed['tipo_vivienda_cod'], cmap='viridis')
plt.title("Segmentación de departamentos")
plt.xlabel("Componente 1")
plt.ylabel("Componente 2")
plt.colorbar(label='Cluster')
plt.show()

#%%

cols_cluster = cols_cluster + ["precio_pen"]

cluster_summary = df_processed.groupby("tipo_vivienda_cod")[cols_cluster].median().round(2)

print(cluster_summary)

# También puedes contar cuántos elementos hay en cada cluster
cluster_counts = df_processed['tipo_vivienda_cod'].value_counts()

print("\nCantidad de viviendas por cluster:")
print(cluster_counts)

map_tipo_vivienda = {
    0: "Medio",
    1: "Premium",
    2: "Económico"
}

df_processed["tipo_vivienda"] = df_processed["tipo_vivienda_cod"].map(map_tipo_vivienda)

#%%

df_processed.to_csv(output_path, index = False)
# %%
