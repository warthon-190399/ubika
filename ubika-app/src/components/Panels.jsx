import { Mark } from "./Logo";
import { CRITERIOS, fmt, minutos, puntajeEntorno, soles } from "../lib/scoring";
import { nombre } from "../lib/distritos";
import Indicadores from "./Indicadores";
import { CATEGORIAS, CATEGORIAS_KEYS, aPie, titulo } from "../lib/poi";

const porMes = p => (p.operacion === "alquiler" ? " /mes" : "");

/* ── Entorno ─────────────────────────────────────────────── */
export function EntornoPanel({ p, ix, distritos, cerca, crimenDist, onVolver, onCapa, enComparacion, onComparar, lleno }) {
  if (!p) return <Vacio titulo="Elige un inmueble en el mapa" texto="Toca cualquier punto para ver su entorno." />;
  const enCmp = enComparacion?.has(p.prop_id);
  const score = puntajeEntorno(ix);
  const dist = distritos?.find(d => d.distrito === p.distrito);
  const comparable = dist && dist.n_inmuebles >= 5 && p.precio_m2_pen && dist.mediana_precio_m2_pen;
  const dif = comparable ? (p.precio_m2_pen / dist.mediana_precio_m2_pen - 1) * 100 : null;

  return (
    <div className="pp">
      {onVolver && (
        <div className="pp-nav">
          <button className="link" onClick={onVolver}>← Volver a resultados</button>
          {onComparar && (
            <button className={`btn-cmp ${enCmp ? "on" : ""}`} onClick={() => onComparar(p)} disabled={!enCmp && lleno}>
              {enCmp ? "✓ En comparación" : "+ Comparar"}
            </button>
          )}
        </div>
      )}
      <div className="pp-head">
        <h2>Depa en {nombre(p.distrito)}</h2>
        <p className="pp-sub">
          {[p.direccion, p.num_dorm != null && `${p.num_dorm} dorm`, p.num_banios != null && `${p.num_banios} baños`]
            .filter(Boolean).join(" · ")} · <span className="mono">{fmt(p.area_m2)} m²</span>
        </p>
      </div>

      <div className="card-score">
        <div>
          <div className="cs-l">Calidad de vida en la zona</div>
          <div className="cs-v mono">{score == null ? "—" : score.toFixed(1)}<span>/10</span></div>
          {ix?.calidadPos != null && <div className="cs-sub">Mejor que el {Math.round(100 * ix.calidadPos)} % de Lima</div>}
        </div>
        <span className="cs-mark"><Mark size={30} /></span>
      </div>

      <div className="card-valor">
        <div className="cv-l">Precio publicado</div>
        <div className="cv-rango mono">{soles(p.precio_pen)}{porMes(p)}</div>
        <div className="cv-pub">
          <span className="mono">{soles(p.precio_m2_pen)}</span> por m²
          {p.mantenimiento_pen ? <> · mantenimiento <span className="mono">{soles(p.mantenimiento_pen)}</span></> : null}
        </div>
        {comparable ? (
          <div className="cv-comp">
            {Math.abs(dif) < 5 ? "En la mediana" : `${Math.abs(dif).toFixed(0)}% ${dif < 0 ? "por debajo" : "por encima"} de la mediana`} por m²
            de {nombre(p.distrito)} <span className="cv-n">({dist.n_inmuebles} avisos)</span>
          </div>
        ) : (
          <div className="cv-comp cv-n">Pocos avisos en {nombre(p.distrito)} para comparar el precio.</div>
        )}
      </div>

      <section className="bloque">
        <div className="eyebrow">Su entorno a 500 m</div>
        <Indicadores p={p} ix={ix} onCapa={onCapa} />
        {crimenDist?.get(p.distrito) && (() => {
          const d = crimenDist.get(p.distrito);
          const lista = [...crimenDist.values()].filter(x => x.poblacion >= 10000).sort((a, b) => a.tasa_10k - b.tasa_10k);
          const puesto = lista.findIndex(x => x.distrito === p.distrito) + 1;
          return (
            <p className="crimen-dist">
              <b className="mono">{fmt(d.tasa_10k)}</b> denuncias por 10 mil habitantes al año en {nombre(p.distrito)}
              {puesto > 0 && <span> · puesto {puesto} de {lista.length}, de menos a más</span>}
            </p>
          );
        })()}
        <p className="nota">Calidad de vida: seguridad pesa 25 %; transporte, servicios, áreas verdes, comercio y tranquilidad, 15 % cada uno. Toca una fila para verla en el mapa.</p>
      </section>

      <section className="bloque">
        <div className="eyebrow">Lo más cercano</div>
        {cerca ? (
          <ul className="cercanos">
            {CATEGORIAS_KEYS.filter(k => cerca[k].length || ["colegio", "salud", "comisaria", "transporte"].includes(k)).map(k => {
              const lista = cerca[k], dentro = lista.filter(x => !x.mas_cercana), top = lista[0];
              return (
                <li key={k}>
                  <i style={{ borderColor: CATEGORIAS[k].color }} aria-hidden="true">{CATEGORIAS[k].emoji}</i>
                  <span className="cc-m">
                    <b>{CATEGORIAS[k].l} <span className="mono">· {dentro.length} a 500 m</span></b>
                    <span>{top ? titulo(top.nombre) : "Ninguno cerca"}</span>
                  </span>
                  <span className="mono cc-d">{top ? aPie(top.dist_m) : "—"}</span>
                </li>
              );
            })}
          </ul>
        ) : (
          <ul className="distancias">
            <li><span>Colegio</span><span className="mono">{minutos(p.min_colegio)}</span></li>
            <li><span>Centro de salud</span><span className="mono">{minutos(p.min_salud)}</span></li>
            <li><span>Comisaría</span><span className="mono">{minutos(p.min_comisaria)}</span></li>
          </ul>
        )}
        <p className="nota">Distancia en línea recta, a 80 m por minuto. En el mapa se ven dentro del círculo de 500 m.</p>
      </section>

      <dl className="ficha">
        <div><dt>Antigüedad</dt><dd>{p.antiguedad_anios == null ? "Sin dato" : p.antiguedad_anios === 0 ? "A estrenar" : `${p.antiguedad_anios} años`}</dd></div>
        <div><dt>Estacionamientos</dt><dd className="mono">{p.num_estac ?? 0}</dd></div>
        {p.inmobiliaria && <div><dt>Publica</dt><dd>{p.inmobiliaria}</dd></div>}
      </dl>

      {p.url && (
        <div className="pp-cta">
          <a className="btn btn-clave" href={p.url} target="_blank" rel="noopener noreferrer">Ver aviso en el portal</a>
        </div>
      )}
    </div>
  );
}

