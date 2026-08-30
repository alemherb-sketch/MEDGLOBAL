import { useState, useEffect, useMemo } from 'react';
import { apiJson } from '../api';
import { Users, Stethoscope, Pill, AlertTriangle, Printer, CalendarRange } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, ResponsiveContainer, Cell } from 'recharts';
import DatePicker from 'react-datepicker';
import 'react-datepicker/dist/react-datepicker.css';
import Select from 'react-select';
import { format } from 'date-fns';
import { selectStyles } from './botiquinShared';

const fechaParam = (fecha) => (fecha ? format(fecha, 'yyyy-MM-dd') : null);

/** Arma "?a=1&b=2" descartando lo vacio. Antes cada pantalla concatenaba a
 *  mano con `+= 'x=' + valor + '&'`, sin escapar y dejando un '&' colgando. */
const consulta = (params) => {
  const busqueda = new URLSearchParams();
  Object.entries(params).forEach(([clave, valor]) => {
    if (valor !== null && valor !== undefined && valor !== '') busqueda.append(clave, valor);
  });
  const texto = busqueda.toString();
  return texto ? `?${texto}` : '';
};

const Dashboard = () => {
  const [kpis, setKpis] = useState({
    total_atenciones: 0,
    total_trabajadores: 0,
    total_medicamentos: 0,
    medicamentos_stock_bajo: 0,
  });

  const [allEmpresas, setAllEmpresas] = useState([]);
  const [allSistemas, setAllSistemas] = useState([]);
  const [allObras, setAllObras] = useState([]);

  const [startDate, setStartDate] = useState(null);
  const [endDate, setEndDate] = useState(null);

  // Filtros y datos del cuadro de Sistemas Atendidos
  const [repSistemas, setRepSistemas] = useState({ total_general: 0, sistemas: [] });
  const [repSisFiltros, setRepSisFiltros] = useState({
    fecha_inicio: null,
    fecha_fin: null,
    sistema_id: '',
    empresa_ids: [],
    obra: '',
  });

  const empresaOptions = useMemo(
    () => (allEmpresas || []).map((e) => ({ value: String(e.id), label: e.nombre || String(e.id) })),
    [allEmpresas]
  );

  useEffect(() => {
    apiJson('/empresas/').then(setAllEmpresas).catch((err) => console.error(err));
    apiJson('/sistemas/').then(setAllSistemas).catch((err) => console.error(err));
    apiJson('/trabajadores/obras').then(setAllObras).catch((err) => console.error(err));
  }, []);

  // Las fechas del encabezado filtran las atenciones contadas arriba. Antes
  // estas dos fechas solo alimentaban a /dashboard/stats, cuya respuesta no se
  // usaba en ninguna parte: elegir un rango no cambiaba nada en pantalla.
  useEffect(() => {
    const url = '/dashboard/kpis' + consulta({
      fecha_inicio: fechaParam(startDate),
      fecha_fin: fechaParam(endDate),
    });
    apiJson(url).then(setKpis).catch((err) => console.error(err));
  }, [startDate, endDate]);

  useEffect(() => {
    const url = '/dashboard/reporte-sistemas' + consulta({
      fecha_inicio: fechaParam(repSisFiltros.fecha_inicio),
      fecha_fin: fechaParam(repSisFiltros.fecha_fin),
      sistema_id: repSisFiltros.sistema_id,
      empresa_id: (repSisFiltros.empresa_ids || []).join(','),
      obra: repSisFiltros.obra,
    });
    apiJson(url).then(setRepSistemas).catch((err) => console.error(err));
  }, [repSisFiltros]);

  const hayRango = Boolean(startDate || endDate);

  return (
    <div className="dashboard-container">
      {/* ── Encabezado ── */}
      <header className="dash-header print-header">
        <div className="dash-header-left">
          <div className="logo-container">
            <img src="/logo.png" alt="MEDGLOBAL Logo" style={{ height: '40px', display: 'block' }} />
          </div>
          <div className="dash-header-text">
            <h1>Dashboard</h1>
            <p>Panel de control y estadísticas</p>
          </div>
        </div>

        <div className="dash-header-right no-print">
          <div className="dash-date-filter">
            <CalendarRange size={16} className="dash-date-icon" />
            <DatePicker
              selected={startDate}
              onChange={setStartDate}
              selectsStart
              startDate={startDate}
              endDate={endDate}
              dateFormat="dd/MM/yyyy"
              placeholderText="Desde"
              className="form-control"
              isClearable
            />
            <span className="dash-date-sep">→</span>
            <DatePicker
              selected={endDate}
              onChange={setEndDate}
              selectsEnd
              startDate={startDate}
              endDate={endDate}
              minDate={startDate}
              dateFormat="dd/MM/yyyy"
              placeholderText="Hasta"
              className="form-control"
              isClearable
            />
          </div>
          <button className="btn btn-primary" onClick={() => window.print()}>
            <Printer size={16} style={{ marginRight: '6px' }} /> Imprimir Todo
          </button>
        </div>
      </header>

      {/* ── Indicadores ──
          Las etiquetas dicen lo que el número realmente cuenta. Antes la
          primera tarjeta decía "Atenciones Hoy" y la segunda "Personal
          Activo", pero mostraban el total histórico de atenciones y el total
          de trabajadores registrados: dos cifras que se leían todos los días
          como si fueran del día. */}
      <section className="dash-kpis">
        <div className="dash-kpi" style={{ '--kpi-accent': 'var(--primary-color)', '--kpi-glow': 'rgba(14,165,233,0.12)' }}>
          <div className="dash-kpi-icon"><Stethoscope size={24} /></div>
          <div className="dash-kpi-info">
            <span className="dash-kpi-label">{hayRango ? 'Atenciones del periodo' : 'Atenciones registradas'}</span>
            <span className="dash-kpi-value">{kpis.total_atenciones}</span>
          </div>
        </div>

        <div className="dash-kpi" style={{ '--kpi-accent': 'var(--secondary-color)', '--kpi-glow': 'rgba(139,92,246,0.12)' }}>
          <div className="dash-kpi-icon"><Users size={24} /></div>
          <div className="dash-kpi-info">
            <span className="dash-kpi-label">Trabajadores registrados</span>
            <span className="dash-kpi-value">{kpis.total_trabajadores}</span>
          </div>
        </div>

        <div className="dash-kpi" style={{ '--kpi-accent': 'var(--success-color)', '--kpi-glow': 'rgba(16,185,129,0.12)' }}>
          <div className="dash-kpi-icon"><Pill size={24} /></div>
          <div className="dash-kpi-info">
            <span className="dash-kpi-label">Productos en catálogo</span>
            <span className="dash-kpi-value">{kpis.total_medicamentos}</span>
          </div>
        </div>

        <div className="dash-kpi dash-kpi--danger" style={{ '--kpi-accent': 'var(--danger-color)', '--kpi-glow': 'rgba(239,68,68,0.12)' }}>
          <div className="dash-kpi-icon"><AlertTriangle size={24} /></div>
          <div className="dash-kpi-info">
            <span className="dash-kpi-label">Stock Bajo</span>
            <span className="dash-kpi-value">{kpis.medicamentos_stock_bajo}</span>
          </div>
        </div>
      </section>

      {/* ── Reporte de sistemas atendidos ── */}
      <section className="dash-charts print-grid">
        <section className="dash-systems-report">
          <div className="dash-report-heading">
            <div>
              <span className="dash-report-eyebrow">Análisis clínico</span>
              <h2>Reporte de sistemas atendidos</h2>
              <p>Consulta y compara la distribución de atenciones según el periodo, sistema clínico, empresa y obra.</p>
            </div>
          </div>
          <div className="dash-report-content">

            {/* Filtros */}
            <div style={{ display: 'flex', gap: '20px', flexWrap: 'wrap', padding: '16px 20px', background: 'rgba(15, 23, 42, 0.4)', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.05)' }}>
              <div style={{ flex: '1 1 220px' }}>
                <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: '500', color: 'var(--text-color)', marginBottom: '8px' }}>Rango de Fechas</label>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <div style={{ flex: 1 }}>
                    <DatePicker
                      selected={repSisFiltros.fecha_inicio}
                      onChange={(date) => setRepSisFiltros({ ...repSisFiltros, fecha_inicio: date })}
                      selectsStart
                      startDate={repSisFiltros.fecha_inicio}
                      endDate={repSisFiltros.fecha_fin}
                      dateFormat="dd/MM/yyyy"
                      placeholderText="Desde..."
                      className="form-control"
                      isClearable
                      wrapperClassName="date-picker-wrapper"
                    />
                  </div>
                  <span style={{ color: 'var(--text-muted)' }}>-</span>
                  <div style={{ flex: 1 }}>
                    <DatePicker
                      selected={repSisFiltros.fecha_fin}
                      onChange={(date) => setRepSisFiltros({ ...repSisFiltros, fecha_fin: date })}
                      selectsEnd
                      startDate={repSisFiltros.fecha_inicio}
                      endDate={repSisFiltros.fecha_fin}
                      minDate={repSisFiltros.fecha_inicio}
                      dateFormat="dd/MM/yyyy"
                      placeholderText="Hasta..."
                      className="form-control"
                      isClearable
                      wrapperClassName="date-picker-wrapper"
                    />
                  </div>
                </div>
              </div>
              <div style={{ flex: '1 1 200px' }}>
                <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: '500', color: 'var(--text-color)', marginBottom: '8px' }}>Sistema Clínico</label>
                <select
                  className="form-control"
                  value={repSisFiltros.sistema_id}
                  onChange={(e) => setRepSisFiltros({ ...repSisFiltros, sistema_id: e.target.value })}
                  style={{ cursor: 'pointer' }}
                >
                  <option value="">Todos los sistemas...</option>
                  {allSistemas.map((s) => <option key={s.id} value={s.id}>{s.nombre}</option>)}
                </select>
              </div>
              <div style={{ flex: '1 1 240px', minWidth: 220 }}>
                <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: '500', color: 'var(--text-color)', marginBottom: '8px' }}>Empresa Contratante</label>
                <Select
                  styles={{
                    ...selectStyles,
                    control: (base) => ({ ...selectStyles.control(base), minHeight: 42 }),
                    menuPortal: (base) => ({ ...base, zIndex: 9999 }),
                  }}
                  menuPortalTarget={typeof document !== 'undefined' ? document.body : null}
                  menuPosition="fixed"
                  isMulti
                  isClearable
                  isSearchable
                  closeMenuOnSelect={false}
                  hideSelectedOptions={false}
                  options={empresaOptions}
                  placeholder="Buscar y seleccionar empresas..."
                  noOptionsMessage={() => 'Sin resultados'}
                  value={empresaOptions.filter((o) => (repSisFiltros.empresa_ids || []).includes(o.value))}
                  onChange={(opts) => setRepSisFiltros({
                    ...repSisFiltros,
                    empresa_ids: (opts || []).map((o) => o.value),
                  })}
                />
              </div>
              <div style={{ flex: '1 1 200px' }}>
                <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: '500', color: 'var(--text-color)', marginBottom: '8px' }}>Obra</label>
                <select
                  className="form-control"
                  value={repSisFiltros.obra}
                  onChange={(e) => setRepSisFiltros({ ...repSisFiltros, obra: e.target.value })}
                  style={{ cursor: 'pointer' }}
                >
                  <option value="">Todas las obras...</option>
                  {allObras.map((o) => <option key={o} value={o}>{o}</option>)}
                </select>
              </div>
            </div>

            {/* Resultados */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
              <div style={{ width: '100%', display: 'flex', flexDirection: 'column', gap: '20px', minWidth: 0 }}>
                <div style={{ padding: '24px', background: 'linear-gradient(135deg, rgba(14, 165, 233, 0.1), rgba(139, 92, 246, 0.05))', borderRadius: '12px', border: '1px solid rgba(14, 165, 233, 0.2)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <div>
                    <span style={{ display: 'block', fontSize: '0.9rem', fontWeight: '500', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Total Atenciones</span>
                    <span style={{ display: 'block', fontSize: '0.8rem', color: 'rgba(255,255,255,0.4)', marginTop: '4px' }}>Según filtros aplicados</span>
                  </div>
                  <span style={{ display: 'block', fontSize: '3rem', lineHeight: '1', fontWeight: '800', color: 'var(--primary-color)', textShadow: '0 0 20px rgba(14,165,233,0.3)' }}>
                    {repSistemas.total_general}
                  </span>
                </div>

                <div style={{ flex: 1, maxHeight: '350px', overflowY: 'auto', background: 'rgba(15, 23, 42, 0.3)', border: '1px solid rgba(255,255,255,0.05)', borderRadius: '12px' }}>
                  <table className="table" style={{ margin: 0 }}>
                    <thead style={{ position: 'sticky', top: 0, background: '#1e293b', zIndex: 1, boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)' }}>
                      <tr>
                        <th style={{ padding: '12px 16px', fontSize: '0.8rem', textTransform: 'uppercase', letterSpacing: '0.5px', color: 'var(--text-muted)' }}>Sistema Clínico</th>
                        <th style={{ padding: '12px 16px', fontSize: '0.8rem', textTransform: 'uppercase', letterSpacing: '0.5px', color: 'var(--text-muted)', textAlign: 'right' }}>Cantidad</th>
                      </tr>
                    </thead>
                    <tbody>
                      {repSistemas.sistemas && repSistemas.sistemas.length > 0 ? (
                        repSistemas.sistemas.map((s, idx) => (
                          <tr key={idx} style={{ borderBottom: '1px solid rgba(255,255,255,0.02)' }}>
                            <td style={{ padding: '12px 16px', fontWeight: '500', color: 'var(--text-color)' }}>{s.name}</td>
                            <td style={{ padding: '12px 16px', textAlign: 'right', fontWeight: '700', color: 'var(--primary-color)' }}>{s.value}</td>
                          </tr>
                        ))
                      ) : (
                        <tr><td colSpan="2" style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '30px' }}>No hay datos para estos filtros</td></tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>

              <div style={{ width: '100%', minWidth: 0, background: 'rgba(15, 23, 42, 0.2)', border: '1px solid rgba(255,255,255,0.05)', borderRadius: '12px', padding: '16px' }}>
                <h4 style={{ fontSize: '0.9rem', fontWeight: '500', color: 'var(--text-muted)', marginBottom: '16px', paddingLeft: '8px' }}>Distribución Visual</h4>
                {repSistemas.sistemas && repSistemas.sistemas.length > 0 ? (
                  <ResponsiveContainer width="100%" height={420}>
                    <BarChart data={repSistemas.sistemas} margin={{ top: 10, right: 20, left: 0, bottom: 70 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.05)" horizontal vertical={false} />
                      <XAxis dataKey="name" type="category" interval={0} height={70} stroke="#475569" tick={{ fontSize: 11, fill: '#cbd5e1' }} axisLine={{ stroke: '#334155' }} tickLine={false} angle={-35} textAnchor="end" tickFormatter={(val) => (val.length > 18 ? val.substring(0, 18) + '…' : val)} />
                      <YAxis type="number" allowDecimals={false} width={40} stroke="#475569" tick={{ fontSize: 11, fill: '#94a3b8' }} axisLine={{ stroke: '#334155' }} tickLine={false} />
                      <RechartsTooltip cursor={{ fill: 'rgba(255,255,255,0.02)' }} contentStyle={{ backgroundColor: '#0f172a', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', boxShadow: '0 10px 25px rgba(0,0,0,0.5)', color: '#fff' }} itemStyle={{ color: '#38bdf8', fontWeight: '600' }} />
                      <Bar dataKey="value" fill="#8b5cf6" maxBarSize={56} radius={[4, 4, 0, 0]} name="Atenciones" animationDuration={1000}>
                        {repSistemas.sistemas.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={`hsl(${190 + (index * 15)}, 80%, 55%)`} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <div style={{ height: '400px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', borderRadius: '8px' }}>
                    <div style={{ textAlign: 'center' }}>
                      <span style={{ fontSize: '2rem', display: 'block', marginBottom: '8px', opacity: 0.5 }}>📊</span>
                      Sin datos para graficar
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </section>
      </section>
    </div>
  );
};

export default Dashboard;
