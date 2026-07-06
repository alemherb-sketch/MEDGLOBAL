import { useState, useEffect } from 'react';
import { API_URL } from '../config';
import { Users, Stethoscope, Pill, AlertTriangle, Printer, CalendarRange } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import DatePicker from 'react-datepicker';
import 'react-datepicker/dist/react-datepicker.css';
import { format } from 'date-fns';

const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4', '#f97316', '#14b8a6'];

const ChartCard = ({ id, title, children, onPrint, accentColor }) => (
  <div id={id} className="dash-chart-card">
    <div className="dash-chart-header">
      <h3 className="dash-chart-title">{title}</h3>
      <button className="no-print dash-print-btn" onClick={() => onPrint(id)} title="Imprimir este reporte">
        <Printer size={16} />
      </button>
    </div>
    <div className="dash-chart-body" style={{'--accent': accentColor}}>
      {children}
    </div>
  </div>
);

const Dashboard = () => {
  const [kpis, setKpis] = useState({
    total_atenciones: 0,
    total_trabajadores: 0,
    total_medicamentos: 0,
    medicamentos_stock_bajo: 0
  });

  const [stats, setStats] = useState({
    enfermedades: [],
    pacientes: [],
    empresas: [],
    medicamentos: [],
    costos: []
  });

  const [startDate, setStartDate] = useState(null);
  const [endDate, setEndDate] = useState(null);

  useEffect(() => {
    fetch(API_URL + '/dashboard/kpis')
      .then(res => res.json())
      .then(data => setKpis(data))
      .catch(err => console.error(err));
  }, []);

  useEffect(() => {
    let url = API_URL + '/dashboard/stats?';
    if (startDate) url += `fecha_inicio=${format(startDate, 'yyyy-MM-dd')}&`;
    if (endDate) url += `fecha_fin=${format(endDate, 'yyyy-MM-dd')}`;
      
    fetch(url)
      .then(res => res.json())
      .then(data => setStats(data))
      .catch(err => console.error(err));
  }, [startDate, endDate]);

  const handlePrint = () => {
    window.print();
  };

  const handlePrintChart = (chartId) => {
    document.body.classList.add('print-single-chart');
    const chart = document.getElementById(chartId);
    if (chart) chart.classList.add('active-print-chart');
    window.print();
    document.body.classList.remove('print-single-chart');
    if (chart) chart.classList.remove('active-print-chart');
  };

  return (
    <div className="dashboard-container">
      {/* ── Header ── */}
      <header className="dash-header print-header">
        <div className="dash-header-left">
          <div className="logo-container">
            <img src="/logo.png" alt="MEDGLOBAL Logo" style={{height: '40px', display: 'block'}} />
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
              onChange={date => setStartDate(date)}
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
              onChange={date => setEndDate(date)}
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
          <button className="btn btn-primary" onClick={handlePrint}>
            <Printer size={16} style={{marginRight: '6px'}} /> Imprimir Todo
          </button>
        </div>
      </header>

      {/* ── KPI Cards ── */}
      <section className="dash-kpis">
        <div className="dash-kpi" style={{'--kpi-accent': 'var(--primary-color)', '--kpi-glow': 'rgba(14,165,233,0.12)'}}>
          <div className="dash-kpi-icon"><Stethoscope size={24} /></div>
          <div className="dash-kpi-info">
            <span className="dash-kpi-label">Atenciones Hoy</span>
            <span className="dash-kpi-value">{kpis.total_atenciones}</span>
          </div>
        </div>

        <div className="dash-kpi" style={{'--kpi-accent': 'var(--secondary-color)', '--kpi-glow': 'rgba(139,92,246,0.12)'}}>
          <div className="dash-kpi-icon"><Users size={24} /></div>
          <div className="dash-kpi-info">
            <span className="dash-kpi-label">Personal Activo</span>
            <span className="dash-kpi-value">{kpis.total_trabajadores}</span>
          </div>
        </div>

        <div className="dash-kpi" style={{'--kpi-accent': 'var(--success-color)', '--kpi-glow': 'rgba(16,185,129,0.12)'}}>
          <div className="dash-kpi-icon"><Pill size={24} /></div>
          <div className="dash-kpi-info">
            <span className="dash-kpi-label">Medicamentos</span>
            <span className="dash-kpi-value">{kpis.total_medicamentos}</span>
          </div>
        </div>

        <div className="dash-kpi dash-kpi--danger" style={{'--kpi-accent': 'var(--danger-color)', '--kpi-glow': 'rgba(239,68,68,0.12)'}}>
          <div className="dash-kpi-icon"><AlertTriangle size={24} /></div>
          <div className="dash-kpi-info">
            <span className="dash-kpi-label">Stock Bajo</span>
            <span className="dash-kpi-value">{kpis.medicamentos_stock_bajo}</span>
          </div>
        </div>
      </section>

      {/* ── Charts Grid ── */}
      <section className="dash-charts print-grid">
        <ChartCard id="chart-enf" title="Top Enfermedades Más Atendidas" onPrint={handlePrintChart} accentColor="var(--primary-color)">
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={stats.enfermedades} layout="vertical" margin={{top: 5, right: 20, left: 5, bottom: 5}}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.1)" />
              <XAxis type="number" stroke="#64748b" tick={{fontSize: 11}} />
              <YAxis dataKey="name" type="category" width={110} stroke="#64748b" tick={{fontSize: 11}} />
              <RechartsTooltip contentStyle={{backgroundColor: '#1e293b', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '10px', boxShadow: '0 8px 24px rgba(0,0,0,0.4)'}} />
              <Bar dataKey="value" fill="#3b82f6" radius={[0, 6, 6, 0]} name="Atenciones" />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard id="chart-pac" title="Pacientes Más Atendidos" onPrint={handlePrintChart} accentColor="var(--secondary-color)">
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={stats.pacientes} margin={{top: 5, right: 20, left: 5, bottom: 5}}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.1)" />
              <XAxis dataKey="name" stroke="#64748b" tick={{fontSize: 10}} tickFormatter={(val) => val.length > 12 ? val.substring(0, 12) + '…' : val} />
              <YAxis stroke="#64748b" tick={{fontSize: 11}} />
              <RechartsTooltip contentStyle={{backgroundColor: '#1e293b', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '10px', boxShadow: '0 8px 24px rgba(0,0,0,0.4)'}} />
              <Bar dataKey="value" fill="#8b5cf6" radius={[6, 6, 0, 0]} name="Atenciones" />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard id="chart-emp" title="Atenciones por Empresa" onPrint={handlePrintChart} accentColor="#f59e0b">
          <ResponsiveContainer width="100%" height={280}>
            <PieChart>
              <Pie data={stats.empresas} cx="50%" cy="45%" innerRadius={55} outerRadius={95} paddingAngle={4} dataKey="value" label={({name, percent}) => `${name} ${(percent*100).toFixed(0)}%`}>
                {stats.empresas.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <RechartsTooltip contentStyle={{backgroundColor: '#1e293b', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '10px', boxShadow: '0 8px 24px rgba(0,0,0,0.4)'}} />
              <Legend iconType="circle" wrapperStyle={{fontSize: '12px'}} />
            </PieChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard id="chart-med" title="Medicamentos Más Usados" onPrint={handlePrintChart} accentColor="var(--success-color)">
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={stats.medicamentos} margin={{top: 5, right: 20, left: 5, bottom: 5}}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.1)" />
              <XAxis dataKey="name" stroke="#64748b" tick={{fontSize: 10}} tickFormatter={(val) => val.length > 14 ? val.substring(0, 14) + '…' : val} />
              <YAxis stroke="#64748b" tick={{fontSize: 11}} />
              <RechartsTooltip contentStyle={{backgroundColor: '#1e293b', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '10px', boxShadow: '0 8px 24px rgba(0,0,0,0.4)'}} />
              <Bar dataKey="value" fill="#10b981" radius={[6, 6, 0, 0]} name="Unidades" />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard id="chart-costos" title="Costos Totales en Medicamentos por Empresa" onPrint={handlePrintChart} accentColor="#f43f5e">
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={stats.costos} margin={{top: 5, right: 20, left: 15, bottom: 5}}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.1)" />
              <XAxis dataKey="name" stroke="#64748b" tick={{fontSize: 11}} />
              <YAxis stroke="#64748b" tick={{fontSize: 11}} tickFormatter={(val) => `S/${val}`} />
              <RechartsTooltip formatter={(value) => [`S/ ${value.toFixed(2)}`, 'Costo']} contentStyle={{backgroundColor: '#1e293b', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '10px', boxShadow: '0 8px 24px rgba(0,0,0,0.4)'}} />
              <Bar dataKey="value" fill="#f43f5e" radius={[6, 6, 0, 0]} name="Costo Total" />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
      </section>
    </div>
  );
};

export default Dashboard;
