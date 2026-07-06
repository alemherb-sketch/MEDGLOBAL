import { useState, useEffect } from 'react';
import { API_URL } from '../config';
import { Users, Stethoscope, Pill, AlertTriangle, Printer, CalendarRange, FileText } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import DatePicker from 'react-datepicker';
import 'react-datepicker/dist/react-datepicker.css';
import { format } from 'date-fns';
import { es } from 'date-fns/locale';

const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4', '#f97316', '#14b8a6'];

/* ══════════════════════════════════════════════════
   REPORT GENERATOR — opens a new window with a
   professional formatted report ready for PDF print
   ══════════════════════════════════════════════════ */
const generateReport = ({ title, subtitle, dateRange, columns, rows, chartSvgHtml, summaryNote }) => {
  const now = new Date();
  const dateStr = format(now, "dd 'de' MMMM 'de' yyyy, HH:mm", { locale: es });

  const tableRows = rows.map((row, i) => `
    <tr>
      <td style="text-align:center; color:#64748b; font-weight:600;">${i + 1}</td>
      ${row.map((cell, ci) => `<td style="${ci === row.length - 1 ? 'text-align:right; font-weight:700;' : ''}">${cell}</td>`).join('')}
    </tr>
  `).join('');

  const totalValue = rows.reduce((acc, r) => acc + (parseFloat(r[r.length - 1].replace(/[^0-9.]/g, '')) || 0), 0);

  const html = `<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <title>${title} - MEDGLOBAL</title>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: 'Inter', 'Segoe UI', sans-serif;
      color: #1e293b;
      background: #fff;
      padding: 0;
      -webkit-print-color-adjust: exact;
      print-color-adjust: exact;
    }
    .page {
      max-width: 800px;
      margin: 0 auto;
      padding: 40px;
    }
    /* Header */
    .report-header {
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      border-bottom: 3px solid #0ea5e9;
      padding-bottom: 16px;
      margin-bottom: 24px;
    }
    .report-brand {
      display: flex;
      align-items: center;
      gap: 14px;
    }
    .report-brand img {
      height: 50px;
    }
    .report-brand-text h2 {
      font-size: 1.4rem;
      font-weight: 700;
      color: #0f172a;
      margin: 0;
    }
    .report-brand-text p {
      font-size: 0.8rem;
      color: #64748b;
      margin: 2px 0 0;
    }
    .report-meta {
      text-align: right;
      font-size: 0.78rem;
      color: #64748b;
      line-height: 1.6;
    }
    .report-meta strong {
      color: #334155;
    }
    /* Title bar */
    .report-title-bar {
      background: linear-gradient(135deg, #0f172a, #1e293b);
      color: #fff;
      padding: 14px 20px;
      border-radius: 8px;
      margin-bottom: 24px;
    }
    .report-title-bar h1 {
      font-size: 1.15rem;
      font-weight: 600;
      margin: 0;
    }
    .report-title-bar p {
      font-size: 0.8rem;
      opacity: 0.7;
      margin: 4px 0 0;
    }
    /* Chart area */
    .report-chart {
      margin-bottom: 28px;
      text-align: center;
    }
    .report-chart svg {
      max-width: 100%;
      height: auto;
    }
    /* Table */
    .report-table {
      width: 100%;
      border-collapse: collapse;
      margin-bottom: 20px;
      font-size: 0.88rem;
    }
    .report-table thead th {
      background: #f1f5f9;
      color: #475569;
      font-weight: 600;
      text-transform: uppercase;
      font-size: 0.72rem;
      letter-spacing: 0.05em;
      padding: 10px 14px;
      text-align: left;
      border-bottom: 2px solid #e2e8f0;
    }
    .report-table thead th:first-child {
      text-align: center;
      width: 40px;
    }
    .report-table tbody td {
      padding: 10px 14px;
      border-bottom: 1px solid #f1f5f9;
      color: #334155;
    }
    .report-table tbody tr:nth-child(even) {
      background: #f8fafc;
    }
    .report-table tbody tr:hover {
      background: #eff6ff;
    }
    .report-table tfoot td {
      padding: 10px 14px;
      font-weight: 700;
      border-top: 2px solid #e2e8f0;
      background: #f1f5f9;
      color: #0f172a;
    }
    /* Summary */
    .report-summary {
      background: #f8fafc;
      border: 1px solid #e2e8f0;
      border-radius: 8px;
      padding: 14px 18px;
      font-size: 0.82rem;
      color: #475569;
      margin-bottom: 24px;
    }
    .report-summary strong { color: #1e293b; }
    /* Footer */
    .report-footer {
      border-top: 1px solid #e2e8f0;
      padding-top: 12px;
      display: flex;
      justify-content: space-between;
      font-size: 0.72rem;
      color: #94a3b8;
    }
    /* Print */
    @media print {
      body { padding: 0; }
      .page { padding: 20px; max-width: none; }
      .no-print { display: none !important; }
    }
    .print-actions {
      text-align: center;
      margin-bottom: 24px;
    }
    .print-actions button {
      background: linear-gradient(135deg, #0ea5e9, #8b5cf6);
      color: #fff;
      border: none;
      padding: 10px 28px;
      border-radius: 8px;
      font-size: 0.95rem;
      font-weight: 500;
      cursor: pointer;
      font-family: inherit;
      margin: 0 6px;
    }
    .print-actions button:hover { opacity: 0.9; }
    .print-actions button.secondary {
      background: #e2e8f0;
      color: #475569;
    }
  </style>
</head>
<body>
  <div class="page">
    <div class="print-actions no-print">
      <button onclick="window.print()">🖨️ Imprimir / Guardar PDF</button>
      <button class="secondary" onclick="window.close()">Cerrar</button>
    </div>

    <div class="report-header">
      <div class="report-brand">
        <img src="${window.location.origin}/logo.png" alt="MEDGLOBAL" />
        <div class="report-brand-text">
          <h2>MEDGLOBAL</h2>
          <p>Sistema de Gestión de Salud Ocupacional</p>
        </div>
      </div>
      <div class="report-meta">
        <strong>Fecha de emisión:</strong><br/>
        ${dateStr}<br/><br/>
        <strong>Periodo:</strong><br/>
        ${dateRange}
      </div>
    </div>

    <div class="report-title-bar">
      <h1>${title}</h1>
      ${subtitle ? `<p>${subtitle}</p>` : ''}
    </div>

    ${chartSvgHtml ? `<div class="report-chart">${chartSvgHtml}</div>` : ''}

    <table class="report-table">
      <thead>
        <tr>
          <th>#</th>
          ${columns.map(c => `<th${c.align ? ` style="text-align:${c.align}"` : ''}>${c.label}</th>`).join('')}
        </tr>
      </thead>
      <tbody>
        ${tableRows}
      </tbody>
      ${rows.length > 0 ? `
      <tfoot>
        <tr>
          <td></td>
          <td style="text-align:right;" colspan="${columns.length - 1}">TOTAL</td>
          <td style="text-align:right;">${columns[columns.length - 1].isCurrency ? 'S/ ' + totalValue.toFixed(2) : totalValue}</td>
        </tr>
      </tfoot>` : ''}
    </table>

    ${summaryNote ? `<div class="report-summary">${summaryNote}</div>` : ''}

    <div class="report-footer">
      <span>MEDGLOBAL — Reporte generado automáticamente</span>
      <span>Página 1 de 1</span>
    </div>
  </div>
</body>
</html>`;

  const reportWindow = window.open('', '_blank');
  reportWindow.document.write(html);
  reportWindow.document.close();
};


