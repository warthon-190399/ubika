import { useEffect, useMemo, useRef, useState } from "react";
import DeckGL from "@deck.gl/react";
import { WebMercatorViewport } from "@deck.gl/core";
import { BitmapLayer, ColumnLayer, GeoJsonLayer, IconLayer, LineLayer, ScatterplotLayer, TextLayer } from "@deck.gl/layers";
import { TileLayer } from "@deck.gl/geo-layers";
import { SEQ, SEQ_RGB, fmt, hexToRgb, soles, tramo } from "../lib/scoring";
import { nombre } from "../lib/distritos";
import Indicadores from "./Indicadores";
import { PRINCIPALES, VARIABLES, VARIABLES_KEYS, disponible, tramos, valoresCeldas, valoresDistrito } from "../lib/variables";
import { CATEGORIAS, CATEGORIAS_KEYS, aPie, grupoDe, icono, titulo } from "../lib/poi";

// Esri Light Gray Canvas solo tiene imágenes hasta el zoom 16: más cerca se verían pixeladas
const ZOOM_MIN = 9, ZOOM_MAX = 16;
const VISTA_INICIAL = { longitude: -77.03, latitude: -12.09, zoom: 11.3, pitch: 0, bearing: 0, minZoom: ZOOM_MIN, maxZoom: ZOOM_MAX };
const PIN = "/brand/ubika-pin.svg";

/* ── Mapa base: Esri gris claro (sin clave). Calles abajo, nombres encima de los datos ── */
const ESRI = "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas";
const BASE = `${ESRI}/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}`;
const NOMBRES = `${ESRI}/World_Light_Gray_Reference/MapServer/tile/{z}/{y}/{x}`;
const capaTiles = (id, url) => new TileLayer({
  id, data: url, minZoom: 0, maxZoom: ZOOM_MAX, tileSize: 256,
  renderSubLayers: props => {
    const [[w, s], [e, n]] = props.tile.boundingBox;
    return new BitmapLayer(props, { data: null, image: props.data, bounds: [w, s, e, n] });
  },
});

/* ── Qué pintar y a qué escala: mismo formato para todas las variables ── */
export const ESCALAS = [
  { k: "barrio", l: "Barrio", ayuda: "Hexágonos de 350 m" },
  { k: "distrito", l: "Distrito", ayuda: "Los 50 distritos de Lima y Callao" },
];
const HEX_RADIO_M = 196;     // la grilla va cada 350 m (350/√3 ≈ 202 m de radio)
const ALFA = 175;            // la misma opacidad en las dos escalas
const MEZCLA = { blend: true, blendColorSrcFactor: "src-alpha", blendColorDstFactor: "one-minus-src-alpha",
  blendAlphaSrcFactor: "one", blendAlphaDstFactor: "one-minus-src-alpha" };
const ZOOM_PRECIOS = 13.2;   // desde aquí cada burbuja muestra su precio

const porMes = p => (p.operacion === "alquiler" ? " /mes" : "");
const SIN_CAJA = { background: "transparent", border: "none", padding: 0 };
const cuantil = (v, f) => v[Math.min(v.length - 1, Math.max(0, Math.floor(f * (v.length - 1))))];
const corto = n => (n == null ? "" : n >= 1e6 ? `S/ ${(n / 1e6).toFixed(n < 1e7 ? 2 : 1)}M` : n >= 1e3 ? `S/ ${(n / 1e3).toFixed(n < 1e4 ? 1 : 0)}k` : `S/ ${Math.round(n)}`);

/** Radio de la burbuja (px): área proporcional al precio (tope p95) y crece al acercarse. */
function escalaPrecio(props, zoom) {
  const v = props.map(p => p.precio_pen).filter(Boolean).sort((a, b) => a - b);
  const tope = cuantil(v, 0.95) || 1;
  const k = Math.min(2.2, Math.max(0.8, 1 + (zoom - 11.3) * 0.3));
  const r = precio => k * (3.5 + 10.5 * Math.sqrt(Math.min(precio ?? 0, tope) / tope));
  return { r, muestras: v.length ? [cuantil(v, 0.1), cuantil(v, 0.5), tope] : [] };
}

