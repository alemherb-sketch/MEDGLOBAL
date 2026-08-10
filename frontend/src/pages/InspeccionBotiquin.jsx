import { useState, useEffect, useMemo } from 'react';
import Select from 'react-select';
import DatePicker from 'react-datepicker';
import 'react-datepicker/dist/react-datepicker.css';
import * as XLSX from 'xlsx';
import {
  Search, Plus, Trash2, X, ClipboardCheck, Download,
  Filter, History, Save
} from 'lucide-react';
import { apiFetch, apiJson } from '../api';
import {
  TIPOS_EQUIPO_EMERGENCIA,
  AREAS,
  EQUIPOS,
  selectStyles,
  labelMedicamento,
} from './botiquinShared';

const InspeccionBotiquin = () => {
  const [tab, setTab] = useState('inspecciones'); // inspecciones | reporte
  const [botiquines, setBotiquines] = useState([]);
  const [inspecciones, setInspecciones] = useState([]);
  const [empresas, setEmpresas] = useState([]);
  const [personal, setPersonal] = useState([]);
  const [medicamentos, setMedicamentos] = useState([]);

  const [filters, setFilters] = useState({
    search: '',
    empresa_id: '',
  });

  const [modalInspeccion, setModalInspeccion] = useState(false);
  const [formInspeccion, setFormInspeccion] = useState({
    botiquin_id: '',
    responsable_id: '',
    fecha: new Date(),
    observaciones: '',
    insumos: [],
  });
  const [insumoSelect, setInsumoSelect] = useState(null);
  const [insumoCantidad, setInsumoCantidad] = useState(1);
  const [cargandoInsumos, setCargandoInsumos] = useState(false);

  const [reporteFiltros, setReporteFiltros] = useState({
    empresa_id: '',
    botiquin_id: '',
    area: '',
    tipo_equipo: '',
    equipo: '',
    fecha_inicio: null,
    fecha_fin: null,
  });
  const [reporte, setReporte] = useState({
    rango_fechas: [],
    insumos: [],
    totales: { sub_total: 0, igv: 0, total: 0 },
  });
  const [loadingReporte, setLoadingReporte] = useState(false);

  const empresaOptions = useMemo(
    () => empresas.map(e => ({ value: String(e.id), label: `${e.nombre}${e.ruc ? ` (${e.ruc})` : ''}` })),
    [empresas]
  );

  const personalOptions = useMemo(
    () => personal
      .filter(p => (p.estado || 'ACTIVO') === 'ACTIVO')
      .map(p => ({
        value: String(p.id),
        label: `${p.nombre || ''} ${p.apellidos || ''}`.trim() + (p.especialidad ? ` — ${p.especialidad}` : ''),
      })),
    [personal]
  );

  const botiquinOptions = useMemo(
    () => botiquines.map(b => ({
      value: String(b.id),
      label: `${b.codigo ? b.codigo + ' · ' : ''}${b.tipo_botiquin?.nombre || b.tipo_equipo}${b.vehiculo ? ` · ${b.vehiculo}` : ''}${b.ubicacion ? ` · ${b.ubicacion}` : ''}`,
    })),
    [botiquines]
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

  const mapInsumosFromApi = (list) =>
    (list || []).map(p => ({
      medicamento_id: String(p.medicamento_id),
      cantidad: p.cantidad || 1,
      label: p.medicamento ? labelMedicamento(p.medicamento) : String(p.medicamento_id),
    }));

  const loadCatalogos = () => {
    apiJson('/empresas/').then(setEmpresas).catch(() => setEmpresas([]));
    apiJson('/personal_salud/').then(setPersonal).catch(() => setPersonal([]));
    apiJson('/medicamentos/').then(setMedicamentos).catch(() => setMedicamentos([]));
    apiJson('/botiquines/').then(setBotiquines).catch(() => setBotiquines([]));
  };

  const loadInspecciones = () => {
    const params = new URLSearchParams();
    if (filters.empresa_id) params.append('empresa_id', filters.empresa_id);
    if (filters.search) params.append('search', filters.search);
    const q = params.toString();
    apiJson(`/botiquin_inspecciones/${q ? `?${q}` : ''}`)
      .then(setInspecciones)
      .catch(() => setInspecciones([]));
  };

  useEffect(() => {
    loadCatalogos();
  }, []);

  useEffect(() => {
    if (tab === 'inspecciones') loadInspecciones();
  }, [tab, filters]);

  const cargarInsumosDeBotiquin = async (botiquinId) => {
    if (!botiquinId) {
      setFormInspeccion(prev => ({ ...prev, botiquin_id: '', insumos: [] }));
      return;
    }
    setCargandoInsumos(true);
    try {
      const insumos = await apiJson(`/botiquines/${botiquinId}/insumos`);
      setFormInspeccion(prev => ({
        ...prev,
        botiquin_id: String(botiquinId),
        insumos: mapInsumosFromApi(insumos),
      }));
    } catch (err) {
      console.error(err);
      const bot = botiquines.find(b => String(b.id) === String(botiquinId));
      const insumosTipo = bot?.tipo_botiquin?.insumos || [];
      setFormInspeccion(prev => ({
        ...prev,
        botiquin_id: String(botiquinId),
        insumos: mapInsumosFromApi(insumosTipo),
      }));
    } finally {
      setCargandoInsumos(false);
    }
  };

  const openNewInspeccion = (botiquinId = '') => {
    setFormInspeccion({
      botiquin_id: botiquinId ? String(botiquinId) : '',
      responsable_id: '',
      fecha: new Date(),
      observaciones: '',
      insumos: [],
    });
    setInsumoSelect(null);
    setInsumoCantidad(1);
    setModalInspeccion(true);
    if (botiquinId) cargarInsumosDeBotiquin(botiquinId);
  };

  const addInsumoLinea = () => {
    if (!insumoSelect) return;
    const cantidad = Math.max(1, parseInt(insumoCantidad, 10) || 1);
    setFormInspeccion(prev => {
      const existing = prev.insumos.find(i => String(i.medicamento_id) === String(insumoSelect.value));
      if (existing) {
        return {
          ...prev,
          insumos: prev.insumos.map(i =>
            String(i.medicamento_id) === String(insumoSelect.value)
              ? { ...i, cantidad: i.cantidad + cantidad }
              : i
          ),
        };
      }
      return {
        ...prev,
        insumos: [
          ...prev.insumos,
          { medicamento_id: insumoSelect.value, cantidad, label: insumoSelect.label },
        ],
      };
    });
    setInsumoSelect(null);
    setInsumoCantidad(1);
  };

  const removeInsumoLinea = (medicamento_id) => {
    setFormInspeccion(prev => ({
      ...prev,
      insumos: prev.insumos.filter(i => String(i.medicamento_id) !== String(medicamento_id)),
    }));
  };

  const saveInspeccion = (e) => {
    e.preventDefault();
    if (!formInspeccion.botiquin_id) {
      alert('Seleccione un botiquín');
      return;
    }
    if (!formInspeccion.responsable_id) {
      alert('Seleccione el responsable de la inspección');
      return;
    }
    const payload = {
      botiquin_id: formInspeccion.botiquin_id,
      responsable_id: formInspeccion.responsable_id || null,
      fecha: formInspeccion.fecha
        ? new Date(formInspeccion.fecha).toISOString()
        : new Date().toISOString(),
      observaciones: formInspeccion.observaciones || null,
      insumos: formInspeccion.insumos.map(i => ({
        medicamento_id: i.medicamento_id,
        cantidad: i.cantidad,
      })),
    };

    apiFetch('/botiquin_inspecciones/', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
      .then(async res => {
        if (!res.ok) throw new Error(await res.text());
        setModalInspeccion(false);
        setTab('inspecciones');
        loadInspecciones();
      })
      .catch(err => alert('Error al registrar inspección: ' + err.message));
  };

  const deleteInspeccion = (id) => {
    if (!window.confirm('¿Eliminar esta inspección?')) return;
    apiFetch(`/botiquin_inspecciones/${id}`, { method: 'DELETE' })
      .then(() => loadInspecciones());
  };

  const buscarReporte = async () => {
    setLoadingReporte(true);
    try {
      const params = new URLSearchParams();
      Object.entries(reporteFiltros).forEach(([k, v]) => {
        if (!v) return;
        if (k === 'fecha_inicio' || k === 'fecha_fin') {
          params.append(k, v.toISOString().split('T')[0]);
        } else {
          params.append(k, v);
        }
      });
      const data = await apiJson(`/reportes/consumo-insumos-botiquin?${params.toString()}`);
      setReporte(data);
    } catch (err) {
      console.error(err);
      alert('Error al generar reporte: ' + err.message);
    } finally {
      setLoadingReporte(false);
    }
  };

  const exportarExcel = () => {
    if (!(reporte.insumos || []).length) return;
    const empresa = empresas.find(e => String(e.id) === String(reporteFiltros.empresa_id));
    const aoa = [
      ['Reporte de Consumo de Insumos de Botiquín'],
      ['Empresa: ' + (empresa ? empresa.nombre : 'Todas')],
      ['Área: ' + (reporteFiltros.area || 'Todas')],
      ['Tipo equipo: ' + (reporteFiltros.tipo_equipo || 'Todos')],
      ['Equipo: ' + (reporteFiltros.equipo || 'Todos')],
      [],
      ['Código', 'Insumo', 'Presentación', 'Tipo', ...reporte.rango_fechas, 'Cantidad', 'P. Unit.', 'Total (S/.)'],
    ];

    reporte.insumos.forEach(ins => {
      const row = [ins.codigo, ins.nombre, ins.presentacion, ins.tipo || ''];
      reporte.rango_fechas.forEach(f => row.push(ins.consumos[f] || 0));
      row.push(ins.sub_total_cantidad, ins.precio_und, ins.total_soles);
      aoa.push(row);
    });

    aoa.push([]);
    const baseCols = 4 + reporte.rango_fechas.length;
    const totSub = new Array(baseCols + 3).fill('');
    totSub[baseCols + 1] = 'SUB TOTAL';
    totSub[baseCols + 2] = reporte.totales.sub_total;
    const totIgv = new Array(baseCols + 3).fill('');
    totIgv[baseCols + 1] = 'IGV (18%)';
    totIgv[baseCols + 2] = reporte.totales.igv;
    const totGen = new Array(baseCols + 3).fill('');
    totGen[baseCols + 1] = 'TOTAL GENERAL';
    totGen[baseCols + 2] = reporte.totales.total;
    aoa.push(totSub, totIgv, totGen);

    const ws = XLSX.utils.aoa_to_sheet(aoa);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, 'Consumo Botiquín');
    XLSX.writeFile(wb, 'Reporte_Consumo_Insumos_Botiquin.xlsx');
  };

  return (
    <div>
      <div className="flex justify-between items-center mb-4" style={{ flexWrap: 'wrap', gap: 12 }}>
        <div>
          <h1 style={{ margin: 0 }}>Inspección</h1>
          <p style={{ margin: '4px 0 0', color: 'var(--text-muted)' }}>
            Registro de inspecciones de botiquín y consumo de insumos
          </p>
        </div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <button type="button" className="btn btn-primary" onClick={() => openNewInspeccion()}>
            <ClipboardCheck size={18} /> Registrar inspección
          </button>
        </div>
      </div>

      <div className="flex gap-2 mb-4" style={{ flexWrap: 'wrap' }}>
        {[
          { id: 'inspecciones', label: 'Inspecciones', icon: History },
          { id: 'reporte', label: 'Consumo de insumos', icon: Download },
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

      {tab === 'inspecciones' && (
        <div className="glass-panel mb-4" style={{ padding: 16 }}>
          <div className="flex items-center mb-3" style={{ gap: 8 }}>
            <Filter size={18} />
            <strong>Filtros</strong>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12 }}>
            <div className="form-group" style={{ margin: 0 }}>
              <label className="form-label">Buscar</label>
              <div style={{ position: 'relative' }}>
                <Search size={16} style={{ position: 'absolute', left: 10, top: 12, opacity: 0.5 }} />
                <input
                  className="form-control"
                  style={{ paddingLeft: 32 }}
                  placeholder="Botiquín, ubicación, tipo..."
                  value={filters.search}
                  onChange={e => setFilters({ ...filters, search: e.target.value })}
                />
              </div>
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
          </div>
        </div>
      )}

      {tab === 'inspecciones' && (
        <div className="glass-panel" style={{ overflowX: 'auto' }}>
          <table className="table">
            <thead>
              <tr>
                <th>Fecha</th>
                <th>Botiquín</th>
                <th>Área</th>
                <th>Empresa</th>
                <th>Responsable</th>
                <th>Insumos</th>
                <th style={{ width: 80 }}></th>
              </tr>
            </thead>
            <tbody>
              {inspecciones.length === 0 && (
                <tr><td colSpan={7} style={{ textAlign: 'center', opacity: 0.7 }}>Sin inspecciones</td></tr>
              )}
              {inspecciones.map(ins => (
                <tr key={ins.id}>
                  <td>{ins.fecha ? new Date(ins.fecha).toLocaleString() : '—'}</td>
                  <td>
                    {ins.botiquin
                      ? `${ins.botiquin.codigo ? ins.botiquin.codigo + ' · ' : ''}${ins.botiquin.tipo_botiquin?.nombre || ins.botiquin.tipo_equipo} · ${ins.botiquin.ubicacion || ''}`
                      : '—'}
                  </td>
                  <td>{ins.botiquin?.area || '—'}</td>
                  <td>{ins.botiquin?.empresa?.nombre || '—'}</td>
                  <td>
                    {ins.responsable
                      ? `${ins.responsable.nombre || ''} ${ins.responsable.apellidos || ''}`.trim()
                      : '—'}
                  </td>
                  <td>
                    {(ins.insumos || []).length
                      ? ins.insumos.map(i =>
                          `${i.medicamento?.nombre || i.medicamento_id} (x${i.cantidad})`
                        ).join(', ')
                      : '—'}
                  </td>
                  <td>
                    <button type="button" className="btn-icon btn-icon-danger" title="Eliminar" onClick={() => deleteInspeccion(ins.id)}>
                      <Trash2 size={16} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tab === 'reporte' && (
        <div>
          <div className="glass-panel mb-4" style={{ padding: 16 }}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12, marginBottom: 16 }}>
              <div className="form-group" style={{ margin: 0 }}>
                <label className="form-label">Empresa</label>
                <Select
                  styles={selectStyles}
                  options={empresaOptions}
                  isClearable
                  placeholder="Todas..."
                  value={empresaOptions.find(o => o.value === reporteFiltros.empresa_id) || null}
                  onChange={opt => setReporteFiltros({ ...reporteFiltros, empresa_id: opt ? opt.value : '' })}
                />
              </div>
              <div className="form-group" style={{ margin: 0 }}>
                <label className="form-label">Botiquín</label>
                <Select
                  styles={selectStyles}
                  options={botiquinOptions}
                  isClearable
                  placeholder="Todos..."
                  value={botiquinOptions.find(o => o.value === reporteFiltros.botiquin_id) || null}
                  onChange={opt => setReporteFiltros({ ...reporteFiltros, botiquin_id: opt ? opt.value : '' })}
                />
              </div>
              <div className="form-group" style={{ margin: 0 }}>
                <label className="form-label">Área</label>
                <select className="form-control" value={reporteFiltros.area} onChange={e => setReporteFiltros({ ...reporteFiltros, area: e.target.value })}>
                  <option value="">Todas</option>
                  {AREAS.map(o => <option key={o} value={o}>{o}</option>)}
                </select>
              </div>
              <div className="form-group" style={{ margin: 0 }}>
                <label className="form-label">Tipo de equipo</label>
                <select className="form-control" value={reporteFiltros.tipo_equipo} onChange={e => setReporteFiltros({ ...reporteFiltros, tipo_equipo: e.target.value })}>
                  <option value="">Todos</option>
                  {TIPOS_EQUIPO_EMERGENCIA.map(o => <option key={o} value={o}>{o}</option>)}
                </select>
              </div>
              <div className="form-group" style={{ margin: 0 }}>
                <label className="form-label">Equipo</label>
                <select className="form-control" value={reporteFiltros.equipo} onChange={e => setReporteFiltros({ ...reporteFiltros, equipo: e.target.value })}>
                  <option value="">Todos</option>
                  {EQUIPOS.map(o => <option key={o} value={o}>{o}</option>)}
                </select>
              </div>
              <div className="form-group" style={{ margin: 0 }}>
                <label className="form-label">Desde</label>
                <DatePicker
                  selected={reporteFiltros.fecha_inicio}
                  onChange={d => setReporteFiltros({ ...reporteFiltros, fecha_inicio: d })}
                  dateFormat="dd/MM/yyyy"
                  className="form-control"
                  isClearable
                  placeholderText="Fecha inicio"
                />
              </div>
              <div className="form-group" style={{ margin: 0 }}>
                <label className="form-label">Hasta</label>
                <DatePicker
                  selected={reporteFiltros.fecha_fin}
                  onChange={d => setReporteFiltros({ ...reporteFiltros, fecha_fin: d })}
                  dateFormat="dd/MM/yyyy"
                  className="form-control"
                  isClearable
                  placeholderText="Fecha fin"
                />
              </div>
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              <button type="button" className="btn btn-primary" onClick={buscarReporte} disabled={loadingReporte}>
                <Search size={16} />
                {loadingReporte ? 'Generando...' : 'Generar reporte'}
              </button>
              <button type="button" className="btn btn-secondary" onClick={exportarExcel} disabled={!(reporte.insumos || []).length}>
                <Download size={16} /> Exportar Excel
              </button>
            </div>
          </div>

          <div className="glass-panel" style={{ overflowX: 'auto' }}>
            <table className="table">
              <thead>
                <tr>
                  <th>Código</th>
                  <th>Insumo</th>
                  <th>Presentación</th>
                  {(reporte.rango_fechas || []).map(f => <th key={f}>{f}</th>)}
                  <th>Cantidad</th>
                  <th>P. Unit. (S/.)</th>
                  <th>Total (S/.)</th>
                </tr>
              </thead>
              <tbody>
                {(reporte.insumos || []).length === 0 && (
                  <tr>
                    <td colSpan={6 + (reporte.rango_fechas || []).length} style={{ textAlign: 'center', opacity: 0.7 }}>
                      Sin datos. Genere el reporte con los filtros deseados.
                    </td>
                  </tr>
                )}
                {(reporte.insumos || []).map(ins => (
                  <tr key={ins.id}>
                    <td>{ins.codigo}</td>
                    <td>{ins.nombre}</td>
                    <td>{ins.presentacion}</td>
                    {(reporte.rango_fechas || []).map(f => (
                      <td key={f}>{ins.consumos?.[f] || 0}</td>
                    ))}
                    <td>{ins.sub_total_cantidad}</td>
                    <td>{Number(ins.precio_und || 0).toFixed(2)}</td>
                    <td>{Number(ins.total_soles || 0).toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
              {(reporte.insumos || []).length > 0 && (
                <tfoot>
                  <tr>
                    <td colSpan={3 + (reporte.rango_fechas || []).length} style={{ textAlign: 'right', fontWeight: 600 }}>Subtotal</td>
                    <td colSpan={2}>{Number(reporte.totales?.sub_total || 0).toFixed(2)}</td>
                  </tr>
                  <tr>
                    <td colSpan={3 + (reporte.rango_fechas || []).length} style={{ textAlign: 'right', fontWeight: 600 }}>IGV (18%)</td>
                    <td colSpan={2}>{Number(reporte.totales?.igv || 0).toFixed(2)}</td>
                  </tr>
                  <tr>
                    <td colSpan={3 + (reporte.rango_fechas || []).length} style={{ textAlign: 'right', fontWeight: 700 }}>Total general</td>
                    <td colSpan={2} style={{ fontWeight: 700 }}>{Number(reporte.totales?.total || 0).toFixed(2)}</td>
                  </tr>
                </tfoot>
              )}
            </table>
          </div>
        </div>
      )}

      {modalInspeccion && (
        <div className="modal-overlay">
          <div className="modal-content" style={{ maxWidth: 640 }}>
            <div className="modal-header">
              <h3>Registrar inspección</h3>
              <button className="close-btn" type="button" onClick={() => setModalInspeccion(false)}><X size={24} /></button>
            </div>
            <form onSubmit={saveInspeccion}>
              <div className="modal-body">
                <div className="form-group">
                  <label className="form-label">Botiquín</label>
                  <Select
                    styles={selectStyles}
                    options={botiquinOptions}
                    placeholder="Buscar botiquín..."
                    value={botiquinOptions.find(o => o.value === formInspeccion.botiquin_id) || null}
                    onChange={opt => cargarInsumosDeBotiquin(opt ? opt.value : '')}
                    noOptionsMessage={() => 'Sin botiquines'}
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">Fecha (automática)</label>
                  <DatePicker
                    selected={formInspeccion.fecha}
                    onChange={d => setFormInspeccion({ ...formInspeccion, fecha: d || new Date() })}
                    showTimeSelect
                    dateFormat="dd/MM/yyyy HH:mm"
                    className="form-control"
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">Responsable de la inspección</label>
                  <Select
                    styles={selectStyles}
                    options={personalOptions}
                    placeholder="Buscar personal de salud..."
                    value={personalOptions.find(o => o.value === formInspeccion.responsable_id) || null}
                    onChange={opt => setFormInspeccion({ ...formInspeccion, responsable_id: opt ? opt.value : '' })}
                    noOptionsMessage={() => 'Sin resultados'}
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">
                    Lista de insumos
                    {cargandoInsumos && <span style={{ marginLeft: 8, opacity: 0.7, fontWeight: 400 }}>(cargando del tipo...)</span>}
                  </label>
                  <p style={{ margin: '0 0 10px', fontSize: '0.88rem', opacity: 0.7 }}>
                    Se completan automáticamente según el tipo del botiquín seleccionado. Puede ajustar cantidades o agregar más.
                  </p>
                  <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'stretch' }}>
                    <div style={{ flex: '1 1 240px' }}>
                      <Select
                        styles={selectStyles}
                        options={insumoOptions}
                        placeholder="Agregar insumo adicional..."
                        value={insumoSelect}
                        onChange={setInsumoSelect}
                        noOptionsMessage={() => 'Sin resultados'}
                      />
                    </div>
                    <div style={{ width: 88 }}>
                      <input
                        type="number"
                        min={1}
                        className="form-control"
                        value={insumoCantidad}
                        onChange={e => setInsumoCantidad(e.target.value)}
                      />
                    </div>
                    <button
                      type="button"
                      className="btn btn-primary btn-sm"
                      onClick={addInsumoLinea}
                      disabled={!insumoSelect}
                    >
                      <Plus size={16} /> Agregar
                    </button>
                  </div>
                  {formInspeccion.insumos.length > 0 ? (
                    <ul style={{ marginTop: 12, paddingLeft: 0, listStyle: 'none', display: 'flex', flexDirection: 'column', gap: 8 }}>
                      {formInspeccion.insumos.map(i => (
                        <li
                          key={i.medicamento_id}
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
                          <span style={{ flex: 1 }}>{i.label}</span>
                          <input
                            type="number"
                            min={1}
                            className="form-control"
                            style={{ width: 72 }}
                            value={i.cantidad}
                            onChange={e => {
                              const cantidad = Math.max(1, parseInt(e.target.value, 10) || 1);
                              setFormInspeccion(prev => ({
                                ...prev,
                                insumos: prev.insumos.map(x =>
                                  String(x.medicamento_id) === String(i.medicamento_id)
                                    ? { ...x, cantidad }
                                    : x
                                ),
                              }));
                            }}
                          />
                          <button
                            type="button"
                            className="btn-icon btn-icon-sm btn-icon-danger"
                            title="Quitar insumo"
                            onClick={() => removeInsumoLinea(i.medicamento_id)}
                          >
                            <Trash2 size={15} />
                          </button>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p style={{ marginTop: 10, opacity: 0.6, fontSize: '0.9rem' }}>
                      {formInspeccion.botiquin_id
                        ? 'Este botiquín no tiene tipo con insumos definidos.'
                        : 'Seleccione un botiquín para cargar sus insumos.'}
                    </p>
                  )}
                </div>
                <div className="form-group">
                  <label className="form-label">Observaciones</label>
                  <textarea
                    className="form-control"
                    rows={2}
                    value={formInspeccion.observaciones}
                    onChange={e => setFormInspeccion({ ...formInspeccion, observaciones: e.target.value })}
                  />
                </div>
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={() => setModalInspeccion(false)}>
                  <X size={16} /> Cancelar
                </button>
                <button type="submit" className="btn btn-primary">
                  <Save size={16} /> Guardar inspección
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default InspeccionBotiquin;
