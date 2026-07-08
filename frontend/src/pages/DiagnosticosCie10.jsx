import { useState, useEffect, useRef } from 'react';
import { API_URL } from '../config';
import { Search, Plus, Trash2, Edit2, Upload, FileSpreadsheet, X } from 'lucide-react';

const DiagnosticosCie10 = () => {
  const [diagnosticos, setDiagnosticos] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [searchTerm, setSearchTerm] = useState('');
  const limit = 10;
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isImporting, setIsImporting] = useState(false);
  
  const [newDiag, setNewDiag] = useState({
    id: null,
    codigo: '',
    descripcion: ''
  });
  
  const fileInputRef = useRef(null);

  const fetchDiagnosticos = () => {
    fetch(`${API_URL}/diagnosticos/?skip=${page * limit}&limit=${limit}${searchTerm ? `&search=${encodeURIComponent(searchTerm)}` : ''}`)
      .then(res => res.json())
      .then(data => {
        setDiagnosticos(data.items || []);
        setTotal(data.total || 0);
      })
      .catch(err => console.error("Error cargando diagnosticos", err));
  };

  useEffect(() => {
    const timer = setTimeout(() => {
      fetchDiagnosticos();
    }, 300);
    return () => clearTimeout(timer);
  }, [page, searchTerm]);

  const handleAdd = (e) => {
    e.preventDefault();
    
    const isEdit = !!newDiag.id;
    const url = isEdit ? `${API_URL}/diagnosticos/${newDiag.id}` : `${API_URL}/diagnosticos/`;
    const method = isEdit ? 'PUT' : 'POST';
    
    const payload = { codigo: newDiag.codigo, descripcion: newDiag.descripcion };

    fetch(url, {
      method: method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
    .then(res => {
      if(!res.ok) throw new Error("Error al guardar");
      return res.json();
    })
    .then(() => {
      fetchDiagnosticos();
      setIsModalOpen(false);
      setNewDiag({ id: null, codigo: '', descripcion: '' });
    })
    .catch(err => {
      alert("Error al guardar el diagnóstico (Verifica que el código no exista o sea correcto).");
      console.error(err);
    });
  };

  const openEditModal = (diag) => {
    setNewDiag({ id: diag.id, codigo: diag.codigo, descripcion: diag.descripcion });
    setIsModalOpen(true);
  };

  const handleDelete = (id) => {
    if (window.confirm('¿Eliminar este diagnóstico del catálogo?')) {
      fetch(`${API_URL}/diagnosticos/${id}`, { method: 'DELETE' })
        .then(() => fetchDiagnosticos())
        .catch(err => console.error("Error eliminando", err));
    }
  };

  const handleImport = (e) => {
    const file = e.target.files[0];
    if (!file) return;
    
    setIsImporting(true);
    const formData = new FormData();
    formData.append('file', file);
    
    fetch(API_URL + '/diagnosticos/importar/', {
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
      fetchDiagnosticos();
      if(fileInputRef.current) fileInputRef.current.value = '';
    })
    .catch(err => {
      setIsImporting(false);
      alert("Error en la importación: " + err.message);
      console.error(err);
      if(fileInputRef.current) fileInputRef.current.value = '';
    });
  };

  // Removed frontend filter, handled by server

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <h1>Catálogo de Diagnósticos (CIE-10)</h1>
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
          
          <button className="btn btn-primary" onClick={() => { setNewDiag({id: null, codigo: '', descripcion: ''}); setIsModalOpen(true); }}>
            <Plus size={18} style={{marginRight: '8px'}} /> Nuevo Diagnóstico
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
                placeholder="Buscar por código o descripción..." 
                value={searchTerm} 
                onChange={e => { setSearchTerm(e.target.value); setPage(0); }} 
              />
            </div>
          </div>
          <div style={{color: 'var(--text-muted)', fontSize: '0.9rem', display: 'flex', alignItems: 'center'}}>
            Total: {total} registros
          </div>
        </div>

        <div className="table-container">
          <table className="table table-compact">
            <thead>
              <tr>
                <th style={{width: '120px'}}>Código</th>
                <th>Descripción / Enfermedad</th>
                <th style={{width: '100px', textAlign: 'center'}}>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {diagnosticos.map(d => (
                <tr key={d.id}>
                  <td><strong>{d.codigo}</strong></td>
                  <td>{d.descripcion}</td>
                  <td style={{textAlign: 'center', whiteSpace: 'nowrap'}}>
                    <button className="icon-btn text-primary" style={{marginRight: '8px', padding: '4px'}} onClick={() => openEditModal(d)} title="Editar">
                      <Edit2 size={16} />
                    </button>
                    <button className="icon-btn text-danger" style={{padding: '4px'}} onClick={() => handleDelete(d.id)} title="Eliminar">
                      <Trash2 size={16} />
                    </button>
                  </td>
                </tr>
              ))}
              {diagnosticos.length === 0 && (
                <tr>
                  <td colSpan="3" style={{textAlign: 'center', padding: '2rem'}}>No se encontraron diagnósticos</td>
                </tr>
              )}
            </tbody>
          </table>
          
          {total > limit && (
            <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '15px', borderTop: '1px solid var(--border-color)'}}>
              <button 
                className="btn btn-secondary" 
                onClick={() => setPage(p => Math.max(0, p - 1))} 
                disabled={page === 0}
              >
                Anterior
              </button>
              <span style={{fontSize: '0.9rem', color: 'var(--text-muted)'}}>
                Página {page + 1} de {Math.ceil(total / limit)}
              </span>
              <button 
                className="btn btn-secondary" 
                onClick={() => setPage(p => p + 1)} 
                disabled={(page + 1) * limit >= total}
              >
                Siguiente
              </button>
            </div>
          )}
        </div>
      </div>

      {isModalOpen && (
        <div className="modal-overlay">
          <div className="modal-content" style={{maxWidth: '500px', padding: '0'}}>
            <div className="modal-header" style={{padding: '20px', borderBottom: '1px solid var(--border-color)', display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
              <h3 style={{margin: 0}}>{newDiag.id ? 'Editar Diagnóstico' : 'Registrar Nuevo Diagnóstico'}</h3>
              <button className="icon-btn text-muted" onClick={() => setIsModalOpen(false)}><X size={20} /></button>
            </div>
            
            <div className="modal-body" style={{padding: '20px'}}>
              <form onSubmit={handleAdd}>
                <div className="form-group">
                  <label className="form-label">Código CIE-10 (u otro)</label>
                  <input 
                    type="text" 
                    className="form-control" 
                    value={newDiag.codigo} 
                    onChange={e => setNewDiag({...newDiag, codigo: e.target.value})} 
                    required 
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">Descripción / Enfermedad</label>
                  <textarea 
                    className="form-control" 
                    rows="4"
                    value={newDiag.descripcion} 
                    onChange={e => setNewDiag({...newDiag, descripcion: e.target.value})} 
                    required 
                  />
                </div>
                <div className="modal-actions" style={{marginTop: '30px', display: 'flex', justifyContent: 'flex-end', gap: '10px'}}>
                  <button type="button" className="btn btn-secondary" onClick={() => setIsModalOpen(false)}>Cancelar</button>
                  <button type="submit" className="btn btn-primary">Guardar Diagnóstico</button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default DiagnosticosCie10;
