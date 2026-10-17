import Logo from "./Logo";

/** Marca, búsqueda por distrito y operación. Las secciones viven en la barra lateral. */
export default function Topbar({ operacion, onOperacion, query, onQuery, distritos }) {
  return (
    <header className="topbar">
      <Logo />
      <label className="search">
        <svg width="16" height="16" viewBox="0 0 24 24" aria-hidden="true">
          <circle cx="11" cy="11" r="7" fill="none" stroke="currentColor" strokeWidth="2" />
          <path d="m20 20-4-4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
        </svg>
        <input
          id="busqueda" list="lista-distritos" value={query}
          onChange={e => onQuery(e.target.value)}
          placeholder="Busca un distrito" aria-label="Buscar distrito"
        />
        <datalist id="lista-distritos">
          {distritos.map(d => <option key={d} value={d} />)}
        </datalist>
      </label>

      <div className="seg" role="group" aria-label="Operación">
        {["alquiler", "venta"].map(o => (
          <button key={o} aria-pressed={operacion === o} onClick={() => onOperacion(o)}>
            {o === "alquiler" ? "Alquiler" : "Venta"}
          </button>
        ))}
      </div>
    </header>
  );
}
