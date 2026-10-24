import { CAPAS, CAPAS_KEYS, pct } from "../lib/ciudad";
import { SEQ, fmt, puntajeEntorno, soles, tramo } from "../lib/scoring";
import { nombre } from "../lib/distritos";
import { useState } from "react";

// Un color por inmueble, el mismo en el radar, las tarjetas y la tabla
export const COLORES = ["#054F46", "#E0A21A", "#3E6FB0", "#C8384F"];
const EJES = [
  { k: "precio", l: "Precio", ayuda: "más barato que los demás avisos" },
  { k: "espacio", l: "Espacio", ayuda: "área, dormitorios, baños, cochera" },
  { k: "antiguedad", l: "Antigüedad", ayuda: "más nuevo" },
  { k: "seguridad", l: "Seguridad", ayuda: "menos denuncias cerca y menos homicidios en el distrito" },
  { k: "transporte", l: "Transporte", ayuda: "cerca de metro o Metropolitano" },
  { k: "servicios", l: "Servicios", ayuda: "colegios, salud, comisarías" },
  { k: "verde", l: "Verde", ayuda: "m² de parque por habitante" },
  { k: "barrio", l: "Comercio", ayuda: "mercados, farmacias, restaurantes" },
  { k: "ruido", l: "Tranquilidad", ayuda: "menos ruido de tráfico" },
];
const valorEje = (c, k) => (CAPAS_KEYS.includes(k) ? c.ix?.[k] : c.ixAviso?.[k]) ?? null;

/** Radar 0 a 10 por eje; un polígono por inmueble. Solo los ejes con dato para alguno. */
function Radar({ ejes: EJES, cols, activo, onActivo }) {
  const W = 420, H = 360, cx = W / 2, cy = H / 2 + 6, R = 128;
  const ang = i => -Math.PI / 2 + (i * 2 * Math.PI) / EJES.length;
  const punto = (i, v) => [cx + R * v * Math.cos(ang(i)), cy + R * v * Math.sin(ang(i))];
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="radar" role="img"
      aria-label={`Radar de ${cols.length} inmuebles en ${EJES.map(e => e.l.toLowerCase()).join(", ")}`}>
      {[0.25, 0.5, 0.75, 1].map(f => (
        <polygon key={f} points={EJES.map((_, i) => punto(i, f).join(",")).join(" ")}
          fill={f === 1 ? "var(--hueso)" : "none"} stroke="var(--linea)" strokeWidth="1" strokeDasharray={f === 1 ? "0" : "3 4"} />
      ))}
      {EJES.map((e, i) => {
        const [x, y] = punto(i, 1), [lx, ly] = punto(i, 1.2);
        return (
          <g key={e.k}>
            <line x1={cx} y1={cy} x2={x} y2={y} stroke="var(--linea)" />
            <text x={lx} y={ly + 4} textAnchor={Math.abs(lx - cx) < 8 ? "middle" : lx > cx ? "start" : "end"}
              fontSize="12.5" fontWeight="600" fill="var(--grafito)">{e.l}</text>
          </g>
        );
      })}
      <text x={cx + 4} y={cy - R * 0.5 - 3} fontSize="10" fill="var(--grafito-2)">5</text>
      <text x={cx + 4} y={cy - R - 3} fontSize="10" fill="var(--grafito-2)">10</text>
      {cols.map((c, j) => {
        const pts = EJES.map((e, i) => punto(i, valorEje(c, e.k) ?? 0));
        const tenue = activo != null && activo !== j;
        return (
          <g key={c.p.prop_id} opacity={tenue ? 0.18 : 1} onMouseEnter={() => onActivo(j)} onMouseLeave={() => onActivo(null)}>
            <polygon points={pts.map(p => p.join(",")).join(" ")} fill={COLORES[j]} fillOpacity={activo === j ? 0.28 : 0.13}
              stroke={COLORES[j]} strokeWidth="2.25" strokeLinejoin="round" />
            {pts.map(([x, y], i) => (
              <circle key={i} cx={x} cy={y} r="3.5" fill={valorEje(c, EJES[i].k) == null ? "#fff" : COLORES[j]} stroke={COLORES[j]} strokeWidth="1.5" />
            ))}
          </g>
        );
      })}
    </svg>
  );
}

export const MAX_COMPARAR = 4;

const entorno = k => (p, x) => x.ix?.val?.[k] ?? null;
const antiguedad = p => (p.antiguedad_anios == null ? "Sin dato" : p.antiguedad_anios === 0 ? "A estrenar" : `${p.antiguedad_anios} años`);

/**
 * Filas del comparador. `mejor` dice qué valor gana la fila ("min" o "max");
 * sin `mejor`, la fila solo informa.
 */
