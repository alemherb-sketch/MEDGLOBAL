// En la web del VPS el frontend vive en medglobal.erpgest.com.pe y el API en
// api.medglobal.erpgest.com.pe (origen distinto). Una ruta relativa rompe las
// llamadas y el dashboard queda en ceros aunque la data exista.
// Para el .exe de escritorio, definir VITE_API_URL='' al compilar.
export const API_URL = import.meta.env.VITE_API_URL || (import.meta.env.PROD
  ? 'https://api.medglobal.erpgest.com.pe'
  : 'http://localhost:8000');
