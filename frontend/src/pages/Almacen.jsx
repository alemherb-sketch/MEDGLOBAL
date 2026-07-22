import { useState, useEffect } from 'react';
import { apiFetch, apiJson } from '../api';
import { Search, RefreshCw, X, ClipboardList, TrendingUp, TrendingDown, Edit2, Trash2 } from 'lucide-react';

const TIPOS_MEDICAMENTO = ['MEDICAMENTO', 'INSUMO', 'OTROS'];
const PAGE_SIZE = 20;

const Almacen = () => {
  const [medicamentos, setMedicamentos] = useState([]);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [kardexForm, setKardexForm] = useState({ medicamento_id: '', tipo_movimiento: 'INGRESO', cantidad: '' });
  const [filters, setFilters] = useState({ search: '' });
  const [page, setPage] = useState(0);

  // Nuevo estado para el modal de visualización del Kardex
  const [viewKardexMed, setViewKardexMed] = useState(null);
  const [kardexData, setKardexData] = useState([]);

  // Edicion rapida del medicamento desde la misma tabla de almacen
  const [editMed, setEditMed] = useState(null);

  const fetchMedicamentos = () => {
    apiJson('/medicamentos/')
      .then(data => setMedicamentos(data));
  };

  useEffect(() => {
    fetchMedicamentos();
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
    apiJson(`/kardex/${m.id}`)
      .then(data => setKardexData(data));
  };

  const closeKardexView = () => {
    setViewKardexMed(null);
    setKardexData([]);
  };

  const openEditModal = (m) => setEditMed({ ...m });
  const closeEditModal = () => setEditMed(null);

  const handleEditMed = (e) => {
    e.preventDefault();
    const dataToSend = { ...editMed };
    delete dataToSend.id;
    delete dataToSend.stock_actual; // el stock no se toca por aca, solo por Kardex

    apiFetch(`/medicamentos/${editMed.id}`, {
      method: 'PUT',
      body: JSON.stringify(dataToSend)
    }).then(async res => {
      if (!res.ok) {
        const err = await res.text();
        throw new Error(err);
      }
      fetchMedicamentos();
      closeEditModal();
    }).catch(err => {
      alert("Error al guardar: " + err.message);
    });
  };

  const handleDeleteMed = (id) => {
    if (window.confirm('¿Eliminar medicamento del catálogo?')) {
      apiFetch(`/medicamentos/${id}`, { method: 'DELETE' })
        .then(() => fetchMedicamentos());
    }
  };

  const filteredMedicamentos = medicamentos.filter(m =>
    ((m.codigo || '') + ' ' + m.nombre + ' ' + m.presentacion + ' ' + (m.tipo || '')).toLowerCase().includes(filters.search.toLowerCase())
  );

  const totalPages = Math.max(1, Math.ceil(filteredMedicamentos.length / PAGE_SIZE));
  const pageSafe = Math.min(page, totalPages - 1);
  const paginatedMedicamentos = filteredMedicamentos.slice(pageSafe * PAGE_SIZE, (pageSafe + 1) * PAGE_SIZE);

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
                onChange={e => { setFilters({...filters, search: e.target.value}); setPage(0); }}
              />
            </div>
          </div>
          <div style={{color: 'var(--text-muted)', fontSize: '0.9rem', display: 'flex', alignItems: 'center'}}>
            Total: {filteredMedicamentos.length} registros
          </div>
        </div>

        <div className="table-container">
          <table className="table table-compact" style={{tableLayout: 'fixed'}}>
            <thead>
              <tr>
                <th style={{width: '85px'}} title="Código">Cód.</th>
                <th>Nombre</th>
                <th style={{width: '110px'}}>Tipo</th>
                <th style={{width: '100px'}} title="Presentación">Present.</th>
                <th style={{width: '90px', textAlign: 'right'}}>Stock</th>
                <th style={{width: '110px', textAlign: 'right'}} title="Acciones">Acc.</th>
              </tr>
            </thead>
            <tbody>
              {paginatedMedicamentos.map(m => (
                <tr key={m.id}>
                  <td style={{whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis'}} title={m.codigo}>{m.codigo}</td>
                  <td style={{overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap'}} title={m.nombre}>{m.nombre}</td>
                  <td style={{whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis'}} title={m.tipo || 'MEDICAMENTO'}>{m.tipo || 'MEDICAMENTO'}</td>
                  <td style={{whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis'}} title={m.presentacion}>{m.presentacion}</td>
                  <td style={{textAlign: 'right'}}>
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
                  <td style={{textAlign: 'right', whiteSpace: 'nowrap'}}>
                    <button className="action-btn view" style={{color: '#3b82f6', marginRight: '5px'}} onClick={() => openKardexView(m)} title="Ver Movimientos (Kardex)">
                      <ClipboardList size={16} />
                    </button>
                    <button className="action-btn edit" onClick={() => openEditModal(m)} title="Editar"><Edit2 size={16} /></button>
                    <button className="action-btn delete" onClick={() => handleDeleteMed(m.id)} title="Eliminar"><Trash2 size={16} /></button>
                  </td>
                </tr>
              ))}
              {filteredMedicamentos.length === 0 && (
                <tr>
                  <td colSpan="6" className="text-center text-muted py-4">No se encontraron medicamentos en el almacén</td>
                </tr>
              )}
            </tbody>
          </table>

          {filteredMedicamentos.length > PAGE_SIZE && (
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

      {/* Modal Editar Medicamento */}
      {editMed && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div className="modal-header">
              <h3>Editar Medicamento</h3>
              <button className="close-btn" onClick={closeEditModal}><X size={24} /></button>
            </div>
            <div className="modal-body">
              <form onSubmit={handleEditMed}>
                <div className="grid grid-cols-2">
                  <div className="form-group">
                    <label className="form-label">Código</label>
                    <input readOnly disabled className="form-control" value={editMed.codigo || ''} style={{opacity: 0.7}} />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Nombre</label>
                    <input required className="form-control" value={editMed.nombre} onChange={e => setEditMed({...editMed, nombre: e.target.value})} />
                  </div>
                </div>
                <div className="grid grid-cols-2">
                  <div className="form-group">
                    <label className="form-label">Presentación</label>
                    <select required className="form-control" value={editMed.presentacion} onChange={e => setEditMed({...editMed, presentacion: e.target.value})}>
                      <option value="">Seleccione...</option>
                      <option value="FRASCO">FRASCO</option>
                      <option value="ROLLO">ROLLO</option>
                      <option value="TABLETA">TABLETA</option>
                      <option value="UNIDAD">UNIDAD</option>
                      <option value="AMPOLLA">AMPOLLA</option>
                      <option value="TUBO">TUBO</option>
                      <option value="SOBRE">SOBRE</option>
                      <option value="CAJA">CAJA</option>
                    </select>
                  </div>
                  <div className="form-group">
                    <label className="form-label">Tipo</label>
                    <select required className="form-control" value={editMed.tipo || 'MEDICAMENTO'} onChange={e => setEditMed({...editMed, tipo: e.target.value})}>
                      {TIPOS_MEDICAMENTO.map(t => <option key={t} value={t}>{t}</option>)}
                    </select>
                  </div>
                </div>
                <div className="grid grid-cols-2">
                  <div className="form-group">
                    <label className="form-label">Lote</label>
                    <input className="form-control" value={editMed.lote || ''} onChange={e => setEditMed({...editMed, lote: e.target.value})} />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Fecha de Vencimiento</label>
                    <input type="date" className="form-control" value={editMed.fecha_vencimiento || ''} onChange={e => setEditMed({...editMed, fecha_vencimiento: e.target.value})} />
                  </div>
                </div>
                <div className="form-group">
                  <label className="form-label">Costo Unitario (S/)</label>
                  <input type="number" step="0.01" min="0" required className="form-control" value={editMed.costo_unitario || 0} onChange={e => setEditMed({...editMed, costo_unitario: parseFloat(e.target.value) || 0})} />
                </div>
                <div className="form-group">
                  <label className="form-label">Descripción</label>
                  <textarea className="form-control" value={editMed.descripcion || ''} onChange={e => setEditMed({...editMed, descripcion: e.target.value})} />
                </div>
                <div style={{display: 'flex', justifyContent: 'flex-end', gap: '12px', marginTop: '24px'}}>
                  <button type="button" className="btn btn-secondary" onClick={closeEditModal}>Cancelar</button>
                  <button type="submit" className="btn btn-primary">Guardar</button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}

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