const FILAS = [
  { g: "Precio" },
  { l: "Precio publicado", v: p => p.precio_pen, f: (v, p) => `${soles(v)}${p.operacion === "alquiler" ? " /mes" : ""}`, mejor: "min" },
  { l: "Precio por m²", v: p => p.precio_m2_pen, f: v => soles(v), mejor: "min" },
  { l: "Mantenimiento", v: p => p.mantenimiento_pen, f: v => (v ? soles(v) : "—"), mejor: "min" },
  { g: "Inmueble" },
  { l: "Área", v: p => p.area_m2, f: v => `${fmt(v)} m²`, mejor: "max" },
  { l: "Dormitorios", v: p => p.num_dorm, f: v => fmt(v), mejor: "max" },
  { l: "Baños", v: p => p.num_banios, f: v => fmt(v), mejor: "max" },
  { l: "Estacionamientos", v: p => p.num_estac ?? 0, f: v => fmt(v), mejor: "max" },
  { l: "Antigüedad", v: p => p.antiguedad_anios, f: (v, p) => antiguedad(p), mejor: "min" },
  { g: "Entorno a 500 m" },
  { l: "Denuncias por habitante", capa: "seguridad", v: entorno("seguridad"), f: v => CAPAS.seguridad.texto(v), mejor: "min" },
  { l: "Homicidios en el distrito", v: entorno("homicidios"), f: v => (v == null ? "—" : `${v.toFixed(1)} por 100 mil hab.`), mejor: "min" },
  { l: "Transporte", capa: "transporte", v: entorno("transporte"), f: v => CAPAS.transporte.texto(v), mejor: "min" },
  { l: "Servicios", capa: "servicios", v: entorno("servicios"), f: v => CAPAS.servicios.texto(v), mejor: "max" },
  { l: "Áreas verdes", capa: "verde", v: entorno("verde"), f: v => CAPAS.verde.texto(v), mejor: "max" },
  { l: "Comercio de barrio", capa: "barrio", v: entorno("barrio"), f: v => CAPAS.barrio.texto(v), mejor: "max" },
  { l: "Ruido estimado", capa: "ruido", v: entorno("ruido"), f: v => CAPAS.ruido.texto(v), mejor: "min" },
  { g: "Puntajes" },
  { l: "Calidad de vida", v: (p, x) => puntajeEntorno(x.ix), f: v => (v == null ? "—" : `${v.toFixed(1)} /10`), mejor: "max" },
  { l: "Oportunidad con tus prioridades", v: (p, x) => 10 * (x.puntaje ?? 0), f: v => `${v.toFixed(1)} /10`, mejor: "max" },
];

function ganador(fila, cols) {
  if (!fila.mejor || cols.length < 2) return null;
  const vals = cols.map(c => fila.v(c.p, c)).filter(v => v != null && !Number.isNaN(v));
  if (vals.length < 2) return null;
  const top = fila.mejor === "min" ? Math.min(...vals) : Math.max(...vals);
  return vals.every(v => v === top) ? null : top;   // si todos empatan, nadie gana
}

