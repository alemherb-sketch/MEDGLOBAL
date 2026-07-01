import { useState, useEffect } from 'react';
import { Search, Plus, Trash2, Edit2, X } from 'lucide-react';

const PersonalSalud = () => {
  const [personal, setPersonal] = useState([]);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [formData, setFormData] = useState({
    id: null, nombre: '', apellidos: '', especialidad: '', cmp: '', telefono: '', correo: '', estado: 'ACTIVO'
  });
  const [filters, setFilters] = useState({ search: '' });

  const fetchPersonal = () => {
    fetch((import.meta.env.VITE_API_URL ? (import.meta.env.VITE_API_URL.startsWith('http') ? import.meta.env.VITE_API_URL : 'https://' + import.meta.env.VITE_API_URL) : 'http://localhost:8000') + '/personal_salud/')
      .then(res => res.json())
      .then(data => setPersonal(data));
  };

  useEffect(() => {
    fetchPersonal();
  }, []);

  const handleSubmit = (e) => {
    e.preventDefault();
    const isEditing = formData.id !== null;
    const url = isEditing ? `http://localhost:8000/personal_salud/${formData.id}` : (import.meta.env.VITE_API_URL ? (import.meta.env.VITE_API_URL.startsWith('http') ? import.meta.env.VITE_API_URL : 'https://' + import.meta.env.VITE_API_URL) : 'http://localhost:8000') + '/personal_salud/';
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
      fetchPersonal();
      closeModal();
    }).catch(err => {
      alert("Error al guardar: " + err.message);
    });
  };

  const handleDelete = (id) => {
    if (window.confirm('¿Está seguro de eliminar a este personal de salud?')) {
      fetch(`http://localhost:8000/personal_salud/${id}`, { method: 'DELETE' })
        .then(() => fetchPersonal());
    }
  };

  const openModal = (p = null) => {
    if (p) {
      setFormData(p);
    } else {
      setFormData({
        id: null, nombre: '', apellidos: '', especialidad: '', cmp: '', telefono: '', correo: '', estado: 'ACTIVO'
      });
    }
    setIsModalOpen(true);
  };

  const closeModal = () => setIsModalOpen(false);

  const filteredPersonal = personal.filter(p => {
    return ((p.nombre||'') + ' ' + (p.apellidos||'') + ' ' + (p.especialidad||'') + ' ' + (p.cmp||''))
      .toLowerCase().includes(filters.search.toLowerCase());
  });

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <h1>Personal de Salud Externo</h1>
        <button className="btn btn-primary" onClick={() => openModal()}>
          <Plus size={18} style={{marginRight: '8px'}} /> Agregar Personal
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
                placeholder="Buscar por nombre, especialidad o CMP..." 
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
                <th>Nombres y Apellidos</th>
                <th>Especialidad</th>
                <th>CMP / CEP</th>
                <th>Contacto</th>
                <th>Estado</th>
                <th style={{textAlign: 'right'}}>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {filteredPersonal.map(p => (
                <tr key={p.id}>
                  <td style={{fontWeight: '500'}}>{p.nombre} {p.apellidos}</td>
                  <td>{p.especialidad}</td>
                  <td>{p.cmp || '-'}</td>
                  <td>
                    <div style={{fontSize: '0.85rem'}}>{p.telefono || '-'}</div>
                    <div style={{fontSize: '0.85rem', color: 'var(--text-muted)'}}>{p.correo || '-'}</div>
                  </td>
                  <td>
                    <span style={{
                      padding: '4px 8px', borderRadius: '4px', fontSize: '0.85rem', fontWeight: 'bold',
                      background: p.estado === 'ACTIVO' ? 'rgba(16, 185, 129, 0.2)' : 'rgba(239, 68, 68, 0.2)',
                      color: p.estado === 'ACTIVO' ? 'var(--success-color)' : 'var(--danger-color)'
                    }}>
                      {p.estado}
                    </span>
                  </td>
                  <td style={{textAlign: 'right', whiteSpace: 'nowrap'}}>
                    <button className="action-btn edit" onClick={() => openModal(p)}><Edit2 size={18} /></button>
                    <button className="action-btn delete" onClick={() => handleDelete(p.id)}><Trash2 size={18} /></button>
                  </td>
                </tr>
              ))}
              {filteredPersonal.length === 0 && (
                <tr>
                  <td colSpan="6" className="text-center text-muted py-4">No se encontraron registros</td>
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
              <h3>{formData.id ? 'Editar Personal de Salud' : 'Nuevo Personal de Salud'}</h3>
              <button className="close-btn" onClick={closeModal}><X size={24} /></button>
            </div>
            <div className="modal-body">
              <form onSubmit={handleSubmit}>
                <div className="grid grid-cols-2">
                  <div className="form-group">
                    <label className="form-label">Nombre</label>
                    <input required className="form-control" value={formData.nombre} onChange={e => setFormData({...formData, nombre: e.target.value})} />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Apellidos</label>
                    <input required className="form-control" value={formData.apellidos} onChange={e => setFormData({...formData, apellidos: e.target.value})} />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Especialidad</label>
                    <input required className="form-control" placeholder="Ej. Traumatología" value={formData.especialidad} onChange={e => setFormData({...formData, especialidad: e.target.value})} />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Colegio Médico (CMP/CEP)</label>
                    <input className="form-control" value={formData.cmp} onChange={e => setFormData({...formData, cmp: e.target.value})} />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Teléfono</label>
                    <input className="form-control" value={formData.telefono} onChange={e => setFormData({...formData, telefono: e.target.value})} />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Estado</label>
                    <select className="form-control" value={formData.estado} onChange={e => setFormData({...formData, estado: e.target.value})}>
                      <option value="ACTIVO">Activo</option>
                      <option value="INACTIVO">Inactivo</option>
                    </select>
                  </div>
                  <div className="form-group" style={{gridColumn: 'span 2'}}>
                    <label className="form-label">Correo electrónico</label>
                    <input type="email" className="form-control" value={formData.correo} onChange={e => setFormData({...formData, correo: e.target.value})} />
                  </div>
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

export default PersonalSalud;
