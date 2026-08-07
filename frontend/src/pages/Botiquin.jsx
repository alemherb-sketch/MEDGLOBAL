import { useState, useEffect, useMemo, useCallback } from 'react';
import Select from 'react-select';
import DatePicker from 'react-datepicker';
import 'react-datepicker/dist/react-datepicker.css';
import * as XLSX from 'xlsx';
import {
  Search, Plus, Trash2, Edit2, X, ClipboardCheck, Download,
  Filter, Package, History, Save, Layers
} from 'lucide-react';
import { apiFetch, apiJson } from '../api';

const TIPOS_EQUIPO_EMERGENCIA = [
  'Botiquín de área de trabajo',
  'Botiquín vehículo liviano',
  'Botiquín polvorín de accesorios',
  'Botiquín polvorín explosivos',
  'Estacion de emergencia',
  'Refugio minero',
];

const AREAS = ['Mina', 'Planta'];

const EQUIPOS = [
  'Botiquín de emergencia',
  'Polvorines',
  'Refugios mineros',
];

const selectStyles = {
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
  input: (base) => ({ ...base, color: 'var(--text-color, #e2e8f0)' }),
  placeholder: (base) => ({ ...base, color: '#94a3b8' }),
};

const emptyBotiquin = {
  id: null,
  codigo: '',
  fecha_creacion: new Date(),
  tipo_botiquin_id: '',
  tipo_equipo: TIPOS_EQUIPO_EMERGENCIA[0],
  area: AREAS[0],
  empresa_id: '',
  ubicacion: '',
  numero_serie_placa: '',
  equipo: EQUIPOS[0],
  estado: 'ACTIVO',
};

const emptyTipo = {
  id: null,
  codigo: '',
  nombre: '',
  insumos: [],
};

const labelMedicamento = (m) => {
  if (!m) return '—';
  return `${m.codigo || '—'} · ${m.nombre}${m.presentacion ? ` (${m.presentacion})` : ''}${m.tipo ? ` [${m.tipo}]` : ''}`;
};

