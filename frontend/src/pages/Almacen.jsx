import { useState, useEffect } from 'react';
import { apiFetch, apiJson } from '../api';
import { Search, RefreshCw, X, ClipboardList, TrendingUp, TrendingDown } from 'lucide-react';

const PAGE_SIZE = 20;

const Almacen = () => {
  const [medicamentos, setMedicamentos] = useState([]);
  const [kardexEntries, setKardexEntries] = useState([]);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [kardexForm, setKardexForm] = useState({ medicamento_id: '', tipo_movimiento: 'INGRESO', cantidad: '', lote: '', fecha_vencimiento: '' });
  const [filters, setFilters] = useState({ search: '' });
  const [page, setPage] = useState(0);

  // Modal de historial de un solo producto (se abre desde una fila del ledger)
  const [viewKardexMed, setViewKardexMed] = useState(null);
  const [kardexData, setKardexData] = useState([]);

  const fetchMedicamentos = () => {
    apiJson('/medicamentos/')
      .then(data => setMedicamentos(data));
  };

  const fetchKardexEntries = () => {
    apiJson('/kardex/todos/')
      .then(data => setKardexEntries(data));
  };

  useEffect(() => {
    fetchMedicamentos();
    fetchKardexEntries();
  }, []);

  const handleKardex = (e) => {
    e.preventDefault();
    apiFetch('/kardex/', {
      method: 'POST',
      body: JSON.stringify({ ...kardexForm, cantidad: parseInt(kardexForm.cantidad) })
    }).then(async res => {
      if (!res.ok) {
        const err = await res.text();
        throw new Error(err);
      }
      fetchKardexEntries();
      fetchMedicamentos();
      closeModal();
    }).catch(err => {
      alert("Error al registrar movimiento: " + err.message);
    });
  };

  const openModal = () => {
    setKardexForm({ medicamento_id: '', tipo_movimiento: 'INGRESO', cantidad: '', lote: '', fecha_vencimiento: '' });
    setIsModalOpen(true);
  };

  const closeModal = () => setIsModalOpen(false);

  const openKardexView = (medicamento) => {
    setViewKardexMed(medicamento);
    apiJson(`/kardex/${medicamento.id}`)
      .then(data => setKardexData(data));
  };

  const closeKardexView = () => {
    setViewKardexMed(null);
    setKardexData([]);
  };

  const filteredEntries = kardexEntries.filter(k => {
    const m = k.medicamento || {};
    const texto = ((m.codigo || '') + ' ' + (m.nombre || '') + ' ' + (m.tipo || '') + ' ' + k.tipo_movimiento).toLowerCase();
    return texto.includes(filters.search.toLowerCase());
  });

  const totalPages = Math.max(1, Math.ceil(filteredEntries.length / PAGE_SIZE));
  const pageSafe = Math.min(page, totalPages - 1);
  const paginatedEntries = filteredEntries.slice(pageSafe * PAGE_SIZE, (pageSafe + 1) * PAGE_SIZE);

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
                placeholder="Buscar por código, producto o tipo de movimiento..."
                value={filters.search}
                onChange={e => { setFilters({...filters, search: e.target.value}); setPage(0); }}
              />
            </div>
          </div>
          <div style={{color: 'var(--text-muted)', fontSize: '0.9rem', display: 'flex', alignItems: 'center'}}>
            Total: {filteredEntries.length} movimientos
          </div>
        </div>

        <div className="table-container">
          <table className="table table-compact" style={{tableLayout: 'fixed'}}>
            <thead>
              <tr>
                <th style={{width: '105px'}}>Fecha</th>
                <th style={{width: '75px'}} title="Código">Cód.</th>
                <th>Producto</th>
                <th style={{width: '90px'}}>Tipo</th>
                <th style={{width: '95px'}} title="Movimiento">Movim.</th>
                <th style={{width: '135px'}} title="Lote / Vencimiento">Lote / Venc.</th>
                <th style={{width: '65px', textAlign: 'right'}}>Cant.</th>
                <th style={{width: '65px', textAlign: 'right'}}>Saldo</th>
              </tr>
            </thead>
            <tbody>
              {paginatedEntries.map(k => {
                const m = k.medicamento || {};
                return (
                  <tr key={k.id} style={{cursor: m.id ? 'pointer' : 'default'}} onClick={() => m.id && openKardexView(m)} title="Ver historial completo de este producto">
                    <td style={{whiteSpace: 'nowrap', fontSize: '0.85rem'}}>
                      {new Date(k.fecha).toLocaleDateString()} <span className="text-muted">{new Date(k.fecha).toLocaleTimeString().substring(0,5)}</span>
                    </td>
                    <td style={{whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis'}} title={m.codigo}>
                      <span style={{fontWeight: 'bold', color: 'var(--primary-color)'}}>{m.codigo}</span>
                    </td>
                    <td style={{overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap'}} title={m.nombre}>{m.nombre}</td>
                    <td style={{whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis'}} title={m.tipo || 'MEDICAMENTO'}>{m.tipo || 'MEDICAMENTO'}</td>
                    <td style={{whiteSpace: 'nowrap'}}>
                      {k.tipo_movimiento === 'INGRESO' ? (
                        <span style={{color: '#16a34a', display: 'flex', alignItems: 'center', gap: '4px', fontWeight: '500', fontSize: '0.85rem'}}><TrendingUp size={14}/> Ingreso</span>
                      ) : (
                        <span style={{color: 'var(--danger-color)', display: 'flex', alignItems: 'center', gap: '4px', fontWeight: '500', fontSize: '0.85rem'}}><TrendingDown size={14}/> Salida</span>
                      )}
                    </td>
                    <td style={{fontSize: '0.8rem', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis'}}>
                      {k.lote && <div>Lote: {k.lote}</div>}
                      {k.fecha_vencimiento ? (
                        <div className="text-muted">Vence: {k.fecha_vencimiento}</div>
                      ) : (!k.lote && <span className="text-muted">—</span>)}
                    </td>
                    <td style={{textAlign: 'right', fontWeight: 'bold', color: k.tipo_movimiento === 'INGRESO' ? '#16a34a' : 'var(--danger-color)'}}>
                      {k.tipo_movimiento === 'INGRESO' ? '+' : '-'}{k.cantidad}
                    </td>
                    <td style={{textAlign: 'right', fontWeight: 'bold'}}>{k.saldo}</td>
                  </tr>
                );
              })}
              {filteredEntries.length === 0 && (
                <tr>
                  <td colSpan="8" className="text-center text-muted py-4">No hay movimientos registrados en el almacén</td>
                </tr>
              )}
            </tbody>
          </table>

          {filteredEntries.length > PAGE_SIZE && (
            <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '15px', borderTop: '1px solid var(--border-color)'}}>
              <button
                className="btn btn-secondary"
                onClick={() => setPage(p => Math.max(0, p - 1))}
                disabled={pageSafe === 0}
              >
                Anterior
              </button>
              <span style={{fontSize: '0.9rem', color: 'var(--text-muted)'}}>
                Página {pageSafe + 1} de {totalPages}
              </span>
              <button
                className="btn btn-secondary"
                onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))}
                disabled={pageSafe >= totalPages - 1}
              >
                Siguiente
              </button>
            </div>
          )}
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
                <div className="flex gap-4">
                  <div className="form-group" style={{flex: 1}}>
                    <label className="form-label">Lote</label>
                    <input className="form-control" value={kardexForm.lote} onChange={e => setKardexForm({...kardexForm, lote: e.target.value})} />
                  </div>
                  <div className="form-group" style={{flex: 1}}>
                    <label className="form-label">Fecha de Vencimiento</label>
                    <input type="date" className="form-control" value={kardexForm.fecha_vencimiento} onChange={e => setKardexForm({...kardexForm, fecha_vencimiento: e.target.value})} />
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

      {/* Modal Visor de Kardex de un producto especifico */}
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
                      <th>Lote / Vencimiento</th>
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
                        <td style={{fontSize: '0.85rem'}}>
                          {k.lote && <div>Lote: {k.lote}</div>}
                          {k.fecha_vencimiento ? (
                            <div className="text-muted">Vence: {k.fecha_vencimiento}</div>
                          ) : (!k.lote && <span className="text-muted">—</span>)}
                        </td>
                        <td style={{textAlign: 'right', fontWeight: 'bold', color: k.tipo_movimiento === 'INGRESO' ? '#16a34a' : 'var(--danger-color)'}}>
                          {k.tipo_movimiento === 'INGRESO' ? '+' : '-'}{k.cantidad}
                        </td>
                        <td style={{textAlign: 'right', fontWeight: 'bold'}}>{k.saldo}</td>
                      </tr>
                    ))}
                    {kardexData.length === 0 && (
                      <tr>
                        <td colSpan="5" className="text-center text-muted py-4">No hay movimientos registrados para este medicamento.</td>
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
