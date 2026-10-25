# Metodología del score de calidad de vida

**Versión 2** · octubre 2026 · ubika

El score de calidad de vida resume en un número de **0 a 10** qué tan bien está una zona de Lima y Callao para vivir, frente al resto de la ciudad. Se calcula para cada barrio (celda de ~350 m), cada inmueble y cada distrito, y queda **guardado en Neon** para que la app, los modelos y cualquier análisis usen el mismo valor.

| Qué | Dónde |
|---|---|
| Cálculo | `src/ubika/pipeline/calidad.py` (etapa `calidad` del pipeline) |
| Pesos y versión | `config.yaml`, sección `calidad_vida` |
| Tablas | `sql/13_calidad_vida.sql`: `calidad_vida_celda`, `calidad_vida_inmueble`, `calidad_vida_distrito` |
| Pruebas | `tests/test_calidad.py` (Python) y `ubika-app/test/calidad.test.js` (app) |
| Uso en la app | `ubika-app/src/lib/ciudad.js` lee el score guardado; si no existe, lo calcula con la misma fórmula |

---

## 1. Resumen de la fórmula

```
score = 10 × Σ (peso_k × posición_k) / Σ peso_k        (solo los componentes con dato)
```

- **Siete componentes** (k): seguridad, longevidad, transporte, servicios, áreas verdes, comercio de barrio y tranquilidad.
- **Posición** de un componente: qué fracción de las celdas de Lima y Callao está *peor* que la zona (0 = la peor de la ciudad, 1 = la mejor; los empates cuentan a la mitad). Así se pueden sumar cosas que se miden en unidades distintas (denuncias, años, metros, m², dB), y un valor extremo no deforma la escala.
- **Seguridad** combina dos fuentes: `posición_seguridad = 0,5 × posición_denuncias + 0,5 × posición_homicidios`.
- Si a una zona le falta un componente, su peso se reparte entre los demás.

### Pesos (versión 1)

| Componente | Peso | Mide | Mejor si… |
|---|---|---|---|
| Seguridad | **25 %** | ½ denuncias de robo y violencia a 500 m por habitante + ½ homicidios del distrito por habitante | hay menos |
| Longevidad | **10 %** | edad promedio al morir por causas naturales en el distrito | es mayor |
| Transporte | **15 %** | distancia al transporte masivo más cercano: estación de Metro o Metropolitano, o paradero de Corredor Complementario × 1,5 | es menor |
| Servicios | **15 %** | colegios + establecimientos de salud + comisarías + malls a 500 m | hay más |
| Áreas verdes | **15 %** | m² de parque a 500 m por habitante | hay más |
| Comercio de barrio | **10 %** | mercados, supermercados, farmacias, restaurantes, gimnasios y bancos a 500 m | hay más |
| Tranquilidad | **10 %** | ruido de tráfico estimado (dB) | hay menos |

**Por qué estos pesos.** La seguridad es lo que más pesa en la decisión de dónde vivir, y es el componente con más evidencia detrás (dos fuentes independientes). Transporte, servicios y áreas verdes son el día a día. Longevidad, comercio y tranquilidad pesan menos: la longevidad es un dato por distrito (no distingue barrios) y también refleja la edad de la población; el ruido es una estimación, no una medición. Los pesos son una **decisión de diseño**, no un estándar: se cambian en `config.yaml` (ver §7).

---

## 2. Inventario de datos y cuáles entran

