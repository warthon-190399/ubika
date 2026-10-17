#!/usr/bin/env bash
# Fase 4 · Borra los componentes de la app anterior (tema azul) que ya no se usan.
# Correr una vez desde la raíz del repo, en Git Bash:  bash scripts/fase4_limpiar_app.sh
set -euo pipefail
cd "$(dirname "$0")/../ubika-app"
for f in src/App.module.css \
         src/components/GridView.jsx src/components/GridView.module.css \
         src/components/InsightsPanel.jsx src/components/InsightsPanel.module.css \
         src/components/Sidebar.jsx src/components/Sidebar.module.css \
         src/components/MapView.module.css src/components/Topbar.module.css \
         src/hooks/useProperties.js public/logo.png; do
  if [ -e "$f" ]; then rm "$f"; echo "  borrado $f"; fi
done
echo "Listo. Luego: npm install  (se quitaron dependencias que ya no se usan)"
