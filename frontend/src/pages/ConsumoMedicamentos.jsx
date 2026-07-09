import React, { useState, useEffect } from 'react';
import DatePicker from 'react-datepicker';
import 'react-datepicker/dist/react-datepicker.css';
import { Download, Printer, Search } from 'lucide-react';
import * as XLSX from 'xlsx';
import { API_URL } from '../config';

const ConsumoMedicamentos = () => {
  const [empresas, setEmpresas] = useState([]);
  const [filtros, setFiltros] = useState({
    empresa_id: '',
    fecha_inicio: null,
    fecha_fin: null
  });
  
  const [reporte, setReporte] = useState({
    rango_fechas: [],
    medicamentos: [],
    totales: { sub_total: 0, igv: 0, total: 0 }
  });
  
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    fetch(`${API_URL}/empresas/`)
      .then(res => res.json())
      .then(data => setEmpresas(data))
      .catch(err => console.error("Error fetching empresas:", err));
  }, []);

  const handleSearch = async () => {
    setIsLoading(true);
    try {
      const params = new URLSearchParams();
      if (filtros.empresa_id) params.append('empresa_id', filtros.empresa_id);
      if (filtros.fecha_inicio) params.append('fecha_inicio', filtros.fecha_inicio.toISOString().split('T')[0]);
      if (filtros.fecha_fin) params.append('fecha_fin', filtros.fecha_fin.toISOString().split('T')[0]);
      
      const res = await fetch(`${API_URL}/reportes/consumo-medicamentos?${params.toString()}`);
      const data = await res.json();
      setReporte(data);
    } catch (err) {
      console.error("Error fetching report:", err);
    } finally {
      setIsLoading(false);
    }
  };

  const handlePrint = () => {
    window.print();
  };

  const handleExportExcel = () => {
    if (!reporte.medicamentos.length) return;
    
    const empresaSeleccionada = empresas.find(e => e.id.toString() === filtros.empresa_id);
    const empresaName = empresaSeleccionada ? empresaSeleccionada.nombre : 'Todas las Empresas';
    
    const fInicio = filtros.fecha_inicio ? filtros.fecha_inicio.toLocaleDateString() : '';
    const fFin = filtros.fecha_fin ? filtros.fecha_fin.toLocaleDateString() : '';
    const dateRangeText = (fInicio && fFin) ? `${fInicio} al ${fFin}` : 'Todas las fechas';
    
    const aoa = [
      ['Reporte de Consumo de Medicamentos'],
      ['Empresa: ' + empresaName],
      ['Fechas: ' + dateRangeText],
      [],
      ['Código', 'Medicamento', 'Presentación', ...reporte.rango_fechas, 'Sub Total (Cant)', 'Precio UND', 'Total (Soles)']
    ];

    reporte.medicamentos.forEach(med => {
      const row = [med.codigo, med.nombre, med.presentacion];
      reporte.rango_fechas.forEach(fecha => {
        row.push(med.consumos[fecha] || 0);
      });
      row.push(med.sub_total_cantidad, med.precio_und, med.total_soles);
      aoa.push(row);
    });

    aoa.push([]); // Empty row before totals

    const makeTotalRow = (labelC, labelF, valG) => {
      const row = new Array(3 + reporte.rango_fechas.length + 3).fill('');
      if (labelC) row[2] = labelC;
      row[3 + reporte.rango_fechas.length + 1] = labelF;
      row[3 + reporte.rango_fechas.length + 2] = valG;
      return row;
    };

    aoa.push(makeTotalRow('TOTALES', 'SUB TOTAL', reporte.totales.sub_total));
    aoa.push(makeTotalRow('', 'IGV (18%)', reporte.totales.igv));
    aoa.push(makeTotalRow('', 'TOTAL GENERAL', reporte.totales.total));

    const worksheet = XLSX.utils.aoa_to_sheet(aoa);
    const workbook = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(workbook, worksheet, "Consumo Medicamentos");
    XLSX.writeFile(workbook, "Reporte_Consumo_Medicamentos.xlsx");
  };

  return (
    <div className="page-container" style={{ padding: '24px' }}>
      <div className="dash-header no-print" style={{ marginBottom: '24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ fontSize: '1.8rem', fontWeight: 'bold', color: 'var(--primary-color)', margin: 0 }}>Consumo Medicamentos</h2>
          <p style={{ color: 'var(--text-muted)', margin: '4px 0 0 0' }}>Reporte de medicamentos consumidos por empresa</p>
        </div>
        <div style={{ display: 'flex', gap: '12px' }}>
          <button className="btn btn-secondary" onClick={handleExportExcel} disabled={!reporte.medicamentos.length} style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Download size={18} /> Exportar Excel
          </button>
          <button className="btn btn-primary" onClick={handlePrint} disabled={!reporte.medicamentos.length} style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Printer size={18} /> Imprimir
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="dash-chart-card no-print" style={{ marginBottom: '24px', overflow: 'visible' }}>
        <div className="dash-chart-body" style={{ padding: '20px' }}>
          <div style={{ display: 'flex', gap: '20px', flexWrap: 'wrap', alignItems: 'flex-end' }}>
            <div style={{ flex: '1 1 250px' }}>
              <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: '500', color: 'var(--text-color)', marginBottom: '8px' }}>Empresa</label>
              <select 
                className="form-control" 
                value={filtros.empresa_id} 
                onChange={e => setFiltros({...filtros, empresa_id: e.target.value})}
              >
                <option value="">Todas las empresas...</option>
                {empresas.map(e => <option key={e.id} value={e.id}>{e.nombre}</option>)}
              </select>
            </div>
            <div style={{ flex: '1 1 350px' }}>
              <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: '500', color: 'var(--text-color)', marginBottom: '8px' }}>Rango de Fechas</label>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <div style={{ flex: 1 }}>
                  <DatePicker
                    selected={filtros.fecha_inicio}
                    onChange={date => setFiltros({...filtros, fecha_inicio: date})}
                    selectsStart
                    startDate={filtros.fecha_inicio}
                    endDate={filtros.fecha_fin}
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
                    selected={filtros.fecha_fin}
                    onChange={date => setFiltros({...filtros, fecha_fin: date})}
                    selectsEnd
                    startDate={filtros.fecha_inicio}
                    endDate={filtros.fecha_fin}
                    minDate={filtros.fecha_inicio}
                    dateFormat="dd/MM/yyyy"
                    placeholderText="Hasta..."
                    className="form-control"
                    isClearable
                    wrapperClassName="date-picker-wrapper"
                  />
                </div>
              </div>
            </div>
            <div>
              <button className="btn btn-primary" onClick={handleSearch} disabled={isLoading} style={{ display: 'flex', alignItems: 'center', gap: '8px', height: '42px' }}>
                <Search size={18} /> {isLoading ? 'Buscando...' : 'Buscar'}
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Global Totals KPI */}
      {reporte.medicamentos.length > 0 && (
        <div className="no-print" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '20px', marginBottom: '24px' }}>
          <div className="dash-chart-card" style={{ padding: '20px', background: 'linear-gradient(135deg, rgba(14, 165, 233, 0.1), rgba(15, 23, 42, 0.5))' }}>
            <span style={{ display: 'block', fontSize: '0.85rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Sub Total (S/.)</span>
            <span style={{ display: 'block', fontSize: '2rem', fontWeight: '800', color: '#fff', marginTop: '8px' }}>S/ {reporte.totales.sub_total.toFixed(2)}</span>
          </div>
          <div className="dash-chart-card" style={{ padding: '20px', background: 'linear-gradient(135deg, rgba(234, 179, 8, 0.1), rgba(15, 23, 42, 0.5))' }}>
            <span style={{ display: 'block', fontSize: '0.85rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>IGV (18%)</span>
            <span style={{ display: 'block', fontSize: '2rem', fontWeight: '800', color: '#facc15', marginTop: '8px' }}>S/ {reporte.totales.igv.toFixed(2)}</span>
          </div>
          <div className="dash-chart-card" style={{ padding: '20px', background: 'linear-gradient(135deg, rgba(16, 185, 129, 0.1), rgba(15, 23, 42, 0.5))' }}>
            <span style={{ display: 'block', fontSize: '0.85rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Total General</span>
            <span style={{ display: 'block', fontSize: '2rem', fontWeight: '800', color: '#10b981', marginTop: '8px' }}>S/ {reporte.totales.total.toFixed(2)}</span>
          </div>
        </div>
      )}

      {/* Table */}
      <div className="dash-chart-card print-full-width">
        <div className="dash-chart-header print-only" style={{ display: 'none', padding: '20px', borderBottom: '2px solid #000' }}>
          <h2 style={{ color: '#000', margin: 0, marginBottom: '12px' }}>Reporte de Consumo de Medicamentos</h2>
          <div style={{ display: 'flex', gap: '40px', color: '#000' }}>
            <div><strong>Empresa:</strong> {empresas.find(e => e.id.toString() === filtros.empresa_id)?.nombre || 'Todas las Empresas'}</div>
            <div><strong>Rango de Fechas:</strong> {(filtros.fecha_inicio && filtros.fecha_fin) ? `${filtros.fecha_inicio.toLocaleDateString()} al ${filtros.fecha_fin.toLocaleDateString()}` : 'Todas las fechas'}</div>
          </div>
        </div>
        <div className="dash-chart-body" style={{ overflowX: 'auto', padding: 0 }}>
          {reporte.medicamentos.length > 0 ? (
            <table className="table" style={{ minWidth: '100%', margin: 0, whiteSpace: 'nowrap' }}>
              <thead style={{ background: 'rgba(15, 23, 42, 0.9)' }}>
                <tr>
                  <th>Código</th>
                  <th>Medicamento</th>
                  <th>Presentación</th>
                  {reporte.rango_fechas.map(f => (
                    <th key={f} style={{ textAlign: 'center' }}>{f}</th>
                  ))}
                  <th style={{ textAlign: 'center', borderLeft: '1px solid rgba(255,255,255,0.1)' }}>Sub Total (Cant)</th>
                  <th style={{ textAlign: 'right' }}>Precio UND</th>
                  <th style={{ textAlign: 'right', color: 'var(--primary-color)' }}>Total (S/.)</th>
                </tr>
              </thead>
              <tbody>
                {reporte.medicamentos.map(med => (
                  <tr key={med.id}>
                    <td style={{ color: 'var(--text-muted)' }}>{med.codigo}</td>
                    <td style={{ fontWeight: '500' }}>{med.nombre}</td>
                    <td>{med.presentacion}</td>
                    {reporte.rango_fechas.map(f => (
                      <td key={f} style={{ textAlign: 'center', color: med.consumos[f] ? '#fff' : 'var(--text-muted)' }}>
                        {med.consumos[f] || 0}
                      </td>
                    ))}
                    <td style={{ textAlign: 'center', fontWeight: 'bold', borderLeft: '1px solid rgba(255,255,255,0.05)' }}>
                      {med.sub_total_cantidad}
                    </td>
                    <td style={{ textAlign: 'right' }}>{med.precio_und.toFixed(2)}</td>
                    <td style={{ textAlign: 'right', fontWeight: 'bold', color: 'var(--primary-color)' }}>
                      {med.total_soles.toFixed(2)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div style={{ padding: '60px 20px', textAlign: 'center', color: 'var(--text-muted)' }}>
              {isLoading ? 'Cargando datos...' : 'Realiza una búsqueda para ver el reporte'}
            </div>
          )}
        </div>
      </div>
      
      {/* Print Styles */}
      <style>{`
        @media print {
          .page-container { padding: 0 !important; }
          .no-print { display: none !important; }
          .print-only { display: block !important; }
          .dash-chart-card { border: none !important; box-shadow: none !important; background: transparent !important; }
          .table { border: 1px solid #ddd; }
          .table th { background: #f1f5f9 !important; color: #000 !important; border: 1px solid #ddd !important; }
          .table td { color: #000 !important; border: 1px solid #ddd !important; }
          body { background: #fff !important; }
          * { -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }
        }
      `}</style>
    </div>
  );
};

export default ConsumoMedicamentos;