| Dato | Fuente | Período | Nivel | ¿Entra? | Motivo |
|---|---|---|---|---|---|
| Denuncias de robo y violencia | SIDPOL, MININTER (`delitos_puntos`, 249,926 con ubicación) | 2025-01 a 2026-07 (últimos 12 meses) | punto → 500 m | ✅ seguridad | Mide delito cerca del inmueble, pero solo lo que se denuncia |
| Homicidios | SINADEF, MINSA (`defunciones_distrito_mes`, 3,230 en Lima+Callao) | promedio 2019, 2022 y 2023 | distrito | ✅ seguridad | Casi sin subregistro: corrige a los distritos que denuncian poco |
| Edad al morir (causas naturales) | SINADEF (`defunciones_edad_distrito`, 390,531 defunciones con edad) | promedio 2019, 2022 y 2023 | distrito | ✅ longevidad | Salud y acceso a atención de la población |
| Parques | OpenStreetMap (7,673) | 2026 | punto → 500 m | ✅ áreas verdes | |
| Comercio diario | OpenStreetMap (11,819 locales) | 2026 | punto → 500 m | ✅ comercio | |
| Colegios | MINEDU (7,653) | | punto → 500 m | ✅ servicios | |
| Establecimientos de salud | IPRESS, MINSA (249) | | punto → 500 m | ✅ servicios | Solo los principales; subestima la oferta |
| Comisarías | MININTER (134) | | punto → 500 m | ✅ servicios | |
| Malls | CSV propio (1,509) | | punto → 500 m | ✅ servicios | |
| Estaciones de metro, tren y Metropolitano | CSV propio (75) | | punto | ✅ transporte | Faltan 4 estaciones de la Línea 1 y la Línea 2 (pendiente) |
| Paraderos de los Corredores Complementarios (Amarillo, Rojo, Azul, Morado) | OpenStreetMap, rutas de la red SIT de la ATU (370 paraderos) | 2026 | punto | ✅ transporte | Desde la versión 2; cuentan a 1,5 veces su distancia |
| Paraderos de bus en general | OpenStreetMap (2,211) | 2026 | punto | ❌ | Lima tiene decenas de miles de paraderos informales y OSM mapeó pocos y de forma desigual: premiaría a los barrios mejor mapeados, no a los mejor servidos |
| Ruido de tráfico | modelo propio con vías de OSM y el aeropuerto (`ruido_fuentes`) | 2026 | celda | ✅ tranquilidad | Estimado, no medido |
| Población por distrito | INEI, Censos 2017 (`distritos.poblacion`) | 2017 | distrito | 🔧 | Para las tasas por habitante |
| Muertes de tránsito | SINADEF | 2017–2024 | distrito | ❌ | Pocos casos por distrito; podría entrar como «seguridad vial» en una versión futura |
| Suicidios, otros accidentes, violentas «no se conoce» | SINADEF | | distrito | ❌ | No son crimen; las «no se conoce» no siguen el patrón de los homicidios (correlación 0,07) y suben a los distritos de playa por ahogamientos |
| Domicilios de internos INPE | INPE 2024 | | punto | ❌ | Estigmatiza barrios; dice dónde vivía alguien, no dónde ocurrió un delito |
| Zona APEIM / NSE | APEIM | | distrito | ❌ | Mide ingreso; sesgaría el score hacia los distritos ricos |
| Precio de los avisos | scraping de adondevivir | semanal | inmueble | ❌ | Es lo que el score ayuda a explicar, no un componente |

---

## 3. Cálculo paso a paso

### 3.1 La grilla de la ciudad
La etapa `capas` del pipeline cubre la zona urbana de Lima y Callao con una grilla hexagonal de ~350 m (`capas_grilla`, 10,997 celdas). Solo entran celdas con al menos 5 puntos de interés o denuncias a menos de 700 m, para que cerros y zonas vacías no salgan «muy seguros» solo porque nadie denuncia ahí. Para cada celda guarda, en un radio de 500 m: denuncias ponderadas, metros a la estación más cercana, servicios, m² de parque, comercio y dB estimados.

### 3.2 A qué distrito pertenece cada celda
Cada celda se ubica en el polígono distrital (IGN) donde cae su centro, con los mismos límites que dibuja la app (`ubika-app/public/geo/distritos-lima.geojson`). 335 celdas caen fuera de todo distrito (mar, bordes): no tienen población ni datos distritales y se calculan con 4 de los 7 componentes.

