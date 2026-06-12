"""
waterfall_score.py
==================
Gráfico de waterfall que descompone el score de oportunidad
de una propiedad específica, mostrando cuánto aporta (o resta)
cada variable al score final.

Requiere haber corrido train_weights.py al menos una vez.

Ejecutar con:
    python waterfall_score.py
"""

import os
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

# ══════════════════════════════════════════════════════════════════════════════
# CONFIGURACIÓN
# ══════════════════════════════════════════════════════════════════════════════

BASE_DIR    = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
INPUT_PATH  = os.path.join(BASE_DIR, 'data', 'processed', 'adondevivir_rent',
                           'adondevivir_rent_data_preprocessing_eng.csv')
MODELS_DIR  = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'models')
PESOS_PATH  = os.path.join(MODELS_DIR, 'pesos.json')

DISTRITO        = 'miraflores'   # distrito a analizar
PROPIEDAD_IDX   = 0              # índice de la propiedad dentro del distrito
PRECIO_MAX      = 12_000
OUTLIER_P99     = 99

BG      = '#0F1923'
WHITE   = '#E8F0F5'
SUBTEXT = '#607080'
ACCENT  = '#00E5FF'
VERDE   = '#4CAF50'
ROJO    = '#FF5252'
GOLD    = '#FFD700'


# ══════════════════════════════════════════════════════════════════════════════
# PREPARAR DATOS
# ══════════════════════════════════════════════════════════════════════════════

def preparar_datos(df_raw: pd.DataFrame, pesos: dict) -> pd.DataFrame:
    df = df_raw.copy()
    df['score_ubicacion'] = (
        df['total_servicios_prox'] * 0.6 +
        df['total_transporte_aprox'] * 0.4
    )
    df['mantenimiento_soles'] = df.groupby('distrito')['mantenimiento_soles'].transform(
        lambda s: s.fillna(s.median())
    ).fillna(df['mantenimiento_soles'].median())

    features = pesos['vars_positivas'] + pesos['vars_negativas']
    df = df.dropna(subset=features + ['precio_pen']).reset_index(drop=True)
    df = df[df['precio_pen'] < PRECIO_MAX].reset_index(drop=True)

    for col in ['area_m2', 'mantenimiento_soles', 'antiguedad']:
        if col in df.columns:
            df[col] = df[col].clip(upper=df[col].quantile(OUTLIER_P99 / 100))
    return df


def _norm(s: pd.Series) -> pd.Series:
    rng = s.max() - s.min()
    return (s - s.min()) / rng if rng > 0 else pd.Series(0.0, index=s.index)


# ══════════════════════════════════════════════════════════════════════════════
# CALCULAR CONTRIBUCIONES
# ══════════════════════════════════════════════════════════════════════════════

def calcular_contribuciones(df: pd.DataFrame, idx: int, pesos: dict) -> pd.DataFrame:
    """
    Para la propiedad en `idx`, calcula cuánto aporta cada variable
    al score final.

    Retorna DataFrame con columnas:
        variable, valor_raw, valor_norm, contribucion, es_positiva
    """
    alpha     = pesos['alpha']
    rows      = []

    for var in pesos['vars_positivas']:
        norm_serie  = _norm(df[var])
        peso        = pesos['pesos_pos'][var]
        contribucion = (1 - alpha) * peso * norm_serie.iloc[idx]
        rows.append({
            'variable'   : var,
            'valor_raw'  : df[var].iloc[idx],
            'valor_norm' : norm_serie.iloc[idx],
            'contribucion': contribucion,
            'es_positiva': True,
        })

    for var in pesos['vars_negativas']:
        norm_serie   = _norm(df[var])
        peso         = pesos['pesos_neg'][var]
        contribucion = -alpha * peso * norm_serie.iloc[idx]
        rows.append({
            'variable'   : var,
            'valor_raw'  : df[var].iloc[idx],
            'valor_norm' : norm_serie.iloc[idx],
            'contribucion': contribucion,
            'es_positiva': False,
        })

    df_contrib = pd.DataFrame(rows)
    df_contrib['score_final'] = df_contrib['contribucion'].sum()
    return df_contrib


