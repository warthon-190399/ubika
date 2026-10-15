#!/usr/bin/env bash
# Fase 0 · Mueve el código antiguo a legacy/ para que solo quede a la vista lo nuevo.
# Correr UNA vez desde la raíz del repo, en Git Bash:
#     bash scripts/fase0_reorganizar.sh
# No borra nada: todo queda en legacy/ como referencia.
set -euo pipefail
cd "$(dirname "$0")/.."

mover() {  # mover <origen> <destino>
  if [ -e "$1" ]; then
    mkdir -p "$(dirname "$2")"
    mv "$1" "$2"
    echo "  $1 → $2"
  fi
}

echo "Moviendo código antiguo a legacy/ ..."
mover app                 legacy/app_streamlit      # guía para el mapa, sliders y score de oportunidad
mover src/data            legacy/src/data           # scrapers y procesamiento antiguos
mover src/features        legacy/src/features
mover src/modeling        legacy/src/modeling       # referencia para la Fase 6
mover src/service         legacy/src/service
mover pipeline.py         legacy/pipeline_old.py
mover format.sql          legacy/format_old.sql
mover test_neon.py        legacy/test_neon.py
mover requirements_old.txt legacy/requirements_old.txt
mover urbania_alquiler.csv legacy/urbania_alquiler.csv

find legacy -name "__pycache__" -type d -prune -exec rm -rf {} + 2>/dev/null || true

cat > legacy/README.md <<'MD'
# legacy/

Código anterior a la reactivación (octubre 2026). No se ejecuta ni se mantiene.
Se guarda como referencia:

- `app_streamlit/`: dashboard con mapa de puntos/hexágonos/calor, sliders de prioridades y score de oportunidad. Guía para la Fase 4.
- `src/modeling/`: comparación de modelos. Referencia para la Fase 6.
- `src/data/scraping/`: selectores de los portales. Referencia para la Fase 2.
MD

echo
echo "Listo. Revisa con: git status"
echo "Siguiente paso: python -m venv .venv && source .venv/Scripts/activate && pip install -r requirements.txt && pip install -e ."
