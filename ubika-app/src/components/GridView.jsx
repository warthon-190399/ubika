import { useMemo } from "react";
import { computeScore, computeBounds } from "../lib/scoring";
import styles from "./GridView.module.css";

function scoreHex(s) {
  if (s >= .72) return "#e8ff47";
  if (s >= .56) return "#2dd4bf";
  if (s >= .40) return "#8b7cf8";
  return "#e63329";
}
function segStyle(seg) {
  if (seg === "Premium")  return { bg: "rgba(247,200,78,.15)", color: "#f7c84e" };
  if (seg === "Medio")    return { bg: "rgba(45,212,191,.15)", color: "#2dd4bf" };
  return                         { bg: "rgba(230,51,41,.15)",  color: "#e63329" };
}

export default function GridView({ props, weights }) {
  const bounds = useMemo(() => computeBounds(props), [props]);
  const sorted = useMemo(() =>
    props.map(p => ({ ...p, score: computeScore(p, weights, bounds) }))
      .sort((a, b) => b.score - a.score)
      .slice(0, 60),
    [props, weights, bounds]
  );

  if (!sorted.length) return (
    <div className={styles.empty}>Sin propiedades con los filtros actuales.</div>
  );

  return (
    <div className={styles.grid}>
      {sorted.map(p => {
        const col = scoreHex(p.score);
        const ss = segStyle(p.tipo_vivienda);
        const pm2 = p.area_m2 ? Math.round(p.precio_pen / p.area_m2) : null;
        return (
          <div key={p.prop_id} className={styles.card}
            onClick={() => p.url && window.open(p.url, "_blank")}>
            <div className={styles.cardTop}>
              <div className={styles.cardDist}>{p.distrito}</div>
              <div className={styles.scoreCircle}
                style={{ background: col + "22", color: col, border: `1px solid ${col}44` }}>
                {p.score.toFixed(2)}
              </div>
            </div>
            <div className={styles.price}>S/ {(p.precio_pen || 0).toLocaleString()}</div>
            <div className={styles.stats}>
              <span>{p.area_m2 || "—"}m²</span>
              <span>{p.num_dorm || "—"} dorm</span>
              <span>{p.num_banios || "—"} baños</span>
              {pm2 && <span>S/{pm2}/m²</span>}
            </div>
            <div className={styles.footer}>
              {p.tipo_vivienda && (
                <span className={styles.badge}
                  style={{ background: ss.bg, color: ss.color }}>
                  {p.tipo_vivienda}
                </span>
              )}
              <span className={styles.fuente}>{p.fuente}</span>
            </div>
            <div className={styles.spark}>
              <div className={styles.sparkFill} style={{ width: `${(p.score * 100).toFixed(0)}%`, background: col }} />
            </div>
          </div>
        );
      })}
    </div>
  );
}
