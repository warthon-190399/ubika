import { useState, useMemo } from "react";
import { useProperties, useDistritos } from "./hooks/useProperties";
import { computeScore, computeBounds, DEFAULT_WEIGHTS } from "./lib/scoring";
import Sidebar from "./components/Sidebar";
import Topbar from "./components/Topbar";
import MapView from "./components/MapView";
import InsightsPanel from "./components/InsightsPanel";
import styles from "./App.module.css";

export default function App() {
  const [weights, setWeights] = useState(DEFAULT_WEIGHTS);
  const [filters, setFilters] = useState({ distrito:"", precio_max:15000, segmento:"", fuente:"" });
  const [capa, setCapa] = useState("score");

  const { data: props, loading, error } = useProperties({
    distrito:   filters.distrito   || undefined,
    precio_max: filters.precio_max < 15000 ? filters.precio_max : undefined,
    segmento:   filters.segmento   || undefined,
    fuente:     filters.fuente     || undefined,
  });
  const distritos = useDistritos();

  const filtered = useMemo(() =>
    props.filter(p => {
      if (filters.segmento && p.tipo_vivienda !== filters.segmento) return false;
      if (p.precio_pen && p.precio_pen > filters.precio_max) return false;
      return true;
    }), [props, filters]);

  const bounds = useMemo(() => computeBounds(filtered), [filtered]);
  const stats = useMemo(() => {
    const total = filtered.length;
    const avg = total ? Math.round(filtered.reduce((a,p)=>a+(p.precio_pen||0),0)/total) : 0;
    const scores = filtered.map(p=>computeScore(p,weights,bounds));
    const maxScore = scores.length ? Math.max(...scores) : 0;
    const dists = new Set(filtered.map(p=>p.distrito)).size;
    return { total, avg, maxScore, dists };
  }, [filtered, weights, bounds]);

  return (
    <div className={styles.shell}>
      <Sidebar
        filters={filters} onFilters={setFilters}
        weights={weights} onWeights={setWeights}
        distritos={distritos}
      />
      <div className={styles.main}>
        <Topbar stats={stats} error={error} />
        <div className={styles.content}>
          {loading && (
            <div className={styles.loader}>
              <div className={styles.loaderDot}/>
              <span>Cargando datos...</span>
            </div>
          )}
          {!loading && error && (
            <div className={styles.errorMsg}>
              Sin conexión al servidor — verifica que <code>node server.js</code> esté corriendo.
            </div>
          )}
          {!loading && !error && (
            <div className={styles.mapCol}>
              <MapView props={filtered} weights={weights} capa={capa} onCapa={setCapa} />
              <InsightsPanel props={filtered} weights={weights} capa={capa} onCapa={setCapa} />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
