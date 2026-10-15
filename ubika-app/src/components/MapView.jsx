import { useMemo, useState, useCallback, useRef, useEffect } from "react";
import DeckGL from "@deck.gl/react";
import { Map } from "react-map-gl/maplibre";
import { ScatterplotLayer } from "@deck.gl/layers";
import { HeatmapLayer } from "@deck.gl/aggregation-layers";
import { computeScore, computeBounds } from "../lib/scoring";
import styles from "./MapView.module.css";

const MAP_STYLE = "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json";
const INITIAL_VIEW = { longitude:-77.03, latitude:-12.05, zoom:11, pitch:0, bearing:0 };

function scoreHex(s) {
  if (s>=.68) return "#FF8C42";
  if (s>=.52) return "#2dd4bf";
  if (s>=.38) return "#8b7cf8";
  return "#e63329";
}
function segBg(seg) {
  if (seg==="Premium") return "rgba(255,140,66,.18)";
  if (seg==="Medio")   return "rgba(45,212,191,.18)";
  return "rgba(230,51,41,.18)";
}
function segCol(seg) {
  if (seg==="Premium") return "#FF8C42";
  if (seg==="Medio")   return "#2dd4bf";
  return "#e63329";
}

const CAPAS = [
  {v:"score",      l:"Score",      icon:"◈"},
  {v:"precio",     l:"Precio",     icon:"$"},
  {v:"seguridad",  l:"Seguridad",  icon:"⬡"},
  {v:"transporte", l:"Transporte", icon:"⬡"},
  {v:"servicios",  l:"Servicios",  icon:"⬡"},
];

