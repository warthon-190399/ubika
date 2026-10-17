"""
Pipeline descriptivo de ubika, todo en Neon:

    raw_listings + raw_detalles
        │ limpieza   textos → números, descarta lo implausible, une repetidos
        ▼
    propiedades + avisos
        │ geocoding  coordenadas de Google solo para los que el portal no ubicó
        ▼
    propiedades (con lat/lon)
        │ entorno    colegios, salud, comisarías, transporte, malls, INPE y delitos cercanos
        ▼
    entorno  →  v_app_propiedades (lo que lee la API)

    capas      grilla de toda la ciudad (seguridad, transporte, servicios) → capas_grilla

Cada etapa se puede volver a correr: actualiza sin duplicar.

    python -m ubika.pipeline                       # todas las etapas
    python -m ubika.pipeline --etapas entorno      # solo una
    python -m ubika.pipeline --sin-google          # salta el geocoding
"""
from __future__ import annotations

import argparse
import logging

from ubika.db import corrida, read_df
from ubika.pipeline import capas, entorno, geocoding, limpieza

log = logging.getLogger(__name__)

ETAPAS = {"limpieza": limpieza.correr, "geocoding": geocoding.correr, "entorno": entorno.correr,
          "capas": capas.correr}


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description="Pipeline descriptivo de ubika.")
    p.add_argument("--etapas", default=",".join(ETAPAS), help="lista separada por comas: " + ", ".join(ETAPAS))
    p.add_argument("--sin-google", action="store_true", help="no consulta Google (salta geocoding)")
    args = p.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-7s %(message)s", datefmt="%H:%M:%S")

    etapas = [e.strip() for e in args.etapas.split(",") if e.strip()]
    if args.sin_google:
        etapas = [e for e in etapas if e != "geocoding"]
    desconocidas = set(etapas) - set(ETAPAS)
    if desconocidas:
        raise SystemExit(f"Etapas desconocidas: {', '.join(desconocidas)}")

    for e in ETAPAS:                      # siempre en orden
        if e in etapas:
            log.info("▶ %s", e)
            with corrida(e) as c:
                ETAPAS[e](c)

    r = read_df("""SELECT operacion, COUNT(*) AS inmuebles,
                          COUNT(*) FILTER (WHERE latitud IS NOT NULL) AS en_mapa
                   FROM propiedades WHERE activo GROUP BY 1 ORDER BY 1""")
    log.info("Resultado (inmuebles activos):\n%s", r.to_string(index=False))


if __name__ == "__main__":
    main()
