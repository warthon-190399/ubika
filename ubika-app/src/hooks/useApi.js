/**
 * useApi.js · lectura de la API Express (server.js) con caché por ruta.
 */
import { useEffect, useState } from "react";

const BASE = import.meta.env.VITE_API_URL || "";
const cache = new Map();

export function useApi(ruta) {
  const [estado, setEstado] = useState(() =>
    cache.has(ruta) ? { data: cache.get(ruta), loading: false, error: null } : { data: null, loading: !!ruta, error: null });

  useEffect(() => {
    if (!ruta) return;
    if (cache.has(ruta)) { setEstado({ data: cache.get(ruta), loading: false, error: null }); return; }
    let vivo = true;
    setEstado(e => ({ ...e, loading: true, error: null }));
    fetch(`${BASE}${ruta}`)
      .then(async r => {
        const j = await r.json().catch(() => ({}));
        if (!r.ok) throw new Error(j.error || `Error ${r.status}`);
        return j;
      })
      .then(d => { cache.set(ruta, d); if (vivo) setEstado({ data: d, loading: false, error: null }); })
      .catch(e => vivo && setEstado({ data: null, loading: false, error: e.message }));
    return () => { vivo = false; };
  }, [ruta]);

  return estado;
}
