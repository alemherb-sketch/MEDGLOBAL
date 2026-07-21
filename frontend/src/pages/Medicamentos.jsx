import { useState, useEffect, useRef } from 'react';
import { apiFetch, apiJson } from '../api';
import { Search, Plus, Trash2, Edit2, X, ClipboardList, TrendingUp, TrendingDown, FileSpreadsheet } from 'lucide-react';

const TIPOS_MEDICAMENTO = ['MEDICAMENTO', 'INSUMO', 'OTROS'];

const Medicamentos = () => {
  const [medicamentos, setMedicamentos] = useState([]);
  const [modalType, setModalType] = useState(null); // 'med', 'edit_med', 'kardex'
  const [newMed, setNewMed] = useState({ id: null, codigo: '', nombre: '', presentacion: '', descripcion: '', tipo: 'MEDICAMENTO', lote: '', fecha_vencimiento: '', costo_unitario: 0.0 });
  const [filters, setFilters] = useState({ search: '' });
  const [isImporting, setIsImporting] = useState(false);
  const fileInputRef = useRef(null);

  const [selectedKardexMed, setSelectedKardexMed] = useState(null);
  const [kardexData, setKardexData] = useState([]);

  const fetchMedicamentos = () => {
    apiJson('/medicamentos/')
      .then(data => setMedicamentos(data));
  };

  useEffect(() => {
    fetchMedicamentos();
  }, []);

  const handleAddMed = (e) => {
    e.preventDefault();
    const isEditing = newMed.id !== null;
    const url = isEditing ? `/medicamentos/${newMed.id}` : '/medicamentos/';
    const method = isEditing ? 'PUT' : 'POST';

    const dataToSend = { ...newMed };
    delete dataToSend.id;
    delete dataToSend.stock_actual; // shouldn't update stock via this endpoint

    apiFetch(url, {
      method,
      body: JSON.stringify(dataToSend)
    }).then(async res => {
      if (!res.ok) {
        const err = await res.text();
        throw new Error(err);
      }
      fetchMedicamentos();
      closeModal();
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

  const openModal = (type, data = null) => {
    setModalType(type);
    if (type === 'med') {
      setNewMed({ id: null, codigo: '', nombre: '', presentacion: '', descripcion: '', tipo: 'MEDICAMENTO', lote: '', fecha_vencimiento: '', costo_unitario: 0.0 });
    } else if (type === 'edit_med') {
      setNewMed(data);
    } else if (type === 'kardex') {
      setSelectedKardexMed(data);
      apiJson(`/kardex/${data.id}`)
        .then(kData => setKardexData(kData));
    }
  };

  const closeModal = () => {
    setModalType(null);
    setSelectedKardexMed(null);
    setKardexData([]);
  };

  const handleImport = (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setIsImporting(true);
    const formData = new FormData();
    formData.append('file', file);

    apiFetch('/medicamentos/importar/', {
      method: 'POST',
      body: formData
    })
    .then(async res => {
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || "Error desconocido del servidor");
      }
      return data;
    })
    .then(data => {
      setIsImporting(false);
      alert(data.message || "Importación completada");
      fetchMedicamentos();
      if (fileInputRef.current) fileInputRef.current.value = '';
    })
    .catch(err => {
      setIsImporting(false);
      alert("Error en la importación: " + err.message);
      if (fileInputRef.current) fileInputRef.current.value = '';
    });
  };

  const filteredMedicamentos = medicamentos.filter(m =>
    ((m.codigo || '') + ' ' + m.nombre + ' ' + m.presentacion + ' ' + (m.tipo || '') + ' ' + (m.lote || '')).toLowerCase().includes(filters.search.toLowerCase())
  );

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <h1>Catálogo de Medicamentos y Almacén</h1>
        <div style={{display: 'flex', gap: '10px'}}>
          <input
            type="file"
            accept=".xlsx, .xls"
            style={{display: 'none'}}
            ref={fileInputRef}
            onChange={handleImport}
          />
          <button className="btn btn-secondary" onClick={() => fileInputRef.current?.click()} disabled={isImporting}>
            {isImporting ? <span className="spinner"></span> : <FileSpreadsheet size={18} style={{marginRight: '8px'}} />}
            Importar Excel
          </button>
          <button className="btn btn-primary" onClick={() => openModal('med')}>
            <Plus size={18} style={{marginRight: '8px'}} /> Nuevo Medicamento
          </button>
        </div>
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
                <th>Tipo</th>
                <th>Presentación</th>
                <th>Lote / Vencimiento</th>
                <th>Costo Unit.</th>
                <th>Stock Actual</th>
                <th style={{textAlign: 'right'}}>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {filteredMedicamentos.map(m => (
                <tr key={m.id}>
                  <td><span style={{fontWeight: 'bold', color: 'var(--primary-color)'}}>{m.codigo}</span></td>
                  <td>{m.nombre} <br/><span className="text-muted" style={{fontSize: '0.8rem'}}>{m.descripcion}</span></td>
                  <td>{m.tipo || 'MEDICAMENTO'}</td>
                  <td>{m.presentacion}</td>
                  <td style={{fontSize: '0.85rem'}}>
                    {m.lote ? <>Lote: {m.lote}<br/></> : null}
                    {m.fecha_vencimiento ? <span className="text-muted">Vence: {m.fecha_vencimiento}</span> : (!m.lote ? <span className="text-muted">—</span> : null)}
                  </td>
                  <td>S/ {Number(m.costo_unitario || 0).toFixed(2)}</td>
                  <td>
                    <span style={{
                      padding: '4px 8px', 
                      borderRadius: '12px', 
                      background: m.stock_actual <= 10 ? 'rgba(239, 68, 68, 0.1)' : 'rgba(34, 197, 94, 0.1)',
                      color: m.stock_actual <= 10 ? 'var(--danger-color)' : '#16a34a',
                      fontWeight: 'bold'
                    }}>
                      {m.stock_actual} unid.
                    </span>
                  </td>
                  <td style={{textAlign: 'right', whiteSpace: 'nowrap'}}>
                    <button className="action-btn view" style={{color: '#3b82f6', marginRight: '5px'}} onClick={() => openModal('kardex', m)} title="Ver Movimientos (Kardex)">
                      <ClipboardList size={18} />
                    </button>
                    <button className="action-btn edit" onClick={() => openModal('edit_med', m)} title="Editar"><Edit2 size={18} /></button>
                    <button className="action-btn delete" onClick={() => handleDeleteMed(m.id)} title="Eliminar"><Trash2 size={18} /></button>
                  </td>
                </tr>
              ))}
              {filteredMedicamentos.length === 0 && (
                <tr>
                  <td colSpan="8" className="text-center text-muted py-4">No se encontraron medicamentos</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* CRUD Modal */}
      {(modalType === 'med' || modalType === 'edit_med') && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div className="modal-header">
              <h3>{modalType === 'edit_med' ? 'Editar Medicamento' : 'Nuevo Medicamento'}</h3>
              <button className="close-btn" onClick={closeModal}><X size={24} /></button>
            </div>
            <div className="modal-body">
              <form onSubmit={handleAddMed}>
                <div className="grid grid-cols-2">
                  {newMed.id && (
                    <div className="form-group">
                      <label className="form-label">Código</label>
                      <input readOnly disabled className="form-control" value={newMed.codigo || ''} style={{opacity: 0.7}} />
                    </div>
                  )}
                  <div className="form-group" style={{gridColumn: newMed.id ? 'span 1' : 'span 2'}}>
                    <label className="form-label">Nombre</label>
                    <input required className="form-control" value={newMed.nombre} onChange={e => setNewMed({...newMed, nombre: e.target.value})} />
                  </div>
                </div>
                <div className="grid grid-cols-2">
                  <div className="form-group">
                    <label className="form-label">Presentación</label>
                    <select required className="form-control" value={newMed.presentacion} onChange={e => setNewMed({...newMed, presentacion: e.target.value})}>
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
                    <select required className="form-control" value={newMed.tipo || 'MEDICAMENTO'} onChange={e => setNewMed({...newMed, tipo: e.target.value})}>
                      {TIPOS_MEDICAMENTO.map(t => <option key={t} value={t}>{t}</option>)}
                    </select>
                  </div>
                </div>
                <div className="grid grid-cols-2">
                  <div className="form-group">
                    <label className="form-label">Lote</label>
                    <input className="form-control" value={newMed.lote || ''} onChange={e => setNewMed({...newMed, lote: e.target.value})} />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Fecha de Vencimiento</label>
                    <input type="date" className="form-control" value={newMed.fecha_vencimiento || ''} onChange={e => setNewMed({...newMed, fecha_vencimiento: e.target.value})} />
                  </div>
                </div>
                <div className="form-group">
                  <label className="form-label">Costo Unitario (S/)</label>
                  <input type="number" step="0.01" min="0" required className="form-control" value={newMed.costo_unitario || 0} onChange={e => setNewMed({...newMed, costo_unitario: parseFloat(e.target.value) || 0})} />
                </div>
                <div className="form-group">
                  <label className="form-label">Descripción</label>
                  <textarea className="form-control" value={newMed.descripcion || ''} onChange={e => setNewMed({...newMed, descripcion: e.target.value})} />
                </div>
                <div style={{display: 'flex', justifyContent: 'flex-end', gap: '12px', marginTop: '24px'}}>
                  <button type="button" className="btn btn-secondary" onClick={closeModal}>Cancelar</button>
                  <button type="submit" className="btn btn-primary">Guardar</button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}

      {/* Kardex Modal */}
      {modalType === 'kardex' && selectedKardexMed && (
        <div className="modal-overlay" style={{padding: '20px 0'}}>
          <div className="modal-content" style={{maxWidth: '700px', maxHeight: '90vh', overflowY: 'auto'}}>
            <div className="modal-header" style={{position: 'sticky', top: 0, zIndex: 10, background: 'var(--surface-color)'}}>
              <div>
                <h3 style={{marginBottom: '4px'}}>Kardex Físico - Valorizado</h3>
                <div style={{fontSize: '0.9rem', color: 'var(--text-muted)'}}>
                  {selectedKardexMed.codigo} | {selectedKardexMed.nombre} ({selectedKardexMed.presentacion})
                </div>
              </div>
              <button className="close-btn" onClick={closeModal}><X size={24} /></button>
            </div>
            
            <div className="modal-body" style={{paddingTop: '20px'}}>
              <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px', padding: '15px', background: 'var(--background-color)', borderRadius: '8px'}}>
                <div>
                  <span className="text-muted" style={{display: 'block', fontSize: '0.8rem', textTransform: 'uppercase', letterSpacing: '1px'}}>Stock Actual</span>
                  <span style={{fontSize: '2rem', fontWeight: 'bold', color: 'var(--primary-color)'}}>{selectedKardexMed.stock_actual}</span>
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

export default Medicamentos;
