/**
 * useProperties.js
 * Fetches property data from the Express API.
 */

import { useState, useEffect, useCallback } from "react";

const API = import.meta.env.VITE_API_URL || "http://localhost:3001";

export function useProperties(filters = {}) {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      if (filters.distrito)   params.set("distrito",   filters.distrito);
      if (filters.precio_max) params.set("precio_max", filters.precio_max);
      if (filters.segmento)   params.set("segmento",   filters.segmento);
      if (filters.fuente)     params.set("fuente",     filters.fuente);

      const res = await fetch(`${API}/api/propiedades?${params}`);
      if (!res.ok) throw new Error(`API error ${res.status}`);
      const json = await res.json();
      setData(Array.isArray(json) ? json : []);
    } catch (err) {
      setError(err.message);
      setData([]);
    } finally {
      setLoading(false);
    }
  }, [filters.distrito, filters.precio_max, filters.segmento, filters.fuente]);

  useEffect(() => { fetchData(); }, [fetchData]);
  return { data, loading, error, refetch: fetchData };
}

export function useDistritos() {
  const [distritos, setDistritos] = useState([]);
  useEffect(() => {
    fetch(`${API}/api/distritos`)
      .then(r => r.json())
      .then(d => setDistritos(Array.isArray(d) ? d : []))
      .catch(() => setDistritos([]));
  }, []);
  return distritos;
}