export default function MapView({ props, grillas, ciudad, capa, onCapa, escala, onEscala, distritos, crimenDist, limites,
  colorDe, colorTitulo, selected, ixSelected, ficha, onCerrarFicha, onVerFicha, onSelect, foco,
  enComparacion, onComparar, lleno, nComparar, onAbrirComparador, cerca, poiFiltro, onPoiFiltro,
  punto, onPunto, resaltar }) {
  const [viewState, setViewState] = useState(VISTA_INICIAL);
  const [hover, setHover] = useState(null);
  const [poiSel, setPoiSel] = useState(null);         // lugar cercano tocado en el mapa
  const [menu, setMenu] = useState(false);            // menú «Más capas»
  const [tam, setTam] = useState({ width: 800, height: 600 });
  const caja = useRef(null);

  useEffect(() => {
    const ro = new ResizeObserver(([e]) => setTam({ width: e.contentRect.width, height: e.contentRect.height }));
    if (caja.current) ro.observe(caja.current);
    return () => ro.disconnect();
  }, []);
  useEffect(() => setPoiSel(null), [selected?.prop_id]);

  // Al elegir: acercar hasta que el círculo de 500 m se lea y correr el mapa para que la ficha quepa al costado
  useEffect(() => {
    if (selected && foco) setViewState(vs => {
      const zoom = Math.max(vs.zoom, 14.6);
      const correr = (tam.width < 640 ? 0 : 160) * 360 / (512 * 2 ** zoom);
      return { ...vs, longitude: selected.longitud + correr, latitude: selected.latitud, zoom, transitionDuration: 500 };
    });
  }, [selected?.prop_id, foco]);

  const zoomPaso = Math.round(viewState.zoom * 2) / 2;
  const escalaB = useMemo(() => escalaPrecio(props, zoomPaso), [props, zoomPaso]);
  const V = capa ? VARIABLES[capa] : null;
  const hay = useMemo(() => Object.fromEntries(VARIABLES_KEYS.map(k => [k, disponible(k, { ciudad })])), [ciudad]);
  const otras = VARIABLES_KEYS.filter(k => !PRINCIPALES.includes(k) && hay[k]);
  const elegirCapa = k => { onCapa(k); setMenu(false); };

  // Valores de la variable elegida: por celda (barrio) y por distrito; tramos de color sobre lo que se ve
  const celdas = useMemo(() => (capa ? valoresCeldas(capa, { grillas, ciudad, props }) : null), [capa, grillas, ciudad, props]);
  const porDistrito = useMemo(() => (capa ? valoresDistrito(capa, { celdas, ciudad, crimenDist, distritos }) : new Map()),
    [capa, celdas, ciudad, crimenDist, distritos]);
  const escalaColor = useMemo(() => {
    if (!V) return null;
    const vals = escala === "barrio" ? (celdas || []) : [...porDistrito.values()].filter(x => !x.pequeno).map(x => x.v);
    return tramos(vals, V.invertido);
  }, [V, escala, celdas, porDistrito]);
  const colorDeTramo = t => (t < 0 ? null : [...hexToRgb(V.paleta[t]), ALFA]);
  const celdasConDato = useMemo(() => {
    const base = grillas.seguridad?.celdas;
    if (!base || !celdas) return [];
    return base.map((c, i) => ({ lat: c[0], lon: c[1], v: celdas[i], d: ciudad?.terr?.dist[i], i })).filter(c => c.v != null);
  }, [grillas.seguridad, celdas, ciudad]);

  const capasCiudad = () => {
    if (!V || !escalaColor) return [];
    const bordes = limites && new GeoJsonLayer({
      id: "limites", data: limites, stroked: true, filled: escala === "distrito", pickable: escala === "distrito", parameters: MEZCLA,
      getFillColor: f => colorDeTramo(escalaColor.tramo(porDistrito.get(f.properties.distrito)?.v)) || [190, 195, 192, 50],
      getLineColor: escala === "distrito" ? [255, 255, 255, 235] : [8, 51, 47, 90],
      lineWidthUnits: "pixels", getLineWidth: escala === "distrito" ? 1.4 : 1,
      updateTriggers: { getFillColor: [capa, escala, porDistrito, escalaColor], getLineColor: [escala], getLineWidth: [escala] },
    });
    if (escala === "distrito") return [bordes];
    return [
      new ColumnLayer({
        id: `hex-${capa}`, data: celdasConDato, getPosition: c => [c.lon, c.lat], pickable: true,
        diskResolution: 6, radius: HEX_RADIO_M, angle: 90, extruded: false, parameters: MEZCLA,
        getFillColor: c => colorDeTramo(escalaColor.tramo(c.v)) || [0, 0, 0, 0],
        updateTriggers: { getFillColor: [capa, escalaColor] },
      }),
      bordes,
    ];
  };

  const poisVisibles = useMemo(() => !cerca ? [] : CATEGORIAS_KEYS.filter(k => poiFiltro[k]).flatMap(k => cerca[k]), [cerca, poiFiltro]);
  const estacionLejos = cerca && poiFiltro.transporte ? cerca.transporte.find(x => x.mas_cercana) : null;
  const conCapa = !!V;
  const conPrecio = !conCapa && viewState.zoom >= ZOOM_PRECIOS;

  const layers = [
    capaTiles("base", BASE),
    ...capasCiudad(),
    capaTiles("nombres", NOMBRES),     // nombres de calles y distritos encima de los colores
    // Radio de 500 m del inmueble elegido: la zona que miden sus indicadores
    selected && new ScatterplotLayer({
      id: "radio", data: [selected], getPosition: p => [p.longitud, p.latitud],
      getRadius: 500, radiusUnits: "meters", stroked: true, filled: true, parameters: MEZCLA,
      getFillColor: [254, 183, 34, conCapa ? 0 : 30], getLineColor: [8, 51, 47, 220], lineWidthUnits: "pixels", getLineWidth: 1.5,
      updateTriggers: { getFillColor: [conCapa] },
    }),
    // Estación más cercana cuando queda fuera del círculo: una línea hasta ella
    selected && estacionLejos && new LineLayer({
      id: "a-estacion", data: [estacionLejos], parameters: MEZCLA,
      getSourcePosition: () => [selected.longitud, selected.latitud], getTargetPosition: e => [e.longitud, e.latitud],
      getColor: [...hexToRgb(CATEGORIAS.transporte.color), 170], getWidth: 1.5, widthUnits: "pixels",
    }),
    new ScatterplotLayer({
      id: "inmuebles", data: props, getPosition: p => [p.longitud, p.latitud], parameters: MEZCLA,
      radiusUnits: "pixels", stroked: true, lineWidthUnits: "pixels", pickable: true,
      getRadius: p => {
        const base = conCapa ? 3.5 : escalaB.r(p.precio_pen);
        return p.prop_id === hover ? base + 2 : base;
      },
      getFillColor: p => conCapa ? [255, 255, 255, 250] : [...SEQ_RGB[tramo(colorDe(p) ?? 0)], 230],
      getLineColor: conCapa ? [8, 51, 47, 255] : [255, 255, 255, 240],
      getLineWidth: conCapa ? 1.5 : 1.25,
      onHover: ({ object }) => setHover(object?.prop_id ?? null),
      onClick: ({ object }) => object && onSelect(object),
      updateTriggers: { getRadius: [hover, conCapa, escalaB], getFillColor: [conCapa, colorDe] },
    }),
    // Precio sobre cada burbuja al acercarse
    conPrecio && new TextLayer({
      id: "precios", data: props.filter(p => p.prop_id !== selected?.prop_id), parameters: MEZCLA,
      getPosition: p => [p.longitud, p.latitud], getText: p => corto(p.precio_pen),
      getPixelOffset: p => [0, -(escalaB.r(p.precio_pen) + 11)], getSize: 11, getColor: [8, 51, 47, 255],
      fontFamily: "Inter, system-ui, sans-serif", fontWeight: 600, characterSet: "auto",
      background: true, getBackgroundColor: [255, 255, 255, 235], backgroundPadding: [5, 2], getBorderColor: [217, 222, 220, 255], getBorderWidth: 1,
      updateTriggers: { getPixelOffset: [escalaB] },
    }),
    // Lo que hay alrededor del inmueble elegido: un emoji por lugar, según el filtro
    selected && poisVisibles.length > 0 && new IconLayer({
      id: "pois", data: poisVisibles, getPosition: d => [d.longitud, d.latitud], parameters: MEZCLA, pickable: true,
      getIcon: d => icono(grupoDe(d.categoria)), getSize: d => (d === poiSel ? 34 : 26), sizeUnits: "pixels",
      onClick: ({ object }) => object && setPoiSel(object),
      updateTriggers: { getSize: [poiSel] },
    }),
    // Evaluador: los avisos que usa como comparables y el punto que se evalúa
    resaltar?.length > 0 && new ScatterplotLayer({
      id: "comparables", data: resaltar, getPosition: p => [p.longitud, p.latitud], parameters: MEZCLA,
      radiusUnits: "pixels", getRadius: 11, stroked: true, filled: false,
      getLineColor: [254, 183, 34, 255], lineWidthUnits: "pixels", getLineWidth: 2.5,
    }),
    punto && new IconLayer({
      id: "punto", data: [punto], getPosition: d => [d.lon, d.lat], parameters: MEZCLA,
      getIcon: () => ({ url: PIN, width: 96, height: 96, anchorY: 48 }), getSize: 44, sizeUnits: "pixels",
    }),
    selected && new IconLayer({
      id: "activo", data: [selected], getPosition: p => [p.longitud, p.latitud], parameters: MEZCLA,
      getIcon: () => ({ url: PIN, width: 96, height: 96, anchorY: 48 }), getSize: 40, sizeUnits: "pixels",
    }),
  ].filter(Boolean);

  // Ficha flotante anclada al inmueble elegido (en pantallas angostas va abajo, a todo lo ancho)
  const angosto = tam.width < 640;
  const vp = new WebMercatorViewport({ ...viewState, ...tam });
  let pos = null;
  if (ficha && selected && !angosto) {
    const [x, y] = vp.project([selected.longitud, selected.latitud]);
    const W = 300, H = cerca ? 262 : 210;
    // Radio del círculo de 500 m en píxeles: la ficha va a su lado para no tapar lo que hay alrededor
    const R = 500 / (40_075_016 * Math.cos(selected.latitud * Math.PI / 180) / (512 * 2 ** viewState.zoom));
    const der = x + R + 18, izq = x - R - 18 - W;
    const left = der + W <= tam.width - 12 ? der : izq >= 12 ? izq : Math.min(Math.max(x - W / 2, 12), tam.width - W - 12);
    pos = { left, top: Math.min(Math.max(y - H / 2, 12), tam.height - H - 84) };
  }
  let posPoi = null;
  if (poiSel) {
    const [x, y] = vp.project([poiSel.longitud, poiSel.latitud]);
    posPoi = { left: Math.min(Math.max(x - 120, 8), tam.width - 248), top: Math.max(y - 116, 8) };
  }

  const tooltip = ({ object, layer }) => {
    if (!object || !layer) return null;
    const id = layer.id;
    let html = null;
    if (id === "pois") {
      if (object === poiSel) return null;
      const c = CATEGORIAS[grupoDe(object.categoria)];
      html = `<div class="tt-t">${c.emoji} ${titulo(object.nombre)}</div>
        <div class="tt-s">${c.uno} · <span class="mono">${aPie(object.dist_m)}</span></div><div class="tt-h">Clic para más detalle</div>`;
    } else if (id === "inmuebles") {
      const x = colorDe(object);
      html = `<div class="tt-t">${nombre(object.distrito)}</div>
        <div class="tt-r mono">${soles(object.precio_pen)}${porMes(object)}</div>
        <div class="tt-s">${object.num_dorm ?? "—"} dorm · <span class="mono">${fmt(object.area_m2)} m²</span></div>
        ${!conCapa && x != null ? `<div class="tt-v mono">${colorTitulo} ${(x * 10).toFixed(1)}/10</div>` : ""}
        <div class="tt-h">Clic para ver su entorno</div>`;
    } else if (V && id.startsWith("hex-")) {
      // Mismo formato en las dos escalas: valor, unidad y dónde
      html = `<div class="tt-t mono">${V.f(object.v)}<span class="tt-u">${V.sufijo}</span></div>
        <div class="tt-s">${object.d ? nombre(object.d) : "Lima"} · celda de 350 m</div>
        ${capa === "crimen" ? `<div class="tt-h mono">${fmt(grillas.seguridad?.celdas[object.i]?.[3])} denuncias a 500 m en 12 meses</div>` : ""}`;
    } else if (V && id === "limites") {
      const d = object.properties.distrito, x = porDistrito.get(d);
      const extra = capa === "crimen" && x ? `${fmt(x.r.denuncias)} denuncias · ${fmt(x.r.poblacion)} hab.`
        : capa === "precio" && x ? `mediana de ${x.r.n_inmuebles} avisos` : "";
      html = `<div class="tt-t">${nombre(d)}</div>
        <div class="tt-r mono">${x ? `${V.f(x.v)}<span class="tt-u">${V.sufijo}</span>` : "Sin datos"}</div>
        ${extra ? `<div class="tt-s mono">${extra}</div>` : ""}`;
    }
    return html && { style: SIN_CAJA, html: `<div class="tt">${html}</div>` };
  };

  return (
    <div className="map" ref={caja}>
      <DeckGL
        viewState={viewState} controller={true} layers={layers}
        onViewStateChange={({ viewState: vs }) => setViewState(vs)}
        onClick={({ object, coordinate }) => {
          if (object) return;
          onCerrarFicha(); setPoiSel(null);
          if (onPunto && coordinate) onPunto({ lat: coordinate[1], lon: coordinate[0] });
        }}
        getCursor={({ isHovering, isDragging }) => (isDragging ? "grabbing" : isHovering || onPunto ? "pointer" : "grab")}
        getTooltip={tooltip}
      />

      {V ? <LeyendaVariable V={V} escala={escala} escalaColor={escalaColor} />
        : <LeyendaInmuebles escala={escalaB} colorTitulo={colorTitulo} alquiler={props[0]?.operacion === "alquiler"} conPrecio={conPrecio} />}

      <div className="map-der">
        <div className="map-zoom" role="group" aria-label="Zoom">
          <button aria-label="Acercar" onClick={() => setViewState(vs => ({ ...vs, zoom: Math.min(vs.zoom + 1, ZOOM_MAX), transitionDuration: 250 }))}>+</button>
          <button aria-label="Alejar" onClick={() => setViewState(vs => ({ ...vs, zoom: Math.max(vs.zoom - 1, ZOOM_MIN), transitionDuration: 250 }))}>−</button>
        </div>
      </div>

      <div className="map-barra" role="toolbar" aria-label="Qué ver en el mapa">
        <div className="seg seg-mapa" role="group" aria-label="Capa">
          <button aria-pressed={!capa} onClick={() => elegirCapa(null)}>Inmuebles</button>
          {PRINCIPALES.filter(k => hay[k]).map(k => (
            <button key={k} aria-pressed={capa === k} onClick={() => elegirCapa(k)}>{VARIABLES[k].l}</button>
          ))}
          {otras.length > 0 && (
            <div className="mas-capas">
              <button aria-pressed={otras.includes(capa)} aria-expanded={menu} aria-haspopup="menu" onClick={() => setMenu(m => !m)}>
                {otras.includes(capa) ? VARIABLES[capa].l : "Más capas"} <span aria-hidden="true">▾</span>
              </button>
              {menu && (
                <ul className="menu-capas" role="menu">
                  {otras.map(k => (
                    <li key={k}>
                      <button role="menuitemradio" aria-checked={capa === k} onClick={() => elegirCapa(k)}>
                        <b>{VARIABLES[k].titulo}</b><span>{VARIABLES[k].unidad.split(" (")[0]}</span>
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </div>
        {capa && (
          <div className="seg seg-escala" role="group" aria-label="Escala">
            {ESCALAS.map(e => (
              <button key={e.k} aria-pressed={escala === e.k} title={e.ayuda} onClick={() => onEscala(e.k)}>{e.l}</button>
            ))}
          </div>
        )}
        {nComparar > 0 && (
          <button className="btn-abrir-cmp" onClick={onAbrirComparador}>Comparar <span className="mono">{nComparar}</span></button>
        )}
      </div>

      <div className="map-atrib">
        {capa && !celdas && escala === "barrio" && <span>Cargando capa… · </span>}
        <span className="mono">{fmt(props.length)} inmuebles</span> · © Esri, HERE, Garmin, © OpenStreetMap
      </div>

      {ficha && selected && (
        <section className={`ficha-mapa ${angosto ? "abajo" : ""}`} style={pos || undefined} aria-label="Inmueble elegido">
          <header>
            <div>
              <h3>{nombre(selected.distrito)}</h3>
              <p className="mono">
                {soles(selected.precio_pen)}{porMes(selected)} · {selected.num_dorm ?? "—"} dorm · {fmt(selected.area_m2)} m²
              </p>
            </div>
            <button className="x" aria-label="Cerrar" onClick={onCerrarFicha}>×</button>
          </header>
          <Indicadores p={selected} ix={ixSelected} compacto onCapa={onCapa} />
          {cerca && (
            <div className="poi-filtro" role="group" aria-label="Qué mostrar alrededor">
              {CATEGORIAS_KEYS.filter(k => cerca[k].length).map(k => (
                <button key={k} className="poi-chip" aria-pressed={!!poiFiltro[k]}
                  onClick={() => onPoiFiltro(f => ({ ...f, [k]: !f[k] }))}
                  title={`${poiFiltro[k] ? "Ocultar" : "Mostrar"} ${CATEGORIAS[k].l.toLowerCase()}`}>
                  <span aria-hidden="true">{CATEGORIAS[k].emoji}</span>
                  {CATEGORIAS[k].l} <span className="mono">{cerca[k].filter(x => !x.mas_cercana).length}</span>
                </button>
              ))}
            </div>
          )}
          <footer>
            <button className={`btn-cmp ${enComparacion.has(selected.prop_id) ? "on" : ""}`} onClick={() => onComparar(selected)}
              disabled={!enComparacion.has(selected.prop_id) && lleno}
              title={!enComparacion.has(selected.prop_id) && lleno ? "Ya hay 4 inmuebles para comparar" : undefined}>
              {enComparacion.has(selected.prop_id) ? "✓ En comparación" : "+ Comparar"}
            </button>
            {onVerFicha && <button className="link" onClick={onVerFicha}>Ficha completa</button>}
          </footer>
          <p className="ficha-nota">Barras: posición frente a toda Lima. Toca una fila para verla en el mapa.</p>
        </section>
      )}

      {poiSel && (
        <section className="poi-card" style={posPoi} aria-label="Lugar cercano">
          <span className="poi-emoji" aria-hidden="true">{CATEGORIAS[grupoDe(poiSel.categoria)].emoji}</span>
          <div>
            <b>{titulo(poiSel.nombre)}</b>
            <span>{CATEGORIAS[grupoDe(poiSel.categoria)].uno}{poiSel.mas_cercana ? " · la más cercana" : ""}</span>
            <span className="mono">{fmt(poiSel.dist_m)} m · {aPie(poiSel.dist_m)}</span>
            <a href={`https://www.google.com/maps/search/?api=1&query=${poiSel.latitud},${poiSel.longitud}`}
              target="_blank" rel="noopener noreferrer">Abrir en Google Maps</a>
          </div>
          <button className="x" aria-label="Cerrar" onClick={() => setPoiSel(null)}>×</button>
        </section>
      )}
    </div>
  );
}

/* ── Leyendas: un solo formato para todas las variables ─────────────────── */
function LeyendaVariable({ V, escala, escalaColor }) {
  const c = escalaColor?.cortes || [];
  // Los cortes van de menor a mayor valor; si la variable está invertida (transporte), se leen al revés
  const cortes = V.invertido ? [...c].reverse() : c;
  return (
    <div className="map-leyenda">
      <div className="ley-t">{V.titulo} <span>· {escala === "barrio" ? "por barrio" : "por distrito"}</span></div>
      <div className="ley-u">{V.unidad}</div>
      <div className="sw">{V.paleta.map(col => <i key={col} style={{ background: col }} />)}</div>
      {cortes.length > 0 && <div className="sw-cortes mono">{cortes.map((v, i) => <span key={i}>{(V.corto || V.f)(v).replace("S/ ", "")}</span>)}</div>}
      <div className="sw-l"><span>{V.bajo}</span><span>{V.alto}</span></div>
      <div className="ley-n">{V.nota[escala]} Cada color reúne un sexto de {escala === "barrio" ? "las celdas" : "los distritos"}.</div>
    </div>
  );
}

function LeyendaInmuebles({ escala, colorTitulo, alquiler, conPrecio }) {
  return (
    <div className="map-leyenda">
      <div className="ley-t">Inmuebles</div>
      <div className="ley-u">Color: {colorTitulo.toLowerCase()}</div>
      <div className="sw">{SEQ.map(c => <i key={c} style={{ background: c }} />)}</div>
      <div className="sw-l mono"><span>0</span><span>10</span></div>
      {escala.muestras.length > 0 && (
        <div className="ley-tam">
          <div className="ley-u">Tamaño: precio{alquiler ? " al mes" : ""}</div>
          <div className="tam">
            {escala.muestras.map((v, i) => (
              <span key={i}>
                <i style={{ width: 2 * escala.r(v), height: 2 * escala.r(v) }} />
                <small className="mono">{soles(v)}{i === 2 ? "+" : ""}</small>
              </span>
            ))}
          </div>
        </div>
      )}
      {!conPrecio && <div className="ley-n">Acércate para ver el precio de cada inmueble.</div>}
    </div>
  );
}