/** Hasta 4 inmuebles lado a lado; el mejor valor de cada fila se marca. */
export default function Comparador({ props, ixCiudad, indices, puntajes, onQuitar, onLimpiar, onCerrar, onVer }) {
  const [activo, setActivo] = useState(null);
  const cols = props.map(p => ({ p, ix: ixCiudad.get(p.prop_id), ixAviso: indices.get(p.prop_id), puntaje: puntajes.get(p.prop_id) }));
  // En qué eje gana cada inmueble (solo si le saca ventaja clara al resto)
  const ejes = EJES.filter(e => cols.some(c => valorEje(c, e.k) != null));
  const gana = cols.map((c, j) => ejes.filter(e => {
    const v = valorEje(c, e.k);
    if (v == null || cols.length < 2) return false;
    return cols.every((o, i) => i === j || (valorEje(o, e.k) ?? -1) < v - 0.02);
  }).map(e => e.l));
  const mejor = cols.length > 1 ? cols.reduce((a, c, j) => ((c.puntaje ?? 0) > (cols[a].puntaje ?? 0) ? j : a), 0) : -1;

  return (
    <section className="comparador" aria-label="Comparador de inmuebles">
      <header className="cmp-head">
        <div>
          <h2>Comparar inmuebles</h2>
          <p className="cmp-cupos">
            <span className="cmp-casillas" aria-hidden="true">
              {Array.from({ length: MAX_COMPARAR }, (_, i) => <i key={i} style={i < cols.length ? { "--c": COLORES[i] } : undefined} className={i < cols.length ? "llena" : ""} />)}
            </span>
            <b>{cols.length} de {MAX_COMPARAR}</b>
            {cols.length < MAX_COMPARAR
              ? `· puedes agregar ${MAX_COMPARAR - cols.length} más`
              : "· llegaste al máximo; quita uno para agregar otro"}
          </p>
          {cols.length > 1 && <p><span className="cmp-mejor-ej" aria-hidden="true" /> mejor valor de cada fila</p>}
        </div>
        <div className="cmp-acciones">
          {cols.length > 0 && <button className="link" onClick={onLimpiar}>Quitar todos</button>}
          <button className="btn btn-primario" onClick={onCerrar}>Volver al mapa</button>
        </div>
      </header>

      {cols.length === 0 ? (
        <div className="vacio">
          <h3>Todavía no elegiste inmuebles</h3>
          <p>En el mapa, toca un inmueble y usa «Comparar» en su ficha, o el botón + en el ranking de Oportunidades.</p>
        </div>
      ) : (
        <div className="cmp-scroll">
          <div className="cmp-resumen">
            <div className="cmp-radar">
              <Radar ejes={ejes} cols={cols} activo={activo} onActivo={setActivo} />
              <p className="nota">Cada eje va de 0 a 10. Precio, espacio y antigüedad frente a los demás avisos; entorno frente a Lima.</p>
            </div>
            <div className="cmp-cards">
              {cols.map((c, j) => (
                <article key={c.p.prop_id} className={`cmp-card ${activo === j ? "on" : ""}`} style={{ "--c": COLORES[j] }}
                  onMouseEnter={() => setActivo(j)} onMouseLeave={() => setActivo(null)}>
                  {j === mejor && <span className="cmp-top">★ Mejor con tus prioridades</span>}
                  <header>
                    <i aria-hidden="true" />
                    <div>
                      <b>{nombre(c.p.distrito)}</b>
                      <span className="mono">{soles(c.p.precio_pen)}{c.p.operacion === "alquiler" ? " /mes" : ""} · {fmt(c.p.area_m2)} m² · {c.p.num_dorm ?? "—"} dorm</span>
                    </div>
                  </header>
                  <div className="cmp-scores">
                    <div><span>Oportunidad</span><b className="mono">{(10 * (c.puntaje ?? 0)).toFixed(1)}</b></div>
                    <div><span>Calidad de vida</span><b className="mono">{puntajeEntorno(c.ix) == null ? "—" : puntajeEntorno(c.ix).toFixed(1)}</b></div>
                  </div>
                  <div className="cmp-gana">
                    {gana[j].length
                      ? <>Gana en {gana[j].map(g => <em key={g}>{g}</em>)}</>
                      : <span>No lidera ningún eje</span>}
                  </div>
                  <div className="cmp-card-acciones">
                    <button className="link" onClick={() => onVer(c.p)}>Ver en el mapa →</button>
                    <button className="link cmp-quitar" onClick={() => onQuitar(c.p)}
                      aria-label={`Quitar ${nombre(c.p.distrito)} de la comparación`}>✕ Quitar</button>
                  </div>
                </article>
              ))}
              {/* Cupos libres: cómo sumar otro inmueble */}
              {cols.length < MAX_COMPARAR && (
                <div className="cmp-card cmp-libre">
                  <b>{MAX_COMPARAR - cols.length === 1 ? "Queda 1 espacio libre" : `Quedan ${MAX_COMPARAR - cols.length} espacios libres`}</b>
                  <span>Agrega otro inmueble con «+ Comparar» en su ficha o en el ranking.</span>
                  <button className="link" onClick={onCerrar}>Ir al mapa →</button>
                </div>
              )}
            </div>
          </div>
          <table className="cmp-tabla" style={{ "--cols": cols.length }}>
            <thead>
              <tr>
                <th scope="col" className="cmp-l"><span className="sr-only">Atributo</span></th>
                {cols.map(({ p }) => (
                  <th key={p.prop_id} scope="col">
                    <div className="cmp-col" style={{ "--c": COLORES[cols.findIndex(c => c.p === p)] }}>
                      <button className="x" aria-label={`Quitar ${nombre(p.distrito)}`} onClick={() => onQuitar(p)}>×</button>
                      <b>{nombre(p.distrito)}</b>
                      <span>{p.direccion || "Sin dirección publicada"}</span>
                      <button className="link" onClick={() => onVer(p)}>Ver en el mapa</button>
                    </div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {FILAS.filter(f => !f.capa || cols.some(c => f.v(c.p, c) != null)).map((fila, i) => {
                if (fila.g) return (
                  <tr key={i} className="cmp-grupo"><th scope="rowgroup" colSpan={cols.length + 1}>{fila.g}</th></tr>
                );
                const top = ganador(fila, cols);
                return (
                  <tr key={i}>
                    <th scope="row" className="cmp-l">{fila.l}</th>
                    {cols.map(c => {
                      const v = fila.v(c.p, c);
                      const gana = top != null && v === top;
                      const x = fila.capa ? c.ix?.[fila.capa] : null;
                      return (
                        <td key={c.p.prop_id} className={gana ? "gana" : ""}>
                          <span className="mono">{v == null || Number.isNaN(v) ? "—" : fila.f(v, c.p)}</span>
                          {x != null && (
                            <span className="cmp-bar" title={`mejor que el ${pct(x)} de Lima`}>
                              <i style={{ width: `${Math.max(4, x * 100)}%`, background: SEQ[tramo(x)] }} />
                            </span>
                          )}
                        </td>
                      );
                    })}
                  </tr>
                );
              })}
              <tr>
                <th scope="row" className="cmp-l">Aviso original</th>
                {cols.map(({ p }) => (
                  <td key={p.prop_id}>
                    {p.url ? <a href={p.url} target="_blank" rel="noopener noreferrer">Ver en el portal</a> : "—"}
                  </td>
                ))}
              </tr>
            </tbody>
          </table>
          <p className="nota">Barras de entorno: posición frente a toda Lima. Minutos a pie en línea recta.</p>
        </div>
      )}
    </section>
  );
}
