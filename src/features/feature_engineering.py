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
#%%
df_processed.columns
# %%
df_processed['distrito'].unique()
# %%
df_processed['nivel_socioeconomico']
# %%
df_processed['total_ambientes'] = df_processed['num_dorm'] + df_processed['num_banios']

df_processed['tiene_estac'] = (df_processed['num_estac'] > 0).astype(int)

# %%
df_processed["tamano"] = pd.cut(
    df_processed["area_m2"],
    bins=[0,50,100, float("inf")],
    labels=["pequeno", "mediano", "grande"]
)

zona_apeim = {
    # 1
    'puente piedra': 1,
    'comas': 1,
    'carabayllo': 1,
    
    # 2
    'independencia': 2,
    'los olivos': 2,
    'smp': 2,  # San Martín de Porres
    
    # 3
    'san juan de lurigancho': 3,
    
    # 4
    'lima cercado': 4,
    'rimac': 4,
    'brena': 4,
    'la victoria': 4,
    
    # 5
    'ate': 5,
    'chaclacayo': 5,
    'lurigancho': 5,
    'santa anita': 5,
    'san luis': 5,
    'el agustino': 5,
    
    # 6
    'jesus maria': 6,
    'lince': 6,
    'pueblo libre': 6,
    'magdalena': 6,
    'san miguel': 6,
    
    # 7
    'miraflores': 7,
    'san isidro': 7,
    'san borja': 7,
    'surco': 7,
    'la molina': 7,
    
    # 8
    'surquillo': 8,
    'barranco': 8,
    'chorrillos': 8,
    'san juan de miraflores': 8,
    
    # 9
    'ves': 9,
    'villa maria del triunfo': 9,
    'lurin': 9,
    'pachacamac': 9,
    
    # 10
    'callao': 10,
    'bellavista': 10,
    'la perla': 10,
    'la punta': 10,
    'carmen de la legua': 10,
    'ventanilla': 10
}

df_processed['antiguedad_categoria'] = pd.cut(
    df_processed['antiguedad'],
    bins=[-1, 5, 20, float('inf')],
    labels=['nuevo', 'seminuevo', 'antiguo']
 )

df_processed['antiguedad_cod'] = df_processed['antiguedad_categoria'].map({'nuevo': 1, 'seminuevo': 2, 'antiguo': 3})
df_processed['zona_apeim_cod'] = df_processed["distrito"].map(zona_apeim)

df_processed['tamano_cod'] = df_processed['tamano'].map({'pequeno': 1, 'mediano': 2, 'grande': 3})

#df_processed['nivel_socioeconomico'] = df_processed['nivel_socioeconomico'].apply(nivel_socioeconomico)

df_processed['nivel_socioeconomico_cod'] = df_processed['nivel_socioeconomico'].map({'A': 1, 'B': 2, 'C': 3, 'D': 4})
df_processed['nivel_socioeconomico_cod']

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
import seaborn as sns
import matplotlib.pyplot as plt

df_miraflores = df_processed[df_processed['distrito'] == 'miraflores']

plt.figure(figsize=(6,4))
sns.boxplot(data=df_miraflores, x='distrito', y='precio_pen')
plt.title('Distribución de precios en Miraflores')
plt.ylabel('Precio (S/.)')
plt.tight_layout()
plt.show()

df_miraflores.info()
#%%
# ph = df_miraflores['precio_pen'].quantile(0.70)
# pl = df_miraflores['precio_pen'].quantile(0.30)

# df_miraflores = df_miraflores[
#     (df_miraflores['precio_pen'] >= pl) & (df_miraflores['precio_pen'] <= ph)
#     ]

# plt.figure(figsize=(6,4))
# sns.boxplot(data=df_miraflores, x='distrito', y='precio_pen')
# plt.title('Distribución de precios en Miraflores')
# plt.ylabel('Precio (S/.)')
# plt.tight_layout()
# plt.show()

# df_miraflores.info()

df_otros = df_processed[df_processed['distrito'] != 'miraflores']

df_processed = pd.concat([df_miraflores, df_otros], ignore_index=True)
df_processed
# %% Drop 'num_visualizaciones' column 
df_processed.drop('num_visualizaciones', axis=1, inplace=True)
df_processed['nivel_socioeconomico_cod'].info()
#%%
df_processed.to_csv(output_path, index = False)
# %%
