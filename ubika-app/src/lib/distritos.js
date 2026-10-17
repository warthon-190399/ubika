export const NOMBRE = {
  "miraflores": "Miraflores", "san isidro": "San Isidro", "surco": "Santiago de Surco", "barranco": "Barranco",
  "san borja": "San Borja", "la molina": "La Molina", "lima cercado": "Cercado de Lima", "jesus maria": "Jesús María",
  "lince": "Lince", "magdalena": "Magdalena del Mar", "pueblo libre": "Pueblo Libre", "san miguel": "San Miguel",
  "surquillo": "Surquillo", "chorrillos": "Chorrillos", "los olivos": "Los Olivos", "smp": "San Martín de Porres",
  "la victoria": "La Victoria", "brena": "Breña", "rimac": "Rímac", "san luis": "San Luis", "ate": "Ate",
  "sjl": "San Juan de Lurigancho", "sjm": "San Juan de Miraflores", "callao": "Callao", "comas": "Comas",
  "independencia": "Independencia", "santa anita": "Santa Anita", "el agustino": "El Agustino",
  "vmt": "Villa María del Triunfo", "ves": "Villa El Salvador",
};
export const nombre = d => NOMBRE[d] || (d ? d.replace(/\b\w/g, c => c.toUpperCase()) : "—");

/** Centro aproximado de cada distrito, para rotular el mapa. */
export const CENTROS = {
  "miraflores": [-12.1211, -77.0297], "san isidro": [-12.0970, -77.0365], "surco": [-12.1420, -76.9930],
  "barranco": [-12.1490, -77.0210], "san borja": [-12.1050, -76.9990], "la molina": [-12.0790, -76.9450],
  "lima cercado": [-12.0500, -77.0400], "jesus maria": [-12.0760, -77.0480], "lince": [-12.0860, -77.0350],
  "magdalena": [-12.0930, -77.0700], "pueblo libre": [-12.0760, -77.0640], "san miguel": [-12.0800, -77.0900],
  "surquillo": [-12.1130, -77.0200], "chorrillos": [-12.1720, -77.0150], "los olivos": [-11.9720, -77.0700],
  "smp": [-12.0050, -77.0820], "la victoria": [-12.0720, -77.0180], "brena": [-12.0600, -77.0520],
  "rimac": [-12.0300, -77.0300], "san luis": [-12.0770, -76.9970], "ate": [-12.0350, -76.9300],
  "sjl": [-11.9850, -77.0000], "sjm": [-12.1560, -76.9700], "callao": [-12.0560, -77.1200],
  "comas": [-11.9400, -77.0500], "independencia": [-11.9950, -77.0550], "santa anita": [-12.0450, -76.9700],
  "el agustino": [-12.0450, -76.9950], "vmt": [-12.1650, -76.9450], "ves": [-12.2100, -76.9400],
  "bellavista": [-12.0600, -77.1050], "la perla": [-12.0700, -77.1150], "ventanilla": [-11.8750, -77.1250],
  "puente piedra": [-11.8650, -77.0750], "carabayllo": [-11.8500, -77.0350], "lurigancho": [-11.9800, -76.8700],
};
