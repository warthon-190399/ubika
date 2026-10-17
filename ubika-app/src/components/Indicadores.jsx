import { CAPAS, CAPAS_KEYS, pct } from "../lib/ciudad";
import { SEQ, fmt, tramo } from "../lib/scoring";

// Componente del entorno → variable del mapa que lo pinta
const VARIABLE = { seguridad: "crimen", transporte: "transporte", servicios: "servicios", verde: "verde", barrio: "barrio", ruido: "ruido" };

/**
 * Los componentes de la calidad de vida de un inmueble: su valor real y una barra con su
 * posición frente a toda la ciudad (llena = mejor que todo Lima). Los que no tienen dato no se muestran.
 */
export default function Indicadores({ p, ix, onCapa, compacto }) {
  const keys = CAPAS_KEYS.filter(k => ix?.[k] != null || ix?.val?.[k] != null);
  return (
    <ul className={`ind ${compacto ? "ind-c" : ""}`}>
      {keys.map(k => {
        const v = ix?.val?.[k];
        const x = ix?.[k];
        const fila = (
          <>
            <span className="ind-l">{CAPAS[k].l}</span>
            <span className="ind-v mono">{(compacto && CAPAS[k].corto ? CAPAS[k].corto : CAPAS[k].texto)(v)}</span>
            <span className="ind-bar" role="img"
              aria-label={x == null ? "sin comparación" : `mejor que el ${pct(x)} de la ciudad`}>
              <i style={{ width: `${Math.max(4, (x ?? 0) * 100)}%`, background: x == null ? "var(--linea)" : SEQ[tramo(x)] }} />
            </span>
            {!compacto && (
              <span className="ind-p">
                {x == null ? "sin dato" : `mejor que el ${pct(x)} de Lima`}
                {k === "seguridad" && p.n_delitos_12m != null && ` · ${fmt(p.n_delitos_12m)} denuncias a 500 m en 12 meses`}
                {k === "ruido" && " · modelo con vías y aeropuerto, no es una medición"}
              </span>
            )}
          </>
        );
        return (
          <li key={k}>
            {onCapa
              ? <button className="ind-row" onClick={() => onCapa(VARIABLE[k])} title={`Ver ${CAPAS[k].l.toLowerCase()} en el mapa`}>{fila}</button>
              : <div className="ind-row">{fila}</div>}
          </li>
        );
      })}
    </ul>
  );
}
