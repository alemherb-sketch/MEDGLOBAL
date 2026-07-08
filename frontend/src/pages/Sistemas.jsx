import { useState, useEffect } from 'react';
import { API_URL } from '../config';
import { Search, Plus, Trash2, Edit2, X } from 'lucide-react';

const Sistemas = () => {
  const [sistemas, setSistemas] = useState([]);
  const [contingencias, setContingencias] = useState([]);
  const [modalType, setModalType] = useState(null); // 'sistema' or 'clasificacion'
  const [newSistema, setNewSistema] = useState({ id: null, nombre: '' });
  const [newClasificacion, setNewClasificacion] = useState({ id: null, nombre: '' });
  const [filters, setFilters] = useState({ searchSistemas: '', searchContingencias: '' });

  const fetchData = () => {
    fetch(API_URL + '/sistemas/')
      .then(res => res.json())
      .then(data => setSistemas(data));
    
    fetch(API_URL + '/clasificaciones/')
      .then(res => res.json())
      .then(data => setContingencias(data));
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleAddSistema = (e) => {
    e.preventDefault();
    const isEditing = newSistema.id !== null;
    const url = isEditing ? `${API_URL}/sistemas/${newSistema.id}` : API_URL + '/sistemas/';
    const method = isEditing ? 'PUT' : 'POST';

    fetch(url, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ nombre: newSistema.nombre })
    }).then(() => {
      fetchData();
      closeModal();
    });
  };

  const handleDeleteSistema = (id) => {
    if (window.confirm('¿Eliminar este sistema?')) {
      fetch(`${API_URL}/sistemas/${id}`, { method: 'DELETE' })
        .then(() => fetchData());
    }
  };

  const handleAddClasificacion = (e) => {
    e.preventDefault();
    const isEditing = newClasificacion.id !== null;
    const url = isEditing ? `${API_URL}/clasificaciones/${newClasificacion.id}` : API_URL + '/clasificaciones/';
    const method = isEditing ? 'PUT' : 'POST';

    const dataToSend = { nombre: newClasificacion.nombre };

    fetch(url, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(dataToSend)
    }).then(() => {
      fetchData();
      closeModal();
    });
  };

  const handleDeleteClasificacion = (id) => {
    if (window.confirm('¿Eliminar esta contingencia?')) {
      fetch(`${API_URL}/clasificaciones/${id}`, { method: 'DELETE' })
        .then(() => fetchData());
    }
  };

  const openModal = (type, data = null) => {
    setModalType(type);
    if (type === 'sistema') {
      if (data) {
        setNewSistema({ id: data.id, nombre: data.nombre });
      } else {
        setNewSistema({ id: null, nombre: '' });
      }
    } else if (type === 'clasificacion') {
      if (data) {
        setNewClasificacion({ id: data.id, nombre: data.nombre });
      } else {
        setNewClasificacion({ id: null, nombre: '' });
      }
    }
  };

  const closeModal = () => setModalType(null);

  const filteredSistemas = sistemas.filter(s => s.nombre.toLowerCase().includes(filters.searchSistemas.toLowerCase()));
  const filteredContingencias = contingencias.filter(c => c.nombre.toLowerCase().includes(filters.searchContingencias.toLowerCase()));

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <h1>Sistemas Clínicos y Contingencias</h1>
      </div>
      
      <div className="grid" style={{ gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
        {/* Sistemas Column */}
        <div className="glass-panel">
          <div className="flex justify-between items-center mb-4">
            <h2 style={{ fontSize: '1.25rem', margin: 0 }}>Sistemas Clínicos</h2>
            <button className="btn btn-secondary btn-sm" onClick={() => openModal('sistema')} style={{ padding: '6px 12px' }}>
              <Plus size={16} style={{marginRight: '6px'}} /> Nuevo
            </button>
          </div>
          
          <div className="filter-bar mb-4">
            <div className="form-group mb-0" style={{flex: 1}}>
              <div style={{position: 'relative'}}>
                <Search size={18} style={{position: 'absolute', top: '14px', left: '14px', color: 'var(--text-muted)'}} />
                <input 
                  className="form-control search-input" 
                  style={{paddingLeft: '40px'}}
                  placeholder="Buscar sistema..." 
                  value={filters.searchSistemas} 
                  onChange={e => setFilters({...filters, searchSistemas: e.target.value})} 
                />
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {filteredSistemas.map(s => (
              <div key={s.id} className="p-3 flex justify-between items-center" style={{background: 'rgba(255,255,255,0.05)', borderRadius: '12px', border: '1px solid var(--border-color)'}}>
                <span style={{color: 'var(--primary-color)', fontWeight: '500'}}>{s.nombre}</span>
                <div className="flex gap-2">
                  <button className="action-btn edit" onClick={() => openModal('sistema', s)}><Edit2 size={16} /></button>
                  <button className="action-btn delete" onClick={() => handleDeleteSistema(s.id)}><Trash2 size={16} /></button>
                </div>
              </div>
            ))}
            {filteredSistemas.length === 0 && (
              <div className="text-center text-muted py-4">No se encontraron sistemas</div>
            )}
          </div>
        </div>

        {/* Contingencias Column */}
        <div className="glass-panel">
          <div className="flex justify-between items-center mb-4">
            <h2 style={{ fontSize: '1.25rem', margin: 0 }}>Contingencias</h2>
            <button className="btn btn-primary btn-sm" onClick={() => openModal('clasificacion')} style={{ padding: '6px 12px' }}>
              <Plus size={16} style={{marginRight: '6px'}} /> Nueva
            </button>
          </div>
          
          <div className="filter-bar mb-4">
            <div className="form-group mb-0" style={{flex: 1}}>
              <div style={{position: 'relative'}}>
                <Search size={18} style={{position: 'absolute', top: '14px', left: '14px', color: 'var(--text-muted)'}} />
                <input 
                  className="form-control search-input" 
                  style={{paddingLeft: '40px'}}
                  placeholder="Buscar contingencia..." 
                  value={filters.searchContingencias} 
                  onChange={e => setFilters({...filters, searchContingencias: e.target.value})} 
                />
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {filteredContingencias.map(c => (
              <div key={c.id} className="p-3 flex justify-between items-center" style={{background: 'rgba(255,255,255,0.05)', borderRadius: '12px', border: '1px solid var(--border-color)'}}>
                <span style={{ fontWeight: '500' }}>{c.nombre}</span>
                <div className="flex gap-2">
                  <button className="action-btn edit" onClick={() => openModal('clasificacion', c)}><Edit2 size={16} /></button>
                  <button className="action-btn delete" onClick={() => handleDeleteClasificacion(c.id)}><Trash2 size={16} /></button>
                </div>
              </div>
            ))}
            {filteredContingencias.length === 0 && (
              <div className="text-center text-muted py-4">No se encontraron contingencias</div>
            )}
          </div>
        </div>
      </div>

      {modalType === 'sistema' && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div className="modal-header">
              <h3>{newSistema.id ? 'Editar Sistema Clínico' : 'Nuevo Sistema Clínico'}</h3>
              <button className="close-btn" onClick={closeModal}><X size={24} /></button>
            </div>
            <div className="modal-body">
              <form onSubmit={handleAddSistema}>
                <div className="form-group">
                  <label className="form-label">Nombre del Sistema</label>
                  <input required className="form-control" placeholder="Ej. Respiratorio" value={newSistema.nombre} onChange={e => setNewSistema({...newSistema, nombre: e.target.value})} />
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

      {modalType === 'clasificacion' && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div className="modal-header">
              <h3>{newClasificacion.id ? 'Editar Contingencia' : 'Nueva Contingencia'}</h3>
              <button className="close-btn" onClick={closeModal}><X size={24} /></button>
            </div>
            <div className="modal-body">
              <form onSubmit={handleAddClasificacion}>
                <div className="form-group">
                  <label className="form-label">Nombre de Contingencia</label>
                  <input required className="form-control" placeholder="Ej. Neumonía leve" value={newClasificacion.nombre} onChange={e => setNewClasificacion({...newClasificacion, nombre: e.target.value})} />
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
    </div>
  );
};

export default Sistemas;
