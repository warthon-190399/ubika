"""
test_frontier_plot.py
=====================
Tests unitarios para frontier_plot.py
Ubicacion: src/visualization/efficient_frontier/test_frontier_plot.py

Correr con:
    pytest src/visualization/efficient_frontier/test_frontier_plot.py -v
"""

import os
import sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')   # sin ventana grafica durante tests

# Asegurar que Python encuentre frontier_plot.py en la misma carpeta
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from frontier_plot import (
    preparar_datos,
    calcular_pareto_mask,
    build_frontier_figure,
    get_top_distritos,
    get_color_map,
    COLUMNAS_REQUERIDAS,
)

# ── Fixture: DataFrame minimo valido ──────────────────────────────────────────

def _make_df(n: int = 20) -> pd.DataFrame:
    """Crea un DataFrame sintetico con las columnas requeridas."""
    rng = np.random.default_rng(42)
    distritos = ['miraflores', 'san isidro', 'surco']
    return pd.DataFrame({
        'precio_pen'          : rng.integers(1500, 8000, n).astype(float),
        'precio_por_m2'       : rng.integers(20, 80, n).astype(float),
        'area_m2'             : rng.integers(40, 200, n).astype(float),
        'num_dorm'            : rng.integers(1, 5, n).astype(float),
        'num_banios'          : rng.integers(1, 4, n).astype(float),
        'total_servicios_prox': rng.integers(2, 20, n).astype(float),
        'mantenimiento_soles' : rng.integers(100, 800, n).astype(float),
        'distrito'            : rng.choice(distritos, n),
    })


# ── Tests: preparar_datos ─────────────────────────────────────────────────────

def test_preparar_datos_agrega_columna_score():
    df = preparar_datos(_make_df())
    assert 'score' in df.columns, "Debe existir columna 'score'"


def test_preparar_datos_score_rango():
    df = preparar_datos(_make_df(50))
    assert df['score'].between(-0.1, 1.1).all(), "Score debe estar en rango [-0.1, 1.1]"


def test_preparar_datos_elimina_outliers_precio():
    df_raw = _make_df(30)
    df_raw.loc[0, 'precio_pen'] = 99_999   # outlier
    df = preparar_datos(df_raw)
    assert df['precio_pen'].max() < 12_000, "Debe filtrar precios > 12000"


def test_preparar_datos_elimina_nulos():
    df_raw = _make_df(20)
    df_raw.loc[0, 'area_m2'] = None
    df_raw.loc[1, 'precio_pen'] = None
    df = preparar_datos(df_raw)
    assert df[COLUMNAS_REQUERIDAS].isna().sum().sum() == 0, "No deben quedar nulos"


def test_preparar_datos_no_modifica_original():
    df_raw = _make_df()
    cols_antes = set(df_raw.columns)
    preparar_datos(df_raw)
    assert set(df_raw.columns) == cols_antes, "No debe modificar el DataFrame original"


# ── Tests: calcular_pareto_mask ───────────────────────────────────────────────

def test_pareto_mask_tipo_retorno():
    df = preparar_datos(_make_df())
    mask = calcular_pareto_mask(df)
    assert isinstance(mask, np.ndarray), "Debe retornar np.ndarray"
    assert mask.dtype == bool, "Debe ser de tipo bool"
    assert len(mask) == len(df), "Debe tener misma longitud que el DataFrame"


def test_pareto_mask_al_menos_un_punto():
    df = preparar_datos(_make_df(30))
    mask = calcular_pareto_mask(df)
    assert mask.sum() >= 1, "Debe haber al menos un punto en la frontera"


def test_pareto_mask_no_dominados():
    """Ningun punto de la frontera debe ser dominado por otro."""
    df   = preparar_datos(_make_df(40))
    mask = calcular_pareto_mask(df)
    pts  = df[['precio_pen', 'score']].values
    front = pts[mask]
    for i, p in enumerate(front):
        for j, q in enumerate(front):
            if i == j:
                continue
            assert not (q[0] <= p[0] and q[1] >= p[1] and (q[0] < p[0] or q[1] > p[1])), \
                f"Punto {i} es dominado por {j} — error en pareto_mask"


# ── Tests: build_frontier_figure ─────────────────────────────────────────────

def test_build_figure_retorna_figura():
    import matplotlib.pyplot as plt
    df  = preparar_datos(_make_df(30))
    fig = build_frontier_figure(df, distritos=['miraflores'])
    assert isinstance(fig, plt.Figure), "Debe retornar matplotlib Figure"
    plt.close(fig)


def test_build_figure_con_seleccion():
    import matplotlib.pyplot as plt
    df  = preparar_datos(_make_df(30))
    fig = build_frontier_figure(df, distritos=['miraflores'], viviendas_sel=[0, 1, 2])
    assert isinstance(fig, plt.Figure)
    plt.close(fig)


def test_build_figure_distrito_vacio():
    """Con lista de distritos vacia no debe lanzar excepcion."""
    import matplotlib.pyplot as plt
    df  = preparar_datos(_make_df(20))
    fig = build_frontier_figure(df, distritos=[])
    plt.close(fig)


def test_build_figure_multiples_distritos():
    import matplotlib.pyplot as plt
    df  = preparar_datos(_make_df(60))
    fig = build_frontier_figure(df, distritos=['miraflores', 'san isidro', 'surco'])
    assert isinstance(fig, plt.Figure)
    plt.close(fig)


# ── Tests: utilidades ─────────────────────────────────────────────────────────

def test_get_top_distritos():
    df     = preparar_datos(_make_df(60))
    top    = get_top_distritos(df, n=2)
    assert len(top) <= 2
    assert all(isinstance(d, str) for d in top)


def test_get_color_map():
    distritos = ['miraflores', 'san isidro', 'surco']
    cmap      = get_color_map(distritos)
    assert set(cmap.keys()) == set(distritos)
    assert all(len(v) == 4 for v in cmap.values()), "Colores deben ser RGBA (4 valores)"