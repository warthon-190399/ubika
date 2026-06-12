"""
frontier_plot.py
================
Genera el gráfico de Frontera de Pareto usando los pesos
pre-entrenados por train_weights.py.

El score de oportunidad se calcula con pesos FIJOS (del modelo entrenado
con toda la data), por lo que es estable sin importar cuántas filas
tenga el subconjunto que el usuario quiera visualizar.

Requiere haber corrido train_weights.py al menos una vez.

Ejecutar con:
    python frontier_plot.py
"""

import os
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
from matplotlib.lines import Line2D

# ══════════════════════════════════════════════════════════════════════════════
# CONFIGURACIÓN — ajusta estos valores
# ══════════════════════════════════════════════════════════════════════════════

BASE_DIR   = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
INPUT_PATH = os.path.join(BASE_DIR, 'data', 'processed', 'adondevivir_rent',
                          'adondevivir_rent_data_preprocessing_eng.csv')
MODELS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'models')
PESOS_PATH = os.path.join(MODELS_DIR, 'pesos.json')

DISTRITOS  = ['miraflores', 'san isidro']   # distritos a visualizar
PRECIO_MAX = 12_000
OUTLIER_P99 = 99

BG         = '#0F1923'
WHITE      = '#E8F0F5'
SUBTEXT    = '#607080'
ACCENT     = '#00E5FF'
GOLD       = '#FFD700'
COLORES    = ['#FF6B6B', '#4FC3F7', '#81C784', '#FFB74D', '#CE93D8']


# ══════════════════════════════════════════════════════════════════════════════
# 1. CARGAR PESOS
# ══════════════════════════════════════════════════════════════════════════════

def cargar_pesos(path: str) -> dict:
    if not os.path.exists(path):
        raise FileNotFoundError(
            f'No se encontró {path}\n'
            'Corre primero: python train_weights.py'
        )
    with open(path) as f:
        pesos = json.load(f)
    print(f'Pesos cargados desde: {path}')
    print(f'  R² del modelo  : {pesos.get("r2", "N/A"):.4f}')
    print(f'  MAE del modelo : S/. {pesos.get("mae", 0):,.0f}')
    print(f'  Alpha          : {pesos["alpha"]:.3f}')
    return pesos


# ══════════════════════════════════════════════════════════════════════════════
# 2. PREPARAR DATOS (sin reentrenar)
# ══════════════════════════════════════════════════════════════════════════════

def preparar_datos(df_raw: pd.DataFrame, pesos: dict) -> pd.DataFrame:
    """
    Limpia los datos y calcula el score con los pesos fijos del modelo.
    No entrena nada — solo aplica la fórmula.
    """
    vars_requeridas = pesos['vars_positivas'] + pesos['vars_negativas']
    # score_ubicacion se calcula, no se lee del CSV directamente
    vars_csv = [v for v in vars_requeridas if v != 'score_ubicacion']

    df = df_raw.copy()

    # Recalcular score_ubicacion
    df['score_ubicacion'] = (
        df['total_servicios_prox'] * 0.6 +
        df['total_transporte_aprox'] * 0.4
    )

    # Imputar mantenimiento con mediana por distrito
    df['mantenimiento_soles'] = df.groupby('distrito')['mantenimiento_soles'].transform(
        lambda s: s.fillna(s.median())
    ).fillna(df['mantenimiento_soles'].median())

    df = df.dropna(subset=vars_requeridas + ['precio_pen']).reset_index(drop=True)
    df = df[df['precio_pen'] < PRECIO_MAX].reset_index(drop=True)

    # Clipear outliers al p99 — mismos cortes que en entrenamiento
    for col in ['area_m2', 'mantenimiento_soles', 'antiguedad']:
        if col in df.columns:
            df[col] = df[col].clip(upper=df[col].quantile(OUTLIER_P99 / 100))

    df = _calcular_score(df, pesos)
    return df


def _norm(s: pd.Series) -> pd.Series:
    rng = s.max() - s.min()
    return (s - s.min()) / rng if rng > 0 else pd.Series(0.0, index=s.index)