const Botiquin = () => {
  const [tab, setTab] = useState('botiquines'); // tipos | botiquines | inspecciones | reporte
  const [botiquines, setBotiquines] = useState([]);
  const [tiposBotiquin, setTiposBotiquin] = useState([]);
  const [inspecciones, setInspecciones] = useState([]);
  const [empresas, setEmpresas] = useState([]);
  const [personal, setPersonal] = useState([]);
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

  const [modalTipo, setModalTipo] = useState(false);
  const [formTipo, setFormTipo] = useState(emptyTipo);
  const [insumoTipoSelect, setInsumoTipoSelect] = useState(null);
  const [insumoTipoCantidad, setInsumoTipoCantidad] = useState(1);

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
  const [reporte, setReporte] = useState({ rango_fechas: [], insumos: [], totales: { sub_total: 0, igv: 0, total: 0 } });
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
      label: `${b.codigo ? b.codigo + ' · ' : ''}${b.tipo_botiquin?.nombre || b.tipo_equipo} · ${b.ubicacion || 's/u'} · ${b.numero_serie_placa || 's/n'}`,
    })),
    [botiquines]
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
    apiJson('/personal_salud/').then(setPersonal).catch(() => setPersonal([]));
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
      .catch(err => {
        console.error(err);
        setBotiquines([]);
      });
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
    loadTipos();
    // Cargar botiquines para combos de inspeccion/reporte aunque no este la pestana
    apiJson('/botiquines/').then(setBotiquines).catch(() => setBotiquines([]));
  }, []);

  useEffect(() => {
    if (tab === 'tipos') loadTipos();
    if (tab === 'botiquines') loadBotiquines();
    if (tab === 'inspecciones') loadInspecciones();
  }, [tab, filters, loadTipos]);

  const mapInsumosFromApi = (list) =>
    (list || []).map(p => ({
      medicamento_id: String(p.medicamento_id),
      cantidad: p.cantidad || 1,
      label: p.medicamento ? labelMedicamento(p.medicamento) : String(p.medicamento_id),
    }));

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
      // Fallback: usar tipo embebido si el botiquin ya lo trae
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

  // --- Tipos de botiquin ---
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

  // --- Botiquines ---
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
      numero_serie_placa: b.numero_serie_placa || '',
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
    const data = {
      codigo: (formBotiquin.codigo || '').trim() || null,
      tipo_botiquin_id: formBotiquin.tipo_botiquin_id || null,
      tipo_equipo: formBotiquin.tipo_equipo,
      area: formBotiquin.area,
      empresa_id: formBotiquin.empresa_id || null,
      ubicacion: formBotiquin.ubicacion || null,
      numero_serie_placa: formBotiquin.numero_serie_placa || null,
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

  // --- Inspecciones ---
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
    if (botiquinId) {
      cargarInsumosDeBotiquin(botiquinId);
    }
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
        if (tab === 'inspecciones') loadInspecciones();
        else setTab('inspecciones');
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
          <h1 style={{ margin: 0 }}>Botiquín</h1>
          <p style={{ margin: '4px 0 0', color: 'var(--text-muted)' }}>
            Tipos de botiquín, equipos, inspecciones y consumo de insumos
          </p>
        </div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <button type="button" className="btn btn-secondary" onClick={() => openNewInspeccion()}>
            <ClipboardCheck size={18} /> Registrar inspección
          </button>
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

      {(tab === 'botiquines' || tab === 'inspecciones') && (
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
                  placeholder="Ubicación, serie, tipo..."
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
            {tab === 'botiquines' && (
              <div className="form-group" style={{ margin: 0 }}>
                <label className="form-label">Estado</label>
                <select className="form-control" value={filters.estado} onChange={e => setFilters({ ...filters, estado: e.target.value })}>
                  <option value="">Todos</option>
                  <option value="ACTIVO">Activo</option>
                  <option value="INACTIVO">Inactivo</option>
                </select>
              </div>
            )}
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
                <th>Fecha creación</th>
                <th>Tipo de botiquín</th>
                <th>Tipo de equipo</th>
                <th>Área</th>
                <th>Empresa</th>
                <th>Ubicación</th>
                <th>Serie / Placa</th>
                <th>Equipo</th>
                <th>Estado</th>
                <th style={{ width: 140 }}>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {botiquines.length === 0 && (
                <tr><td colSpan={11} style={{ textAlign: 'center', opacity: 0.7 }}>Sin botiquines registrados</td></tr>
              )}
              {botiquines.map(b => (
                <tr key={b.id}>
                  <td>{b.codigo || '—'}</td>
                  <td>
                    {b.fecha_creacion
                      ? new Date(b.fecha_creacion).toLocaleDateString()
                      : (b.created_at ? new Date(b.created_at).toLocaleDateString() : '—')}
                  </td>
                  <td>{b.tipo_botiquin?.nombre || '—'}</td>
                  <td>{b.tipo_equipo}</td>
                  <td>{b.area}</td>
                  <td>{b.empresa?.nombre || '—'}</td>
                  <td>{b.ubicacion || '—'}</td>
                  <td>{b.numero_serie_placa || '—'}</td>
                  <td>{b.equipo}</td>
                  <td>{b.estado}</td>
                  <td>
                    <div style={{ display: 'inline-flex', gap: 6 }}>
                      <button type="button" className="btn-icon" title="Inspeccionar" onClick={() => openNewInspeccion(b.id)}>
                        <ClipboardCheck size={16} />
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
              ))}
            </tbody>
          </table>
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
              <button className="btn btn-primary" onClick={buscarReporte} disabled={loadingReporte}>
                <Search size={16} />
                {loadingReporte ? 'Generando...' : 'Generar reporte'}
              </button>
              <button className="btn btn-secondary" onClick={exportarExcel} disabled={!(reporte.insumos || []).length}>
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
                  <tr><td colSpan={6 + (reporte.rango_fechas || []).length} style={{ textAlign: 'center', opacity: 0.7 }}>
                    Sin datos. Genere el reporte con los filtros deseados.
                  </td></tr>
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

      {/* Modal Tipo de Botiquín */}
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
                        title="Cantidad"
                        aria-label="Cantidad"
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

      {/* Modal Botiquín */}
      {modalBotiquin && (
        <div className="modal-overlay">
          <div className="modal-content" style={{ maxWidth: 640 }}>
            <div className="modal-header">
              <h3>{formBotiquin.id ? 'Editar botiquín' : 'Nuevo botiquín'}</h3>
              <button className="close-btn" type="button" onClick={() => setModalBotiquin(false)}><X size={24} /></button>
            </div>
            <form onSubmit={saveBotiquin}>
              <div className="modal-body">
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
                <div className="form-group">
                  <label className="form-label">Ubicación</label>
                  <input
                    className="form-control"
                    value={formBotiquin.ubicacion}
                    onChange={e => setFormBotiquin({ ...formBotiquin, ubicacion: e.target.value })}
                    placeholder="Ubicación física del equipo"
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">Número de serie o placa</label>
                  <input
                    className="form-control"
                    value={formBotiquin.numero_serie_placa}
                    onChange={e => setFormBotiquin({ ...formBotiquin, numero_serie_placa: e.target.value })}
                  />
                </div>
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

      {/* Modal Inspección */}
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

export default Botiquin;
