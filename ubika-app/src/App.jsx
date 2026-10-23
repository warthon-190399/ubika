import { useCallback, useEffect, useMemo, useState } from "react";
import { useApi } from "./hooks/useApi";
import { PESOS_INICIALES, calcularIndices, puntaje } from "./lib/scoring";
import { frenteCiudad, referencia, territorio } from "./lib/ciudad";
import { nombre } from "./lib/distritos";
import { FILTRO_INICIAL, agrupar } from "./lib/poi";
import { CREDITO_INICIAL, capacidad } from "./lib/credito";
import { CONSULTA_INICIAL, distritoCercano, errorTipico, estimar } from "./lib/evaluador";
import Topbar from "./components/Topbar";
import Sidebar from "./components/Sidebar";
import MapView from "./components/MapView";
import { EntornoPanel, OportunidadesPanel, ProximamentePanel } from "./components/Panels";
import Comparador, { MAX_COMPARAR } from "./components/Comparador";
import CreditoPanel from "./components/CreditoPanel";
import EvaluadorPanel from "./components/EvaluadorPanel";
import "./app.css";

const FILTROS_INICIALES = { distrito: "", precioMax: Infinity, dormMin: 0 };

// La selección para comparar se recuerda en este navegador, una lista por operación
const leerComparar = op => { try { return JSON.parse(localStorage.getItem(`ubika.comparar.${op}`)) || []; } catch { return []; } };
const guardarComparar = (op, ids) => { try { localStorage.setItem(`ubika.comparar.${op}`, JSON.stringify(ids)); } catch { /* sin almacenamiento */ } };

/**
 * Secciones (barra lateral): explorar · comparar · credito · valor · evolucion.
 * El mapa queda montado siempre; Comparar y Evolución se abren encima, así al volver
 * el mapa conserva su zoom y posición.
 */
