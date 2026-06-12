"""
train_weights.py
================
Entrena un Random Forest con TODA la data para derivar los pesos
del score de oportunidad. Guarda el modelo y los pesos en archivos
que luego usa frontier_plot.py.

Outputs generados:
    models/rf_weights.pkl   — modelo entrenado
    models/pesos.json       — pesos listos para usar en el score

Ejecutar UNA sola vez (o cuando quieras recalibrar con data nueva):
    python train_weights.py
"""

import os
import json
import pickle
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score

# ══════════════════════════════════════════════════════════════════════════════
# CONFIGURACIÓN
# ══════════════════════════════════════════════════════════════════════════════

BASE_DIR   = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
INPUT_PATH = os.path.join(BASE_DIR, 'data', 'processed', 'adondevivir_rent',
                          'adondevivir_rent_data_preprocessing_eng.csv')
MODELS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'models')

VARS_POSITIVAS = ['score_ubicacion', 'area_m2', 'num_dorm', 'num_banios', 'flg_estac']
VARS_NEGATIVAS = ['mantenimiento_soles', 'antiguedad']
FEATURES       = VARS_POSITIVAS + VARS_NEGATIVAS

RF_PARAMS  = dict(n_estimators=300, random_state=42, n_jobs=-1)
OUTLIER_P99 = 99

# ══════════════════════════════════════════════════════════════════════════════
# PREPARAR DATOS
# ══════════════════════════════════════════════════════════════════════════════

def preparar_datos(df_raw):
    df = df_raw.copy()
    df['score_ubicacion'] = (
        df['total_servicios_prox'] * 0.6 +
        df['total_transporte_aprox'] * 0.4
    )
    df['mantenimiento_soles'] = df.groupby('distrito')['mantenimiento_soles'].transform(
        lambda s: s.fillna(s.median())
    ).fillna(df['mantenimiento_soles'].median())
    df = df.dropna(subset=FEATURES + ['precio_pen']).reset_index(drop=True)
    df = df[df['precio_pen'] < 12_000].reset_index(drop=True)
    for col in ['area_m2', 'mantenimiento_soles', 'antiguedad']:
        df[col] = df[col].clip(upper=df[col].quantile(OUTLIER_P99 / 100))
    return df

# ══════════════════════════════════════════════════════════════════════════════
# ENTRENAR Y EXTRAER PESOS
# ══════════════════════════════════════════════════════════════════════════════

def entrenar(df):
    X = df[FEATURES]
    y = df['precio_pen']
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    print(f'  Train: {len(X_train):,} filas  |  Test: {len(X_test):,} filas')
    rf = RandomForestRegressor(**RF_PARAMS)
    rf.fit(X_train, y_train)
    y_pred = rf.predict(X_test)
    mae = mean_absolute_error(y_test, y_pred)
    r2  = r2_score(y_test, y_pred)
    print(f'  R²  = {r2:.4f}')
    print(f'  MAE = S/. {mae:,.0f}')
    return rf, mae, r2

def extraer_pesos(rf):
    importancia = pd.Series(rf.feature_importances_, index=FEATURES)
    imp_pos   = importancia[VARS_POSITIVAS]
    imp_neg   = importancia[VARS_NEGATIVAS]
    pesos_pos = (imp_pos / imp_pos.sum()).to_dict()
    pesos_neg = (imp_neg / imp_neg.sum()).to_dict()
    alpha     = float(importancia[VARS_NEGATIVAS].sum() / importancia.sum())
    return {
        'pesos_pos'     : pesos_pos,
        'pesos_neg'     : pesos_neg,
        'alpha'         : alpha,
        'vars_positivas': VARS_POSITIVAS,
        'vars_negativas': VARS_NEGATIVAS,
    }

# ══════════════════════════════════════════════════════════════════════════════
# VISUALIZAR IMPORTANCIAS
# ══════════════════════════════════════════════════════════════════════════════

