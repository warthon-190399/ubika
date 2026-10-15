import styles from "./Sidebar.module.css";
import { DEFAULT_WEIGHTS } from "../lib/scoring";

const PREFS = [
  {k:"seg",label:"Seguridad",   icon:"🛡"},
  {k:"trn",label:"Transporte",  icon:"🚇"},
  {k:"pre",label:"Precio",      icon:"💰"},
  {k:"srv",label:"Servicios",   icon:"🏫"},
  {k:"esp",label:"Espacio",     icon:"📐"},
  {k:"val",label:"Valoriz.",    icon:"📈"},
];

export default function Sidebar({ filters, onFilters, weights, onWeights, distritos }) {
  const distList = Array.isArray(distritos)
    ? [...new Set(distritos.map(d=>d.distrito))].filter(Boolean).sort()
    : [];

  return (
    <aside className={styles.sidebar}>
      {/* Logo */}
      <div className={styles.logo}>
        <img
          src="/logo.png"
          alt="Ubika"
          className={styles.logoImg}
          onError={e=>{
            e.target.style.display="none";
            e.target.nextSibling.style.display="flex";
          }}
        />
        <div className={styles.logoFallback} style={{display:"none"}}>
          <span className={styles.logoText}>ubika</span>
        </div>
      </div>

      <div className={styles.body}>
        {/* Filtros */}
        <section className={styles.section}>
          <div className={styles.secLabel}>Filtros</div>

          <div className={styles.filterGroup}>
            <div className={styles.filterLabel}>Distrito</div>
            <select value={filters.distrito} onChange={e=>onFilters(f=>({...f,distrito:e.target.value}))}>
              <option value="">Todos los distritos</option>
              {distList.map(d=><option key={d} value={d}>{d}</option>)}
            </select>
          </div>

          <div className={styles.filterGroup}>
            <div className={styles.filterLabel}>
              Presupuesto
              <span className={styles.filterVal}>S/ {Number(filters.precio_max).toLocaleString()}</span>
            </div>
            <input type="range" min={500} max={15000} step={100} value={filters.precio_max}
              onChange={e=>onFilters(f=>({...f,precio_max:+e.target.value}))}/>
          </div>

          <div className={styles.filterGroup}>
            <div className={styles.filterLabel} style={{marginBottom:6}}>Segmento</div>
            <div className={styles.chipRow}>
              {["","Premium","Medio","Económico"].map(s=>(
                <button key={s||"all"}
                  className={`${styles.chip} ${filters.segmento===s?styles.chipOn:""}`}
                  onClick={()=>onFilters(f=>({...f,segmento:s}))}>
                  {s||"Todos"}
                </button>
              ))}
            </div>
          </div>

          <div className={styles.filterGroup}>
            <div className={styles.filterLabel}>Fuente</div>
            <select value={filters.fuente} onChange={e=>onFilters(f=>({...f,fuente:e.target.value}))}>
              <option value="">Urbania + Adondevivir</option>
              <option value="urbania">Urbania</option>
              <option value="adondevivir">Adondevivir</option>
            </select>
          </div>
        </section>

        {/* Preferencias */}
        <section className={styles.section}>
          <div className={styles.secLabel}>Preferencias Urbanas</div>
          {PREFS.map(({k,label,icon})=>(
            <div key={k} className={styles.prefRow}>
              <div className={styles.prefHeader}>
                <div className={styles.prefName}><span>{icon}</span>{label}</div>
                <div className={styles.prefNum}>{weights[k]}</div>
              </div>
              <div className={styles.prefTrack}>
                <div className={styles.prefFill} style={{width:`${weights[k]*10}%`}}/>
                <input type="range" min={0} max={10} step={1} value={weights[k]}
                  className={styles.prefInput}
                  onChange={e=>onWeights(w=>({...w,[k]:+e.target.value}))}/>
              </div>
            </div>
          ))}
        </section>
      </div>
    </aside>
  );
}