export default function App() {
  const [vista, setVista] = useState("explorar");
  const [operacion, setOperacion] = useState("alquiler");
  const [capa, setCapa] = useState(null);               // variable pintada en el mapa (ver lib/variables.js)
  const [escala, setEscala] = useState("barrio");       // barrio (hexágonos de 350 m) | distrito
  const [ficha, setFicha] = useState(false);            // ficha flotante del inmueble elegido
  const [detalle, setDetalle] = useState(false);        // Explorar: el panel muestra el inmueble y no el ranking
  const [pesos, setPesos] = useState(PESOS_INICIALES);
  const [filtros, setFiltros] = useState(FILTROS_INICIALES);
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState(null);
  const [foco, setFoco] = useState(false);              // centrar el mapa solo cuando el usuario elige
  const [poiFiltro, setPoiFiltro] = useState(FILTRO_INICIAL);
  const [comparar, setComparar] = useState(() => leerComparar("alquiler"));
  const [credito, setCredito] = useState(CREDITO_INICIAL);
  const [soloAlcanza, setSoloAlcanza] = useState(true);
  const [consulta, setConsulta] = useState(CONSULTA_INICIAL);   // Evaluador: el inmueble que se evalúa

  const elegir = p => { setFoco(true); setSelected(p); setFicha(true); setDetalle(true); };
  // Soltar el inmueble elegido: clic en el mapa vacío, Esc o cambio de sección
  const deseleccionar = () => { setSelected(null); setFicha(false); setDetalle(false); };
  const cambiarVista = v => { if (v !== vista) deseleccionar(); setVista(v); };
  useEffect(() => {
    const alTeclear = e => { if (e.key === "Escape") deseleccionar(); };
    window.addEventListener("keydown", alTeclear);
    return () => window.removeEventListener("keydown", alTeclear);
  }, []);
  const alternarComparar = p => setComparar(ids => {
    const sig = ids.includes(p.prop_id) ? ids.filter(i => i !== p.prop_id)
      : ids.length >= MAX_COMPARAR ? ids : [...ids, p.prop_id];
    guardarComparar(operacion, sig);
    return sig;
  });

  const { data, loading, error } = useApi(`/api/propiedades?operacion=${operacion}`);
  const { data: distritos } = useApi(`/api/distritos?operacion=${operacion}`);
  const todos = useMemo(() => data || [], [data]);

  // La ciudad como referencia: cada capa se carga una vez (≈ 7 500 celdas cada una).
  // Verde, comercio y ruido salen de OpenStreetMap; si todavía no están cargados, la app sigue sin ellos.
  const { data: gSeg } = useApi("/api/capas/seguridad");
  const { data: gTra } = useApi("/api/capas/transporte");
  const { data: gSrv } = useApi("/api/capas/servicios");
  const { data: gVer } = useApi("/api/capas/verde");
  const { data: gBar } = useApi("/api/capas/barrio");
  const { data: gRui } = useApi("/api/capas/ruido");
  const grillas = useMemo(() => ({ seguridad: gSeg, transporte: gTra, servicios: gSrv, verde: gVer, barrio: gBar, ruido: gRui }),
    [gSeg, gTra, gSrv, gVer, gBar, gRui]);

  // Crimen por 10 mil habitantes, por distrito, y los límites distritales para pintarlo
  const { data: crimenRows } = useApi("/api/crimen-distritos");
  const crimenDist = useMemo(() => new Map((crimenRows || []).map(d => [d.distrito, d])), [crimenRows]);
  const { data: limites } = useApi("/geo/distritos-lima.geojson");

  // Cada celda de la grilla con su distrito y su población; con eso, el crimen por habitante en toda la ciudad
  const terr = useMemo(() => territorio(grillas.seguridad, limites, crimenDist), [grillas.seguridad, limites, crimenDist]);
  const ciudad = useMemo(() => referencia(grillas, terr), [grillas, terr]);
  const ixCiudad = useMemo(() => new Map(todos.map(p => [p.prop_id, frenteCiudad(ciudad, p)])), [todos, ciudad]);

  // Puntos de interés a 500 m del inmueble elegido
  const { data: cercaRaw } = useApi(selected ? `/api/cerca?lat=${selected.latitud}&lon=${selected.longitud}` : null);
  const cerca = useMemo(() => (cercaRaw?.puntos ? agrupar(cercaRaw.puntos) : null), [cercaRaw]);

  // Índices sobre todos los avisos de la operación: no cambian al filtrar
  const indices = useMemo(() => calcularIndices(todos), [todos]);
  const puntajes = useMemo(() => new Map(todos.map(p => [p.prop_id, puntaje(indices.get(p.prop_id), pesos)])), [todos, indices, pesos]);

  // Crédito: precio máximo que alcanza con el ingreso, el ahorro y la tasa del usuario
  const precioMax = useMemo(() => capacidad(credito).precioMax, [credito]);
  const filtraCredito = vista === "credito" && operacion === "venta" && soloAlcanza;

  const visibles = useMemo(() => todos.filter(p =>
    (!filtros.distrito || p.distrito === filtros.distrito) &&
    (p.precio_pen ?? 0) <= filtros.precioMax &&
    (p.num_dorm ?? 0) >= filtros.dormMin &&
    (!filtraCredito || (p.precio_pen && p.precio_pen <= precioMax))), [todos, filtros, filtraCredito, precioMax]);
  const alcanzan = useMemo(() => operacion !== "venta" ? [] : todos
    .filter(p => p.precio_pen && p.precio_pen <= precioMax)
    .sort((a, b) => (puntajes.get(b.prop_id) ?? 0) - (puntajes.get(a.prop_id) ?? 0)), [todos, operacion, precioMax, puntajes]);

  // Evaluador: estimación por comparables (si se evalúa un aviso publicado, sin usarlo a él mismo)
  const enValor = vista === "valor";
  const estimacion = useMemo(() => (enValor ? estimar(todos, consulta, { excluir: consulta.propId }) : null),
    [enValor, todos, consulta]);
  const errorEval = useMemo(() => (enValor ? errorTipico(todos) : null), [enValor, todos]);
  const ponerPunto = ({ lat, lon }) =>
    setConsulta(q => ({ ...q, lat, lon, propId: null, distrito: distritoCercano(todos, lat, lon) || q.distrito }));

  const ranking = useMemo(() => visibles.map(p => ({ p, s: puntajes.get(p.prop_id) ?? 0 }))
    .sort((a, b) => b.s - a.s).slice(0, 15), [visibles, puntajes]);

  // Al cambiar de operación: limpiar filtros, selección y comparación
  useEffect(() => {
    setFiltros(FILTROS_INICIALES); setSelected(null); setFicha(false); setDetalle(false);
    setComparar(leerComparar(operacion));
    setConsulta(q => ({ ...q, pedido: null, propId: null }));   // un precio de alquiler no sirve para venta
  }, [operacion]);

  // Búsqueda por distrito: filtra y centra en el mejor aviso de ese distrito
  const nombresDistrito = useMemo(() => [...new Set(todos.map(p => nombre(p.distrito)))].sort(), [todos]);
  useEffect(() => {
    const q = query.trim().toLowerCase();
    if (q.length < 3) return;
    const d = todos.find(p => nombre(p.distrito).toLowerCase().startsWith(q))?.distrito;
    if (!d) return;
    setFiltros(f => ({ ...f, distrito: d }));
    const mejor = todos.filter(p => p.distrito === d).sort((a, b) => (puntajes.get(b.prop_id) ?? 0) - (puntajes.get(a.prop_id) ?? 0))[0];
    if (mejor) { setVista("explorar"); elegir(mejor); }
  }, [query]);

  const colorDe = useCallback(p => puntajes.get(p.prop_id) ?? 0, [puntajes]);
  const aComparar = useMemo(() => comparar.map(id => todos.find(p => p.prop_id === id)).filter(Boolean), [comparar, todos]);
  const enComparacion = useMemo(() => new Set(comparar), [comparar]);
  const sinAntiguedad = useMemo(() => visibles.filter(p => p.antiguedad_anios == null).length, [visibles]);
  const cmp = { enComparacion, onComparar: alternarComparar, lleno: comparar.length >= MAX_COMPARAR };

  return (
    <div className="shell">
      <Topbar operacion={operacion} onOperacion={setOperacion} query={query} onQuery={setQuery} distritos={nombresDistrito} />
      <div className="cuerpo">
        <Sidebar vista={vista} onVista={cambiarVista} nComparar={aComparar.length} />
        <main className="work">
          {loading && <div className="estado">Cargando inmuebles…</div>}
          {!loading && error && (
            <div className="estado">
              <b>No pudimos conectar con los datos.</b><br />
              Revisa que la API esté corriendo (<code>npm run api</code>) y que <code>ubika-app/.env</code> tenga la DATABASE_URL.
              <div className="nota">Detalle: {error}</div>
            </div>
          )}
          {!loading && !error && (
            <>
              <MapView props={visibles} grillas={grillas} ciudad={ciudad} capa={capa} onCapa={setCapa}
                escala={escala} onEscala={setEscala} distritos={distritos} colorDe={colorDe} colorTitulo="Oportunidad"
                selected={selected} ixSelected={selected && ixCiudad.get(selected.prop_id)}
                cerca={cerca} poiFiltro={poiFiltro} onPoiFiltro={setPoiFiltro} crimenDist={crimenDist} limites={limites}
                distritoSel={filtros.distrito} ficha={ficha} onCerrarFicha={() => setFicha(false)}
                onVerFicha={() => { setVista("explorar"); setDetalle(true); }}
                onSelect={elegir} onDeseleccionar={deseleccionar} foco={foco} {...cmp}
                nComparar={aComparar.length} onAbrirComparador={() => setVista("comparar")}
                punto={enValor && consulta.lat != null ? consulta : null} onPunto={enValor ? ponerPunto : null}
                resaltar={estimacion?.comparables.map(c => c.p)} />

              <aside className="panel" aria-label="Detalle" key={`${vista}-${detalle && selected ? selected.prop_id : "lista"}`}>
                {vista === "explorar" && (detalle && selected
                  ? <EntornoPanel p={selected} ix={ixCiudad.get(selected.prop_id)} distritos={distritos} cerca={cerca} crimenDist={crimenDist}
                      onVolver={() => setDetalle(false)} onCapa={setCapa} {...cmp} />
                  : <OportunidadesPanel filtros={filtros} onFiltros={setFiltros} pesos={pesos} onPesos={setPesos}
                      ranking={ranking} total={visibles.length} selected={selected} onSelect={elegir} {...cmp}
                      distritos={distritos} operacion={operacion} sinAntiguedad={sinAntiguedad} />)}
                {enValor && (
                  <EvaluadorPanel q={consulta} onQ={setConsulta} operacion={operacion} props={todos} distritos={distritos}
                    est={estimacion} error={errorEval} selected={selected} onSelect={elegir} />
                )}
                {vista === "credito" && (
                  <CreditoPanel c={credito} onC={setCredito} operacion={operacion} onVenta={() => setOperacion("venta")}
                    selected={selected} alcanzan={alcanzan} soloAlcanza={soloAlcanza} onSoloAlcanza={setSoloAlcanza} onSelect={elegir} />
                )}
              </aside>

              {vista === "comparar" && (
                <Comparador props={aComparar} ixCiudad={ixCiudad} indices={indices} puntajes={puntajes}
                  onQuitar={alternarComparar} onLimpiar={() => { setComparar([]); guardarComparar(operacion, []); }}
                  onCerrar={() => setVista("explorar")}
                  onVer={p => { setVista("explorar"); elegir(p); }} />
              )}
              {vista === "evolucion" && (
                <section className="comparador pagina-pronto"><ProximamentePanel vista="evolucion" /></section>
              )}
            </>
          )}
        </main>
      </div>
    </div>
  );
}