def _calcular_score(df: pd.DataFrame, pesos: dict) -> pd.DataFrame:
    """
    Aplica la fórmula de score con pesos fijos:

        score = (1 - alpha) × Σ(peso_pos_i × norm(var_pos_i))
              -      alpha  × Σ(peso_neg_j × norm(var_neg_j))

    Los pesos NO cambian con el subconjunto de datos — vienen del modelo.
    La normalización sí es local al subconjunto para que el score
    sea relativo dentro del conjunto que se está visualizando.
    """
    df = df.copy()
    alpha = pesos['alpha']

    bloque_pos = sum(
        pesos['pesos_pos'][var] * _norm(df[var])
        for var in pesos['vars_positivas']
    )
    bloque_neg = sum(
        pesos['pesos_neg'][var] * _norm(df[var])
        for var in pesos['vars_negativas']
    )

    df['score'] = ((1 - alpha) * bloque_pos - alpha * bloque_neg).clip(0, 1)
    return df


# ══════════════════════════════════════════════════════════════════════════════
# 3. FRONTERA DE PARETO
# ══════════════════════════════════════════════════════════════════════════════

def pareto_inferior(df: pd.DataFrame) -> pd.DataFrame:
    """Maximiza score, minimiza precio — oportunidades."""
    if df.empty:
        return df
    pts   = df[['precio_pen', 'score']].values
    orden = np.lexsort((pts[:, 0], -pts[:, 1]))
    mask  = np.zeros(len(pts), dtype=bool)
    min_p = np.inf
    for idx in orden:
        if pts[idx, 0] < min_p:
            mask[idx] = True
            min_p = pts[idx, 0]
    return df[mask].sort_values('precio_pen')


def pareto_superior(df: pd.DataFrame) -> pd.DataFrame:
    """Maximiza score, maximiza precio — premium."""
    if df.empty:
        return df
    pts   = df[['precio_pen', 'score']].values
    orden = np.lexsort((-pts[:, 0], -pts[:, 1]))
    mask  = np.zeros(len(pts), dtype=bool)
    max_p = -np.inf
    for idx in orden:
        if pts[idx, 0] > max_p:
            mask[idx] = True
            max_p = pts[idx, 0]
    return df[mask].sort_values('precio_pen')


# ══════════════════════════════════════════════════════════════════════════════
# 4. GRÁFICO
# ══════════════════════════════════════════════════════════════════════════════

