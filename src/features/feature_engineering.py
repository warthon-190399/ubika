# %%
import pandas as pd
import numpy as np
import os
# %%
def zone_classification(distrito):
    distrito = str(distrito).strip().lower()
    if distrito in ['miraflores', 'san isidro', 'san borja', 'surco', 'surquillo', 'jesus maria', 'lince', 'magdalena', 'pueblo libre']:
        return 'Lima Moderna'
    elif distrito in ['lima cercado', 'brena', 'la victoria', 'san luis', 'rimac']:
        return 'Lima Centro'
    elif distrito in ['los olivos', 'comas', 'independencia', 'puente piedra', 'carabayllo', 'ancon', 'smp']:
        return 'Lima Norte'
    elif distrito in ['ate', 'santa anita', 'lurigancho', 'chaclacayo', 'cieneguilla', 'el agustino', 'la molina']:
        return 'Lima Este'
    elif distrito in ['chorrillos', 'sjm', 'vmt', 'ves', 'lurin', 'pachacamac']:
        return 'Lima Sur Urbana'
    elif distrito in ['punta hermosa', 'san bartolo', 'punta negra', 'pucusana', 'santa maria del mar', 'barranco']:
        return 'Lima Sur Balnearios'
    elif distrito == 'callao':
        return 'Callao'
    else:
        return 'Otro'

def nivel_socioeconomico(distrito):
    distrito = str(distrito).strip().lower()
    if distrito in ['barranco', 'la molina', 'miraflores', 'san borja', 'san isidro', 'surco']:
        return 'A'
    elif distrito in ['chorrillos', 'cieneguilla', 'jesus maria', 'lince', 'magdalena', 'pucusana', 
                    'pueblo libre', 'punta hermosa', 'punta negra', 'san bartolo', 'san miguel',
                    'santa anita', 'santa maria del mar']:
        return 'B'
    elif distrito in ['ate', 'brena', 'callao', 'chaclacayo', 'comas', 'el agustino', 'independencia', 
                      'la victoria', 'lima cercado', 'los olivos', 'rimac', 'san luis', 'smp', 'surquillo']:
        return 'C'
    elif distrito in ['ancon', 'carabayllo', 'lurigancho', 'lurin', 'pachacamac', 'puente piedra', 
                      'sjl', 'sjm', 'ves', 'vmt']:
        return 'D'
    else:
        return 'Otro'
# %%
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", ".."))
input_path = os.path.join(BASE_DIR, "data", "processed", "data_preprocessing.csv")
output_path = os.path.join(BASE_DIR, "data", "processed", "data_preprocessing_eng.csv")

df = pd.read_csv(input_path)
df_processed = df.copy()
# %%
#df_grouped = (
#    df_processed.groupby('nivel_socioeconomico')['distrito']
#    .apply(lambda x: sorted(set(x)))
#    .reset_index()
#    )
#df_grouped.columns = ['Nivel Socioeconómico', 'Distritos']

df_processed['total_ambientes'] = df_processed['num_dorm'] + df_processed['num_banios']

df_processed['tiene_estac'] = (df_processed['num_estac'] > 0).astype(int)
#df_grouped
# %%
df_processed["tamano"] = pd.cut(
    df_processed["area_m2"],
    bins=[0,50,100, float("inf")],
    labels=["pequeno", "mediano", "grande"]
)

df_processed['antiguedad_categoria'] = pd.cut(
    df_processed['antiguedad'],
    bins=[-1, 5, 20, float('inf')],
    labels=['nuevo', 'seminuevo', 'antiguo']
)

df_processed['tamano_cod'] = df_processed['tamano'].map({'pequeno': 1, 'mediano': 2, 'grande': 3})
df_processed['antiguedad_cod'] = df_processed['antiguedad_categoria'].map({'nuevo': 1, 'seminuevo': 2, 'antiguo': 3})

#df_processed['nivel_socioeconomico'] = df_processed['nivel_socioeconomico'].apply(nivel_socioeconomico)

df_processed['nivel_socioeconomico_cod'] = df_processed['nivel_socioeconomico'].map({'A': 1, 'B': 2, 'C': 3, 'D': 4})
# %% precio total por distrito
df_processed['total_servicios_prox'] = (
    df_processed['num_colegios_prox'] + df_processed['num_malls_prox'] + df_processed['num_hospitales_prox'] +
    df_processed['num_tren_est_prox'] + df_processed['num_metro_est_prox'] + df_processed['num_comisarias_prox']
)

df_processed['total_transporte_prox'] =  df_processed['num_tren_est_prox'] + df_processed['num_metro_est_prox']

#%%
#df_processed['distrito'].unique()
df_processed['zona_funcional'] = df_processed['distrito'].apply(zone_classification)
df_processed['zona_funcional_cod'] = df_processed['zona_funcional'].map({'Callao':1,
                                                                        'Lima Centro':2, 
                                                                        'Lima Este':3, 
                                                                        'Lima Moderna':4,
                                                                        'Lima Norte':5,
                                                                        'Lima Sur Balnearios':6,
                                                                        'Lima Sur Urbana':7, 
                                                                        'Otro':8,})
#df_processed['zona_funcional_cod'] = df_processed['zona_funcional_cod'].astype(int)
# %%
#import matplotlib.pyplot as plt

#df_grouped = df_processed.groupby('distrito').size().reset_index(name = 'conteo')
#df_grouped = df_grouped.sort_values(by = "conteo", ascending=False)

#df_grouped['porcentaje'] = 100*df['conteo']/df['conteo'].sum()
#df_grouped['porcentaje_acumulado']=df['porcentaje'].cumsum()

#Create graph
#fig, ax1 = plt.subplots()

#ax1.bar(df[])
# %% Drop 'num_visualizaciones' column 
df_processed.drop('num_visualizaciones', axis=1, inplace=True)
df_processed['nivel_socioeconomico_cod'].info()
#%%
df_processed.to_csv(output_path, index = False)
# %%
