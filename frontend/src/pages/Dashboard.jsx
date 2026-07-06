import { useState, useEffect } from 'react';
import { API_URL } from '../config';
import { Users, Stethoscope, Pill, AlertTriangle, Printer } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';

const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4'];

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

  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');

  useEffect(() => {
    fetch(API_URL + '/dashboard/kpis')
      .then(res => res.json())
      .then(data => setKpis(data))
      .catch(err => console.error(err));
  }, []);

  useEffect(() => {
    let url = API_URL + '/dashboard/stats?';
    if (startDate) url += `fecha_inicio=${startDate}&`;
    if (endDate) url += `fecha_fin=${endDate}`;
      
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
      <div className="flex items-center justify-between mb-8 print-header">
        <div className="flex items-center">
          <div className="logo-container" style={{marginRight: '20px'}}>
            <img src="/logo.png" alt="MEDGLOBAL Logo" style={{height: '45px', display: 'block'}} />
          </div>
          <div>
            <h1 style={{margin: 0, fontSize: '2.2rem', textShadow: '0 2px 10px rgba(0,0,0,0.3)'}}>Dashboard</h1>
            <p className="text-muted" style={{margin: 0, fontSize: '1.1rem'}}>Visión general y Estadísticas</p>
          </div>
        </div>
        <div className="flex items-center gap-4 no-print">
          <div style={{display: 'flex', alignItems: 'center', gap: '8px', background: 'var(--panel-bg)', padding: '5px 10px', borderRadius: '8px', border: '1px solid var(--border-color)'}}>
            <span style={{fontSize: '0.9rem', color: 'var(--text-muted)'}}>Fechas:</span>
            <input type="date" className="form-control" style={{padding: '4px 8px', minHeight: 'auto'}} value={startDate} onChange={e => setStartDate(e.target.value)} />
            <span style={{color: 'var(--text-muted)'}}>-</span>
            <input type="date" className="form-control" style={{padding: '4px 8px', minHeight: 'auto'}} value={endDate} onChange={e => setEndDate(e.target.value)} />
          </div>
          <button className="btn btn-primary" onClick={handlePrint} style={{display: 'flex', alignItems: 'center', gap: '8px'}}>
            <Printer size={18} /> Todo a PDF
          </button>
        </div>
      </div>

      <div className="grid grid-cols-4 mb-6">
        <div className="glass-panel kpi-card">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="form-label" style={{textTransform: 'uppercase', letterSpacing: '1px', fontSize: '0.8rem'}}>Atenciones Hoy</h3>
              <h2 style={{fontSize: '2.5rem', margin: 0, fontWeight: '700'}}>{kpis.total_atenciones}</h2>
            </div>
            <div style={{padding: '16px', background: 'rgba(14,165,233,0.1)', borderRadius: '16px', boxShadow: 'inset 0 0 0 1px rgba(14,165,233,0.2)'}}>
              <Stethoscope size={32} color="var(--primary-color)" />
            </div>
          </div>
        </div>

        <div className="glass-panel kpi-card">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="form-label" style={{textTransform: 'uppercase', letterSpacing: '1px', fontSize: '0.8rem'}}>Personal Activo</h3>
              <h2 style={{fontSize: '2.5rem', margin: 0, fontWeight: '700'}}>{kpis.total_trabajadores}</h2>
            </div>
            <div style={{padding: '16px', background: 'rgba(139,92,246,0.1)', borderRadius: '16px', boxShadow: 'inset 0 0 0 1px rgba(139,92,246,0.2)'}}>
              <Users size={32} color="var(--secondary-color)" />
            </div>
          </div>
        </div>

        <div className="glass-panel kpi-card">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="form-label" style={{textTransform: 'uppercase', letterSpacing: '1px', fontSize: '0.8rem'}}>Medicamentos</h3>
              <h2 style={{fontSize: '2.5rem', margin: 0, fontWeight: '700'}}>{kpis.total_medicamentos}</h2>
            </div>
            <div style={{padding: '16px', background: 'rgba(16,185,129,0.1)', borderRadius: '16px', boxShadow: 'inset 0 0 0 1px rgba(16,185,129,0.2)'}}>
              <Pill size={32} color="var(--success-color)" />
            </div>
          </div>
        </div>

        <div className="glass-panel kpi-card" style={{ borderLeft: '4px solid var(--danger-color)', position: 'relative', overflow: 'hidden' }}>
          <div className="flex items-center justify-between">
            <div>
              <h3 className="form-label" style={{textTransform: 'uppercase', letterSpacing: '1px', fontSize: '0.8rem'}}>Stock Bajo</h3>
              <h2 style={{fontSize: '2.5rem', margin: 0, fontWeight: '700', color: 'var(--danger-color)'}}>{kpis.medicamentos_stock_bajo}</h2>
            </div>
            <div style={{padding: '16px', background: 'rgba(239,68,68,0.1)', borderRadius: '16px', boxShadow: 'inset 0 0 0 1px rgba(239,68,68,0.2)'}}>
              <AlertTriangle size={32} color="var(--danger-color)" />
            </div>
          </div>
        </div>
      </div>
      
      <div className="grid grid-cols-2 gap-6 print-grid">
        {/* Enfermedades más frecuentes */}
        <div id="chart-enf" className="glass-panel chart-container">
          <div className="flex items-center justify-between mb-4">
            <h3 style={{fontSize: '1.2rem', margin: 0, color: 'var(--text-color)'}}>Top Enfermedades Más Atendidas</h3>
            <button className="no-print action-btn view" onClick={() => handlePrintChart('chart-enf')} title="Imprimir este gráfico">
              <Printer size={18} color="var(--primary-color)" />
            </button>
          </div>
          <div style={{width: '100%', height: 300}}>
            <ResponsiveContainer>
              <BarChart data={stats.enfermedades} layout="vertical" margin={{top: 5, right: 30, left: 20, bottom: 5}}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis type="number" stroke="#94a3b8" />
                <YAxis dataKey="name" type="category" width={100} stroke="#94a3b8" tick={{fontSize: 12}} />
                <RechartsTooltip contentStyle={{backgroundColor: '#1e293b', border: 'none', borderRadius: '8px'}} />
                <Bar dataKey="value" fill="var(--primary-color)" radius={[0, 4, 4, 0]} name="Atenciones" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Pacientes más atendidos */}
        <div id="chart-pac" className="glass-panel chart-container">
          <div className="flex items-center justify-between mb-4">
            <h3 style={{fontSize: '1.2rem', margin: 0, color: 'var(--text-color)'}}>Pacientes Más Atendidos</h3>
            <button className="no-print action-btn view" onClick={() => handlePrintChart('chart-pac')} title="Imprimir este gráfico">
              <Printer size={18} color="var(--secondary-color)" />
            </button>
          </div>
          <div style={{width: '100%', height: 300}}>
            <ResponsiveContainer>
              <BarChart data={stats.pacientes} margin={{top: 5, right: 30, left: 0, bottom: 5}}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="name" stroke="#94a3b8" tick={{fontSize: 11}} tickFormatter={(val) => val.substring(0, 10) + '...'} />
                <YAxis stroke="#94a3b8" />
                <RechartsTooltip contentStyle={{backgroundColor: '#1e293b', border: 'none', borderRadius: '8px'}} />
                <Bar dataKey="value" fill="var(--secondary-color)" radius={[4, 4, 0, 0]} name="Atenciones" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Empresas más atendidas */}
        <div id="chart-emp" className="glass-panel chart-container">
          <div className="flex items-center justify-between mb-4">
            <h3 style={{fontSize: '1.2rem', margin: 0, color: 'var(--text-color)'}}>Atenciones por Empresa</h3>
            <button className="no-print action-btn view" onClick={() => handlePrintChart('chart-emp')} title="Imprimir este gráfico">
              <Printer size={18} color="var(--primary-color)" />
            </button>
          </div>
          <div style={{width: '100%', height: 300}}>
            <ResponsiveContainer>
              <PieChart>
                <Pie data={stats.empresas} cx="50%" cy="50%" innerRadius={60} outerRadius={100} paddingAngle={5} dataKey="value" label>
                  {stats.empresas.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <RechartsTooltip contentStyle={{backgroundColor: '#1e293b', border: 'none', borderRadius: '8px'}} />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Medicamentos más usados */}
        <div id="chart-med" className="glass-panel chart-container">
          <div className="flex items-center justify-between mb-4">
            <h3 style={{fontSize: '1.2rem', margin: 0, color: 'var(--text-color)'}}>Medicamentos Más Usados</h3>
            <button className="no-print action-btn view" onClick={() => handlePrintChart('chart-med')} title="Imprimir este gráfico">
              <Printer size={18} color="var(--success-color)" />
            </button>
          </div>
          <div style={{width: '100%', height: 300}}>
            <ResponsiveContainer>
              <BarChart data={stats.medicamentos} margin={{top: 5, right: 30, left: 0, bottom: 5}}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="name" stroke="#94a3b8" tick={{fontSize: 11}} tickFormatter={(val) => val.substring(0, 12)} />
                <YAxis stroke="#94a3b8" />
                <RechartsTooltip contentStyle={{backgroundColor: '#1e293b', border: 'none', borderRadius: '8px'}} />
                <Bar dataKey="value" fill="var(--success-color)" radius={[4, 4, 0, 0]} name="Unidades" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Costos por Empresa */}
        <div id="chart-costos" className="glass-panel chart-container" style={{gridColumn: 'span 2'}}>
          <div className="flex items-center justify-between mb-4">
            <h3 style={{fontSize: '1.2rem', margin: 0, color: 'var(--text-color)'}}>Costos Totales en Medicamentos por Empresa</h3>
            <button className="no-print action-btn view" onClick={() => handlePrintChart('chart-costos')} title="Imprimir este gráfico">
              <Printer size={18} color="#f43f5e" />
            </button>
          </div>
          <div style={{width: '100%', height: 350}}>
            <ResponsiveContainer>
              <BarChart data={stats.costos} margin={{top: 5, right: 30, left: 20, bottom: 5}}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="name" stroke="#94a3b8" />
                <YAxis stroke="#94a3b8" tickFormatter={(val) => `S/ ${val}`} />
                <RechartsTooltip formatter={(value) => `S/ ${value.toFixed(2)}`} contentStyle={{backgroundColor: '#1e293b', border: 'none', borderRadius: '8px'}} />
                <Bar dataKey="value" fill="#f43f5e" radius={[4, 4, 0, 0]} name="Costo Total" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
