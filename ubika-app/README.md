# Ubika — Real Estate Intelligence Platform

Bloomberg inmobiliario para Lima. Stack: React + Deck.gl (WebGL) + MapLibre + Express + Neon.

## Estructura

```
ubika-app/
├── server.js              ← API Express (conecta a Neon)
├── src/
│   ├── App.jsx            ← root component
│   ├── hooks/
│   │   └── useProperties.js  ← fetch desde API + fallback mock
│   ├── lib/
│   │   └── scoring.js     ← lógica de scores
│   └── components/
│       ├── Sidebar.jsx    ← filtros + sliders de preferencias
│       ├── Topbar.jsx     ← KPIs + toggle vista
│       ├── MapView.jsx    ← Deck.gl: scatter + heatmap + hex 3D
│       ├── InsightsPanel.jsx ← rankings + scatter mini
│       └── GridView.jsx   ← lista de tarjetas
```

## Setup

### 1. Instalar dependencias

```bash
cd ubika-app
npm install

# Dependencias del servidor
npm install express cors pg
```

### 2. Configurar variables de entorno

```bash
cp .env.example .env
# Editar .env con tu DATABASE_URL de Neon
```

### 3. Correr en desarrollo

**Terminal 1 — API:**
```bash
node server.js
# → http://localhost:3001
```

**Terminal 2 — Frontend:**
```bash
npm run dev
# → http://localhost:5173
```

### 4. Build para producción

```bash
npm run build
# Output en dist/
```

## Variables de entorno

| Variable         | Descripción                          |
|------------------|--------------------------------------|
| `DATABASE_URL`   | Connection string de Neon PostgreSQL |
| `VITE_API_URL`   | URL del servidor Express (default: http://localhost:3001) |

## Capas del mapa

| Modo      | Descripción                                      |
|-----------|--------------------------------------------------|
| Puntos    | ScatterplotLayer — un punto por propiedad         |
| Heatmap   | HeatmapLayer — densidad de oportunidades          |
| 3D Hex    | HexagonLayer — torres 3D por concentración        |
| Todo      | Las tres capas superpuestas                       |

## Colores (score compuesto)

| Rango      | Color  | Significado              |
|------------|--------|--------------------------|
| ≥ 0.72     | Amarillo `#e8ff47` | Alto      |
| 0.56–0.72  | Teal `#2dd4bf`     | Medio     |
| 0.40–0.56  | Púrpura `#8b7cf8`  | Base      |
| < 0.40     | Rojo `#e63329`     | Bajo      |

## Notas

- Sin `DATABASE_URL` o si el servidor no responde, la app corre en **modo demo** con datos sintéticos.
- El score se recalcula en el cliente cada vez que cambias un slider — no requiere llamada a la API.
- Los filtros de distrito/presupuesto/fuente sí hacen llamadas a la API para reducir el volumen de datos.