/* ══════════════════════════════════════════════════
   ChartCard Component
   ══════════════════════════════════════════════════ */
const ChartCard = ({ id, title, children, onPrint }) => (
  <div id={id} className="dash-chart-card">
    <div className="dash-chart-header">
      <h3 className="dash-chart-title">{title}</h3>
      <button className="no-print dash-print-btn" onClick={() => onPrint(id)} title="Generar Reporte">
        <FileText size={16} />
      </button>
    </div>
    <div className="dash-chart-body">
      {children}
    </div>
  </div>
);


/* ══════════════════════════════════════════════════
   DASHBOARD
   ══════════════════════════════════════════════════ */
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

  const getDateRangeLabel = () => {
    if (startDate && endDate) return `${format(startDate, 'dd/MM/yyyy')} — ${format(endDate, 'dd/MM/yyyy')}`;
    if (startDate) return `Desde ${format(startDate, 'dd/MM/yyyy')}`;
    if (endDate) return `Hasta ${format(endDate, 'dd/MM/yyyy')}`;
    return 'Todos los registros (sin filtro)';
  };

  const captureChartSvg = (chartId) => {
    const card = document.getElementById(chartId);
    if (!card) return '';
    const svg = card.querySelector('.recharts-wrapper svg');
    if (!svg) return '';
    
    // Deep clone and inline all computed styles
    const clone = svg.cloneNode(true);
    const origElements = svg.querySelectorAll('*');
    const cloneElements = clone.querySelectorAll('*');
    
    origElements.forEach((orig, i) => {
      const cs = window.getComputedStyle(orig);
      const target = cloneElements[i];
      if (!target) return;
      // Inline key visual properties
      ['fill', 'stroke', 'stroke-width', 'stroke-dasharray', 'opacity',
       'font-size', 'font-family', 'font-weight', 'text-anchor',
       'dominant-baseline', 'color'].forEach(prop => {
        const val = cs.getPropertyValue(prop);
        if (val && val !== 'none' && val !== 'normal' && val !== '') {
          target.style.setProperty(prop, val);
        }
      });
    });
    
    clone.removeAttribute('class');
    clone.setAttribute('width', '700');
    clone.setAttribute('height', '300');
    clone.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
    clone.style.background = 'transparent';
    
    return clone.outerHTML;
  };

  const handlePrintReport = (chartId) => {
    const dateRange = getDateRangeLabel();
    const chartSvg = captureChartSvg(chartId);

    const reportConfigs = {
      'chart-enf': {
        title: 'Reporte de Enfermedades Más Atendidas',
        subtitle: 'Ranking de diagnósticos con mayor frecuencia de atención médica',
        columns: [{ label: 'Enfermedad / Diagnóstico' }, { label: 'Nº Atenciones', align: 'right' }],
        rows: stats.enfermedades.map(e => [e.name, String(e.value)]),
        summaryNote: `<strong>Análisis:</strong> Este reporte muestra las ${stats.enfermedades.length} enfermedades que concentran la mayor cantidad de atenciones médicas en el periodo seleccionado. Utilice esta información para planificar campañas de prevención y abastecimiento de medicamentos.`
      },
      'chart-pac': {
        title: 'Reporte de Pacientes Más Atendidos',
        subtitle: 'Trabajadores con mayor frecuencia de visitas al tópico médico',
        columns: [{ label: 'Nombre del Paciente' }, { label: 'Nº Atenciones', align: 'right' }],
        rows: stats.pacientes.map(p => [p.name, String(p.value)]),
        summaryNote: `<strong>Análisis:</strong> Se identificaron ${stats.pacientes.length} pacientes con alta recurrencia de atenciones. Se recomienda evaluar estos casos para seguimiento preventivo o derivación especializada.`
      },
      'chart-emp': {
        title: 'Reporte de Atenciones por Empresa',
        subtitle: 'Distribución de atenciones médicas agrupadas por empresa contratante',
        columns: [{ label: 'Empresa' }, { label: 'Nº Atenciones', align: 'right' }],
        rows: stats.empresas.map(e => [e.name, String(e.value)]),
        summaryNote: `<strong>Análisis:</strong> Este reporte permite comparar la demanda de servicios médicos entre las diferentes empresas. Las empresas con mayor número de atenciones podrían requerir revisiones de sus condiciones laborales.`
      },
      'chart-med': {
        title: 'Reporte de Medicamentos Más Usados',
        subtitle: 'Medicamentos con mayor volumen de dispensación en el periodo',
        columns: [{ label: 'Medicamento' }, { label: 'Unidades Dispensadas', align: 'right' }],
        rows: stats.medicamentos.map(m => [m.name, String(m.value)]),
        summaryNote: `<strong>Análisis:</strong> Este ranking de consumo de medicamentos permite optimizar la gestión de inventario y anticipar necesidades de reposición de stock en la farmacia.`
      },
      'chart-costos': {
        title: 'Reporte de Costos Totales por Empresa',
        subtitle: 'Gasto acumulado en medicamentos desglosado por empresa contratante',
        columns: [{ label: 'Empresa' }, { label: 'Costo Total (S/)', align: 'right', isCurrency: true }],
        rows: stats.costos.map(c => [c.name, 'S/ ' + c.value.toFixed(2)]),
        summaryNote: `<strong>Análisis:</strong> El costo total refleja la suma de medicamentos dispensados (precio unitario × cantidad) para cada empresa. Este informe es clave para la facturación y control de gastos por convenio.`
      }
    };

    const config = reportConfigs[chartId];
    if (!config) return;

    generateReport({
      ...config,
      dateRange,
      chartSvgHtml: chartSvg
    });
  };

  const handlePrintAll = () => {
    window.print();
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
          <button className="btn btn-primary" onClick={handlePrintAll}>
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
        <ChartCard id="chart-enf" title="Top Enfermedades Más Atendidas" onPrint={handlePrintReport}>
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

        <ChartCard id="chart-pac" title="Pacientes Más Atendidos" onPrint={handlePrintReport}>
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

        <ChartCard id="chart-emp" title="Atenciones por Empresa" onPrint={handlePrintReport}>
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

        <ChartCard id="chart-med" title="Medicamentos Más Usados" onPrint={handlePrintReport}>
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

        <ChartCard id="chart-costos" title="Costos Totales en Medicamentos por Empresa" onPrint={handlePrintReport}>
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
