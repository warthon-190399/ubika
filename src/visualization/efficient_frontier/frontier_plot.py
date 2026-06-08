"""
frontier_plot.py
================
Lógica pura del gráfico de Frontera de Pareto — Oportunidad vs Precio.
Sin widgets, sin interactividad, sin side effects al importar.

Uso desde otra interfaz:
    from frontier_plot import preparar_datos, build_frontier_figure

    df  = preparar_datos(df_raw)
    fig = build_frontier_figure(df, distritos=['miraflores', 'san isidro'])
    fig = build_frontier_figure(df, distritos=['miraflores'], viviendas_sel=[12, 45, 78])
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.patheffects as pe
from matplotlib.gridspec import GridSpec
from matplotlib.lines import Line2D

# ── Constantes ────────────────────────────────────────────────────────────────
PRECIO_MAX    = 12_000
MAX_VIVIENDAS = 5
TOP_N_TABLA   = 15

COLUMNAS_REQUERIDAS = [
    'precio_pen', 'precio_por_m2', 'area_m2',
    'num_dorm', 'num_banios', 'total_servicios_prox',
    'mantenimiento_soles', 'distrito',
]

# ── Paleta ────────────────────────────────────────────────────────────────────
BG         = '#0F1923'
WHITE      = '#E8F0F5'
SUBTEXT    = '#607080'
ACCENT     = '#00E5FF'
GOLD       = '#FFD700'
SEL_COLORS = ['#FF6B6B', '#4FC3F7', '#81C784', '#FFB74D', '#CE93D8']


# ── Funciones de cálculo ──────────────────────────────────────────────────────

def preparar_datos(df_raw: pd.DataFrame) -> pd.DataFrame:
    """
    Limpia el DataFrame y calcula el score de oportunidad por distrito.

    Parámetros
    ----------
    df_raw : DataFrame crudo con las columnas requeridas.

    Retorna
    -------
    DataFrame limpio con columna 'score' agregada.
    """
    df = df_raw.dropna(subset=COLUMNAS_REQUERIDAS).copy()
    df = df[df['precio_pen'] < PRECIO_MAX].reset_index(drop=True)
    return _calcular_score(df)


def _calcular_score(df: pd.DataFrame) -> pd.DataFrame:
    """Calcula score de oportunidad normalizado dentro de cada distrito."""
    result = []
    for _, grp in df.groupby('distrito'):
        grp = grp.copy()
        med = grp['precio_por_m2'].median()

        def norm(s):
            rng = s.max() - s.min()
            return (s - s.min()) / rng if rng > 0 else pd.Series(0, index=s.index)

        grp['score'] = (
            0.35 * norm(med - grp['precio_por_m2'])
          + 0.30 * norm(grp['area_m2'])
          + 0.20 * norm(grp['num_dorm'])
          + 0.10 * norm(grp['total_servicios_prox'])
          - 0.05 * norm(grp['mantenimiento_soles'])
        )
        result.append(grp)

    return pd.concat(result).reset_index(drop=True)


def calcular_pareto_mask(
    df: pd.DataFrame,
    x_col: str = 'precio_pen',
    y_col: str = 'score',
) -> np.ndarray:
    """
    Devuelve mascara booleana de puntos en la frontera de Pareto.
    Minimiza x (precio), maximiza y (score).

    Parámetros
    ----------
    df    : DataFrame con las columnas x_col e y_col.
    x_col : columna del eje X (minimizar).
    y_col : columna del eje Y (maximizar).

    Retorna
    -------
    np.ndarray de bool con True en los puntos no dominados.
    """
    pts  = df[[x_col, y_col]].values
    n    = len(pts)
    mask = np.ones(n, dtype=bool)

    for i in range(n):
        if not mask[i]:
            continue
        dominated = (
            (pts[:, 0] <= pts[i, 0]) &
            (pts[:, 1] >= pts[i, 1]) &
            ((pts[:, 0] < pts[i, 0]) | (pts[:, 1] > pts[i, 1]))
        )
        dominated[i] = False
        if dominated.any():
            mask[i] = False

    return mask


def get_top_distritos(df: pd.DataFrame, n: int = 8) -> list:
    """Retorna los n distritos con mas propiedades."""
    return df['distrito'].value_counts().head(n).index.tolist()


def get_color_map(distritos: list) -> dict:
    """Asigna un color unico a cada distrito."""
    colors = plt.cm.tab10(np.linspace(0, 0.9, max(len(distritos), 1)))
    return {d: colors[i] for i, d in enumerate(distritos)}


# ── Función principal ─────────────────────────────────────────────────────────

def build_frontier_figure(
    df: pd.DataFrame,
    distritos: list,
    viviendas_sel: list = None,
    dist_color_map: dict = None,
    figsize: tuple = (14, 9),
) -> plt.Figure:
    """
    Construye y retorna la figura matplotlib de la Frontera de Pareto.

    Parámetros
    ----------
    df             : DataFrame preparado con preparar_datos().
    distritos      : Lista de distritos a mostrar.
    viviendas_sel  : Lista de indices del DataFrame de viviendas a resaltar (max 5).
    dist_color_map : Diccionario {distrito: color}. Si None se genera automaticamente.
    figsize        : Tamaño de la figura en pulgadas.

    Retorna
    -------
    matplotlib.figure.Figure lista para renderizar.

    Ejemplos
    --------
    # Guardar como imagen
    fig = build_frontier_figure(df, ['miraflores'])
    fig.savefig('output.png', dpi=150)

    # Mostrar en ventana local
    plt.show()

    # Streamlit
    st.pyplot(fig)

    # Dash
    # Convertir a imagen base64 y usar en dcc.Graph, o usar mpl_to_plotly
    """
    viviendas_sel = viviendas_sel or []

    if dist_color_map is None:
        dist_color_map = get_color_map(get_top_distritos(df))

    df_dist = df[df['distrito'].isin(distritos)].copy()

    # ── Figura ────────────────────────────────────────────────────────────────
    fig = plt.figure(figsize=figsize, facecolor=BG)
    gs  = GridSpec(
        2, 1, figure=fig,
        left=0.08, right=0.97, top=0.92, bottom=0.10,
        hspace=0.45, height_ratios=[2.2, 1.0],
    )
    ax_main  = fig.add_subplot(gs[0])
    ax_table = fig.add_subplot(gs[1])

    for ax in [ax_main, ax_table]:
        ax.set_facecolor(BG)
        for sp in ax.spines.values():
            sp.set_edgecolor('#1A2D3D')

    # ── Scatter fondo ─────────────────────────────────────────────────────────
    for dist in distritos:
        sub = df_dist[df_dist['distrito'] == dist]
        c   = dist_color_map.get(dist, 'gray')
        ax_main.scatter(
            sub['precio_pen'], sub['score'],
            color=c, s=18, alpha=0.30, zorder=2, linewidths=0,
        )

    # ── Frontera de Pareto global ─────────────────────────────────────────────
    pm       = calcular_pareto_mask(df_dist)
    df_front = df_dist[pm].sort_values('precio_pen')

    ax_main.step(
        df_front['precio_pen'], df_front['score'],
        where='post', color=ACCENT, linewidth=2.0, zorder=4, alpha=0.85,
        path_effects=[
            pe.Stroke(linewidth=4, foreground='#003344', alpha=0.4),
            pe.Normal(),
        ],
    )
    ax_main.fill_between(
        df_front['precio_pen'], df_front['score'],
        step='post', alpha=0.05, color=ACCENT, zorder=1,
    )

    for dist in distritos:
        sub_p = df_front[df_front['distrito'] == dist]
        c     = dist_color_map.get(dist, 'gray')
        ax_main.scatter(
            sub_p['precio_pen'], sub_p['score'],
            color=c, s=60, alpha=1.0, zorder=5,
            edgecolors=ACCENT, linewidths=1.0,
        )

    # ── Viviendas seleccionadas ───────────────────────────────────────────────
    if viviendas_sel:
        df_sel = df.loc[viviendas_sel]

        for rank, (_, row) in enumerate(df_sel.iterrows()):
            sc = SEL_COLORS[rank % len(SEL_COLORS)]
            ax_main.scatter(
                row['precio_pen'], row['score'],
                color=sc, s=200, zorder=7,
                edgecolors='white', linewidths=1.5, marker='*',
            )
            ax_main.annotate(
                f"#{rank+1}  S/.{row['precio_pen']:,.0f}\n"
                f"{row['area_m2']:.0f}m²  ·  {int(row['num_dorm'])}D",
                xy=(row['precio_pen'], row['score']),
                xytext=(row['precio_pen'] + 120, row['score'] + 0.015),
                fontsize=7.5, color=sc,
                arrowprops=dict(arrowstyle='->', color=sc, lw=0.9),
                bbox=dict(boxstyle='round,pad=0.3',
                          facecolor='#0D1E2C', edgecolor=sc, alpha=0.9),
                zorder=8,
            )

        if len(viviendas_sel) >= 2:
            pm_sel = calcular_pareto_mask(df_sel)
            df_ps  = df_sel[pm_sel].sort_values('precio_pen')
            if len(df_ps) >= 2:
                ax_main.step(
                    df_ps['precio_pen'], df_ps['score'],
                    where='post', color=GOLD, linewidth=2.0,
                    linestyle='--', zorder=6, alpha=0.9,
                )

    # ── Medianas ──────────────────────────────────────────────────────────────
    med_p = df_dist['precio_pen'].median()
    med_s = df_dist['score'].median()
    ax_main.axvline(med_p, color='#2A3F52', lw=1, linestyle=':', zorder=1)
    ax_main.axhline(med_s, color='#2A3F52', lw=1, linestyle=':', zorder=1)
    ax_main.text(med_p + 50, ax_main.get_ylim()[0] + 0.005,
                 'precio\nmediano', color='#2A3F52', fontsize=7, va='bottom')

    # ── Leyenda ───────────────────────────────────────────────────────────────
    handles = [
        Line2D([0],[0], marker='o', color='w',
               markerfacecolor=dist_color_map.get(d, 'gray'),
               markersize=8, label=d.title())
        for d in distritos
    ]
    handles.append(Line2D([0],[0], color=ACCENT, lw=2,
                          label=f'Frontera Pareto ({pm.sum()} props)'))
    if len(viviendas_sel) >= 2:
        handles.append(Line2D([0],[0], color=GOLD, lw=2, linestyle='--',
                              label='Frontera seleccion'))

    ax_main.legend(handles=handles, loc='lower right',
                   facecolor='#0D1E2C', edgecolor='#1A3040',
                   labelcolor=WHITE, fontsize=8, framealpha=0.9)

    ax_main.set_xlabel('Precio mensual (S/.)', color=SUBTEXT, fontsize=10, labelpad=8)
    ax_main.set_ylabel('Score de Oportunidad',  color=SUBTEXT, fontsize=10, labelpad=8)
    ax_main.tick_params(colors=SUBTEXT, labelsize=8)
    ax_main.grid(True, color='#131F2A', linestyle='--', linewidth=0.5, alpha=0.8)
    ax_main.set_title(
        f"Frontera de Pareto — Oportunidad vs Precio\n"
        f"{' · '.join(d.title() for d in distritos)}  |  {len(df_dist):,} propiedades",
        color=WHITE, fontsize=12, fontweight='bold', pad=10,
    )

    # ── Tabla ─────────────────────────────────────────────────────────────────
    _draw_table(ax_table, df_dist, viviendas_sel)

    fig.text(
        0.5, 0.01,
        'Score = 0.35×(precio bajo vs. distrito) + 0.30×area + 0.20×dormitorios'
        ' + 0.10×servicios - 0.05×mantenimiento'
        '   |   linea azul = frontera mercado   ·   linea dorada = frontera seleccion',
        ha='center', color=SUBTEXT, fontsize=7, style='italic',
    )

    return fig


def _draw_table(ax: plt.Axes, df: pd.DataFrame, viviendas_sel: list) -> None:
    """Dibuja la tabla de top viviendas en el eje dado."""
    df_tabla = (
        df.nlargest(TOP_N_TABLA, 'score')
          [['distrito','precio_pen','area_m2','num_dorm','num_banios',
            'mantenimiento_soles','score']]
          .copy()
          .reset_index()
    )
    n = len(df_tabla)

    ax.set_xlim(0, 1)
    ax.set_ylim(0, n + 1)
    ax.set_xticks([]); ax.set_yticks([])
    ax.set_facecolor(BG)
    ax.set_title(
        f'Top {TOP_N_TABLA} por Score de Oportunidad'
        f'  (seleccionadas: {len(viviendas_sel)}/{MAX_VIVIENDAS})',
        color=WHITE, fontsize=9, pad=6,
    )

    cols  = ['Distrito', 'Precio/mes', 'Area m2', 'Dorm.', 'Banos', 'Mant. S/.', 'Score']
    col_x = [0.01, 0.14, 0.30, 0.42, 0.52, 0.63, 0.80]

    for cx, col in zip(col_x, cols):
        ax.text(cx, n + 0.5, col, color=ACCENT, fontsize=8,
                fontweight='bold', va='center')

    for i, row in df_tabla.iterrows():
        y        = n - i - 0.5
        orig_idx = row['index']
        is_sel   = orig_idx in viviendas_sel
        sel_rank = viviendas_sel.index(orig_idx) + 1 if is_sel else None

        bg_color = ('#1E3020' if is_sel
                    else '#1A2E3E' if i % 2 == 0
                    else '#142330')

        ax.add_patch(mpatches.FancyBboxPatch(
            (0, y - 0.45), 1, 0.9,
            boxstyle='round,pad=0.01',
            facecolor=bg_color,
            edgecolor=GOLD if is_sel else 'none',
            linewidth=1.2 if is_sel else 0, zorder=1,
        ))

        prefix    = f'*{sel_rank} ' if is_sel else '   '
        txt_color = SEL_COLORS[sel_rank - 1] if is_sel else WHITE
        vals = [
            prefix + row['distrito'].title(),
            f"S/. {row['precio_pen']:,.0f}",
            f"{row['area_m2']:.0f}",
            f"{int(row['num_dorm'])}",
            f"{int(row['num_banios'])}",
            f"S/. {row['mantenimiento_soles']:,.0f}",
            f"{row['score']:.3f}",
        ]
        for cx, val in zip(col_x, vals):
            ax.text(cx, y, val, color=txt_color, fontsize=8, va='center')

        bar_w = row['score'] * 0.14
        bar_c = GOLD if row['score'] > df_tabla['score'].quantile(0.75) else '#2196F3'
        ax.barh(y, bar_w, height=0.5, left=col_x[-1] + 0.05,
                color=bar_c, alpha=0.6, zorder=2)
