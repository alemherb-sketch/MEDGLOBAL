// Ruta relativa (mismo origen) en produccion: el backend (FastAPI) sirve el
// frontend el mismo, tanto en el VPS (dominio propio) como en el .exe de
// escritorio (127.0.0.1:8000) -- una URL absoluta fija rompe el .exe, que
// nunca comparte origen con api.medglobal.erpgest.com.pe.
export const API_URL = import.meta.env.VITE_API_URL || (import.meta.env.PROD
  ? ''
  : 'http://localhost:8000');