def plot_importancias(pesos, output_path):
    BG, WHITE, ACCENT = '#0F1923', '#E8F0F5', '#00E5FF'
    vars_   = VARS_POSITIVAS + VARS_NEGATIVAS
    vals    = (
        [pesos['pesos_pos'][v] * (1 - pesos['alpha']) for v in VARS_POSITIVAS] +
        [pesos['pesos_neg'][v] *      pesos['alpha']  for v in VARS_NEGATIVAS]
    )
    colores = [ACCENT] * len(VARS_POSITIVAS) + ['#FF6B6B'] * len(VARS_NEGATIVAS)
    orden   = sorted(range(len(vals)), key=lambda i: vals[i], reverse=True)
    vars_ord    = [vars_[i]   for i in orden]
    vals_ord    = [vals[i]    for i in orden]
    colores_ord = [colores[i] for i in orden]

    fig, ax = plt.subplots(figsize=(8, 5), facecolor=BG)
    ax.set_facecolor(BG)
    for sp in ax.spines.values():
        sp.set_edgecolor('#1A2D3D')
    bars = ax.barh(vars_ord, vals_ord, color=colores_ord, edgecolor='none', height=0.6)
    for bar, val in zip(bars, vals_ord):
        ax.text(val + 0.003, bar.get_y() + bar.get_height() / 2,
                f'{val:.3f}', va='center', color=WHITE, fontsize=9)
    ax.set_xlabel('Peso efectivo en el score', color='#607080', fontsize=10)
    ax.tick_params(colors='#607080', labelsize=9)
    ax.set_title('Pesos derivados del Random Forest\n'
                 '(azul = variable positiva  ·  rojo = penalización)',
                 color=WHITE, fontsize=11, fontweight='bold', pad=10)
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(color=ACCENT, label='Suma al score'),
                       Patch(color='#FF6B6B', label='Resta al score')],
              facecolor='#0D1E2C', edgecolor='#1A3040', labelcolor=WHITE, fontsize=8)
    plt.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f'  Gráfico guardado: {output_path}')

# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    os.makedirs(MODELS_DIR, exist_ok=True)
    pkl_path   = os.path.join(MODELS_DIR, 'rf_weights.pkl')
    pesos_path = os.path.join(MODELS_DIR, 'pesos.json')
    plot_path  = os.path.join(MODELS_DIR, 'importancias.png')

    print('─' * 50)
    print('1. Cargando datos...')
    df = preparar_datos(pd.read_csv(INPUT_PATH))
    print(f'   {len(df):,} propiedades  |  {df["distrito"].nunique()} distritos\n')

    print('2. Entrenando Random Forest...')
    rf, mae, r2 = entrenar(df)
    print()

    print('3. Extrayendo pesos...')
    pesos = extraer_pesos(rf)
    print(f'   Alpha (peso bloque negativo): {pesos["alpha"]:.3f}\n')
    print('   Pesos positivos:')
    for var, w in sorted(pesos['pesos_pos'].items(), key=lambda x: -x[1]):
        print(f'     {var:<25} {w:.4f}  {"█" * int(w * 25)}')
    print('   Pesos negativos:')
    for var, w in sorted(pesos['pesos_neg'].items(), key=lambda x: -x[1]):
        print(f'     {var:<25} {w:.4f}  {"█" * int(w * 25)}')
    print()

    print('4. Guardando archivos...')
    with open(pkl_path, 'wb') as f:
        pickle.dump(rf, f)
    print(f'   Modelo : {pkl_path}')
    with open(pesos_path, 'w') as f:
        json.dump({**pesos, 'r2': r2, 'mae': mae}, f, indent=2)
    print(f'   Pesos  : {pesos_path}')

    print()
    print('5. Generando gráfico de importancias...')
    plot_importancias(pesos, plot_path)

    print()
    print('─' * 50)
    print('Listo. Ahora puedes correr frontier_plot.py')
    print('─' * 50)
