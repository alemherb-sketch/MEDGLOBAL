/** Constantes y utilidades compartidas de Botiquín / Inspección */
export const TIPOS_EQUIPO_EMERGENCIA = [
  'Botiquín de área de trabajo',
  'Botiquín vehículo liviano',
  'Botiquín polvorín de accesorios',
  'Botiquín polvorín explosivos',
  'Estacion de emergencia',
  'Refugio minero',
];

export const AREAS = ['Mina', 'Planta'];

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
  menu: (base) => ({ ...base, zIndex: 50, background: 'var(--input-bg, #1e293b)' }),
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

export const emptyBotiquin = {
  id: null,
  codigo: '',
  fecha_creacion: new Date(),
  tipo_botiquin_id: '',
  tipo_equipo: TIPOS_EQUIPO_EMERGENCIA[0],
  area: AREAS[0],
  empresa_id: '',
  ubicacion: '',
  mapa_url: '',
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