### 3.3 Valores «por habitante»
No hay población por manzana, así que se estima:
1. La población del distrito (censo 2017) se reparte por igual entre sus celdas: `pob_celda = población_distrito / n_celdas_distrito`.
2. Un círculo de 500 m contiene unas `CELDAS_500M = π·0,5² / ((√3/2)·0,35²) ≈ 7,4` celdas.
3. `denuncias_10k = 10 000 × denuncias_a_500m / (pob_celda × 7,4)` y `verde_m2_hab = m²_parque_a_500m / (pob_celda × 7,4)`.

Homicidios (por 100 mil) y edad al morir son del distrito: todas sus celdas tienen el mismo valor.

### 3.4 Posición frente a toda la ciudad
Para cada componente, con la distribución de las 10,997 celdas como referencia:

```
posición = (celdas peores + celdas iguales / 2) / celdas con dato
```

«Peores» depende del sentido: para denuncias, homicidios, distancia a transporte y ruido, peor = mayor; para el resto, peor = menor.

### 3.4 bis Transporte (desde la versión 2)
Un paradero de Corredor Complementario es más lento y menos frecuente que una estación de Metro o Metropolitano, así que cuenta como una estación a `factor_corredor` (1,5) veces su distancia:

```
distancia_transporte = min(metros a la estación más cercana, 1,5 × metros al paradero de corredor más cercano)
```

Un paradero a 400 m equivale a una estación a 600 m. La ficha de la app muestra la distancia **real** al acceso que cuenta (por ejemplo, «3 min a pie · paradero de corredor») y la posición se calcula con la equivalente. Los paraderos vienen de OpenStreetMap (rutas de la red SIT: 101 Amarillo; 201, 204 y 206 Rojo; 301–306 Azul; 404, 405, 409, 412 y SE-02 Morado); los nodos de un mismo paradero (andenes de cada sentido) se juntan en un punto si están a menos de 60 m.

### 3.5 Seguridad
`posición_seguridad = 0,5 × posición_denuncias + 0,5 × posición_homicidios` (`peso_homicidios` en `config.yaml`). Si falta una de las dos, cuenta solo la otra.

**Por qué no solo denuncias.** Las denuncias miden cuánto denuncia la gente, no cuántos delitos ocurren. Comparadas con los homicidios del Ministerio Público (2012), la correlación de rangos por distrito es **−0,16**: San Juan de Lurigancho (puesto 34 de 49 en denuncias) o Ancón (48) salían «seguros», y San Isidro (4) o Miraflores (3), donde denuncia mucha gente de paso, «inseguros». Los homicidios casi no tienen subregistro (siempre hay un certificado de defunción).

### 3.6 Score
`score = 10 × Σ peso × posición / Σ pesos con dato`. Un inmueble o celda sin un componente no se castiga: su peso se reparte.

### 3.7 Inmuebles
Cada inmueble usa:
- sus **propios conteos** de la tabla `entorno` para denuncias a 500 m, distancia a transporte y servicios;
- la **celda más cercana** (a menos de 400 m) para áreas verdes, comercio y ruido;
- **su distrito** para homicidios y longevidad.

Sus posiciones se miden frente a las mismas celdas de la ciudad, así un inmueble y un barrio son comparables. `pos_score` dice qué fracción de las celdas de Lima tiene peor score.

### 3.8 Distritos
El score del distrito es la **mediana** de sus celdas (con `score_p25` y `score_p75` para ver la dispersión dentro del distrito) y `puesto` es su lugar entre los 50 (1 = mejor).

---

## 4. Tablas en Neon

Las tres tablas tienen, para cada componente, el **valor real** (`val_*`) y la **posición** (`pos_*`), así cualquier score se puede auditar.

