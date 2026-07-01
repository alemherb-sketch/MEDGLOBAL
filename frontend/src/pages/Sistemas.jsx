import { useState, useEffect } from 'react';
import { Search, Plus, Trash2, Edit2, X } from 'lucide-react';

const Sistemas = () => {
  const [sistemas, setSistemas] = useState([]);
  const [modalType, setModalType] = useState(null); // 'sistema' or 'clasificacion'
  const [newSistema, setNewSistema] = useState({ id: null, nombre: '' });
  const [newClasificacion, setNewClasificacion] = useState({ id: null, nombre: '', sistema_id: '' });
  const [filters, setFilters] = useState({ search: '' });

  const fetchSistemas = () => {
    fetch((import.meta.env.VITE_API_URL ? (import.meta.env.VITE_API_URL.startsWith('http') ? import.meta.env.VITE_API_URL : 'https://' + import.meta.env.VITE_API_URL) : 'http://localhost:8000') + '/sistemas/')
      .then(res => res.json())
      .then(data => setSistemas(data));
  };

  useEffect(() => {
    fetchSistemas();
  }, []);

  const handleAddSistema = (e) => {
    e.preventDefault();
    const isEditing = newSistema.id !== null;
    const url = isEditing ? `http://localhost:8000/sistemas/${newSistema.id}` : (import.meta.env.VITE_API_URL ? (import.meta.env.VITE_API_URL.startsWith('http') ? import.meta.env.VITE_API_URL : 'https://' + import.meta.env.VITE_API_URL) : 'http://localhost:8000') + '/sistemas/';
    const method = isEditing ? 'PUT' : 'POST';

    fetch(url, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ nombre: newSistema.nombre })
    }).then(() => {
      fetchSistemas();
      closeModal();
    });
  };

  const handleDeleteSistema = (id) => {
    if (window.confirm('¿Eliminar sistema y sus clasificaciones?')) {
      fetch(`http://localhost:8000/sistemas/${id}`, { method: 'DELETE' })
        .then(() => fetchSistemas());
    }
  };

  const handleAddClasificacion = (e) => {
    e.preventDefault();
    const isEditing = newClasificacion.id !== null;
    const url = isEditing ? `http://localhost:8000/clasificaciones/${newClasificacion.id}` : (import.meta.env.VITE_API_URL ? (import.meta.env.VITE_API_URL.startsWith('http') ? import.meta.env.VITE_API_URL : 'https://' + import.meta.env.VITE_API_URL) : 'http://localhost:8000') + '/clasificaciones/';
    const method = isEditing ? 'PUT' : 'POST';

    const dataToSend = { ...newClasificacion };
    delete dataToSend.id;

    fetch(url, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(dataToSend)
    }).then(() => {
      fetchSistemas();
      closeModal();
    });
  };

  const handleDeleteClasificacion = (id) => {
    if (window.confirm('¿Eliminar esta clasificación?')) {
      fetch(`http://localhost:8000/clasificaciones/${id}`, { method: 'DELETE' })
        .then(() => fetchSistemas());
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
        setNewClasificacion({ id: data.id, nombre: data.nombre, sistema_id: data.sistema_id });
      } else {
        setNewClasificacion({ id: null, nombre: '', sistema_id: data?.sistema_id || '' });
      }
    }
  };

  const closeModal = () => setModalType(null);

  const filteredSistemas = sistemas.filter(s => s.nombre.toLowerCase().includes(filters.search.toLowerCase()));

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <h1>Sistemas Clínicos y Clasificaciones</h1>
        <div className="flex gap-2">
          <button className="btn btn-secondary" onClick={() => openModal('sistema')}>
            <Plus size={18} style={{marginRight: '8px'}} /> Nuevo Sistema
          </button>
          <button className="btn btn-primary" onClick={() => openModal('clasificacion')}>
            <Plus size={18} style={{marginRight: '8px'}} /> Nueva Clasificación
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
                placeholder="Buscar sistema clínico..." 
                value={filters.search} 
                onChange={e => setFilters({...filters, search: e.target.value})} 
              />
            </div>
          </div>
        </div>

        <div className="mt-3">
          {filteredSistemas.map(s => (
            <div key={s.id} className="mb-4 p-4" style={{background: 'rgba(255,255,255,0.05)', borderRadius: '12px', border: '1px solid var(--border-color)'}}>
              <div className="flex justify-between items-center mb-3 pb-2" style={{borderBottom: '1px solid rgba(255,255,255,0.1)'}}>
                <h3 style={{color: 'var(--primary-color)', margin: 0}}>{s.nombre}</h3>
                <div>
                  <button className="action-btn edit" onClick={() => openModal('sistema', s)}><Edit2 size={18} /></button>
                  <button className="action-btn delete" onClick={() => handleDeleteSistema(s.id)}><Trash2 size={18} /></button>
                </div>
              </div>
              <ul style={{listStyle: 'none', paddingLeft: '0', margin: 0}}>
                {s.clasificaciones && s.clasificaciones.length > 0 ? (
                  s.clasificaciones.map(c => (
                    <li key={c.id} className="flex justify-between items-center" style={{padding: '8px 12px', borderRadius: '6px', transition: 'background 0.2s'}}>
                      <span>{c.nombre}</span>
                      <div className="flex gap-2">
                        <button className="action-btn edit" onClick={() => openModal('clasificacion', {id: c.id, nombre: c.nombre, sistema_id: s.id})}><Edit2 size={16} /></button>
                        <button className="action-btn delete" onClick={() => handleDeleteClasificacion(c.id)}><Trash2 size={16} /></button>
                      </div>
                    </li>
                  ))
                ) : (
                  <li className="text-muted p-2">Sin clasificaciones</li>
                )}
              </ul>
            </div>
          ))}
          {filteredSistemas.length === 0 && (
            <div className="text-center text-muted py-4">No se encontraron sistemas</div>
          )}
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
              <h3>{newClasificacion.id ? 'Editar Clasificación' : 'Nueva Clasificación'}</h3>
              <button className="close-btn" onClick={closeModal}><X size={24} /></button>
            </div>
            <div className="modal-body">
              <form onSubmit={handleAddClasificacion}>
                <div className="form-group">
                  <label className="form-label">Sistema</label>
                  <select required className="form-control" value={newClasificacion.sistema_id} onChange={e => setNewClasificacion({...newClasificacion, sistema_id: e.target.value})}>
                    <option value="">Seleccione un sistema...</option>
                    {sistemas.map(s => <option key={s.id} value={s.id}>{s.nombre}</option>)}
                  </select>
                </div>
                <div className="form-group">
                  <label className="form-label">Nombre de Clasificación</label>
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
