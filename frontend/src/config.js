// En la web del VPS el frontend vive en medglobal.erpgestapp.com y el API en
// api.medglobal.erpgestapp.com (origen distinto). Una ruta relativa rompe las
// llamadas y el dashboard queda en ceros aunque la data exista.
//
// En la app de ESCRITORIO (ventana nativa o 127.0.0.1) el frontend y el API
// salen del mismo motor local: las rutas DEBEN ser relativas. Si una build
// del .exe embebiera por error la URL del VPS, el login falla con
// "Failed to fetch" (CORS / red) aunque la clave sea correcta.
//
// Por eso primero se mira el hostname en runtime, y solo si no es local se
// usa VITE_API_URL o el fallback de produccion.
//
// VITE_API_URL='' al compilar sigue siendo valido; con `||` la cadena vacia
// es falsy y caia al fallback de produccion — la comparacion es contra
// undefined, no un `||`.

function _esOrigenLocal() {
  if (typeof window === 'undefined') return false;
  const h = window.location.hostname;
  return h === '127.0.0.1' || h === 'localhost' || h === '';
}

const desdeEntorno = import.meta.env.VITE_API_URL;

function _resolverApiUrl() {
  // Escritorio / dev local: siempre relativo al origen actual.
  if (_esOrigenLocal()) return '';

  if (typeof desdeEntorno === 'string') return desdeEntorno;

  return import.meta.env.PROD
    ? 'https://api.medglobal.erpgestapp.com'
    : 'http://localhost:8000';
}

export const API_URL = _resolverApiUrl();