def build_figure(df: pd.DataFrame, distritos: list, pesos: dict) -> plt.Figure:
    n         = max(len(distritos), 1)
    cmap_fn   = plt.cm.tab10 if n <= 10 else plt.cm.tab20
    color_map = {d: cmap_fn(i / n) for i, d in enumerate(distritos)}

    df_dist = df[df['distrito'].isin(distritos)].copy()
    df_inf  = pareto_inferior(df_dist)
    df_sup  = pareto_superior(df_dist)

    fig, ax = plt.subplots(figsize=(12, 7), facecolor=BG)
    ax.set_facecolor(BG)
    for sp in ax.spines.values():
        sp.set_edgecolor('#1A2D3D')

    # Scatter
    for dist in distritos:
        sub = df_dist[df_dist['distrito'] == dist]
        ax.scatter(sub['precio_pen'], sub['score'],
                   color=color_map[dist], s=22, alpha=0.30, zorder=2, linewidths=0)

    # Frontera inferior (azul)
    if len(df_inf) > 1:
        ax.step(df_inf['precio_pen'], df_inf['score'],
                where='post', color=ACCENT, linewidth=2.2, zorder=4, alpha=0.9,
                path_effects=[pe.Stroke(linewidth=5, foreground='#003344', alpha=0.4),
                               pe.Normal()])
        ax.fill_between(df_inf['precio_pen'], df_inf['score'],
                        step='post', alpha=0.05, color=ACCENT, zorder=1)
    for dist in distritos:
        sub_f = df_inf[df_inf['distrito'] == dist]
        ax.scatter(sub_f['precio_pen'], sub_f['score'],
                   color=color_map[dist], s=70, zorder=5,
                   edgecolors=ACCENT, linewidths=1.3)

    # Frontera superior (dorada)
    if len(df_sup) > 1:
        ax.step(df_sup['precio_pen'], df_sup['score'],
                where='post', color=GOLD, linewidth=2.2, zorder=4, alpha=0.9,
                linestyle='--',
                path_effects=[pe.Stroke(linewidth=5, foreground='#332200', alpha=0.4),
                               pe.Normal()])
        ax.fill_between(df_sup['precio_pen'], df_sup['score'],
                        step='post', alpha=0.04, color=GOLD, zorder=1)
    for dist in distritos:
        sub_s = df_sup[df_sup['distrito'] == dist]
        ax.scatter(sub_s['precio_pen'], sub_s['score'],
                   color=color_map[dist], s=70, zorder=5,
                   edgecolors=GOLD, linewidths=1.3)

    # Anotaciones frontera inferior
    for _, row in df_inf.iterrows():
        c = color_map.get(row['distrito'], WHITE)
        ax.annotate(
            f"S/.{row['precio_pen']:,.0f}\n"
            f"{row['area_m2']:.0f}m² · {int(row['num_dorm'])}D",
            xy=(row['precio_pen'], row['score']),
            xytext=(row['precio_pen'] + 150, row['score'] + 0.02),
            fontsize=7, color=c,
            arrowprops=dict(arrowstyle='->', color=c, lw=0.8),
            bbox=dict(boxstyle='round,pad=0.25', facecolor='#0D1E2C',
                      edgecolor=c, alpha=0.85),
            zorder=6)

    # Medianas
    med_p = df_dist['precio_pen'].median()
    med_s = df_dist['score'].median()
    ax.axvline(med_p, color='#2A3F52', lw=1, linestyle=':', zorder=1)
    ax.axhline(med_s, color='#2A3F52', lw=1, linestyle=':', zorder=1)
    ymin, _ = ax.get_ylim()
    ax.text(med_p + 50, ymin + 0.005, 'precio\nmediano',
            color='#2A3F52', fontsize=7, va='bottom')

    # Leyenda
    handles = [
        Line2D([0], [0], marker='o', color='w',
               markerfacecolor=color_map[d], markersize=9, label=d.title())
        for d in distritos
    ] + [
        Line2D([0], [0], color=ACCENT, lw=2,
               label=f'Frontera oportunidad ({len(df_inf)} props)'),
        Line2D([0], [0], color=GOLD, lw=2, linestyle='--',
               label=f'Frontera premium ({len(df_sup)} props)'),
    ]
    ax.legend(handles=handles, loc='upper left',
              facecolor='#0D1E2C', edgecolor='#1A3040',
              labelcolor=WHITE, fontsize=8.5, framealpha=0.9)

    ax.set_xlabel('Precio mensual (S/.)', color=SUBTEXT, fontsize=11, labelpad=10)
    ax.set_ylabel('Score de Oportunidad', color=SUBTEXT, fontsize=11, labelpad=10)
    ax.tick_params(colors=SUBTEXT, labelsize=9)
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'S/.{x:,.0f}'))
    ax.grid(True, color='#131F2A', linestyle='--', linewidth=0.5, alpha=0.8)
    ax.set_title(
        f"Frontera de Pareto — Score de Oportunidad vs Precio\n"
        f"{' · '.join(d.title() for d in distritos)}  "
        f"|  {len(df_dist):,} propiedades  "
        f"|  pesos: R²={pesos.get('r2', 0):.3f}",
        color=WHITE, fontsize=12, fontweight='bold', pad=12,
    )

    # Fórmula al pie con pesos reales
    alpha = pesos['alpha']
    pos_str = ' + '.join(
        f'{w:.2f}×{v}' for v, w
        in sorted(pesos['pesos_pos'].items(), key=lambda x: -x[1])
    )
    neg_str = ' + '.join(
        f'{w:.2f}×{v}' for v, w
        in sorted(pesos['pesos_neg'].items(), key=lambda x: -x[1])
    )
    fig.text(
        0.5, 0.01,
        f'Score = {1-alpha:.2f}×({pos_str})  −  {alpha:.2f}×({neg_str})',
        ha='center', color=SUBTEXT, fontsize=6.5, style='italic',
    )
    plt.tight_layout(rect=[0, 0.03, 1, 1])
    return fig


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    print('─' * 50)

    # 1. Cargar pesos pre-entrenados
    pesos = cargar_pesos(PESOS_PATH)
    print()

    # 2. Cargar y preparar datos (sin reentrenar)
    print('Cargando datos...')
    df = preparar_datos(pd.read_csv(INPUT_PATH), pesos)
    print(f'Propiedades cargadas: {len(df):,}')
    print(f'Score — min: {df["score"].min():.3f}  '
          f'media: {df["score"].mean():.3f}  '
          f'max: {df["score"].max():.3f}')
    print(f'Distritos disponibles: {sorted(df["distrito"].unique())}')
    print()

    # 3. Graficar
    print(f'Graficando: {DISTRITOS}')
    fig = build_figure(df, DISTRITOS, pesos)
    plt.show()
