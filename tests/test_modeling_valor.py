"""Pruebas del modelo de valor con datos sintéticos (sin red ni base)."""
import numpy as np
import pandas as pd
import pytest

from modeling import valor

MIRA, COMAS = (-12.1211, -77.0297), (-11.94, -77.05)


def _datos(n_por_zona: int = 40, ruido: float = 0.05, semilla: int = 1) -> pd.DataFrame:
    """Dos barrios: Miraflores (S/ 40/m²) y Comas (S/ 15/m²), con algo de ruido y de nulos como en Neon."""
    rng = np.random.default_rng(semilla)
    filas = []
    for (lat, lon), m2, distrito, zona, nse in ((MIRA, 40, "miraflores", 7, "A"), (COMAS, 15, "comas", 1, "D")):
        for i in range(n_por_zona):
            area = float(rng.uniform(50, 150))
            filas.append({
                "prop_id": f"{distrito}-{i}", "operacion": "alquiler", "distrito": distrito,
                "latitud": lat + rng.normal(0, 0.004), "longitud": lon + rng.normal(0, 0.004),
                "area_m2": area, "precio_pen": area * m2 * float(np.exp(rng.normal(0, ruido))),
                "num_dorm": int(rng.integers(1, 4)), "num_banios": int(rng.integers(1, 3)), "num_estac": int(rng.integers(0, 2)),
                "antiguedad_anios": float(rng.integers(0, 30)) if i % 10 == 0 else None,     # casi siempre nulo
                "mantenimiento_pen": area * 3 if i % 3 else None,
                "zona_apeim": zona, "nse_aprox": nse, "primera_vez": "2026-10-15",
                **{c: int(rng.integers(0, 10)) for c in valor.CONTEOS},
                **{c: int(rng.integers(50, 2000)) for c in valor.DISTANCIAS},
            })
    return pd.DataFrame(filas)


def test_variables():
    df = _datos()
    X = valor.variables(df)
    assert list(X.columns) == valor.VARIABLES
    assert len(X) == len(df)
    assert X["log_area"].notna().all()
    assert X["antiguedad_anios"].isna().mean() > 0.8          # los nulos se conservan
    assert set(X["nse"].unique()) == {5.0, 2.0}
    assert np.allclose(np.exp(valor.objetivo(df)), df["precio_pen"] / df["area_m2"])


def test_comparables_usa_el_barrio():
    df = _datos(ruido=0)
    entreno, prueba = df.drop(index=[0, 45]), df.loc[[0, 45]]      # uno de Miraflores y uno de Comas
    m2 = np.exp(valor.predecir_comparables(entreno, prueba))
    assert m2 == pytest.approx([40, 15])


def test_mediana_distrito_y_respaldo():
    df = _datos(ruido=0)
    prueba = df.loc[[0, 45]].copy()
    prueba.loc[45, "distrito"] = "ate"                              # distrito sin datos: usa la mediana de la ciudad
    m2 = np.exp(valor.predecir_mediana_distrito(df, prueba))
    assert m2[0] == pytest.approx(40)
    assert m2[1] == pytest.approx(np.median(df["precio_pen"] / df["area_m2"]))


def test_metricas():
    m = valor.metricas(np.array([100.0, 200.0, 300.0]), np.array([110.0, 200.0, 240.0]))
    assert m["mape"] == pytest.approx(100 * (0.1 + 0 + 0.2) / 3, abs=0.01)
    assert m["mdape"] == pytest.approx(10.0)
    assert m["dentro_20"] == pytest.approx(100.0)
    assert m["rmse"] == pytest.approx(np.sqrt((100 + 0 + 3600) / 3), abs=1)
    assert m["r2"] < 1


def test_evaluar_compara_todos_los_metodos():
    res = valor.evaluar(_datos(), partes=4, repeticiones=1)
    assert set(res) == {"mediana_distrito", "comparables", "ridge", "random_forest", "hist_gb"}
    for r in res.values():
        assert r["mape"] < 15                                       # con dos barrios bien separados todos aciertan
        assert r["r2"] > 0.8
    assert valor.ganador(res) in res
    assert valor.ganador(res, set(valor.modelos())) in valor.modelos()