| Columna | Qué es |
|---|---|
| `val_denuncias_10k`, `pos_denuncias` | denuncias de robo y violencia a 500 m en 12 meses por 10 mil habitantes |
| `val_homicidios_100k`, `pos_homicidios` | homicidios del distrito por 100 mil habitantes |
| `pos_seguridad` | combinación de las dos anteriores |
| `val_edad_al_morir`, `pos_longevidad` | edad promedio al morir por causas naturales en el distrito |
| `val_transporte_m`, `pos_transporte` | metros equivalentes al transporte masivo (estación, o paradero de corredor × 1,5) |
| `val_corredor_m` | metros reales al paradero de corredor más cercano (desde la versión 2) |
| `val_servicios`, `pos_servicios` | colegios + salud + comisarías + malls a 500 m |
| `val_verde_m2_hab`, `pos_verde` | m² de parque a 500 m por habitante |
| `val_barrio`, `pos_barrio` | comercio de todos los días a 500 m |
| `val_ruido_db`, `pos_ruido` | dB de tráfico estimados |
| `score` | 0–10 |
| `n_componentes` | cuántos de los 7 componentes tuvieron dato |
| `version` | `calidad_vida.version` de `config.yaml` con la que se calculó |

Ejemplos:

```sql
-- Ranking de distritos
SELECT puesto, distrito, ROUND(score::numeric, 1) AS score FROM calidad_vida_distrito ORDER BY puesto;

-- Score de cada aviso con su precio
SELECT p.distrito, p.precio_pen, p.area_m2, q.score, q.pos_seguridad, q.pos_transporte
FROM propiedades p JOIN calidad_vida_inmueble q USING (prop_id)
ORDER BY q.score DESC LIMIT 20;
```

---

## 5. Cómo se recalcula

Requiere que antes estén cargadas las fuentes:

```bash
python -m ubika.referencias.sidpol --desde 2026-09-01   # denuncias (mensual)
python -m ubika.referencias.osm                         # parques, comercio, vías y paraderos de corredores (cada 3–6 meses)
python -m ubika.referencias.sinadef                     # homicidios y edad al morir (cuando MINSA publique)
python -m ubika.pipeline                                # limpieza → geocoding → entorno → capas → calidad
```

Solo el score (por ejemplo, después de cambiar pesos):

```bash
python -m ubika.pipeline --etapas calidad
```

Cada corrida reemplaza las tres tablas completas y queda registrada en `corridas` (etapa `calidad`). Tarda unos 20 segundos.

---

## 6. Resultados de la versión 2 (25 de octubre de 2026)

10,997 celdas (score mediano 5,0; mínimo 1,0; máximo 7,8), 1,122 inmuebles y 50 distritos.

| Puesto | Distrito | Score | Rango p25–p75 | Celdas |
|---|---|---|---|---|
| 1 | Magdalena del Mar | 7.4 | 7.1–7.5 | 30 |
| 2 | Pueblo Libre | 7.3 | 7.2–7.4 | 42 |
| 3 | San Borja | 7.2 | 6.9–7.4 | 95 |
| 4 | San Isidro | 7.2 | 6.9–7.3 | 93 |
| 5 | Miraflores | 7.1 | 6.9–7.3 | 87 |
| 6 | Jesús María | 7.1 | 7.0–7.3 | 40 |
| 7 | San Miguel | 7.0 | 6.7–7.2 | 92 |
| 8 | Lince | 6.8 | 6.6–7.4 | 25 |
| 9 | Santiago de Surco | 6.8 | 6.3–7.1 | 332 |
| 10 | Surquillo | 6.7 | 6.4–7.0 | 42 |
| … | | | | |
| 30 | San Juan de Lurigancho | 5.1 | 4.4–5.8 | 825 |
| 35 | Cercado de Lima | 4.7 | 4.3–5.1 | 204 |
| … | | | | |
| 46 | Pachacámac | 3.6 | 3.1–4.1 | 388 |
| 47 | Santa Rosa | 3.5 | 3.1–3.9 | 137 |
| 48 | Pucusana | 3.4 | 3.0–4.0 | 71 |
| 49 | Ancón | 3.3 | 3.0–3.8 | 218 |
| 50 | Ventanilla | 3.2 | 2.9–3.4 | 469 |