export default function MapView({ props, weights, capa, onCapa }) {
  const [viewState, setViewState] = useState(INITIAL_VIEW);
  const [hoveredId, setHoveredId] = useState(null);
  const [layerMode, setLayerMode] = useState("scatter");
  const [panelOpen, setPanelOpen] = useState(true);

  const bounds = useMemo(() => computeBounds(props), [props]);
  const enriched = useMemo(() =>
    props.map(p => ({
      ...p,
      score: computeScore(p, weights, bounds),
      coordinates: [p.longitud, p.latitud],
    })), [props, weights, bounds]);

  const getColor = useCallback((d) => {
    const s = d.score;
    if (s>=.68) return [255,140,66,210];
    if (s>=.52) return [45,212,191,210];
    if (s>=.38) return [139,124,248,210];
    return [230,51,41,210];
  }, []);

  const layers = useMemo(() => {
    if (layerMode === "heatmap") {
      return [new HeatmapLayer({
        id:"heatmap", data:enriched,
        getPosition: d=>d.coordinates,
        getWeight: d=>d.score,
        radiusPixels:60, intensity:1.2, threshold:0.05,
        colorRange:[
          [15,27,45,0],[100,30,30,120],[180,60,40,160],
          [230,51,41,200],[240,140,60,220],[255,140,66,240],
        ],
        opacity:0.8,
      })];
    }
    // scatter only — no HexagonLayer (GPU issues on many machines)
    return [new ScatterplotLayer({
      id:"scatter", data:enriched,
      getPosition: d=>d.coordinates,
      getRadius: d=>(18+d.score*28)*(d.prop_id===hoveredId?1.5:1),
      getFillColor: d=>d.prop_id===hoveredId?[255,255,255,255]:getColor(d),
      getLineColor: d=>getColor(d),
      getLineWidth: d=>d.prop_id===hoveredId?3:0,
      stroked:true, lineWidthMinPixels:1,
      radiusMinPixels:3, radiusMaxPixels:18,
      pickable:true, autoHighlight:false,
      updateTriggers:{
        getRadius:[hoveredId,weights],
        getFillColor:[hoveredId,weights,capa],
      },
      transitions:{
        getFillColor:{duration:300},
        getRadius:{duration:200},
      },
      onHover:({object})=>setHoveredId(object?.prop_id??null),
    })];
  }, [enriched, layerMode, hoveredId, weights, capa, getColor]);

  return (
    <div className={styles.wrap}>
      <DeckGL
        viewState={viewState}
        onViewStateChange={({viewState:vs})=>setViewState(vs)}
        controller={true}
        layers={layers}
        getTooltip={({object})=>object && {
          html:`<div style="font-family:'IBM Plex Mono',monospace;background:#152236;border:1px solid rgba(255,255,255,0.14);border-radius:8px;padding:12px 14px;min-width:190px">
            <div style="font-family:'Inter',sans-serif;font-size:13px;font-weight:700;color:#e8edf3;margin-bottom:2px">${object.distrito}</div>
            <div style="font-size:9px;color:#6b7f96;margin-bottom:9px">${object.fuente||""} · NSE ${object.nivel_socioeconomico||"—"}</div>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:5px;margin-bottom:9px">
              <div><div style="font-size:12px;font-weight:500;color:#e8edf3">S/ ${(object.precio_pen||0).toLocaleString()}</div><div style="font-size:8px;color:#6b7f96">precio/mes</div></div>
              <div><div style="font-size:12px;font-weight:500;color:#e8edf3">${object.area_m2||"—"} m²</div><div style="font-size:8px;color:#6b7f96">área</div></div>
              <div><div style="font-size:12px;font-weight:500;color:#e8edf3">${object.num_dorm||"—"} dorm.</div><div style="font-size:8px;color:#6b7f96">dormitorios</div></div>
              <div><div style="font-size:12px;font-weight:500;color:#e8edf3">S/ ${object.area_m2?Math.round(object.precio_pen/object.area_m2):"—"}</div><div style="font-size:8px;color:#6b7f96">S//m²</div></div>
            </div>
            <div style="display:flex;align-items:center;justify-content:space-between;border-top:1px solid rgba(255,255,255,0.07);padding-top:7px">
              <div>
                <div style="font-size:18px;font-weight:500;color:${scoreHex(object.score)}">${(object.score||0).toFixed(3)}</div>
                <div style="font-size:8px;color:#6b7f96">OPPORTUNITY SCORE</div>
              </div>
              <div style="font-size:9px;font-weight:600;padding:3px 8px;border-radius:20px;background:${segBg(object.tipo_vivienda)};color:${segCol(object.tipo_vivienda)}">${(object.tipo_vivienda||"").toUpperCase()}</div>
            </div>
          </div>`,
          style:{background:"transparent",border:"none",padding:0},
        }}
      >
        <Map mapStyle={MAP_STYLE} attributionControl={false} reuseMaps />
      </DeckGL>

      {/* Layer mode — top center */}
      <div className={styles.modeBar}>
        {[["scatter","Puntos"],["heatmap","Heatmap"]].map(([v,l])=>(
          <button key={v}
            className={`${styles.modeBtn} ${layerMode===v?styles.modeBtnOn:""}`}
            onClick={()=>setLayerMode(v)}>
            {l}
          </button>
        ))}
      </div>

      {/* Right panel — capa visual */}
      <div className={`${styles.rightPanel} ${panelOpen?styles.panelOpen:""}`}>
        <button className={styles.panelToggle} onClick={()=>setPanelOpen(o=>!o)}>
          <span className={styles.toggleIcon}>{panelOpen?"›":"‹"}</span>
          {!panelOpen && <span className={styles.toggleLabel}>CAPAS</span>}
        </button>
        {panelOpen && (
          <div className={styles.panelBody}>
            <div className={styles.panelTitle}>CAPA VISUAL</div>
            {CAPAS.map(({v,l})=>(
              <button key={v}
                className={`${styles.capaItem} ${capa===v?styles.capaOn:""}`}
                onClick={()=>onCapa(v)}>
                <div className={styles.capaIndicator} style={{background:capa===v?"var(--orange)":"var(--muted2)"}}/>
                {l}
              </button>
            ))}

            <div className={styles.panelDivider}/>
            <div className={styles.panelTitle}>LEYENDA</div>
            {[["#FF8C42","Alto  ≥ 0.68"],["#2dd4bf","Medio 0.52–0.68"],["#8b7cf8","Base  0.38–0.52"],["#e63329","Bajo  < 0.38"]].map(([c,l])=>(
              <div key={c} className={styles.legItem}>
                <div className={styles.legDot} style={{background:c}}/>
                <span className={styles.legLabel}>{l}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
