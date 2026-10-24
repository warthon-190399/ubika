# ubika-app

App web de ubika: mapa de Lima con el entorno de cada inmueble y un ranking según tus prioridades.
React + deck.gl (front) y Express (API de solo lectura sobre Neon).

## Marca

`public/brand/` tiene el logo y el isotipo oficiales en SVG (para la app) y PNG con fondo transparente:
`ubika-logo` (400/800/1600 px), `ubika-logo-blanco` (para fondos verdes), `ubika-isotipo` (64/256/512/1024 px)
y `ubika-pin.svg` (inmueble seleccionado en el mapa). Tipografía: Inter, incluida en la app con `@fontsource/inter`.

## Correr en local

```bash
cd ubika-app
npm install
cp .env.example .env      # y pegar la DATABASE_URL de Neon
npm run api               # API en http://localhost:3001   (una terminal)
npm run dev               # app en http://localhost:5173   (otra terminal)
npm test                  # pruebas de la lógica (node:test, sin base)
```

La app pide los datos a `/api/...`; en desarrollo Vite los redirige a la API.

### Mapa base (Stadia Maps)

El fondo del mapa es [Stadia Maps](https://stadiamaps.com/) (Alidade Smooth, y Stamen Toner Labels para los nombres encima de las capas de color), hasta zoom 19.

- **En local** (`localhost`) funciona sin clave.
- **En producción** hay que crear una cuenta gratuita en Stadia Maps y, en su panel, registrar el dominio donde se publique la app (no hace falta tocar el código). Otra opción es crear una API key y ponerla en `ubika-app/.env` como `VITE_STADIA_API_KEY=...` antes de `npm run build`; la clave queda visible en el navegador, así que conviene restringirla al dominio.
- Sin dominio registrado ni clave, Stadia rechaza las imágenes y el mapa queda en blanco (los datos se siguen viendo).

## Qué muestra

| Pestaña | Contenido |
|---|---|
| Entorno | Mapa con capas de seguridad, transporte o servicios para toda la ciudad; ficha del inmueble con puntaje de entorno, precio por m² frente a la mediana del distrito, minutos a pie y conteos a 500 m. |
| Oportunidades | Filtros (distrito, presupuesto, dormitorios) y seis prioridades: precio, espacio, antigüedad, seguridad, servicios y transporte. Las burbujas del mapa y el ranking se ordenan con ese puntaje. |
| Evaluador | Cuánto debería costar un inmueble: ubicación (toque en el mapa, distrito o el inmueble elegido), área, dormitorios, baños, estacionamientos y antigüedad. Da el precio estimado, el rango, la confianza, si el precio pedido está por debajo o por encima, y los 12 avisos que usó (resaltados en el mapa). |
| Evolución | Próximamente: series de precios (necesita varios cortes semanales). |

## Cómo se calculan los puntajes (`src/lib/scoring.js`)

Cada criterio es el percentil del inmueble entre todos los de su operación (alquiler o venta), de 0 a 1:

- **Precio:** precio + mantenimiento (más barato = mejor).
- **Espacio:** 60% área, 20% dormitorios, 10% baños, 10% estacionamientos.
- **Antigüedad:** más nuevo = mejor. Si el aviso no tiene el dato, el criterio no cuenta para ese aviso.
- **Seguridad:** mitad denuncias de robo y violencia a 500 m en 12 meses (ponderadas por distrito), mitad tasa de homicidios del distrito (SINADEF, por 100 mil habitantes). Las denuncias solas premian a los distritos donde se denuncia poco (SJL, Ancón) y castigan a los que tienen mucha gente de paso (San Isidro, Miraflores); los homicidios casi no tienen subregistro. La regla está en `seguridadIx` (`src/lib/scoring.js`).
- **Servicios:** colegios + salud + comisarías + comercio grande a 500 m.
- **Transporte:** distancia a la estación de metro, tren o Metropolitano más cercana.

Puntaje de oportunidad = promedio ponderado con los pesos de los controles.
Calidad de vida (0–10, `src/lib/ciudad.js`) = 25 % seguridad (la de arriba) + 15 % cada uno: transporte, servicios, áreas verdes, comercio de barrio y tranquilidad. Cada componente es la posición frente a todas las celdas de Lima.

## Cómo estima el evaluador (`src/lib/evaluador.js`)

Por comparables, con los avisos de la misma operación que ya carga la app (no llama a la API):

- **Parecido:** 1 km de distancia pesa lo mismo que 25 % de diferencia de área, 0.6 dormitorios, 0.4 baños o estacionamientos, o 15 años de antigüedad (esta solo si los dos la tienen).
- **Estimación:** mediana del precio por m² de los 12 más parecidos, ponderada por 1/(0.25 + diferencia)², × el área. El rango son los percentiles 25 y 75.
- **Confianza:** alta si hay 8+ comparables a ≤ 1.5 km en mediana y su precio por m² varía poco (p75/p25 ≤ 1.35); media hasta 3 km y 1.7; si no, baja.
- **Error típico:** la pestaña estima cada aviso con los demás y muestra la mediana del error. Con los ~100 avisos por operación de octubre 2026: 13.5 % en alquiler y 15 % en venta. Mejora con más avisos (Fase 5).

No usa los modelos de `models/*.pkl` del evaluador anterior (Streamlit, `app/autoevaluator.py`): se entrenaron con otro dataset y necesitan Python.

## API (`server.js`)

| Ruta | Devuelve |
|---|---|
| `GET /api/salud` | estado de la conexión y fecha del último scraping |
| `GET /api/propiedades?operacion=alquiler\|venta` | inmuebles activos con su entorno (`v_app_propiedades`) |
| `GET /api/distritos?operacion=…` | medianas por distrito (`v_resumen_distrito`) |
| `GET /api/crimen-distritos` | por distrito: denuncias por 10 mil habitantes (`v_crimen_distrito`) y homicidios por 100 mil (`v_mortalidad_distrito_reciente`, necesita `sql/10_defunciones.sql` y `python -m ubika.referencias.sinadef`) y edad promedio al morir por causas naturales (`v_longevidad_distrito`, `sql/12_edad_defuncion.sql`) |
| `GET /api/capas/seguridad\|transporte\|servicios` | grilla de la ciudad (`capas_grilla`): `[lat, lon, índice 0–1, valor]` |

## Capa de crimen

«Crimen» pinta el **índice de crimen** (0–10, `indiceCrimen` en `src/lib/scoring.js`): la seguridad al revés, con la misma regla de mitad denuncias por habitante (SIDPOL) y mitad homicidios del distrito (SINADEF). Por barrio, cada celda frente a todas las de Lima; por distrito, cada distrito frente a los demás. El tooltip muestra las dos cifras de origen. No suma otras muertes violentas (accidentes, suicidios, «no se conoce»): no son crimen o no siguen el patrón de los homicidios.

## Capa de longevidad

«Más capas → Edad al morir», en azul: edad promedio al morir por causas naturales (no violentas) del distrito, SINADEF, promedio de 2019, 2022 y 2023. Más oscuro = la gente muere más longeva. No entra en la calidad de vida: también refleja la edad de la población (donde vive más gente mayor sale más alta), así que se lee junto con ese contexto. Los distritos con menos de 100 muertes naturales en esos años se pintan, pero no cuentan para los cortes de color.

## Limitaciones conocidas

- Las **denuncias** miden cuánto denuncia la gente, no cuántos delitos ocurren: por eso la seguridad suma los homicidios.
- Los **homicidios** son por distrito y por distrito de **residencia** de la víctima (SINADEF no trae dónde ocurrió), con datos hasta 2024-05: todas las celdas de un distrito tienen el mismo valor.
- Los minutos a pie son en línea recta a 80 m/min, no por calles.
- No hay datos de parques todavía.
