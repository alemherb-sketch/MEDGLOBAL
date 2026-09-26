/** Fechas de atencion.

El backend guarda DateTime UTC sin tzinfo. FastAPI las serializa como
`2026-09-26T04:28:00` (sin Z). `new Date` eso lo toma como hora local: en
Peru (UTC-5) una atencion de las 23:28 de ayer aparece como el dia siguiente
con una hora que todavia no llega.
*/

function tieneZona(texto) {
  return /[zZ]|[+-]\d{2}:?\d{2}$/.test(texto);
}

export function parseFechaUtc(valor) {
  if (!valor) return null;
  if (valor instanceof Date) {
    return Number.isNaN(valor.getTime()) ? null : valor;
  }
  const texto = String(valor).trim();
  if (!texto) return null;
  const normalizado = texto.includes('T') ? texto : texto.replace(' ', 'T');
  const conZona = tieneZona(normalizado) ? normalizado : `${normalizado}Z`;
  const fecha = new Date(conZona);
  return Number.isNaN(fecha.getTime()) ? null : fecha;
}

export function fechaLocalYmd(valor) {
  const fecha = parseFechaUtc(valor) || new Date();
  const y = fecha.getFullYear();
  const m = String(fecha.getMonth() + 1).padStart(2, '0');
  const d = String(fecha.getDate()).padStart(2, '0');
  return `${y}-${m}-${d}`;
}

export function fechaLocalTexto(valor) {
  const fecha = parseFechaUtc(valor);
  return fecha ? fecha.toLocaleDateString() : '—';
}

export function fechaLocalHora(valor) {
  const fecha = parseFechaUtc(valor);
  return fecha ? fecha.toLocaleTimeString().substring(0, 5) : '';
}

export function localYmdHoraAIso(ymd, hora = '00:00') {
  const [y, m, day] = String(ymd || '').split('-').map(Number);
  const [hh, mm] = String(hora || '00:00').split(':').map(Number);
  return new Date(y, m - 1, day, hh || 0, mm || 0, 0).toISOString();
}