/* ── Oportunidades ───────────────────────────────────────── */
export function OportunidadesPanel({ filtros, onFiltros, pesos, onPesos, ranking, total, selected, onSelect, enComparacion, onComparar, lleno,
  distritos, operacion, sinAntiguedad }) {
  const maxPrecio = operacion === "alquiler" ? 20000 : 3000000;
  const paso = operacion === "alquiler" ? 100 : 10000;
  return (
    <div className="pp">
      <section className="bloque">
        <div className="eyebrow">Qué buscas</div>
        <label className="campo" htmlFor="f-distrito">
          <span>Distrito</span>
          <select id="f-distrito" value={filtros.distrito} onChange={e => onFiltros(f => ({ ...f, distrito: e.target.value }))}>
            <option value="">Todos</option>
            {(distritos || []).map(d => <option key={d.distrito} value={d.distrito}>{d.distrito_nombre} ({d.n_inmuebles})</option>)}
          </select>
        </label>
        <label className="pref" htmlFor="f-precio">
          <span className="pref-h"><span>Hasta</span><span className="mono">{filtros.precioMax >= maxPrecio ? "sin límite" : soles(filtros.precioMax)}</span></span>
          <input id="f-precio" type="range" min={paso * 5} max={maxPrecio} step={paso} value={Math.min(filtros.precioMax, maxPrecio)}
            onChange={e => onFiltros(f => ({ ...f, precioMax: +e.target.value }))} />
        </label>
        <div className="campo">
          <span>Dormitorios</span>
          <div className="chips" role="group" aria-label="Dormitorios mínimos">
            {[0, 1, 2, 3].map(n => (
              <button key={n} className="chip" aria-pressed={filtros.dormMin === n} onClick={() => onFiltros(f => ({ ...f, dormMin: n }))}>
                {n === 0 ? "Todos" : `${n}+`}
              </button>
            ))}
          </div>
        </div>
      </section>

      <section className="bloque">
        <div className="eyebrow">Qué te importa más</div>
        <div className="prefs">
          {CRITERIOS.map(({ k, l, ayuda }) => (
            <label key={k} className="pref" htmlFor={`peso-${k}`} title={ayuda}>
              <span className="pref-h"><span>{l}</span><span className="mono">{pesos[k]}</span></span>
              <input id={`peso-${k}`} type="range" min={0} max={10} step={1} value={pesos[k]}
                onChange={e => onPesos(w => ({ ...w, [k]: +e.target.value }))} />
            </label>
          ))}
        </div>
        {sinAntiguedad > 0 && (
          <p className="nota">{sinAntiguedad} de {total} avisos todavía no tienen antigüedad; en ellos ese criterio no cuenta.</p>
        )}
      </section>

      <section className="bloque">
        <div className="eyebrow">Mejores coincidencias · {total} avisos</div>
        {ranking.length === 0 && <p className="nota">Ningún aviso cumple los filtros. Prueba con un presupuesto mayor.</p>}
        <ol className="ranking">
          {ranking.map(({ p, s }) => (
            <li key={p.prop_id} className="rk-li">
              <button className={`rk ${selected?.prop_id === p.prop_id ? "on" : ""}`} onClick={() => onSelect(p)}>
                <span className="rk-s mono">{(s * 10).toFixed(1)}</span>
                <span className="rk-m">
                  <b>{nombre(p.distrito)}</b>
                  <span>{p.num_dorm ?? "—"} dorm · <span className="mono">{fmt(p.area_m2)} m² · {soles(p.precio_pen)}{porMes(p)}</span></span>
                </span>
              </button>
              <button className={`rk-cmp ${enComparacion.has(p.prop_id) ? "on" : ""}`} onClick={() => onComparar(p)}
                disabled={!enComparacion.has(p.prop_id) && lleno}
                aria-label={enComparacion.has(p.prop_id) ? `Quitar ${nombre(p.distrito)} de la comparación` : `Comparar ${nombre(p.distrito)}`}
                title={enComparacion.has(p.prop_id) ? "Quitar de la comparación" : lleno ? "Ya hay 4 para comparar" : "Comparar"}>
                {enComparacion.has(p.prop_id) ? "✓" : "+"}
              </button>
            </li>
          ))}
        </ol>
      </section>
    </div>
  );
}

/* ── Próximamente ────────────────────────────────────────── */
export function ProximamentePanel({ vista }) {
  const t = vista === "valor"
    ? ["El evaluador de precio llega pronto",
       "Estimará cuánto debería costar cada depa según su zona y características, con un modelo para alquiler y otro para venta."]
    : ["Aquí verás cómo cambian los precios",
       "La evolución aparece con al menos dos cortes semanales de datos del mismo barrio."];
  return <Vacio titulo={t[0]} texto={t[1]} grafico />;
}

function Vacio({ titulo, texto, grafico }) {
  return (
    <div className="pp"><div className="vacio">
      {grafico && (
        <svg width="120" height="48" viewBox="0 0 120 48" aria-hidden="true">
          <path d="M4 40 L28 32 L52 34 L76 20 L100 22 L116 10" fill="none" stroke="var(--linea)" strokeWidth="3" strokeDasharray="6 6" strokeLinecap="round" />
        </svg>
      )}
      <h3>{titulo}</h3>
      <p>{texto}</p>
    </div></div>
  );
}
