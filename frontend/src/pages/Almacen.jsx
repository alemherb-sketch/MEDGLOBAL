import { useState, useEffect } from 'react';
import { Search, RefreshCw, X, ClipboardList, TrendingUp, TrendingDown } from 'lucide-react';

const Almacen = () => {
  const [medicamentos, setMedicamentos] = useState([]);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [kardexForm, setKardexForm] = useState({ medicamento_id: '', tipo_movimiento: 'INGRESO', cantidad: '' });
  const [filters, setFilters] = useState({ search: '' });

  // Nuevo estado para el modal de visualización del Kardex
  const [viewKardexMed, setViewKardexMed] = useState(null);
  const [kardexData, setKardexData] = useState([]);

  const fetchMedicamentos = () => {
    fetch((import.meta.env.VITE_API_URL ? (import.meta.env.VITE_API_URL.startsWith('http') ? import.meta.env.VITE_API_URL : 'https://' + import.meta.env.VITE_API_URL) : '${(import.meta.env.VITE_API_URL ? (import.meta.env.VITE_API_URL.startsWith('http') ? import.meta.env.VITE_API_URL : 'https://' + import.meta.env.VITE_API_URL) : 'http://localhost:8000')}') + '/medicamentos/')
      .then(res => res.json())
      .then(data => setMedicamentos(data));
  };

  useEffect(() => {
    fetchMedicamentos();
  }, []);

  const handleKardex = (e) => {
    e.preventDefault();
    fetch((import.meta.env.VITE_API_URL ? (import.meta.env.VITE_API_URL.startsWith('http') ? import.meta.env.VITE_API_URL : 'https://' + import.meta.env.VITE_API_URL) : '${(import.meta.env.VITE_API_URL ? (import.meta.env.VITE_API_URL.startsWith('http') ? import.meta.env.VITE_API_URL : 'https://' + import.meta.env.VITE_API_URL) : 'http://localhost:8000')}') + '/kardex/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ...kardexForm, cantidad: parseInt(kardexForm.cantidad) })
    }).then(async res => {
      if (!res.ok) {
        const err = await res.text();
        throw new Error(err);
      }
      fetchMedicamentos();
      closeModal();
    }).catch(err => {
      alert("Error al registrar movimiento: " + err.message);
    });
  };

  const openModal = () => {
    setKardexForm({ medicamento_id: '', tipo_movimiento: 'INGRESO', cantidad: '' });
    setIsModalOpen(true);
  };

  const closeModal = () => setIsModalOpen(false);

  const openKardexView = (m) => {
    setViewKardexMed(m);
    fetch(`${(import.meta.env.VITE_API_URL ? (import.meta.env.VITE_API_URL.startsWith('http') ? import.meta.env.VITE_API_URL : 'https://' + import.meta.env.VITE_API_URL) : 'http://localhost:8000')}/kardex/${m.id}`)
      .then(res => res.json())
      .then(data => setKardexData(data));
  };

  const closeKardexView = () => {
    setViewKardexMed(null);
    setKardexData([]);
  };

  const filteredMedicamentos = medicamentos.filter(m => 
    ((m.codigo || '') + ' ' + m.nombre + ' ' + m.presentacion).toLowerCase().includes(filters.search.toLowerCase())
  );

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <h1>Control de Almacén (Kardex)</h1>
        <button className="btn btn-secondary" onClick={openModal}>
          <RefreshCw size={18} style={{marginRight: '8px'}} /> Registrar Movimiento
        </button>
      </div>
      
      <div className="glass-panel">
        <div className="filter-bar">
          <div className="form-group mb-0" style={{flex: 1}}>
            <div style={{position: 'relative'}}>
              <Search size={18} style={{position: 'absolute', top: '14px', left: '14px', color: 'var(--text-muted)'}} />
              <input 
                className="form-control search-input" 
                style={{paddingLeft: '40px'}}
                placeholder="Buscar por código, nombre o presentación..." 
                value={filters.search} 
                onChange={e => setFilters({...filters, search: e.target.value})} 
              />
            </div>
          </div>
        </div>

        <div className="table-container">
          <table className="table">
            <thead>
              <tr>
                <th>Código</th>
                <th>Nombre</th>
                <th>Presentación</th>
                <th>Stock Actual</th>
                <th style={{textAlign: 'right'}}>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {filteredMedicamentos.map(m => (
                <tr key={m.id}>
                  <td>{m.codigo}</td>
                  <td>{m.nombre}</td>
                  <td>{m.presentacion}</td>
                  <td>
                    <span style={{
                      padding: '4px 8px', 
                      background: m.stock_actual < 10 ? 'rgba(239, 68, 68, 0.2)' : 'rgba(16, 185, 129, 0.2)', 
                      color: m.stock_actual < 10 ? 'var(--danger-color)' : 'var(--success-color)',
                      borderRadius: '4px',
                      fontWeight: 'bold'
                    }}>
                      {m.stock_actual}
                    </span>
                  </td>
                  <td style={{textAlign: 'right'}}>
                    <button className="action-btn view" style={{color: '#3b82f6'}} onClick={() => openKardexView(m)} title="Ver Movimientos (Kardex)">
                      <ClipboardList size={18} />
                    </button>
                  </td>
                </tr>
              ))}
              {filteredMedicamentos.length === 0 && (
                <tr>
                  <td colSpan="5" className="text-center text-muted py-4">No se encontraron medicamentos en el almacén</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {isModalOpen && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div className="modal-header">
              <h3>Registrar Movimiento Kardex</h3>
              <button className="close-btn" onClick={closeModal}><X size={24} /></button>
            </div>
            <div className="modal-body">
              <form onSubmit={handleKardex}>
                <div className="form-group">
                  <label className="form-label">Medicamento</label>
                  <select required className="form-control" value={kardexForm.medicamento_id} onChange={e => setKardexForm({...kardexForm, medicamento_id: e.target.value})}>
                    <option value="">Seleccione...</option>
                    {medicamentos.map(m => <option key={m.id} value={m.id}>{m.codigo ? `[${m.codigo}] ` : ''}{m.nombre} - {m.presentacion}</option>)}
                  </select>
                </div>
                <div className="flex gap-4">
                  <div className="form-group" style={{flex: 1}}>
                    <label className="form-label">Tipo Movimiento</label>
                    <select className="form-control" value={kardexForm.tipo_movimiento} onChange={e => setKardexForm({...kardexForm, tipo_movimiento: e.target.value})}>
                      <option value="INGRESO">Ingreso (+)</option>
                      <option value="SALIDA">Salida (-)</option>
                    </select>
                  </div>
                  <div className="form-group" style={{flex: 1}}>
                    <label className="form-label">Cantidad</label>
                    <input required type="number" min="1" className="form-control" value={kardexForm.cantidad} onChange={e => setKardexForm({...kardexForm, cantidad: e.target.value})} />
                  </div>
                </div>
                <div style={{display: 'flex', justifyContent: 'flex-end', gap: '12px', marginTop: '24px'}}>
                  <button type="button" className="btn btn-secondary" onClick={closeModal}>Cancelar</button>
                  <button type="submit" className="btn btn-primary">Registrar Movimiento</button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}

      {/* Modal Visor de Kardex */}
      {viewKardexMed && (
        <div className="modal-overlay" style={{padding: '20px 0'}}>
          <div className="modal-content" style={{maxWidth: '700px', maxHeight: '90vh', overflowY: 'auto'}}>
            <div className="modal-header" style={{position: 'sticky', top: 0, zIndex: 10, background: 'var(--surface-color)'}}>
              <div>
                <h3 style={{marginBottom: '4px'}}>Kardex Físico - Valorizado</h3>
                <div style={{fontSize: '0.9rem', color: 'var(--text-muted)'}}>
                  {viewKardexMed.codigo} | {viewKardexMed.nombre} ({viewKardexMed.presentacion})
                </div>
              </div>
              <button className="close-btn" onClick={closeKardexView}><X size={24} /></button>
            </div>
            
            <div className="modal-body" style={{paddingTop: '20px'}}>
              <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px', padding: '15px', background: 'var(--background-color)', borderRadius: '8px'}}>
                <div>
                  <span className="text-muted" style={{display: 'block', fontSize: '0.8rem', textTransform: 'uppercase', letterSpacing: '1px'}}>Stock Actual</span>
                  <span style={{fontSize: '2rem', fontWeight: 'bold', color: 'var(--primary-color)'}}>{viewKardexMed.stock_actual}</span>
                  <span style={{marginLeft: '8px', color: 'var(--text-muted)'}}>unidades</span>
                </div>
              </div>

              <div className="table-container">
                <table className="table" style={{fontSize: '0.9rem'}}>
                  <thead>
                    <tr>
                      <th>Fecha de Movimiento</th>
                      <th>Tipo</th>
                      <th style={{textAlign: 'right'}}>Cantidad</th>
                      <th style={{textAlign: 'right'}}>Saldo Restante</th>
                    </tr>
                  </thead>
                  <tbody>
                    {kardexData.map((k, index) => (
                      <tr key={index}>
                        <td>
                          {new Date(k.fecha).toLocaleDateString()} <span className="text-muted" style={{fontSize: '0.8rem'}}>{new Date(k.fecha).toLocaleTimeString().substring(0,5)}</span>
                        </td>
                        <td>
                          {k.tipo_movimiento === 'INGRESO' ? (
                            <span style={{color: '#16a34a', display: 'flex', alignItems: 'center', gap: '4px', fontWeight: '500'}}><TrendingUp size={14}/> INGRESO</span>
                          ) : (
                            <span style={{color: 'var(--danger-color)', display: 'flex', alignItems: 'center', gap: '4px', fontWeight: '500'}}><TrendingDown size={14}/> SALIDA</span>
                          )}
                        </td>
                        <td style={{textAlign: 'right', fontWeight: 'bold', color: k.tipo_movimiento === 'INGRESO' ? '#16a34a' : 'var(--danger-color)'}}>
                          {k.tipo_movimiento === 'INGRESO' ? '+' : '-'}{k.cantidad}
                        </td>
                        <td style={{textAlign: 'right', fontWeight: 'bold'}}>{k.saldo}</td>
                      </tr>
                    ))}
                    {kardexData.length === 0 && (
                      <tr>
                        <td colSpan="4" className="text-center text-muted py-4">No hay movimientos registrados para este medicamento.</td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>

            </div>
          </div>
        </div>
      )}

    </div>
  );
};

export default Almacen;