**Cambio frente a la versión 1.** Suben los distritos que tienen corredores: Magdalena del Mar (6.º → 1.º), San Miguel (11.º → 7.º), La Molina (22.º → 13.º), Pueblo Libre (5.º → 2.º). Algunos sin corredores bajan algo (Comas 19.º → 22.º, Chorrillos 23.º → 24.º) sin haber empeorado: como el score es relativo, el resto de la ciudad mejoró. 521 de los 1,122 inmuebles tienen un paradero de corredor a menos de 500 m. La tabla completa está en `calidad_vida_distrito`.

---

## 7. Cómo cambiar la metodología

1. Edita `config.yaml` → `calidad_vida.pesos` (deben sumar 1) o `peso_homicidios`.
2. Sube `calidad_vida.version`.
3. Actualiza los pesos de `CAPAS` en `ubika-app/src/lib/ciudad.js` (y `PESO_HOMICIDIOS` en `scoring.js` si cambió): la app los usa para las barras de cada componente. `tests/test_calidad.py` falla si no coinciden.
4. Corre `python -m ubika.pipeline --etapas calidad` y `pytest` (si cambias `factor_corredor`, también `FACTOR_CORREDOR` en `scoring.js`).
5. Anota el cambio en el historial de abajo, con el motivo.

Para agregar un componente nuevo: su valor por celda en `celdas()` y por inmueble en `inmuebles()` (`calidad.py`), su sentido en `VALORES`, su peso en `config.yaml`, columnas `val_*`/`pos_*` en `sql/13_calidad_vida.sql` y la entrada en `CAPAS` de la app.

---

## 8. Limitaciones conocidas

- **Relativo, no absoluto.** Un 7 significa «mejor que la mayoría de Lima», no «bueno» en un estándar externo. Si toda la ciudad mejora, los scores no suben.
- **Población de 2017** repartida por igual dentro de cada distrito: las tasas por habitante de un barrio son estimaciones. Distritos comerciales (Cercado, San Isidro, Miraflores, La Victoria) reciben más gente de la que vive en ellos.
- **Homicidios y longevidad son por distrito**, no por barrio, y por distrito donde **vivía** la persona (SINADEF no trae dónde ocurrió). Los datos de SINADEF llegan solo hasta mayo de 2024; en distritos chicos hay pocos casos.
- **La longevidad también refleja la edad de la población**: donde vive más gente mayor, la edad al morir sale más alta aunque la salud sea igual. Una versión futura podría ajustarla por estructura de edad (censo).
- **Denuncias** dependen de cuánto denuncia la gente; los homicidios lo compensan solo en parte.
- **Servicios** cuenta cantidades, no calidad, y la base de salud (IPRESS) solo tiene los establecimientos principales.
- **Transporte** considera Metro, Metropolitano y los Corredores Complementarios, pero no buses comunes ni frecuencias. El factor 1,5 del corredor es una decisión de diseño, no una medición. Los paraderos dependen de qué tan completo está OpenStreetMap; faltan 4 estaciones de la Línea 1 y la Línea 2.
- **Ruido** es un modelo (cercanía a vías grandes y al aeropuerto), no una medición.
- **335 celdas** fuera de todo distrito se calculan con 4 componentes; su score no es del todo comparable.

---

## 9. Historial

| Versión | Fecha | Cambio |
|---|---|---|
| 2 | 2026-10-25 | Transporte suma los paraderos de los Corredores Complementarios (OSM, red SIT) con penalidad × 1,5 (`factor_corredor`). Nuevas columnas `val_corredor_m`, `entorno.dist_corredor_m`, `entorno.n_corredores` y capa `corredor` en `capas_grilla` (`sql/14_corredores.sql`). |
| 1 | 2026-10-24 | Primera versión guardada en Neon. 7 componentes; seguridad = ½ denuncias + ½ homicidios (SINADEF); se agrega longevidad (10 %); comercio y tranquilidad bajan de 15 % a 10 %. Antes, el score se calculaba solo en la app con 6 componentes (seguridad 25 %, el resto 15 %) y seguridad solo con denuncias. |
