/** Navegación principal a la izquierda (abajo en el teléfono). */
const I = {
  explorar: <path d="M9 4 3 6.5v13.5L9 17.5l6 2.5 6-2.5V4l-6 2.5L9 4Zm0 0v13.5m6-11v13.5" />,
  comparar: <path d="M4 5h6v14H4zM14 5h6v14h-6zM7 9v1m0 3v1m10-5v1m0 3v1" />,
  credito: <path d="M3 10.5 12 4l9 6.5M5.5 9v10h13V9M9.5 19v-5h5v5" />,
  evolucion: <path d="M4 19h16M5 15l4-4 3 3 6-7m0 0h-4m4 0v4" />,
};

export const SECCIONES = [
  { v: "explorar", l: "Explorar", ayuda: "Mapa, entorno y oportunidades" },
  { v: "comparar", l: "Comparar", ayuda: "Inmuebles lado a lado" },
  { v: "credito", l: "Crédito", ayuda: "Simulador hipotecario" },
  { v: "evolucion", l: "Evolución", ayuda: "Precios en el tiempo", pronto: true },
];

export default function Sidebar({ vista, onVista, nComparar }) {
  return (
    <nav className="sidebar" aria-label="Secciones">
      {SECCIONES.map(s => (
        <button key={s.v} className="sb-item" aria-current={vista === s.v ? "page" : undefined}
          onClick={() => onVista(s.v)} title={s.ayuda}>
          <span className="sb-ico">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7"
              strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{I[s.v]}</svg>
            {s.v === "comparar" && nComparar > 0 && <b className="sb-badge mono">{nComparar}</b>}
          </span>
          <span className="sb-l">{s.l}</span>
          {s.pronto && <span className="sb-pronto">Pronto</span>}
        </button>
      ))}
    </nav>
  );
}
