import styles from "./Topbar.module.css";

export default function Topbar({ stats, error }) {
  return (
    <header className={styles.topbar}>
      <div className={styles.kpis}>
        <div className={styles.kpi}>
          <div className={styles.kpiV}>{stats.total.toLocaleString()}</div>
          <div className={styles.kpiL}>PROPIEDADES</div>
        </div>
        <div className={styles.kpi}>
          <div className={styles.kpiV}>S/ {stats.avg.toLocaleString()}</div>
          <div className={styles.kpiL}>PRECIO MEDIO</div>
        </div>
        <div className={`${styles.kpi} ${styles.kpiUp}`}>
          <div className={styles.kpiV}>{stats.maxScore.toFixed(2)}</div>
          <div className={styles.kpiL}>SCORE MÁX</div>
        </div>
        <div className={styles.kpi}>
          <div className={styles.kpiV}>{stats.dists}</div>
          <div className={styles.kpiL}>DISTRITOS</div>
        </div>
      </div>
      {error && (
        <div className={styles.errBadge}>⚠ Sin conexión al servidor</div>
      )}
    </header>
  );
}
