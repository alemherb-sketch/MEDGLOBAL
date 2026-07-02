import { useState, useEffect } from 'react';
import { API_URL } from '../config';
import { Search, Plus, Edit2, Trash2, X } from 'lucide-react';

const Empresas = () => {
  const [empresas, setEmpresas] = useState([]);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [formData, setFormData] = useState({
    id: null, nombre: '', ruc: '', direccion: '', telefono: '', correo_electronico: '', estado: 'ACTIVO'
  });
  const [filters, setFilters] = useState({ search: '' });

  const fetchEmpresas = () => {
    fetch(API_URL + '/empresas/')
      .then(res => res.json())
      .then(data => setEmpresas(data));
  };

  useEffect(() => {
    fetchEmpresas();
  }, []);

  const handleSubmit = (e) => {
    e.preventDefault();
    const isEditing = formData.id !== null;
    const url = isEditing ? `${API_URL}/empresas/${formData.id}` : API_URL + '/empresas/';
    const method = isEditing ? 'PUT' : 'POST';

    const dataToSend = { ...formData };
    delete dataToSend.id;

    fetch(url, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(dataToSend)
    }).then(async res => {
      if (!res.ok) {
        const err = await res.text();
        throw new Error(err);
      }
      fetchEmpresas();
      closeModal();
    }).catch(err => {
      alert("Error al guardar: " + err.message);
    });
  };

  const handleDelete = (id) => {
    if (window.confirm('¿Está seguro de eliminar esta empresa?')) {
      fetch(`${API_URL}/empresas/${id}`, { method: 'DELETE' })
        .then(() => fetchEmpresas());
    }
  };

  const openModal = (empresa = null) => {
    if (empresa) {
      setFormData({
        id: empresa.id,
        nombre: empresa.nombre || '',
        ruc: empresa.ruc || '',
        direccion: empresa.direccion || '',
        telefono: empresa.telefono || '',
        correo_electronico: empresa.correo_electronico || '',
        estado: empresa.estado || 'ACTIVO'
      });
    } else {
      setFormData({
        id: null, nombre: '', ruc: '', direccion: '', telefono: '', correo_electronico: '', estado: 'ACTIVO'
      });
    }
    setIsModalOpen(true);
  };

  const closeModal = () => setIsModalOpen(false);

  const filteredEmpresas = empresas.filter(e => {
    const searchMatch = (e.nombre + ' ' + e.ruc).toLowerCase().includes(filters.search.toLowerCase());
    return searchMatch;
  });

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <h1>Directorio de Empresas</h1>
        <button className="btn btn-primary" onClick={() => openModal()}>
          <Plus size={18} style={{marginRight: '8px'}} /> Agregar Empresa
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
                placeholder="Buscar por RUC o Razón Social..." 
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
                <th>RUC</th>
                <th>Razón Social</th>
                <th>Dirección</th>
                <th>Contacto</th>
                <th>Estado</th>
                <th style={{textAlign: 'right'}}>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {filteredEmpresas.map(e => (
                <tr key={e.id}>
                  <td style={{fontWeight: 'bold'}}>{e.ruc}</td>
                  <td>{e.nombre}</td>
                  <td>{e.direccion || '-'}</td>
                  <td>
                    {e.telefono && <div>📞 {e.telefono}</div>}
                    {e.correo_electronico && <div style={{fontSize: '0.8rem', color: 'var(--primary-color)'}}>✉️ {e.correo_electronico}</div>}
                  </td>
                  <td>
                    <span style={{
                      padding: '4px 8px', borderRadius: '4px', fontSize: '0.85rem', fontWeight: 'bold',
                      background: e.estado === 'ACTIVO' ? 'rgba(16, 185, 129, 0.2)' : 'rgba(239, 68, 68, 0.2)',
                      color: e.estado === 'ACTIVO' ? 'var(--success-color)' : 'var(--danger-color)'
                    }}>
                      {e.estado || 'ACTIVO'}
                    </span>
                  </td>
                  <td style={{textAlign: 'right'}}>
                    <button className="action-btn edit" onClick={() => openModal(e)}><Edit2 size={18} /></button>
                    <button className="action-btn delete" onClick={() => handleDelete(e.id)}><Trash2 size={18} /></button>
                  </td>
                </tr>
              ))}
              {filteredEmpresas.length === 0 && (
                <tr>
                  <td colSpan="6" className="text-center text-muted py-4">No se encontraron empresas registradas.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {isModalOpen && (
        <div className="modal-overlay">
          <div className="modal-content" style={{maxWidth: '600px'}}>
            <div className="modal-header">
              <h3>{formData.id ? 'Editar Empresa' : 'Nueva Empresa'}</h3>
              <button className="close-btn" onClick={closeModal}><X size={24} /></button>
            </div>
            <div className="modal-body">
              <form onSubmit={handleSubmit}>
                <div className="grid grid-cols-2">
                  <div className="form-group" style={{gridColumn: 'span 2'}}>
                    <label className="form-label">Razón Social</label>
                    <input required className="form-control" value={formData.nombre} onChange={e => setFormData({...formData, nombre: e.target.value})} />
                  </div>
                  <div className="form-group">
                    <label className="form-label">RUC</label>
                    <input required className="form-control" maxLength="11" value={formData.ruc} onChange={e => setFormData({...formData, ruc: e.target.value})} />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Estado</label>
                    <select className="form-control" value={formData.estado} onChange={e => setFormData({...formData, estado: e.target.value})}>
                      <option value="ACTIVO">Activo</option>
                      <option value="INACTIVO">Inactivo</option>
                    </select>
                  </div>
                  <div className="form-group" style={{gridColumn: 'span 2'}}>
                    <label className="form-label">Dirección Fiscal / Sede</label>
                    <input className="form-control" value={formData.direccion} onChange={e => setFormData({...formData, direccion: e.target.value})} />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Teléfono de Contacto</label>
                    <input className="form-control" value={formData.telefono} onChange={e => setFormData({...formData, telefono: e.target.value})} />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Correos Electrónicos</label>
                    <input className="form-control" placeholder="Ej: email1@emp.com, email2@emp.com" value={formData.correo_electronico} onChange={e => setFormData({...formData, correo_electronico: e.target.value})} />
                    <small className="text-muted" style={{fontSize: '0.75rem', marginTop: '4px', display: 'block'}}>Separar por comas (Máximo 3 recomendados)</small>
                  </div>
                </div>

                <div style={{display: 'flex', justifyContent: 'flex-end', gap: '12px', marginTop: '24px'}}>
                  <button type="button" className="btn btn-secondary" onClick={closeModal}>Cancelar</button>
                  <button type="submit" className="btn btn-primary">Guardar Empresa</button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Empresas;
