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
const generateReport = ({ title, subtitle, dateRange, bodyHtml, summaryNote, chartSvgHtml }) => {
  const now = new Date();
  const dateStr = format(now, "dd 'de' MMMM 'de' yyyy, HH:mm", { locale: es });

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
      -webkit-print-color-adjust: exact;
      print-color-adjust: exact;
    }
    .page { max-width: 850px; margin: 0 auto; padding: 40px; }
    .report-header {
      display: flex; align-items: flex-start; justify-content: space-between;
      border-bottom: 3px solid #0ea5e9; padding-bottom: 16px; margin-bottom: 24px;
    }
    .report-brand { display: flex; align-items: center; gap: 14px; }
    .report-brand img { height: 50px; }
    .report-brand-text h2 { font-size: 1.4rem; font-weight: 700; color: #0f172a; margin: 0; }
    .report-brand-text p { font-size: 0.8rem; color: #64748b; margin: 2px 0 0; }
    .report-meta { text-align: right; font-size: 0.78rem; color: #64748b; line-height: 1.6; }
    .report-meta strong { color: #334155; }
    .report-title-bar {
      background: linear-gradient(135deg, #0f172a, #1e293b);
      color: #fff; padding: 14px 20px; border-radius: 8px; margin-bottom: 24px;
    }
    .report-title-bar h1 { font-size: 1.15rem; font-weight: 600; margin: 0; }
    .report-title-bar p { font-size: 0.8rem; opacity: 0.7; margin: 4px 0 0; }
    .report-chart { margin-bottom: 28px; text-align: center; }
    .report-chart svg { max-width: 100%; height: auto; }
    /* Main table */
    .rtbl { width: 100%; border-collapse: collapse; margin-bottom: 8px; font-size: 0.85rem; }
    .rtbl th {
      background: #f1f5f9; color: #475569; font-weight: 600;
      text-transform: uppercase; font-size: 0.7rem; letter-spacing: 0.05em;
      padding: 8px 12px; text-align: left; border-bottom: 2px solid #e2e8f0;
    }
    .rtbl td { padding: 8px 12px; border-bottom: 1px solid #f1f5f9; color: #334155; vertical-align: top; }
    .rtbl tr:nth-child(even) > td { background: #f8fafc; }
    .rtbl .num { text-align: center; color: #64748b; font-weight: 600; width: 35px; }
    .rtbl .val { text-align: right; font-weight: 700; }
    .rtbl tfoot td { font-weight: 700; border-top: 2px solid #e2e8f0; background: #f1f5f9; color: #0f172a; }
    /* Sub-detail table */
    .detail-tbl { width: 100%; border-collapse: collapse; margin: 6px 0 0; font-size: 0.78rem; }
    .detail-tbl th {
      background: #eef2ff; color: #6366f1; font-weight: 600; font-size: 0.68rem;
      text-transform: uppercase; letter-spacing: 0.04em; padding: 5px 8px;
      text-align: left; border-bottom: 1px solid #e0e7ff;
    }
    .detail-tbl td { padding: 4px 8px; border-bottom: 1px solid #f1f5f9; color: #475569; }
    .detail-tbl tr:nth-child(even) td { background: #fafbff; }
    .section-block { margin-bottom: 24px; border: 1px solid #e2e8f0; border-radius: 10px; overflow: hidden; }
    .section-title {
      background: linear-gradient(135deg, #1e293b, #334155);
      color: #fff; padding: 10px 16px; font-weight: 600; font-size: 0.9rem;
      display: flex; justify-content: space-between; align-items: center;
    }
    .section-title .badge {
      background: rgba(255,255,255,0.15); padding: 2px 10px; border-radius: 12px; font-size: 0.78rem;
    }
    .section-body { padding: 12px 16px; }
    .section-meta { display: flex; gap: 20px; margin-bottom: 8px; font-size: 0.78rem; color: #64748b; }
    .section-meta strong { color: #334155; }
    /* Summary */
    .report-summary {
      background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px;
      padding: 14px 18px; font-size: 0.82rem; color: #475569; margin: 20px 0;
    }
    .report-summary strong { color: #1e293b; }
    .report-footer {
      border-top: 1px solid #e2e8f0; padding-top: 12px;
      display: flex; justify-content: space-between; font-size: 0.72rem; color: #94a3b8;
    }
    @media print {
      body { padding: 0; }
      .page { padding: 20px; max-width: none; }
      .no-print { display: none !important; }
      .section-block { break-inside: avoid; }
    }
    .print-actions { text-align: center; margin-bottom: 24px; }
    .print-actions button {
      background: linear-gradient(135deg, #0ea5e9, #8b5cf6); color: #fff;
      border: none; padding: 10px 28px; border-radius: 8px;
      font-size: 0.95rem; font-weight: 500; cursor: pointer; font-family: inherit; margin: 0 6px;
    }
    .print-actions button:hover { opacity: 0.9; }
    .print-actions button.secondary { background: #e2e8f0; color: #475569; }
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
        <strong>Fecha de emisión:</strong><br/>${dateStr}<br/><br/>
        <strong>Periodo:</strong><br/>${dateRange}
      </div>
    </div>
    <div class="report-title-bar">
      <h1>${title}</h1>
      ${subtitle ? `<p>${subtitle}</p>` : ''}
    </div>
    ${chartSvgHtml ? `<div class="report-chart">${chartSvgHtml}</div>` : ''}
    ${bodyHtml}
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
    costos: [],
    estado_empresas: [],
    atenciones_por_dia: [],
    ultimas_atenciones: [],
    sistemas_afectados: []
  });

  const [allEmpresas, setAllEmpresas] = useState([]);
  const [allSistemas, setAllSistemas] = useState([]);
  const [allObras, setAllObras] = useState([]);
  const [empresaFilter, setEmpresaFilter] = useState('ALL'); // 'ALL' or 'ACTIVO'

  const [startDate, setStartDate] = useState(null);
  const [endDate, setEndDate] = useState(null);

  // Filtros y datos para el cuadro específico de Sistemas Atendidos
  const [repSistemas, setRepSistemas] = useState({ total_general: 0, sistemas: [] });
  const [repSisFiltros, setRepSisFiltros] = useState({
    fecha_inicio: null,
    fecha_fin: null,
    sistema_id: '',
    empresa_id: '',
    obra: ''
  });

  useEffect(() => {
    fetch(API_URL + '/dashboard/kpis')
      .then(res => res.json())
      .then(data => setKpis(data))
      .catch(err => console.error(err));
      
    fetch(API_URL + '/empresas/')
      .then(res => res.json())
      .then(data => setAllEmpresas(data))
      .catch(err => console.error(err));

    fetch(API_URL + '/sistemas/')
      .then(res => res.json())
      .then(data => setAllSistemas(data))
      .catch(err => console.error(err));

    fetch(API_URL + '/trabajadores/obras')
      .then(res => res.json())
      .then(data => setAllObras(data))
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

  useEffect(() => {
    let url = API_URL + '/dashboard/reporte-sistemas?';
    if (repSisFiltros.fecha_inicio) url += `fecha_inicio=${format(repSisFiltros.fecha_inicio, 'yyyy-MM-dd')}&`;
    if (repSisFiltros.fecha_fin) url += `fecha_fin=${format(repSisFiltros.fecha_fin, 'yyyy-MM-dd')}&`;
    if (repSisFiltros.sistema_id) url += `sistema_id=${repSisFiltros.sistema_id}&`;
    if (repSisFiltros.empresa_id) url += `empresa_id=${repSisFiltros.empresa_id}&`;
    if (repSisFiltros.obra) url += `obra=${encodeURIComponent(repSisFiltros.obra)}`;
    
    fetch(url)
      .then(res => res.json())
      .then(data => setRepSistemas(data))
      .catch(err => console.error(err));
  }, [repSisFiltros]);

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

  const handlePrintReport = async (chartId) => {
    const dateRange = getDateRangeLabel();
    const chartSvg = captureChartSvg(chartId);

    // Map chartId to report type
    const typeMap = {
      'chart-enf': 'enfermedades',
      'chart-pac': 'pacientes',
      'chart-emp': 'empresas',
      'chart-med': 'medicamentos',
      'chart-costos': 'costos'
    };
    const reportType = typeMap[chartId];
    if (!reportType) return;

    // Fetch detailed data
    let url = `${API_URL}/dashboard/report/${reportType}?`;
    if (startDate) url += `fecha_inicio=${format(startDate, 'yyyy-MM-dd')}&`;
    if (endDate) url += `fecha_fin=${format(endDate, 'yyyy-MM-dd')}`;

    let detailData = [];
    try {
      const res = await fetch(url);
      detailData = await res.json();
    } catch (err) {
      console.error(err);
    }

    // Build rich HTML body per report type
    let bodyHtml = '';
    let summaryNote = '';

    if (reportType === 'enfermedades') {
      const totalAten = detailData.reduce((s, d) => s + d.total, 0);
      bodyHtml = detailData.map((item, i) => `
        <div class="section-block">
          <div class="section-title">
            <span>${i + 1}. ${item.name}</span>
            <span class="badge">${item.total} atención${item.total > 1 ? 'es' : ''}</span>
          </div>
          <div class="section-body">
            <table class="detail-tbl">
              <thead><tr><th>Fecha</th><th>Paciente</th><th>DNI</th><th>Empresa</th><th>Área</th></tr></thead>
              <tbody>
                ${item.details.map(d => `<tr><td>${d.fecha}</td><td>${d.paciente}</td><td>${d.dni}</td><td>${d.empresa}</td><td>${d.area}</td></tr>`).join('')}
              </tbody>
            </table>
          </div>
        </div>
      `).join('');
      summaryNote = `<strong>Resumen:</strong> Se registraron <strong>${totalAten}</strong> atenciones distribuidas en <strong>${detailData.length}</strong> diagnósticos distintos durante el periodo seleccionado.`;
    }

    else if (reportType === 'pacientes') {
      const totalAten = detailData.reduce((s, d) => s + d.total, 0);
      bodyHtml = detailData.map((item, i) => `
        <div class="section-block">
          <div class="section-title">
            <span>${i + 1}. ${item.name}</span>
            <span class="badge">${item.total} atención${item.total > 1 ? 'es' : ''}</span>
          </div>
          <div class="section-body">
            <div class="section-meta">
              <span><strong>DNI:</strong> ${item.dni}</span>
              <span><strong>Cargo:</strong> ${item.cargo}</span>
              <span><strong>Área:</strong> ${item.area}</span>
            </div>
            <table class="detail-tbl">
              <thead><tr><th>Fecha</th><th>Diagnóstico</th><th>Empresa</th><th>Destino</th></tr></thead>
              <tbody>
                ${item.details.map(d => `<tr><td>${d.fecha}</td><td>${d.diagnostico}</td><td>${d.empresa}</td><td>${d.destino}</td></tr>`).join('')}
              </tbody>
            </table>
          </div>
        </div>
      `).join('');
      summaryNote = `<strong>Resumen:</strong> Los <strong>${detailData.length}</strong> pacientes más atendidos acumulan un total de <strong>${totalAten}</strong> atenciones. Se recomienda evaluar seguimiento preventivo.`;
    }

    else if (reportType === 'empresas') {
      const totalAten = detailData.reduce((s, d) => s + d.total, 0);
      bodyHtml = detailData.map((item, i) => `
        <div class="section-block">
          <div class="section-title">
            <span>${i + 1}. ${item.name}</span>
            <span class="badge">${item.total} atención${item.total > 1 ? 'es' : ''}</span>
          </div>
          <div class="section-body">
            <div class="section-meta">
              <span><strong>RUC:</strong> ${item.ruc || '—'}</span>
            </div>
            <table class="detail-tbl">
              <thead><tr><th>Fecha</th><th>Paciente</th><th>Diagnóstico</th><th>Destino</th></tr></thead>
              <tbody>
                ${item.details.map(d => `<tr><td>${d.fecha}</td><td>${d.paciente}</td><td>${d.diagnostico}</td><td>${d.destino}</td></tr>`).join('')}
              </tbody>
            </table>
          </div>
        </div>
      `).join('');
      summaryNote = `<strong>Resumen:</strong> Las <strong>${detailData.length}</strong> empresas registran un total acumulado de <strong>${totalAten}</strong> atenciones en el periodo consultado.`;
    }

    else if (reportType === 'medicamentos') {
      const totalUnid = detailData.reduce((s, d) => s + d.total, 0);
      const totalCost = detailData.reduce((s, d) => s + d.costo_total, 0);
      bodyHtml = `
        <table class="rtbl">
          <thead><tr>
            <th class="num">#</th><th>Medicamento</th><th>Presentación</th>
            <th style="text-align:right">C. Unit. (S/)</th>
            <th style="text-align:right">Dispensado</th>
            <th style="text-align:right">Stock Actual</th>
            <th style="text-align:right">Costo Total (S/)</th>
          </tr></thead>
          <tbody>
            ${detailData.map((m, i) => `<tr>
              <td class="num">${i + 1}</td>
              <td><strong>${m.name}</strong></td>
              <td>${m.presentacion}</td>
              <td class="val">${m.costo_unitario.toFixed(2)}</td>
              <td class="val">${m.total}</td>
              <td class="val">${m.stock_actual}</td>
              <td class="val">${m.costo_total.toFixed(2)}</td>
            </tr>`).join('')}
          </tbody>
          <tfoot><tr>
            <td></td><td colspan="3" style="text-align:right">TOTALES</td>
            <td class="val">${totalUnid}</td><td></td>
            <td class="val">S/ ${totalCost.toFixed(2)}</td>
          </tr></tfoot>
        </table>
      `;
      summaryNote = `<strong>Resumen:</strong> Se dispensaron <strong>${totalUnid}</strong> unidades de <strong>${detailData.length}</strong> medicamentos distintos, con un costo total de <strong>S/ ${totalCost.toFixed(2)}</strong>.`;
    }

    else if (reportType === 'costos') {
      const grandTotal = detailData.reduce((s, d) => s + d.total, 0);
      bodyHtml = detailData.map((item, i) => `
        <div class="section-block">
          <div class="section-title">
            <span>${i + 1}. ${item.name}</span>
            <span class="badge">S/ ${item.total.toFixed(2)}</span>
          </div>
          <div class="section-body">
            <div class="section-meta">
              <span><strong>RUC:</strong> ${item.ruc || '—'}</span>
            </div>
            <table class="detail-tbl">
              <thead><tr><th>Medicamento</th><th>Presentación</th><th style="text-align:right">Cantidad</th><th style="text-align:right">C. Unit. (S/)</th><th style="text-align:right">Subtotal (S/)</th></tr></thead>
              <tbody>
                ${item.details.map(d => `<tr><td>${d.medicamento}</td><td>${d.presentacion}</td><td style="text-align:right">${d.cantidad}</td><td style="text-align:right">${d.costo_unitario.toFixed(2)}</td><td style="text-align:right;font-weight:600">${d.subtotal.toFixed(2)}</td></tr>`).join('')}
              </tbody>
            </table>
          </div>
        </div>
      `).join('');
      summaryNote = `<strong>Resumen:</strong> El gasto total en medicamentos para las <strong>${detailData.length}</strong> empresas asciende a <strong>S/ ${grandTotal.toFixed(2)}</strong> en el periodo consultado. Este dato es clave para la facturación y control presupuestario.`;
    }

    const configs = {
      'chart-enf': { title: 'Reporte de Enfermedades Más Atendidas', subtitle: 'Detalle de atenciones agrupadas por diagnóstico' },
      'chart-pac': { title: 'Reporte de Pacientes Más Atendidos', subtitle: 'Historial de atenciones por cada trabajador con mayor recurrencia' },
      'chart-emp': { title: 'Reporte de Atenciones por Empresa', subtitle: 'Desglose de atenciones médicas agrupadas por empresa contratante' },
      'chart-med': { title: 'Reporte de Medicamentos Más Usados', subtitle: 'Detalle de medicamentos dispensados con costos y stock' },
      'chart-costos': { title: 'Reporte de Costos Totales por Empresa', subtitle: 'Desglose de gasto en medicamentos por empresa contratante' }
    };

    generateReport({
      ...configs[chartId],
      dateRange,
      chartSvgHtml: chartSvg,
      bodyHtml,
      summaryNote
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
        {/* 4. Reporte Específico de Sistemas Atendidos */}
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
                      onChange={date => setRepSisFiltros({...repSisFiltros, fecha_inicio: date})}
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
                      onChange={date => setRepSisFiltros({...repSisFiltros, fecha_fin: date})}
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
                  onChange={e => setRepSisFiltros({...repSisFiltros, sistema_id: e.target.value})}
                  style={{ cursor: 'pointer' }}
                >
                  <option value="">Todos los sistemas...</option>
                  {allSistemas.map(s => <option key={s.id} value={s.id}>{s.nombre}</option>)}
                </select>
              </div>
              <div style={{ flex: '1 1 200px' }}>
                <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: '500', color: 'var(--text-color)', marginBottom: '8px' }}>Empresa Contratante</label>
                <select 
                  className="form-control" 
                  value={repSisFiltros.empresa_id} 
                  onChange={e => setRepSisFiltros({...repSisFiltros, empresa_id: e.target.value})}
                  style={{ cursor: 'pointer' }}
                >
                  <option value="">Todas las empresas...</option>
                  {allEmpresas.map(e => <option key={e.id} value={e.id}>{e.nombre}</option>)}
                </select>
              </div>
              <div style={{ flex: '1 1 200px' }}>
                <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: '500', color: 'var(--text-color)', marginBottom: '8px' }}>Obra</label>
                <select 
                  className="form-control" 
                  value={repSisFiltros.obra} 
                  onChange={e => setRepSisFiltros({...repSisFiltros, obra: e.target.value})}
                  style={{ cursor: 'pointer' }}
                >
                  <option value="">Todas las obras...</option>
                  {allObras.map(o => <option key={o} value={o}>{o}</option>)}
                </select>
              </div>
            </div>

            {/* Resultados */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
              <div style={{ width: '100%', display: 'flex', flexDirection: 'column', gap: '20px', minWidth: 0 }}>
                {/* KPI Total */}
                <div style={{ padding: '24px', background: 'linear-gradient(135deg, rgba(14, 165, 233, 0.1), rgba(139, 92, 246, 0.05))', borderRadius: '12px', border: '1px solid rgba(14, 165, 233, 0.2)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <div>
                    <span style={{ display: 'block', fontSize: '0.9rem', fontWeight: '500', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Total Atenciones</span>
                    <span style={{ display: 'block', fontSize: '0.8rem', color: 'rgba(255,255,255,0.4)', marginTop: '4px' }}>Según filtros aplicados</span>
                  </div>
                  <span style={{ display: 'block', fontSize: '3rem', lineHeight: '1', fontWeight: '800', color: 'var(--primary-color)', textShadow: '0 0 20px rgba(14,165,233,0.3)' }}>
                    {repSistemas.total_general}
                  </span>
                </div>
                
                {/* Lista */}
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
                    <BarChart data={repSistemas.sistemas} margin={{top: 10, right: 20, left: 0, bottom: 70}}>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.05)" horizontal={true} vertical={false} />
                      <XAxis dataKey="name" type="category" interval={0} height={70} stroke="#475569" tick={{fontSize: 11, fill: '#cbd5e1'}} axisLine={{stroke: '#334155'}} tickLine={false} angle={-35} textAnchor="end" tickFormatter={(val) => val.length > 18 ? val.substring(0, 18) + '…' : val} />
                      <YAxis type="number" allowDecimals={false} width={40} stroke="#475569" tick={{fontSize: 11, fill: '#94a3b8'}} axisLine={{stroke: '#334155'}} tickLine={false} />
                      <RechartsTooltip cursor={{fill: 'rgba(255,255,255,0.02)'}} contentStyle={{backgroundColor: '#0f172a', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', boxShadow: '0 10px 25px rgba(0,0,0,0.5)', color: '#fff'}} itemStyle={{color: '#38bdf8', fontWeight: '600'}} />
                      <Bar dataKey="value" fill="#8b5cf6" maxBarSize={56} radius={[4, 4, 0, 0]} name="Atenciones" animationDuration={1000}>
                        {
                          repSistemas.sistemas.map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={`hsl(${190 + (index * 15)}, 80%, 55%)`} />
                          ))
                        }
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
