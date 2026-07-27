// En la web del VPS el frontend vive en medglobal.erpgest.com.pe y el API en
// api.medglobal.erpgest.com.pe (origen distinto). Una ruta relativa rompe las
// llamadas y el dashboard queda en ceros aunque la data exista.
//
// Para el .exe de escritorio se compila con VITE_API_URL='' (cadena vacia):
// ahi el frontend y el API los sirve el mismo proceso en 127.0.0.1:8000, asi
// que las rutas tienen que ser relativas y NO apuntar a internet.
//
// Por eso la comparacion es contra undefined y no un `||`: con `||` la cadena
// vacia es falsy y caia al fallback, quedando un instalable "offline" que en
// realidad llamaba al servidor de produccion y no funcionaba sin internet.
const desdeEntorno = import.meta.env.VITE_API_URL;

export const API_URL = typeof desdeEntorno === 'string'
  ? desdeEntorno
  : (import.meta.env.PROD
    ? 'https://api.medglobal.erpgest.com.pe'
    : 'http://localhost:8000');
