import Select from 'react-select';
import { Filter, Search } from 'lucide-react';
import { EQUIPOS, UBICACIONES, selectPortalProps, selectStyles } from '../pages/botiquinShared';

/** Mismos filtros avanzados del listado de Botiquín. */
export default function FiltrosAvanzadosBotiquin({
  filters,
  onChange,
  empresaOptions = [],
  tipoEquipoNombres = [],
  onEmpresaChange,
  extras = null,
  title = 'Filtros avanzados',
  headerRight = null,
  searchPlaceholder = 'Código, tipo, empresa...',
}) {
  const setCampo = (campo, valor) => onChange({ ...filters, [campo]: valor });

  return (
    <div className="glass-panel mb-4" style={{ padding: 16, overflow: 'visible' }}>
      <div className="flex items-center mb-3" style={{ gap: 8, justifyContent: 'space-between', flexWrap: 'wrap' }}>
        <div className="flex items-center" style={{ gap: 8 }}>
          <Filter size={18} />
          <strong>{title}</strong>
        </div>
        {headerRight}
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: 12 }}>
        <div className="form-group" style={{ margin: 0 }}>
          <label className="form-label">Buscar</label>
          <div style={{ position: 'relative' }}>
            <Search size={16} style={{ position: 'absolute', left: 10, top: 12, opacity: 0.5 }} />
            <input
              className="form-control"
              style={{ paddingLeft: 32 }}
              placeholder={searchPlaceholder}
              value={filters.search || ''}
              onChange={e => setCampo('search', e.target.value)}
            />
          </div>
        </div>
        <div className="form-group" style={{ margin: 0 }}>
          <label className="form-label">Tipo de equipo</label>
          <select
            className="form-control"
            value={filters.tipo_equipo || ''}
            onChange={e => setCampo('tipo_equipo', e.target.value)}
          >
            <option value="">Todos</option>
            {tipoEquipoNombres.map(o => <option key={o} value={o}>{o}</option>)}
          </select>
        </div>
        <div className="form-group" style={{ margin: 0 }}>
          <label className="form-label">Ubicación</label>
          <select
            className="form-control"
            value={filters.ubicacion || ''}
            onChange={e => setCampo('ubicacion', e.target.value)}
          >
            <option value="">Todas</option>
            {UBICACIONES.map(o => <option key={o} value={o}>{o}</option>)}
          </select>
        </div>
        <div className="form-group" style={{ margin: 0 }}>
          <label className="form-label">Área</label>
          <input
            className="form-control"
            placeholder="Filtrar por área..."
            value={filters.area || ''}
            onChange={e => setCampo('area', e.target.value)}
          />
        </div>
        <div className="form-group" style={{ margin: 0 }}>
          <label className="form-label">Empresa</label>
          <Select
            styles={selectStyles}
            {...selectPortalProps}
            options={empresaOptions}
            isClearable
            placeholder="Buscar empresa..."
            value={empresaOptions.find(o => o.value === filters.empresa_id) || null}
            onChange={opt => {
              const empresa_id = opt ? opt.value : '';
              if (onEmpresaChange) onEmpresaChange(empresa_id);
              else setCampo('empresa_id', empresa_id);
            }}
            noOptionsMessage={() => 'Sin resultados'}
          />
        </div>
        <div className="form-group" style={{ margin: 0 }}>
          <label className="form-label">Equipo</label>
          <select
            className="form-control"
            value={filters.equipo || ''}
            onChange={e => setCampo('equipo', e.target.value)}
          >
            <option value="">Todos</option>
            {EQUIPOS.map(o => <option key={o} value={o}>{o}</option>)}
          </select>
        </div>
        <div className="form-group" style={{ margin: 0 }}>
          <label className="form-label">Estado</label>
          <select
            className="form-control"
            value={filters.estado || ''}
            onChange={e => setCampo('estado', e.target.value)}
          >
            <option value="">Todos</option>
            <option value="ACTIVO">Activo</option>
            <option value="INACTIVO">Inactivo</option>
          </select>
        </div>
        {extras}
      </div>
    </div>
  );
}
