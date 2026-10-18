import { useState } from "react";
import { TEA_FUENTE, capacidad, cuota, semaforo } from "../lib/credito";
import { fmt, soles } from "../lib/scoring";
import { nombre } from "../lib/distritos";

const NIVEL = {
  ok: { l: "Dentro de tu presupuesto", c: "ok" },
  justo: { l: "Ajustado: pasa tu límite", c: "justo" },
  alto: { l: "Fuera de tu presupuesto", c: "alto" },
};

/** Campo numérico. Con `opcional`, vacío vale null (sin dato) en vez de 0. */
export function Campo({ id, l, valor, onCambio, prefijo, sufijo, paso = 100, min = 0, opcional = false, placeholder }) {
  return (
    <label className="cr-campo" htmlFor={id}>
      <span>{l}</span>
      <span className="cr-input">
        {prefijo && <i>{prefijo}</i>}
        <input id={id} type="number" inputMode="decimal" min={min} step={paso} value={valor ?? ""} placeholder={placeholder}
          onChange={e => onCambio(e.target.value === "" ? (opcional ? null : 0) : +e.target.value)} />
        {sufijo && <i>{sufijo}</i>}
      </span>
    </label>
  );
}

/** Pestaña Crédito: cuánto puedo comprar, cuánto pagaría por este inmueble y qué alcanza en el mapa. */
export default function CreditoPanel({ c, onC, operacion, onVenta, selected, alcanzan, soloAlcanza, onSoloAlcanza, onSelect }) {
  const [avanzado, setAvanzado] = useState(false);
  const set = k => v => onC(x => ({ ...x, [k]: v }));

  if (operacion !== "venta") {
    return (
      <div className="pp"><div className="vacio">
        <h3>El simulador es para comprar</h3>
        <p>Calcula cuánto puedes financiar y qué inmuebles en venta te alcanzan.</p>
        <button className="btn btn-primario" onClick={onVenta}>Ver inmuebles en venta</button>
      </div></div>
    );
  }

  const cap = capacidad(c);
  const sel = selected && selected.operacion === "venta" && selected.precio_pen ? selected : null;
  const inicialSel = sel ? Math.min(c.ahorro, sel.precio_pen) : 0;
  const cs = sel ? cuota(sel.precio_pen, inicialSel, c) : null;
  const sem = cs ? semaforo(cs.total, c) : null;
  const faltaInicial = sel ? Math.max(0, sel.precio_pen * c.inicialMinPct / 100 - c.ahorro) : 0;

  return (
    <div className="pp">
      <section className="bloque">
        <div className="eyebrow">Tu situación</div>
        <div className="cr-grid">
          <Campo id="cr-ingreso" l="Ingreso neto mensual" prefijo="S/" valor={c.ingreso} onCambio={set("ingreso")} />
          <Campo id="cr-ahorro" l="Ahorro para la inicial" prefijo="S/" valor={c.ahorro} onCambio={set("ahorro")} paso={1000} />
        </div>
        <label className="pref" htmlFor="cr-plazo">
          <span className="pref-h"><span>Plazo</span><span className="mono">{c.plazo} años</span></span>
          <input id="cr-plazo" type="range" min={5} max={30} step={1} value={c.plazo} onChange={e => set("plazo")(+e.target.value)} />
        </label>
        <div className="cr-grid">
          <Campo id="cr-tea" l="Tasa anual (TEA)" sufijo="%" valor={c.tea} onCambio={set("tea")} paso={0.05} />
          <Campo id="cr-cuotamax0" l="Cuota máx. / ingreso" sufijo="%" valor={c.cuotaMaxPct} onCambio={set("cuotaMaxPct")} paso={1} />
          <p className="nota cr-fuente">Por defecto, el <a href={TEA_FUENTE.url} target="_blank" rel="noopener noreferrer">{TEA_FUENTE.texto}</a>. Pon la de tu banco si la tienes.</p>
        </div>
        <button className="link" aria-expanded={avanzado} onClick={() => setAvanzado(a => !a)}>
          {avanzado ? "Ocultar supuestos" : "Ajustar supuestos del banco"}
        </button>
        {avanzado && (
          <div className="cr-grid">
            <Campo id="cr-inimin" l="Inicial mínima" sufijo="%" valor={c.inicialMinPct} onCambio={set("inicialMinPct")} paso={1} />
            <Campo id="cr-desg" l="Desgravamen, mensual" sufijo="%" valor={c.desgravamen} onCambio={set("desgravamen")} paso={0.005} />
            <Campo id="cr-seg" l="Seguro del inmueble, mensual" sufijo="%" valor={c.seguroInmueble} onCambio={set("seguroInmueble")} paso={0.005} />
          </div>
        )}
      </section>

      <div className="card-score cr-res">
        <div>
          <div className="cs-l">Puedes comprar hasta</div>
          <div className="cs-v mono">{soles(cap.precioMax)}</div>
          <div className="cr-sub mono">
            Préstamo {soles(cap.prestamo)} · cuota {soles(cap.total)} al mes
          </div>
          <div className="cr-sub">
            {cap.limita === "inicial"
              ? `Te limita la inicial: tu ahorro cubre el ${c.inicialMinPct} % de ese precio.`
              : `Te limita la cuota: hasta el ${c.cuotaMaxPct} % de tu ingreso (${soles(cap.cuotaMax)}).`}
          </div>
        </div>
      </div>

      {sel && (
        <section className="bloque cr-sel">
          <div className="eyebrow">Este inmueble · {nombre(sel.distrito)}</div>
          <div className="cr-fila"><span>Precio</span><span className="mono">{soles(sel.precio_pen)}</span></div>
          <div className="cr-fila"><span>Tu inicial</span><span className="mono">{soles(inicialSel)} ({fmt((100 * inicialSel) / sel.precio_pen)} %)</span></div>
          <div className="cr-fila"><span>Préstamo</span><span className="mono">{soles(cs.prestamo)}</span></div>
          <div className="cr-fila cr-cuota"><span>Cuota mensual</span><span className="mono">{soles(cs.total)}</span></div>
          <div className="cr-fila"><span>Intereses en {c.plazo} años</span><span className="mono">{soles(cs.intereses)}</span></div>
          <div className={`cr-sem ${NIVEL[sem.nivel].c}`}>
            <b>{NIVEL[sem.nivel].l}</b> · la cuota es el <span className="mono">{fmt(sem.pct)} %</span> de tu ingreso
          </div>
          {faltaInicial > 0 && <p className="nota">Para la inicial mínima del {c.inicialMinPct} % te faltan {soles(faltaInicial)}.</p>}
        </section>
      )}

      <section className="bloque">
        <div className="eyebrow">Te alcanzan · {alcanzan.length} inmuebles</div>
        <label className="cr-check">
          <input type="checkbox" checked={soloAlcanza} onChange={e => onSoloAlcanza(e.target.checked)} />
          Mostrar en el mapa solo los que me alcanzan
        </label>
        {alcanzan.length === 0 && <p className="nota">Ninguno con estos datos. Prueba con más plazo o más inicial.</p>}
        <ol className="ranking">
          {alcanzan.slice(0, 12).map(p => {
            const q = cuota(p.precio_pen, Math.min(c.ahorro, p.precio_pen), c);
            return (
              <li key={p.prop_id}>
                <button className={`rk ${selected?.prop_id === p.prop_id ? "on" : ""}`} onClick={() => onSelect(p)}>
                  <span className="rk-s mono cr-rk">{soles(q.total)}</span>
                  <span className="rk-m">
                    <b>{nombre(p.distrito)}</b>
                    <span>{p.num_dorm ?? "—"} dorm · <span className="mono">{fmt(p.area_m2)} m² · {soles(p.precio_pen)}</span></span>
                  </span>
                </button>
              </li>
            );
          })}
        </ol>
      </section>

      <p className="nota">Cálculo referencial con cuota fija. Cada banco aplica su tasa, seguros y evaluación crediticia.</p>
    </div>
  );
}
