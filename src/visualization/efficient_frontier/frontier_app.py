"""
frontier_app.py
===============
Punto de entrada para probar el gráfico de Frontera de Pareto en ventana local.
Ubica este archivo en: src/visualization/efficient_frontier/frontier_app.py
"""

import os
import matplotlib.pyplot as plt
import pandas as pd

from frontier_plot import preparar_datos, build_frontier_figure

# ── Rutas ─────────────────────────────────────────────────────────────────────
BASE_DIR   = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
INPUT_PATH = os.path.join(
    BASE_DIR, 'data', 'processed',
    'adondevivir_rent', 'adondevivir_rent_data_preprocessing_eng.csv'
)

# ── Parámetros de prueba (ajusta según lo que quieras visualizar) ─────────────
DISTRITOS     = ['miraflores', 'san isidro']
VIVIENDAS_SEL = []   # índices del DataFrame; dejar vacío para ver solo el mercado

# ── Ejecutar ──────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    print(f'Cargando datos desde:\n  {INPUT_PATH}\n')

    df  = preparar_datos(pd.read_csv(INPUT_PATH))
    print(f'Propiedades cargadas : {len(df):,}')
    print(f'Distritos disponibles: {sorted(df["distrito"].unique().tolist())}\n')

    fig = build_frontier_figure(
        df,
        distritos=DISTRITOS,
        viviendas_sel=VIVIENDAS_SEL,
    )

    plt.show()
