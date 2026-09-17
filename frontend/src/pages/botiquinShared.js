/** Constantes y utilidades compartidas de Botiquín / Inspección */

/** Nombres para los desplegables: solo tipos del catálogo (y extras puntuales). */
export function listarNombresTipoEquipo({ tipos = [], extras = [] } = {}) {
  const vistos = new Map();
  const agregar = (valor) => {
    const nombre = String(valor || '').trim();
    if (!nombre) return;
    const clave = nombre.toLocaleLowerCase();
    if (!vistos.has(clave)) vistos.set(clave, nombre);
  };
  tipos.forEach((item) => agregar(typeof item === 'string' ? item : item?.nombre));
  extras.forEach(agregar);
  return [...vistos.values()].sort((a, b) => a.localeCompare(b, 'es', { sensitivity: 'base' }));
}

export const AREAS = ['Mina', 'Planta'];
export const UBICACIONES = ['Mina', 'Planta'];

export const EQUIPOS = [
  'Botiquín de emergencia',
  'Polvorines',
  'Refugios mineros',
];

export const selectStyles = {
  control: (base) => ({
    ...base,
    background: 'var(--input-bg, #1e293b)',
    borderColor: 'var(--border-color, #334155)',
    minHeight: 42,
  }),
  menu: (base) => ({ ...base, zIndex: 10050, background: 'var(--input-bg, #1e293b)' }),
  menuPortal: (base) => ({ ...base, zIndex: 10050 }),
  option: (base, state) => ({
    ...base,
    background: state.isFocused ? 'rgba(59,130,246,0.25)' : 'transparent',
    color: 'var(--text-color, #e2e8f0)',
  }),
  singleValue: (base) => ({ ...base, color: 'var(--text-color, #e2e8f0)' }),
  multiValue: (base) => ({ ...base, background: 'rgba(59,130,246,0.3)' }),
  multiValueLabel: (base) => ({ ...base, color: 'var(--text-color, #e2e8f0)' }),
  multiValueRemove: (base) => ({
    ...base,
    color: '#94a3b8',
    ':hover': { background: 'rgba(239,68,68,0.35)', color: '#fff' },
  }),
  input: (base) => ({ ...base, color: 'var(--text-color, #e2e8f0)' }),
  placeholder: (base) => ({ ...base, color: '#94a3b8' }),
};

/** El glass-panel tiene overflow:hidden y recorta el menú si no sale al body. */
export const selectPortalProps = {
  menuPortalTarget: typeof document !== 'undefined' ? document.body : null,
  menuPosition: 'fixed',
};

export const emptyBotiquin = {
  id: null,
  codigo: '',
  fecha_creacion: new Date(),
  tipo_botiquin_id: '',
  tipo_equipo: '',
  area: '',
  empresa_id: '',
  ubicacion: UBICACIONES[0],
  mapa_url: '',
  vehiculo: '',
  marca: '',
  modelo: '',
  serie: '',
  placa: '',
  equipo: EQUIPOS[0],
  estado: 'ACTIVO',
};

/** Resumen automático del vehículo: Marca Modelo · Serie X · Placa Y */
export function resumenVehiculo({ marca = '', modelo = '', serie = '', placa = '' } = {}) {
  const partes = [];
  const m = (marca || '').trim();
  const mo = (modelo || '').trim();
  const s = (serie || '').trim();
  const p = (placa || '').trim();
  if (m || mo) partes.push([m, mo].filter(Boolean).join(' '));
  if (s) partes.push(`Serie ${s}`);
  if (p) partes.push(`Placa ${p}`);
  return partes.join(' · ');
}

export const emptyTipo = {
  id: null,
  codigo: '',
  nombre: '',
  insumos: [],
};

export const labelMedicamento = (m) => {
  if (!m) return '—';
  return `${m.codigo || '—'} · ${m.nombre}${m.presentacion ? ` (${m.presentacion})` : ''}${m.tipo ? ` [${m.tipo}]` : ''}`;
};

/** Sufijo numérico de un código (BS-07 → 7). */
export function codigoNumericSuffix(codigo) {
  if (!codigo) return null;
  const m = String(codigo).trim().match(/(\d+)$/);
  return m ? parseInt(m[1], 10) : null;
}

/** Mayor a menor por código: BS-10 > BS-9 > BS-07; sin número por texto DESC; vacíos al final. */
export function sortBotiquinesByCodigoDesc(list) {
  return [...(list || [])].sort((a, b) => {
    const ca = (a?.codigo || '').trim();
    const cb = (b?.codigo || '').trim();
    if (!ca && !cb) return 0;
    if (!ca) return 1;
    if (!cb) return -1;
    const na = codigoNumericSuffix(ca);
    const nb = codigoNumericSuffix(cb);
    if (na != null && nb != null && na !== nb) return nb - na;
    if (na != null && nb == null) return -1;
    if (na == null && nb != null) return 1;
    return cb.localeCompare(ca, undefined, { numeric: true, sensitivity: 'base' });
  });
}

export const estadoBadgeStyle = (activo) => ({
  display: 'inline-block',
  padding: '4px 10px',
  borderRadius: 999,
  fontSize: '0.8rem',
  fontWeight: 600,
  letterSpacing: '0.02em',
  background: activo ? 'rgba(16, 185, 129, 0.2)' : 'rgba(239, 68, 68, 0.2)',
  color: activo ? 'var(--success-color)' : 'var(--danger-color)',
});
