import { useMemo, useRef, useEffect } from "react";
import { computeScore, computeBounds } from "../lib/scoring";
import styles from "./InsightsPanel.module.css";

function scoreHex(s) {
  if (s>=.68) return "#FF8C42";
  if (s>=.52) return "#2dd4bf";
  if (s>=.38) return "#8b7cf8";
  return "#e63329";
}
function segStyle(seg) {
  if (seg==="Premium") return {bg:"rgba(255,140,66,.15)",color:"#FF8C42"};
  if (seg==="Medio")   return {bg:"rgba(45,212,191,.15)",color:"#2dd4bf"};
  return                      {bg:"rgba(230,51,41,.15)", color:"#e63329"};
}

function ScatterCanvas({ data }) {
  const ref = useRef(null);
  useEffect(()=>{
    if(!ref.current||!data.length) return;
    const c=ref.current;
    const W=c.width=c.offsetWidth*2, H=c.height=160;
    const ctx=c.getContext("2d");
    ctx.clearRect(0,0,W,H);
    ctx.fillStyle="#0f1b2d"; ctx.fillRect(0,0,W,H);
    ctx.strokeStyle="rgba(255,255,255,0.04)"; ctx.lineWidth=1;
    for(let x=0;x<W;x+=W/5){ctx.beginPath();ctx.moveTo(x,0);ctx.lineTo(x,H);ctx.stroke();}
    for(let y=0;y<H;y+=H/4){ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(W,y);ctx.stroke();}
    const xs=data.map(p=>p.area_m2||0),ys=data.map(p=>p.precio_pen||0);
    const xmn=Math.min(...xs),xmx=Math.max(...xs),ymn=Math.min(...ys),ymx=Math.max(...ys);
    data.forEach(p=>{
      const x=((p.area_m2-xmn)/(xmx-xmn||1))*(W-20)+10;
      const y=H-((p.precio_pen-ymn)/(ymx-ymn||1))*(H-16)-8;
      ctx.beginPath(); ctx.arc(x,y,4,0,Math.PI*2);
      ctx.fillStyle=scoreHex(p.score)+"88"; ctx.fill();
    });
    ctx.font="18px IBM Plex Mono"; ctx.fillStyle="#3a4a5c";
    ctx.fillText("m²",W-38,H-5); ctx.fillText("S/",4,18);
  },[data]);
  return <canvas ref={ref} className={styles.scatterCanvas}/>;
}

const CAPAS = [
  {v:"score",l:"Score"},
  {v:"precio",l:"Precio"},
  {v:"seguridad",l:"Seguridad"},
  {v:"transporte",l:"Transporte"},
  {v:"servicios",l:"Servicios"},
];

