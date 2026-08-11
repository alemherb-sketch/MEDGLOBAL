import { useState, useEffect, useMemo, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import Select from 'react-select';
import DatePicker from 'react-datepicker';
import 'react-datepicker/dist/react-datepicker.css';
import {
  Search, Plus, Trash2, Edit2, X, Filter, Package, Save, Layers, Eye, MapPin, ExternalLink, ClipboardCheck
} from 'lucide-react';
import { apiFetch, apiJson } from '../api';
import {
  TIPOS_EQUIPO_EMERGENCIA,
  AREAS,
  EQUIPOS,
  selectStyles,
  emptyBotiquin,
  emptyTipo,
  labelMedicamento,
  estadoBadgeStyle,
  resumenVehiculo,
} from './botiquinShared';

const Botiquin = () => {
  const navigate = useNavigate();
  const [tab, setTab] = useState('botiquines'); // tipos | botiquines
  const [botiquines, setBotiquines] = useState([]);
  const [tiposBotiquin, setTiposBotiquin] = useState([]);
  const [empresas, setEmpresas] = useState([]);
  const [medicamentos, setMedicamentos] = useState([]);

  const [filters, setFilters] = useState({
    search: '',
    tipo_equipo: '',
    area: '',
    empresa_id: '',
    equipo: '',
    estado: '',
  });
  const [tipoSearch, setTipoSearch] = useState('');

  const [modalBotiquin, setModalBotiquin] = useState(false);
  const [formBotiquin, setFormBotiquin] = useState(emptyBotiquin);
  const [viewBotiquin, setViewBotiquin] = useState(null);

  const [modalTipo, setModalTipo] = useState(false);
  const [formTipo, setFormTipo] = useState(emptyTipo);
  const [insumoTipoSelect, setInsumoTipoSelect] = useState(null);
  const [insumoTipoCantidad, setInsumoTipoCantidad] = useState(1);

  const empresaOptions = useMemo(
    () => empresas.map(e => ({ value: String(e.id), label: `${e.nombre}${e.ruc ? ` (${e.ruc})` : ''}` })),
    [empresas]
  );

  const tipoBotiquinOptions = useMemo(
    () => tiposBotiquin.map(t => ({
      value: String(t.id),
      label: `${t.codigo ? t.codigo + ' · ' : ''}${t.nombre} (${(t.insumos || []).length} insumos)`,
    })),
    [tiposBotiquin]
  );

  const insumoOptions = useMemo(() => {
    const list = medicamentos.filter(m => {
      const t = (m.tipo || '').toUpperCase();
      return t === 'INSUMO' || t === 'MEDICAMENTO' || t === 'OTROS' || !t;
    });
    list.sort((a, b) => {
      const ai = (a.tipo || '').toUpperCase() === 'INSUMO' ? 0 : 1;
      const bi = (b.tipo || '').toUpperCase() === 'INSUMO' ? 0 : 1;
      if (ai !== bi) return ai - bi;
      return (a.nombre || '').localeCompare(b.nombre || '');
    });
    return list.map(m => ({
      value: String(m.id),
      label: labelMedicamento(m),
    }));
  }, [medicamentos]);

  const loadCatalogos = () => {
    apiJson('/empresas/').then(setEmpresas).catch(() => setEmpresas([]));
    apiJson('/medicamentos/').then(setMedicamentos).catch(() => setMedicamentos([]));
  };

  const loadTipos = useCallback(() => {
    const params = new URLSearchParams();
    if (tipoSearch) params.append('search', tipoSearch);
    const q = params.toString();
    apiJson(`/tipos_botiquin/${q ? `?${q}` : ''}`)
      .then(setTiposBotiquin)
      .catch(() => setTiposBotiquin([]));
  }, [tipoSearch]);

  const loadBotiquines = () => {
    const params = new URLSearchParams();
    Object.entries(filters).forEach(([k, v]) => {
      if (v) params.append(k, v);
    });
    const q = params.toString();
    apiJson(`/botiquines/${q ? `?${q}` : ''}`)
      .then(setBotiquines)
      .catch(() => setBotiquines([]));
  };

  useEffect(() => {
    loadCatalogos();
    loadTipos();
  }, []);

  useEffect(() => {
    if (tab === 'tipos') loadTipos();
    if (tab === 'botiquines') loadBotiquines();
  }, [tab, filters, loadTipos]);

  const mapInsumosFromApi = (list) =>
    (list || []).map(p => ({
      medicamento_id: String(p.medicamento_id),
      cantidad: p.cantidad || 1,
      label: p.medicamento ? labelMedicamento(p.medicamento) : String(p.medicamento_id),
    }));

  const openNewTipo = () => {
    setFormTipo({ ...emptyTipo, insumos: [] });
    setInsumoTipoSelect(null);
    setInsumoTipoCantidad(1);
    setModalTipo(true);
  };

  const openEditTipo = (t) => {
    setFormTipo({
      id: t.id,
      codigo: t.codigo || '',
      nombre: t.nombre || '',
      insumos: mapInsumosFromApi(t.insumos),
    });
    setInsumoTipoSelect(null);
    setInsumoTipoCantidad(1);
    setModalTipo(true);
  };

  const addInsumoTipoLinea = () => {
    if (!insumoTipoSelect) return;
    const cantidad = Math.max(1, parseInt(insumoTipoCantidad, 10) || 1);
    setFormTipo(prev => {
      const existing = prev.insumos.find(i => String(i.medicamento_id) === String(insumoTipoSelect.value));
      if (existing) {
        return {
          ...prev,
          insumos: prev.insumos.map(i =>
            String(i.medicamento_id) === String(insumoTipoSelect.value)
              ? { ...i, cantidad: i.cantidad + cantidad }
              : i
          ),
        };
      }
      return {
        ...prev,
        insumos: [
          ...prev.insumos,
          { medicamento_id: insumoTipoSelect.value, cantidad, label: insumoTipoSelect.label },
        ],
      };
    });
    setInsumoTipoSelect(null);
    setInsumoTipoCantidad(1);
  };

  const removeInsumoTipoLinea = (medicamento_id) => {
    setFormTipo(prev => ({
      ...prev,
      insumos: prev.insumos.filter(i => String(i.medicamento_id) !== String(medicamento_id)),
    }));
  };

  const saveTipo = (e) => {
    e.preventDefault();
    if (!(formTipo.nombre || '').trim()) {
      alert('Ingrese el nombre del tipo de botiquín');
      return;
    }
    const isEdit = formTipo.id != null;
    const url = isEdit ? `/tipos_botiquin/${formTipo.id}` : '/tipos_botiquin/';
    const method = isEdit ? 'PUT' : 'POST';
    const data = {
      codigo: (formTipo.codigo || '').trim() || null,
      nombre: formTipo.nombre.trim(),
      insumos: (formTipo.insumos || []).map(p => ({
        medicamento_id: p.medicamento_id,
        cantidad: p.cantidad,
      })),
    };
    apiFetch(url, { method, body: JSON.stringify(data) })
      .then(async res => {
        if (!res.ok) throw new Error(await res.text());
        setModalTipo(false);
        loadTipos();
      })
      .catch(err => alert('Error al guardar: ' + err.message));
  };

  const deleteTipo = (id) => {
    if (!window.confirm('¿Eliminar este tipo de botiquín?')) return;
    apiFetch(`/tipos_botiquin/${id}`, { method: 'DELETE' })
      .then(async res => {
        if (!res.ok) throw new Error(await res.text());
        loadTipos();
      })
      .catch(err => alert('Error al eliminar: ' + err.message));
  };

  const openNewBotiquin = () => {
    setFormBotiquin({ ...emptyBotiquin, fecha_creacion: new Date() });
    setModalBotiquin(true);
  };

  const openEditBotiquin = (b) => {
    setFormBotiquin({
      id: b.id,
      codigo: b.codigo || '',
      fecha_creacion: b.fecha_creacion ? new Date(b.fecha_creacion) : (b.created_at ? new Date(b.created_at) : new Date()),
      tipo_botiquin_id: b.tipo_botiquin_id ? String(b.tipo_botiquin_id) : '',
      tipo_equipo: b.tipo_equipo || TIPOS_EQUIPO_EMERGENCIA[0],
      area: b.area || AREAS[0],
      empresa_id: b.empresa_id ? String(b.empresa_id) : '',
      ubicacion: b.ubicacion || '',
      mapa_url: b.mapa_url || '',
      marca: b.marca || '',
      modelo: b.modelo || '',
      serie: b.serie || '',
      placa: b.placa || '',
      equipo: b.equipo || EQUIPOS[0],
      estado: b.estado || 'ACTIVO',
    });
    setModalBotiquin(true);
  };

  const saveBotiquin = (e) => {
    e.preventDefault();
    if (!formBotiquin.tipo_botiquin_id) {
      alert('Seleccione un tipo de botiquín');
      return;
    }
    const isEdit = formBotiquin.id != null;
    const url = isEdit ? `/botiquines/${formBotiquin.id}` : '/botiquines/';
    const method = isEdit ? 'PUT' : 'POST';
    const marca = (formBotiquin.marca || '').trim() || null;
    const modelo = (formBotiquin.modelo || '').trim() || null;
    const serie = (formBotiquin.serie || '').trim() || null;
    const placa = (formBotiquin.placa || '').trim() || null;
    const data = {
      codigo: (formBotiquin.codigo || '').trim() || null,
      tipo_botiquin_id: formBotiquin.tipo_botiquin_id || null,
      tipo_equipo: formBotiquin.tipo_equipo,
      area: formBotiquin.area,
      empresa_id: formBotiquin.empresa_id || null,
      ubicacion: formBotiquin.ubicacion || null,
      mapa_url: (formBotiquin.mapa_url || '').trim() || null,
      marca,
      modelo,
      serie,
      placa,
      vehiculo: resumenVehiculo({ marca, modelo, serie, placa }) || null,
      equipo: formBotiquin.equipo,
      estado: formBotiquin.estado || 'ACTIVO',
      fecha_creacion: formBotiquin.fecha_creacion
        ? new Date(formBotiquin.fecha_creacion).toISOString()
        : new Date().toISOString(),
    };

    apiFetch(url, { method, body: JSON.stringify(data) })
      .then(async res => {
        if (!res.ok) throw new Error(await res.text());
        setModalBotiquin(false);
        loadBotiquines();
        loadTipos();
      })
      .catch(err => alert('Error al guardar: ' + err.message));
  };

  const deleteBotiquin = (id) => {
    if (!window.confirm('¿Eliminar este botiquín?')) return;
    apiFetch(`/botiquines/${id}`, { method: 'DELETE' })
      .then(() => loadBotiquines());
  };

  return (
    <div>
      <div className="flex justify-between items-center mb-4" style={{ flexWrap: 'wrap', gap: 12 }}>
        <div>
          <h1 style={{ margin: 0 }}>Botiquín</h1>
          <p style={{ margin: '4px 0 0', color: 'var(--text-muted)' }}>
            Tipos de botiquín y registro de equipos
          </p>
        </div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <button type="button" className="btn btn-secondary" onClick={openNewTipo}>
            <Layers size={18} /> Nuevo tipo
          </button>
          <button type="button" className="btn btn-primary" onClick={openNewBotiquin}>
            <Plus size={18} /> Nuevo botiquín
          </button>
        </div>
      </div>

      <div className="flex gap-2 mb-4" style={{ flexWrap: 'wrap' }}>
        {[
          { id: 'tipos', label: 'Tipos de botiquín', icon: Layers },
          { id: 'botiquines', label: 'Botiquines', icon: Package },
        ].map(t => (
          <button
            key={t.id}
            type="button"
            className={`btn ${tab === t.id ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setTab(t.id)}
          >
            <t.icon size={16} style={{ marginRight: 6 }} />
            {t.label}
          </button>
        ))}
      </div>

      {tab === 'tipos' && (
        <div className="glass-panel mb-4" style={{ padding: 16 }}>
          <div className="form-group" style={{ margin: 0, maxWidth: 360 }}>
            <label className="form-label">Buscar tipo</label>
            <div style={{ position: 'relative' }}>
              <Search size={16} style={{ position: 'absolute', left: 10, top: 12, opacity: 0.5 }} />
              <input
                className="form-control"
                style={{ paddingLeft: 32 }}
                placeholder="Código o nombre..."
                value={tipoSearch}
                onChange={e => setTipoSearch(e.target.value)}
              />
            </div>
          </div>
        </div>
      )}

      {tab === 'botiquines' && (
        <div className="glass-panel mb-4" style={{ padding: 16 }}>
          <div className="flex items-center mb-3" style={{ gap: 8 }}>
            <Filter size={18} />
            <strong>Filtros avanzados</strong>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: 12 }}>
            <div className="form-group" style={{ margin: 0 }}>
              <label className="form-label">Buscar</label>
              <div style={{ position: 'relative' }}>
                <Search size={16} style={{ position: 'absolute', left: 10, top: 12, opacity: 0.5 }} />
                <input
                  className="form-control"
                  style={{ paddingLeft: 32 }}
                  placeholder="Código, tipo, empresa..."
                  value={filters.search}
                  onChange={e => setFilters({ ...filters, search: e.target.value })}
                />
              </div>
            </div>
            <div className="form-group" style={{ margin: 0 }}>
              <label className="form-label">Tipo de equipo</label>
              <select className="form-control" value={filters.tipo_equipo} onChange={e => setFilters({ ...filters, tipo_equipo: e.target.value })}>
                <option value="">Todos</option>
                {TIPOS_EQUIPO_EMERGENCIA.map(o => <option key={o} value={o}>{o}</option>)}
              </select>
            </div>
            <div className="form-group" style={{ margin: 0 }}>
              <label className="form-label">Área</label>
              <select className="form-control" value={filters.area} onChange={e => setFilters({ ...filters, area: e.target.value })}>
                <option value="">Todas</option>
                {AREAS.map(o => <option key={o} value={o}>{o}</option>)}
              </select>
            </div>
            <div className="form-group" style={{ margin: 0 }}>
              <label className="form-label">Empresa</label>
              <Select
                styles={selectStyles}
                options={empresaOptions}
                isClearable
                placeholder="Buscar empresa..."
                value={empresaOptions.find(o => o.value === filters.empresa_id) || null}
                onChange={opt => setFilters({ ...filters, empresa_id: opt ? opt.value : '' })}
                noOptionsMessage={() => 'Sin resultados'}
              />
            </div>
            <div className="form-group" style={{ margin: 0 }}>
              <label className="form-label">Equipo</label>
              <select className="form-control" value={filters.equipo} onChange={e => setFilters({ ...filters, equipo: e.target.value })}>
                <option value="">Todos</option>
                {EQUIPOS.map(o => <option key={o} value={o}>{o}</option>)}
              </select>
            </div>
            <div className="form-group" style={{ margin: 0 }}>
              <label className="form-label">Estado</label>
              <select className="form-control" value={filters.estado} onChange={e => setFilters({ ...filters, estado: e.target.value })}>
                <option value="">Todos</option>
                <option value="ACTIVO">Activo</option>
                <option value="INACTIVO">Inactivo</option>
              </select>
            </div>
          </div>
        </div>
      )}

      {tab === 'tipos' && (
        <div className="glass-panel" style={{ overflowX: 'auto' }}>
          <table className="table">
            <thead>
              <tr>
                <th>Código</th>
                <th>Nombre</th>
                <th>Insumos</th>
                <th style={{ width: 120 }}>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {tiposBotiquin.length === 0 && (
                <tr><td colSpan={4} style={{ textAlign: 'center', opacity: 0.7 }}>Sin tipos de botiquín. Cree uno para usarlo al registrar botiquines.</td></tr>
              )}
              {tiposBotiquin.map(t => (
                <tr key={t.id}>
                  <td>{t.codigo || '—'}</td>
                  <td>{t.nombre}</td>
                  <td>
                    {(t.insumos || []).length
                      ? t.insumos.map(i =>
                          `${i.medicamento?.nombre || i.medicamento_id} (x${i.cantidad})`
                        ).join(', ')
                      : '—'}
                  </td>
                  <td>
                    <div style={{ display: 'inline-flex', gap: 6 }}>
                      <button type="button" className="btn-icon" title="Editar" onClick={() => openEditTipo(t)}>
                        <Edit2 size={16} />
                      </button>
                      <button type="button" className="btn-icon btn-icon-danger" title="Eliminar" onClick={() => deleteTipo(t.id)}>
                        <Trash2 size={16} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tab === 'botiquines' && (
        <div className="glass-panel" style={{ overflowX: 'auto' }}>
          <table className="table">
            <thead>
              <tr>
                <th>Código</th>
                <th>Fecha</th>
                <th>Empresa</th>
                <th>Vehículo</th>
                <th>Ubicación</th>
                <th>Tipo de botiquín</th>
                <th>Última inspección</th>
                <th style={{ width: 200 }}>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {botiquines.length === 0 && (
                <tr><td colSpan={8} style={{ textAlign: 'center', opacity: 0.7 }}>Sin botiquines registrados</td></tr>
              )}
              {botiquines.map(b => {
                const vehiculoLabel = b.vehiculo
                  || resumenVehiculo({
                    marca: b.marca,
                    modelo: b.modelo,
                    serie: b.serie,
                    placa: b.placa,
                  })
                  || '—';
                return (
                  <tr key={b.id}>
                    <td>{b.codigo || '—'}</td>
                    <td>
                      {b.fecha_creacion
                        ? new Date(b.fecha_creacion).toLocaleDateString()
                        : (b.created_at ? new Date(b.created_at).toLocaleDateString() : '—')}
                    </td>
                    <td>{b.empresa?.nombre || '—'}</td>
                    <td>{vehiculoLabel}</td>
                    <td>
                      {b.ubicacion || '—'}
                      {b.mapa_url ? (
                        <a
                          href={b.mapa_url}
                          target="_blank"
                          rel="noreferrer"
                          title="Ver en Maps"
                          style={{ marginLeft: 6, color: 'var(--primary-color, #60a5fa)' }}
                          onClick={e => e.stopPropagation()}
                        >
                          Maps
                        </a>
                      ) : null}
                    </td>
                    <td>{b.tipo_botiquin?.nombre || '—'}</td>
                    <td>
                      {b.ultima_inspeccion
                        ? new Date(b.ultima_inspeccion).toLocaleString()
                        : <span style={{ opacity: 0.55 }}>Sin inspección</span>}
                    </td>
                    <td>
                      <div style={{ display: 'inline-flex', gap: 6, flexWrap: 'wrap', alignItems: 'center' }}>
                        <button
                          type="button"
                          className="btn btn-primary btn-sm"
                          title="Inspeccionar"
                          onClick={() => navigate(`/inspeccion?botiquin_id=${encodeURIComponent(b.id)}`)}
                        >
                          <ClipboardCheck size={14} /> Inspeccionar
                        </button>
                        <button type="button" className="btn-icon" title="Ver" onClick={() => setViewBotiquin(b)}>
                          <Eye size={16} />
                        </button>
                        <button type="button" className="btn-icon" title="Editar" onClick={() => openEditBotiquin(b)}>
                          <Edit2 size={16} />
                        </button>
                        <button type="button" className="btn-icon btn-icon-danger" title="Eliminar" onClick={() => deleteBotiquin(b.id)}>
                          <Trash2 size={16} />
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {viewBotiquin && (() => {
        const activo = (viewBotiquin.estado || 'ACTIVO') === 'ACTIVO';
        const insumos = viewBotiquin.tipo_botiquin?.insumos || [];
        const fechaCreacion = viewBotiquin.fecha_creacion
          ? new Date(viewBotiquin.fecha_creacion).toLocaleDateString()
          : (viewBotiquin.created_at ? new Date(viewBotiquin.created_at).toLocaleDateString() : '—');

        const DetailField = ({ label, children, span2 = false }) => (
          <div style={{ gridColumn: span2 ? '1 / -1' : undefined, minWidth: 0 }}>
            <div style={{
              fontSize: '0.72rem',
              fontWeight: 600,
              letterSpacing: '0.06em',
              textTransform: 'uppercase',
              color: 'var(--text-muted, #94a3b8)',
              marginBottom: 6,
            }}>
              {label}
            </div>
            <div style={{
              fontSize: '0.95rem',
              fontWeight: 500,
              lineHeight: 1.4,
              color: 'var(--text-color, #e2e8f0)',
              wordBreak: 'break-word',
            }}>
              {children || '—'}
            </div>
          </div>
        );

        return (
          <div className="modal-overlay" onClick={() => setViewBotiquin(null)}>
            <div
              className="modal-content"
              style={{
                maxWidth: 720,
                maxHeight: '90vh',
                display: 'flex',
                flexDirection: 'column',
                overflow: 'hidden',
              }}
              onClick={e => e.stopPropagation()}
            >
              <div className="modal-header" style={{ flexShrink: 0 }}>
                <div style={{ minWidth: 0 }}>
                  <h3 style={{ margin: 0 }}>Detalle del botiquín</h3>
                  <p style={{
                    margin: '6px 0 0',
                    fontSize: '0.88rem',
                    color: 'var(--text-muted, #94a3b8)',
                    whiteSpace: 'nowrap',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                  }}>
                    {viewBotiquin.codigo || 'Sin código'}
                    {viewBotiquin.tipo_botiquin?.nombre ? ` · ${viewBotiquin.tipo_botiquin.nombre}` : ''}
                  </p>
                </div>
                <button className="close-btn" type="button" aria-label="Cerrar" onClick={() => setViewBotiquin(null)}>
                  <X size={24} />
                </button>
              </div>

              <div className="modal-body" style={{ flex: 1, overflowY: 'auto', minHeight: 0 }}>
                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  gap: 12,
                  flexWrap: 'wrap',
                  marginBottom: 20,
                  padding: '12px 14px',
                  borderRadius: 12,
                  background: 'rgba(15, 23, 42, 0.35)',
                  border: '1px solid var(--border-color)',
                }}>
                  <div>
                    <div style={{
                      fontSize: '0.72rem',
                      fontWeight: 600,
                      letterSpacing: '0.06em',
                      textTransform: 'uppercase',
                      color: 'var(--text-muted, #94a3b8)',
                      marginBottom: 4,
                    }}>
                      Código
                    </div>
                    <div style={{ fontSize: '1.15rem', fontWeight: 700, letterSpacing: '0.02em' }}>
                      {viewBotiquin.codigo || '—'}
                    </div>
                  </div>
                  <span style={{
                    ...estadoBadgeStyle(activo),
                    padding: '6px 14px',
                    fontWeight: 700,
                    border: activo
                      ? '1px solid rgba(16, 185, 129, 0.35)'
                      : '1px solid rgba(239, 68, 68, 0.35)',
                  }}>
                    {viewBotiquin.estado || 'ACTIVO'}
                  </span>
                </div>

                <div style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))',
                  gap: '18px 16px',
                  marginBottom: 24,
                }}>
                  <DetailField label="Fecha de creación">{fechaCreacion}</DetailField>
                  <DetailField label="Tipo de botiquín">{viewBotiquin.tipo_botiquin?.nombre || '—'}</DetailField>
                  <DetailField label="Tipo de equipo" span2>{viewBotiquin.tipo_equipo || '—'}</DetailField>
                  <DetailField label="Área">{viewBotiquin.area || '—'}</DetailField>
                  <DetailField label="Empresa">{viewBotiquin.empresa?.nombre || '—'}</DetailField>
                  <DetailField label="Ubicación">
                    {viewBotiquin.ubicacion || '—'}
                    {viewBotiquin.mapa_url && (
                      <div style={{ marginTop: 6 }}>
                        <a
                          href={viewBotiquin.mapa_url}
                          target="_blank"
                          rel="noreferrer"
                          style={{ color: 'var(--primary-color, #60a5fa)', fontSize: '0.88rem', display: 'inline-flex', alignItems: 'center', gap: 4 }}
                        >
                          <MapPin size={14} /> Ver en Maps
                        </a>
                      </div>
                    )}
                  </DetailField>
                  <DetailField label="Vehículo">
                    {viewBotiquin.vehiculo
                      || resumenVehiculo({
                        marca: viewBotiquin.marca,
                        modelo: viewBotiquin.modelo,
                        serie: viewBotiquin.serie,
                        placa: viewBotiquin.placa,
                      })
                      || '—'}
                  </DetailField>
                  <DetailField label="Marca">{viewBotiquin.marca || '—'}</DetailField>
                  <DetailField label="Modelo">{viewBotiquin.modelo || '—'}</DetailField>
                  <DetailField label="Serie">{viewBotiquin.serie || '—'}</DetailField>
                  <DetailField label="Placa">{viewBotiquin.placa || '—'}</DetailField>
                  <DetailField label="Equipo" span2>{viewBotiquin.equipo || '—'}</DetailField>
                </div>

                <div style={{ borderTop: '1px solid var(--border-color)', paddingTop: 18 }}>
                  <div style={{
                    display: 'flex',
                    alignItems: 'baseline',
                    justifyContent: 'space-between',
                    gap: 12,
                    marginBottom: 12,
                    flexWrap: 'wrap',
                  }}>
                    <h4 style={{ margin: 0, fontSize: '0.95rem', fontWeight: 600 }}>Insumos del tipo</h4>
                    <span style={{ fontSize: '0.8rem', color: 'var(--text-muted, #94a3b8)' }}>
                      {insumos.length} ítem{insumos.length === 1 ? '' : 's'}
                    </span>
                  </div>
                  {insumos.length === 0 ? (
                    <p style={{
                      margin: 0,
                      padding: '16px 14px',
                      borderRadius: 10,
                      background: 'rgba(15, 23, 42, 0.35)',
                      border: '1px dashed var(--border-color)',
                      color: 'var(--text-muted, #94a3b8)',
                      fontSize: '0.9rem',
                    }}>
                      Sin insumos definidos en el tipo de botiquín.
                    </p>
                  ) : (
                    <div style={{ border: '1px solid var(--border-color)', borderRadius: 12, overflow: 'hidden' }}>
                      <table className="table" style={{ margin: 0 }}>
                        <thead>
                          <tr>
                            <th style={{ width: '22%' }}>Código</th>
                            <th>Insumo / medicamento</th>
                            <th style={{ width: 90, textAlign: 'right' }}>Cantidad</th>
                          </tr>
                        </thead>
                        <tbody>
                          {insumos.map(i => {
                            const med = i.medicamento;
                            return (
                              <tr key={i.id || i.medicamento_id}>
                                <td style={{
                                  fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace',
                                  fontSize: '0.85rem',
                                  whiteSpace: 'nowrap',
                                }}>
                                  {med?.codigo || '—'}
                                </td>
                                <td>
                                  <div style={{ fontWeight: 500 }}>{med?.nombre || i.medicamento_id || '—'}</div>
                                  {(med?.presentacion || med?.tipo) && (
                                    <div style={{ fontSize: '0.8rem', color: 'var(--text-muted, #94a3b8)', marginTop: 2 }}>
                                      {[med.presentacion, med.tipo].filter(Boolean).join(' · ')}
                                    </div>
                                  )}
                                </td>
                                <td style={{ textAlign: 'right' }}>
                                  <span style={{
                                    display: 'inline-block',
                                    minWidth: 36,
                                    padding: '3px 10px',
                                    borderRadius: 8,
                                    fontWeight: 700,
                                    fontSize: '0.88rem',
                                    background: 'rgba(59, 130, 246, 0.15)',
                                    color: 'var(--primary-color, #60a5fa)',
                                  }}>
                                    {i.cantidad || 1}
                                  </span>
                                </td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              </div>

              <div className="modal-footer" style={{ flexShrink: 0, position: 'static' }}>
                <button type="button" className="btn btn-secondary" onClick={() => setViewBotiquin(null)}>
                  <X size={16} /> Cerrar
                </button>
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={() => {
                    const b = viewBotiquin;
                    setViewBotiquin(null);
                    openEditBotiquin(b);
                  }}
                >
                  <Edit2 size={16} /> Editar
                </button>
              </div>
            </div>
          </div>
        );
      })()}

      {modalTipo && (
        <div className="modal-overlay">
          <div className="modal-content" style={{ maxWidth: 640 }}>
            <div className="modal-header">
              <h3>{formTipo.id ? 'Editar tipo de botiquín' : 'Tipo de botiquín'}</h3>
              <button className="close-btn" type="button" onClick={() => setModalTipo(false)}><X size={24} /></button>
            </div>
            <form onSubmit={saveTipo}>
              <div className="modal-body">
                <div className="form-group">
                  <label className="form-label">Código</label>
                  <input
                    className="form-control"
                    value={formTipo.codigo}
                    onChange={e => setFormTipo({ ...formTipo, codigo: e.target.value })}
                    placeholder="Automático (TB-0001) si se deja vacío"
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">Nombre</label>
                  <input
                    className="form-control"
                    required
                    value={formTipo.nombre}
                    onChange={e => setFormTipo({ ...formTipo, nombre: e.target.value })}
                    placeholder="Ej. Botiquín área de trabajo estándar"
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">Insumos</label>
                  <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'stretch' }}>
                    <div style={{ flex: '1 1 240px', minWidth: 200 }}>
                      <Select
                        styles={selectStyles}
                        options={insumoOptions}
                        placeholder="Buscar y seleccionar medicamento..."
                        value={insumoTipoSelect}
                        onChange={setInsumoTipoSelect}
                        noOptionsMessage={() => 'Sin resultados'}
                      />
                    </div>
                    <div style={{ width: 88 }}>
                      <input
                        type="number"
                        min={1}
                        className="form-control"
                        value={insumoTipoCantidad}
                        onChange={e => setInsumoTipoCantidad(e.target.value)}
                      />
                    </div>
                    <button
                      type="button"
                      className="btn btn-primary btn-sm"
                      onClick={addInsumoTipoLinea}
                      disabled={!insumoTipoSelect}
                    >
                      <Plus size={16} /> Agregar
                    </button>
                  </div>
                  {formTipo.insumos.length > 0 ? (
                    <ul style={{ marginTop: 12, paddingLeft: 0, listStyle: 'none', display: 'flex', flexDirection: 'column', gap: 8 }}>
                      {formTipo.insumos.map(p => (
                        <li
                          key={p.medicamento_id}
                          style={{
                            display: 'flex',
                            justifyContent: 'space-between',
                            alignItems: 'center',
                            gap: 12,
                            padding: '10px 12px',
                            borderRadius: 10,
                            background: 'rgba(15, 23, 42, 0.45)',
                            border: '1px solid var(--border-color)',
                          }}
                        >
                          <span style={{ fontSize: '0.92rem', lineHeight: 1.35 }}>{p.label} × <strong>{p.cantidad}</strong></span>
                          <button
                            type="button"
                            className="btn-icon btn-icon-sm btn-icon-danger"
                            title="Quitar insumo"
                            onClick={() => removeInsumoTipoLinea(p.medicamento_id)}
                          >
                            <Trash2 size={15} />
                          </button>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p style={{ marginTop: 10, opacity: 0.6, fontSize: '0.9rem' }}>
                      Añada los medicamentos e insumos que componen este tipo.
                    </p>
                  )}
                </div>
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={() => setModalTipo(false)}>
                  <X size={16} /> Cancelar
                </button>
                <button type="submit" className="btn btn-primary">
                  <Save size={16} /> Guardar
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {modalBotiquin && (
        <div className="modal-overlay">
          <div className="modal-content" style={{ maxWidth: 640 }}>
            <div className="modal-header">
              <h3>{formBotiquin.id ? 'Editar botiquín' : 'Nuevo botiquín'}</h3>
              <button className="close-btn" type="button" onClick={() => setModalBotiquin(false)}><X size={24} /></button>
            </div>
            <form onSubmit={saveBotiquin}>
              <div className="modal-body">
                {/* 1-2: Código, Fecha creación */}
                <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
                  <div className="form-group" style={{ flex: '1 1 180px' }}>
                    <label className="form-label">Código</label>
                    <input
                      className="form-control"
                      value={formBotiquin.codigo}
                      onChange={e => setFormBotiquin({ ...formBotiquin, codigo: e.target.value })}
                      placeholder="Automático (BOT-0001) si se deja vacío"
                    />
                  </div>
                  <div className="form-group" style={{ flex: '1 1 180px' }}>
                    <label className="form-label">Fecha de creación</label>
                    <DatePicker
                      selected={formBotiquin.fecha_creacion}
                      onChange={d => setFormBotiquin({ ...formBotiquin, fecha_creacion: d || new Date() })}
                      dateFormat="dd/MM/yyyy"
                      className="form-control"
                    />
                  </div>
                </div>

                {/* 3: Empresa */}
                <div className="form-group">
                  <label className="form-label">Empresa</label>
                  <Select
                    styles={selectStyles}
                    options={empresaOptions}
                    isClearable
                    placeholder="Buscar y seleccionar empresa..."
                    value={empresaOptions.find(o => o.value === String(formBotiquin.empresa_id || '')) || null}
                    onChange={opt => setFormBotiquin({ ...formBotiquin, empresa_id: opt ? opt.value : '' })}
                    noOptionsMessage={() => 'Sin resultados'}
                  />
                </div>

                {/* 4: Vehículo (resumen) + Marca, Modelo, Serie, Placa */}
                <div className="form-group">
                  <label className="form-label">Vehículo</label>
                  <input
                    className="form-control"
                    value={resumenVehiculo(formBotiquin)}
                    readOnly
                    placeholder="Se genera con marca, modelo, serie y placa"
                    style={{ opacity: 0.9, cursor: 'default' }}
                    title="Se completa automáticamente"
                  />
                  <p style={{ margin: '6px 0 0', fontSize: '0.82rem', opacity: 0.65 }}>
                    Se genera automáticamente con marca, modelo, serie y placa.
                  </p>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))', gap: 12 }}>
                  <div className="form-group" style={{ margin: 0 }}>
                    <label className="form-label">Marca</label>
                    <input
                      className="form-control"
                      value={formBotiquin.marca}
                      onChange={e => setFormBotiquin({ ...formBotiquin, marca: e.target.value })}
                      placeholder="Marca"
                    />
                  </div>
                  <div className="form-group" style={{ margin: 0 }}>
                    <label className="form-label">Modelo</label>
                    <input
                      className="form-control"
                      value={formBotiquin.modelo}
                      onChange={e => setFormBotiquin({ ...formBotiquin, modelo: e.target.value })}
                      placeholder="Modelo"
                    />
                  </div>
                  <div className="form-group" style={{ margin: 0 }}>
                    <label className="form-label">Serie</label>
                    <input
                      className="form-control"
                      value={formBotiquin.serie}
                      onChange={e => setFormBotiquin({ ...formBotiquin, serie: e.target.value })}
                      placeholder="N° de serie"
                    />
                  </div>
                  <div className="form-group" style={{ margin: 0 }}>
                    <label className="form-label">Placa</label>
                    <input
                      className="form-control"
                      value={formBotiquin.placa}
                      onChange={e => setFormBotiquin({ ...formBotiquin, placa: e.target.value })}
                      placeholder="Placa"
                    />
                  </div>
                </div>

                {/* 5: Ubicación + Maps */}
                <div className="form-group">
                  <label className="form-label">Ubicación</label>
                  <input
                    className="form-control"
                    value={formBotiquin.ubicacion}
                    onChange={e => setFormBotiquin({ ...formBotiquin, ubicacion: e.target.value })}
                    placeholder="Descripción de la ubicación física"
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">Ubicación en Maps (enlace)</label>
                  <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'stretch' }}>
                    <input
                      className="form-control"
                      style={{ flex: '1 1 220px' }}
                      value={formBotiquin.mapa_url}
                      onChange={e => setFormBotiquin({ ...formBotiquin, mapa_url: e.target.value })}
                      placeholder="https://maps.google.com/... o pegar enlace de Maps"
                    />
                    <button
                      type="button"
                      className="btn btn-secondary btn-sm"
                      title="Abrir Google Maps para buscar y copiar el enlace"
                      onClick={() => {
                        const q = encodeURIComponent(
                          [formBotiquin.ubicacion, formBotiquin.empresa_id
                            ? (empresaOptions.find(o => o.value === String(formBotiquin.empresa_id))?.label || '')
                            : ''].filter(Boolean).join(' ') || 'Ubicación'
                        );
                        window.open(`https://www.google.com/maps/search/?api=1&query=${q}`, '_blank', 'noopener,noreferrer');
                      }}
                    >
                      <MapPin size={16} /> Buscar en Maps
                    </button>
                    {formBotiquin.mapa_url && (
                      <button
                        type="button"
                        className="btn btn-secondary btn-sm"
                        title="Abrir enlace guardado"
                        onClick={() => window.open(formBotiquin.mapa_url, '_blank', 'noopener,noreferrer')}
                      >
                        <ExternalLink size={16} /> Abrir
                      </button>
                    )}
                  </div>
                  <p style={{ margin: '8px 0 0', fontSize: '0.82rem', opacity: 0.65 }}>
                    Use «Buscar en Maps», copie el enlace de la ubicación y péguelo aquí.
                  </p>
                </div>

                {/* 6: Tipo de botiquín */}
                <div className="form-group">
                  <label className="form-label">Tipo de botiquín</label>
                  <Select
                    styles={selectStyles}
                    options={tipoBotiquinOptions}
                    placeholder="Buscar tipo de botiquín..."
                    value={tipoBotiquinOptions.find(o => o.value === String(formBotiquin.tipo_botiquin_id || '')) || null}
                    onChange={opt => setFormBotiquin({ ...formBotiquin, tipo_botiquin_id: opt ? opt.value : '' })}
                    noOptionsMessage={() => 'Sin tipos. Cree uno en la pestaña Tipos de botiquín'}
                  />
                </div>

                {/* 7: Tipo de equipo de emergencia */}
                <div className="form-group">
                  <label className="form-label">Tipo de equipo de emergencia</label>
                  <select
                    className="form-control"
                    required
                    value={formBotiquin.tipo_equipo}
                    onChange={e => setFormBotiquin({ ...formBotiquin, tipo_equipo: e.target.value })}
                  >
                    {TIPOS_EQUIPO_EMERGENCIA.map(o => <option key={o} value={o}>{o}</option>)}
                  </select>
                </div>

                {/* 8: Área */}
                <div className="form-group">
                  <label className="form-label">Área</label>
                  <select
                    className="form-control"
                    required
                    value={formBotiquin.area}
                    onChange={e => setFormBotiquin({ ...formBotiquin, area: e.target.value })}
                  >
                    {AREAS.map(o => <option key={o} value={o}>{o}</option>)}
                  </select>
                </div>

                {/* 9: Equipo */}
                <div className="form-group">
                  <label className="form-label">Equipo</label>
                  <select
                    className="form-control"
                    required
                    value={formBotiquin.equipo}
                    onChange={e => setFormBotiquin({ ...formBotiquin, equipo: e.target.value })}
                  >
                    {EQUIPOS.map(o => <option key={o} value={o}>{o}</option>)}
                  </select>
                </div>

                {/* 10: Estado */}
                <div className="form-group">
                  <label className="form-label">Estado</label>
                  <select
                    className="form-control"
                    value={formBotiquin.estado}
                    onChange={e => setFormBotiquin({ ...formBotiquin, estado: e.target.value })}
                  >
                    <option value="ACTIVO">Activo</option>
                    <option value="INACTIVO">Inactivo</option>
                  </select>
                </div>
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={() => setModalBotiquin(false)}>
                  <X size={16} /> Cancelar
                </button>
                <button type="submit" className="btn btn-primary">
                  <Save size={16} /> Guardar
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default Botiquin;