# ══════════════════════════════════════════════════════════════════════════════
# ETIQUETAS LEGIBLES
# ══════════════════════════════════════════════════════════════════════════════

ETIQUETAS = {
    'score_ubicacion'   : 'Ubicación',
    'area_m2'           : 'Área m²',
    'num_dorm'          : 'Dormitorios',
    'num_banios'        : 'Baños',
    'flg_estac'         : 'Estacionamiento',
    'mantenimiento_soles': 'Mantenimiento',
    'antiguedad'        : 'Antigüedad',
}

UNIDADES = {
    'score_ubicacion'   : '',
    'area_m2'           : ' m²',
    'num_dorm'          : '',
    'num_banios'        : '',
    'flg_estac'         : ' (sí/no)',
    'mantenimiento_soles': ' S/.',
    'antiguedad'        : ' años',
}


# ══════════════════════════════════════════════════════════════════════════════
# GRÁFICO WATERFALL
# ══════════════════════════════════════════════════════════════════════════════

def build_waterfall(
    df_contrib: pd.DataFrame,
    propiedad: pd.Series,
    distrito: str,
    idx: int,
) -> plt.Figure:

    # Ordenar: positivas desc, luego negativas asc
    pos = df_contrib[df_contrib['es_positiva']].sort_values('contribucion', ascending=False)
    neg = df_contrib[~df_contrib['es_positiva']].sort_values('contribucion')
    df_ord = pd.concat([pos, neg]).reset_index(drop=True)

    score_final = df_contrib['score_final'].iloc[0]
    n           = len(df_ord)

    fig, ax = plt.subplots(figsize=(10, 6), facecolor=BG)
    ax.set_facecolor(BG)
    for sp in ax.spines.values():
        sp.set_edgecolor('#1A2D3D')

    # Calcular posición acumulada de cada barra
    acum    = 0.0
    bottoms = []
    for _, row in df_ord.iterrows():
        if row['contribucion'] >= 0:
            bottoms.append(acum)
            acum += row['contribucion']
        else:
            acum += row['contribucion']
            bottoms.append(acum)

    # Dibujar barras
    bar_labels = []
    for i, (_, row) in enumerate(df_ord.iterrows()):
        c      = VERDE if row['es_positiva'] else ROJO
        altura = abs(row['contribucion'])
        bar = ax.bar(i, altura, bottom=bottoms[i],
                     color=c, alpha=0.85, width=0.55,
                     edgecolor=BG, linewidth=1.5, zorder=3)

        # Valor encima/debajo de la barra
        y_txt = bottoms[i] + altura + 0.003 if row['contribucion'] >= 0 \
                else bottoms[i] - 0.003
        va    = 'bottom' if row['contribucion'] >= 0 else 'top'
        signo = '+' if row['contribucion'] >= 0 else ''
        ax.text(i, y_txt, f'{signo}{row["contribucion"]:.3f}',
                ha='center', va=va, color=WHITE, fontsize=8.5, fontweight='bold')

        # Etiqueta eje X con valor raw
        var    = row['variable']
        val    = row['valor_raw']
        etiq   = ETIQUETAS.get(var, var)
        unidad = UNIDADES.get(var, '')
        if var == 'flg_estac':
            val_str = 'Sí' if val == 1 else 'No'
        elif val == int(val):
            val_str = f'{int(val)}{unidad}'
        else:
            val_str = f'{val:.1f}{unidad}'
        bar_labels.append(f'{etiq}\n({val_str})')

    # Línea de score final
    ax.axhline(score_final, color=GOLD, lw=1.5, linestyle='--', zorder=4, alpha=0.8)
    ax.text(n - 0.3, score_final + 0.005,
            f'Score final: {score_final:.3f}',
            color=GOLD, fontsize=9, fontweight='bold', va='bottom')

    # Líneas de conexión entre barras
    acum2 = 0.0
    for i, (_, row) in enumerate(df_ord.iterrows()):
        if i < n - 1:
            top = acum2 + row['contribucion'] if row['contribucion'] >= 0 \
                  else acum2
            ax.plot([i + 0.275, i + 0.725], [acum2 + row['contribucion']] * 2,
                    color='#2A3F52', lw=1, linestyle=':', zorder=2)
        acum2 += row['contribucion']

    # Ejes y formato
    ax.set_xticks(range(n))
    ax.set_xticklabels(bar_labels, color=WHITE, fontsize=8)
    ax.tick_params(axis='y', colors=SUBTEXT, labelsize=8)
    ax.set_ylabel('Contribución al Score', color=SUBTEXT, fontsize=10, labelpad=8)
    ax.grid(axis='y', color='#131F2A', linestyle='--', linewidth=0.5, alpha=0.8)
    ax.set_xlim(-0.5, n - 0.5)

    # Fondo de zona positiva / negativa
    ymin, ymax = ax.get_ylim()
    ax.axhspan(0, ymax, alpha=0.03, color=VERDE, zorder=0)
    ax.axhspan(ymin, 0, alpha=0.03, color=ROJO, zorder=0)
    ax.axhline(0, color='#2A3F52', lw=1, zorder=2)

    # Título con info de la propiedad
    precio  = propiedad['precio_pen']
    area    = propiedad['area_m2']
    dorm    = int(propiedad['num_dorm'])
    banios  = int(propiedad['num_banios'])
    estac   = 'con estac.' if propiedad['flg_estac'] == 1 else 'sin estac.'
    ax.set_title(
        f'Descomposición del Score de Oportunidad\n'
        f'{distrito.title()}  ·  idx {idx}  ·  '
        f'S/.{precio:,.0f}/mes  ·  {area:.0f}m²  ·  {dorm}D/{banios}B  ·  {estac}',
        color=WHITE, fontsize=11, fontweight='bold', pad=12,
    )

    # Leyenda
    ax.legend(
        handles=[
            mpatches.Patch(color=VERDE, label='Suma al score'),
            mpatches.Patch(color=ROJO,  label='Resta al score'),
        ],
        facecolor='#0D1E2C', edgecolor='#1A3040',
        labelcolor=WHITE, fontsize=8.5, loc='upper right',
    )

    plt.tight_layout()
    return fig


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    # 1. Cargar pesos
    if not os.path.exists(PESOS_PATH):
        raise FileNotFoundError(
            f'No se encontró {PESOS_PATH}\n'
            'Corre primero: python train_weights.py'
        )
    with open(PESOS_PATH) as f:
        pesos = json.load(f)
    print(f'Pesos cargados  (R²={pesos["r2"]:.3f}  MAE=S/.{pesos["mae"]:,.0f})')

    # 2. Preparar datos y filtrar distrito
    df_full   = preparar_datos(pd.read_csv(INPUT_PATH), pesos)
    df_dist   = df_full[df_full['distrito'] == DISTRITO].reset_index(drop=True)
    print(f'Distrito        : {DISTRITO}  ({len(df_dist):,} propiedades)')

    if PROPIEDAD_IDX >= len(df_dist):
        raise IndexError(
            f'PROPIEDAD_IDX={PROPIEDAD_IDX} fuera de rango '
            f'(el distrito tiene {len(df_dist)} propiedades, índices 0–{len(df_dist)-1})'
        )

    propiedad = df_dist.iloc[PROPIEDAD_IDX]

    # 3. Calcular contribuciones
    df_contrib = calcular_contribuciones(df_dist, PROPIEDAD_IDX, pesos)
    print(f'\nPropiedad idx {PROPIEDAD_IDX}:')
    print(f'  Precio       : S/. {propiedad["precio_pen"]:,.0f}')
    print(f'  Área         : {propiedad["area_m2"]:.0f} m²')
    print(f'  Score final  : {df_contrib["score_final"].iloc[0]:.4f}')
    print()
    print('  Contribuciones:')
    for _, row in df_contrib.sort_values('contribucion', ascending=False).iterrows():
        signo = '+' if row['contribucion'] >= 0 else ''
        etiq  = ETIQUETAS.get(row['variable'], row['variable'])
        print(f'    {etiq:<20} {signo}{row["contribucion"]:.4f}')

    # 4. Graficar
    fig = build_waterfall(df_contrib, propiedad, DISTRITO, PROPIEDAD_IDX)
    plt.show()