export default function InsightsPanel({ props, weights, capa, onCapa }) {
  const bounds = useMemo(()=>computeBounds(props),[props]);
  const enriched = useMemo(()=>
    props.map(p=>({...p,score:computeScore(p,weights,bounds)}))
  ,[props,weights,bounds]);

  const distStats = useMemo(()=>{
    const m={};
    enriched.forEach(p=>{
      if(!m[p.distrito]) m[p.distrito]={name:p.distrito,scores:[],precios:[],n:0};
      m[p.distrito].scores.push(p.score);
      m[p.distrito].precios.push(p.precio_pen||0);
      m[p.distrito].n++;
    });
    return Object.values(m).map(d=>({
      name:d.name,
      score:d.scores.reduce((a,b)=>a+b,0)/d.scores.length,
      avg:Math.round(d.precios.reduce((a,b)=>a+b,0)/d.precios.length),
      n:d.n,
    })).sort((a,b)=>b.score-a.score);
  },[enriched]);

  const top5=distStats.slice(0,5);
  const maxScore=top5[0]?.score||1;
  const total=props.length;
  const avgPrecio=total?Math.round(props.reduce((a,p)=>a+(p.precio_pen||0),0)/total):0;
  const topZona=distStats[0];
  const bestPm2=[...props].filter(p=>p.area_m2>0&&p.precio_pen>0).sort((a,b)=>(a.precio_pen/a.area_m2)-(b.precio_pen/b.area_m2))[0];
  const segCounts=useMemo(()=>{
    const m={Premium:0,Medio:0,Económico:0};
    props.forEach(p=>{if(p.tipo_vivienda&&m[p.tipo_vivienda]!==undefined)m[p.tipo_vivienda]++;});
    return m;
  },[props]);

  // Table sorted by score
  const tableData=useMemo(()=>
    [...enriched].sort((a,b)=>b.score-a.score).slice(0,50)
  ,[enriched]);

  return (
    <div className={styles.panel}>
      {/* ── Section 1: KPIs ── */}
      <div className={styles.sectionHeader}>
        <span>MARKET INTELLIGENCE</span>
        <div className={styles.liveDot}/>
      </div>

      <div className={styles.kpiGrid}>
        <div className={styles.ic}>
          <div className={styles.icLbl}>PROPIEDADES</div>
          <div className={`${styles.icVal} ${styles.orange}`}>{total.toLocaleString()}</div>
          <div className={styles.icSub}>en selección</div>
        </div>
        <div className={styles.ic}>
          <div className={styles.icLbl}>PRECIO MEDIO</div>
          <div className={styles.icVal}>S/ {avgPrecio.toLocaleString()}</div>
          <div className={styles.icSub}>mensual</div>
        </div>
      </div>

      {topZona && (
        <div className={`${styles.ic} ${styles.icFull}`}>
          <div className={styles.icLbl}>ZONA ÓPTIMA</div>
          <div className={`${styles.icVal} ${styles.orange}`}>{topZona.name}</div>
          <div className={styles.icSub}>score: {topZona.score.toFixed(3)} · {topZona.n} propiedades</div>
        </div>
      )}
      {bestPm2 && (
        <div className={`${styles.ic} ${styles.icFull}`}>
          <div className={styles.icLbl}>MEJOR PRECIO / m²</div>
          <div className={styles.icVal}>{bestPm2.distrito}</div>
          <div className={styles.icSub}>S/ {Math.round(bestPm2.precio_pen/bestPm2.area_m2)}/m² · {bestPm2.area_m2}m²</div>
        </div>
      )}

      {/* ── Section 2: Segmentos + Ranking ── */}
      <div className={styles.twoCol}>
        <div className={styles.ic}>
          <div className={styles.icLbl}>SEGMENTOS</div>
          <div className={styles.segRow}>
            {[["Premium","#FF8C42"],["Medio","#2dd4bf"],["Económico","#e63329"]].map(([s,c])=>(
              <div key={s} className={styles.segItem}>
                <div className={styles.segBar} style={{background:c,height:`${Math.max(4,(segCounts[s]/total*40)||0)}px`}}/>
                <div className={styles.segN} style={{color:c}}>{segCounts[s]}</div>
                <div className={styles.segLbl}>{s}</div>
              </div>
            ))}
          </div>
        </div>
        <div className={styles.ic}>
          <div className={styles.icLbl}>PRECIO vs ÁREA</div>
          <ScatterCanvas data={enriched.slice(0,60)}/>
        </div>
      </div>

      <div className={`${styles.ic} ${styles.icFull}`}>
        <div className={styles.icLbl}>RANKING DISTRITOS</div>
        {top5.map((d,i)=>(
          <div key={d.name} className={styles.rankItem}>
            <span className={styles.rankN}>{i+1}</span>
            <span className={styles.rankName}>{d.name}</span>
            <div className={styles.rankBarWrap}>
              <div className={styles.rankBarFill} style={{width:`${(d.score/maxScore*100).toFixed(0)}%`}}/>
            </div>
            <span className={styles.rankVal} style={{color:scoreHex(d.score)}}>{d.score.toFixed(2)}</span>
          </div>
        ))}
      </div>

      {/* ── Section 3: Capa visual controls ── */}
      <div className={styles.sectionHeader} style={{marginTop:4}}>
        <span>CAPA VISUAL</span>
      </div>
      <div className={`${styles.ic} ${styles.icFull}`}>
        <div className={styles.capaRow}>
          {CAPAS.map(({v,l})=>(
            <button key={v}
              className={`${styles.capaBtn} ${capa===v?styles.capaBtnOn:""}`}
              onClick={()=>onCapa(v)}>
              {l}
            </button>
          ))}
        </div>
      </div>

      {/* ── Section 4: Property table ── */}
      <div className={styles.sectionHeader} style={{marginTop:4}}>
        <span>PROPIEDADES · ORDENADAS POR SCORE</span>
        <span className={styles.tableCount}>{tableData.length} resultados</span>
      </div>
      <div className={styles.tableWrap}>
        <table className={styles.table}>
          <thead>
            <tr>
              <th>Score</th>
              <th>Distrito</th>
              <th>Precio</th>
              <th>m²</th>
              <th>Dorm</th>
              <th>Segmento</th>
              <th>Fuente</th>
            </tr>
          </thead>
          <tbody>
            {tableData.map((p,i)=>{
              const col=scoreHex(p.score);
              const ss=segStyle(p.tipo_vivienda);
              return (
                <tr key={p.prop_id||i}
                  className={styles.tableRow}
                  onClick={()=>p.url&&window.open(p.url,"_blank")}>
                  <td>
                    <div className={styles.scoreCell} style={{color:col}}>
                      <div className={styles.scoreDot} style={{background:col}}/>
                      {p.score.toFixed(3)}
                    </div>
                  </td>
                  <td className={styles.tdDist}>{p.distrito}</td>
                  <td className={styles.tdMono}>S/ {(p.precio_pen||0).toLocaleString()}</td>
                  <td className={styles.tdMono}>{p.area_m2||"—"}</td>
                  <td className={styles.tdMono}>{p.num_dorm||"—"}</td>
                  <td>
                    {p.tipo_vivienda && (
                      <span className={styles.badge} style={{background:ss.bg,color:ss.color}}>
                        {p.tipo_vivienda}
                      </span>
                    )}
                  </td>
                  <td className={styles.tdFuente}>{p.fuente}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
