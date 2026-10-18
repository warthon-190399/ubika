import { useMemo } from "react";
import { K, centroDistrito, consultaDe, veredicto } from "../lib/evaluador";
import { fmt, soles } from "../lib/scoring";
import { nombre } from "../lib/distritos";
import { Campo } from "./CreditoPanel";

const uno = n => n.toFixed(1);

const VEREDICTO = {
  bajo: { l: "Por debajo de lo que piden avisos parecidos", c: "ok" },
  rango: { l: "Dentro del rango de avisos parecidos", c: "justo" },
  alto: { l: "Por encima de lo que piden avisos parecidos", c: "alto" },
};
const CONFIANZA = {
  alta: "Confianza alta: hay avisos parecidos cerca y piden precios parejos.",
  media: "Confianza media: los parecidos están algo lejos o sus precios varían.",
  baja: "Confianza baja: hay pocos avisos parecidos en la zona. Tómalo como referencia gruesa.",
};

/**
 * Pestaña Evaluador: cuánto debería costar un inmueble según los avisos más parecidos.
 * La ubicación sale de un toque en el mapa, de un distrito o del inmueble elegido.
 */
export default function EvaluadorPanel({ q, onQ, operacion, props, distritos, est, error, selected, onSelect }) {
  const set = k => v => onQ(x => ({ ...x, [k]: v }));
  const mes = operacion === "alquiler" ? " /mes" : "";
  const ver = veredicto(est, q.pedido);
  const opciones = useMemo(() => (distritos || []).filter(d => d.n_inmuebles >= 3)
    .map(d => d.distrito).sort((a, b) => nombre(a).localeCompare(nombre(b))), [distritos]);

  const elegirDistrito = d => {
    const c = d && centroDistrito(props, d);
    onQ(x => ({ ...x, distrito: d, propId: null, ...(c ? { lat: c.lat, lon: c.lon } : {}) }));
  };
  const usarElegido = () => onQ(consultaDe(selected));
  const elegidoSirve = selected && selected.operacion === operacion && selected.area_m2 > 0;

  return (
    <div className="pp">
      <div className="pp-head">
        <div className="eyebrow">Evaluador · {operacion}</div>
        <h2>¿Cuánto debería costar?</h2>
        <p className="pp-sub">Con los {K} avisos de {operacion} más parecidos: cerca y con área, dormitorios y baños similares.</p>
      </div>

      <section className="bloque">
        <div className="eyebrow">Ubicación</div>
        <label className="cr-campo" htmlFor="ev-distrito">
          <span>Distrito</span>
          <span className="cr-input">
            <select id="ev-distrito" className="ev-select" value={q.distrito || ""} onChange={e => elegirDistrito(e.target.value)}>
              <option value="">Elige un distrito…</option>
              {opciones.map(d => <option key={d} value={d}>{nombre(d)}</option>)}
            </select>
          </span>
        </label>
        <p className="nota">
          {q.lat != null
            ? <>Punto en <b>{nombre(q.distrito)}</b> (<span className="mono">{q.lat.toFixed(4)}, {q.lon.toFixed(4)}</span>). Toca el mapa para moverlo.</>
            : "O toca el mapa donde está el inmueble."}
        </p>
        {elegidoSirve && (
          <button className="link" onClick={usarElegido}>
            Evaluar el inmueble elegido ({nombre(selected.distrito)}, {fmt(selected.area_m2)} m²)
          </button>
        )}
      </section>

      <section className="bloque">
        <div className="eyebrow">Características</div>
        <div className="cr-grid">
          <Campo id="ev-area" l="Área" sufijo="m²" valor={q.area} onCambio={set("area")} paso={5} min={10} />
          <Campo id="ev-dorm" l="Dormitorios" valor={q.dorm} onCambio={set("dorm")} paso={1} />
          <Campo id="ev-banos" l="Baños" valor={q.banos} onCambio={set("banos")} paso={1} />
          <Campo id="ev-estac" l="Estacionamientos" valor={q.estac} onCambio={set("estac")} paso={1} />
          <Campo id="ev-antig" l="Antigüedad" sufijo="años" valor={q.antig} onCambio={set("antig")} paso={1} opcional placeholder="No sé" />
          <Campo id="ev-pedido" l={operacion === "alquiler" ? "Precio pedido, mes" : "Precio pedido"} prefijo="S/" valor={q.pedido}
            onCambio={set("pedido")} paso={operacion === "alquiler" ? 100 : 5000} opcional placeholder="Opcional" />
        </div>
      </section>

      {!est && (
        <p className="nota">
          {q.lat == null ? "Elige la ubicación para ver la estimación."
            : !(q.area > 0) ? "Pon el área para ver la estimación." : "No hay avisos suficientes para estimar."}
        </p>
      )}

      {est && (
        <>
          <div className="card-score cr-res">
            <div>
              <div className="cs-l">Precio estimado</div>
              <div className="cs-v mono">{soles(est.precio)}<span>{mes}</span></div>
              <div className="cr-sub mono">Rango {soles(est.bajo)} – {soles(est.alto)} · {soles(est.precioM2)} por m²</div>
              <div className="cr-sub">{CONFIANZA[est.confianza]}</div>
            </div>
          </div>

          {ver && (
            <div className={`cr-sem ${VEREDICTO[ver.nivel].c}`}>
              <b>{VEREDICTO[ver.nivel].l}</b> · el precio pedido está{" "}
              <span className="mono">{fmt(Math.abs(ver.pct))} %</span> {ver.pct >= 0 ? "encima" : "debajo"} de la estimación
            </div>
          )}

          <section className="bloque">
            <div className="eyebrow">Los {est.comparables.length} avisos que usa · a {uno(est.kmMediana)} km en mediana</div>
            <ol className="ranking">
              {est.comparables.map(({ p, km }) => (
                <li key={p.prop_id}>
                  <button className={`rk ev-rk ${selected?.prop_id === p.prop_id ? "on" : ""}`} onClick={() => onSelect(p)}>
                    <span className="rk-s mono">{soles(p.precio_pen)}</span>
                    <span className="rk-m">
                      <b>{nombre(p.distrito)} · <span className="mono">{km < 1 ? `${Math.round(km * 1000)} m` : `${uno(km)} km`}</span></b>
                      <span>{p.num_dorm ?? "—"} dorm · {p.num_banios ?? "—"} baños · <span className="mono">{fmt(p.area_m2)} m² · {soles(p.precio_pen / p.area_m2)}/m²</span></span>
                    </span>
                  </button>
                </li>
              ))}
            </ol>
          </section>
        </>
      )}

      <p className="nota">
        Es lo que piden hoy avisos parecidos, no una tasación.
        {error && <> Probado con {error.n} avisos de la base: la mitad de las estimaciones queda a menos
          de <span className="mono">{fmt(error.mediana)} %</span> del precio publicado
          y el <span className="mono">{fmt(error.dentro20)} %</span> a menos de 20 %.</>}
      </p>
    </div>
  );
}
