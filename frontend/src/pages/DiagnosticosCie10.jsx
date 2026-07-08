import { useState, useEffect, useRef } from 'react';
import { API_URL } from '../config';
import { Search, Plus, Trash2, Upload, FileSpreadsheet } from 'lucide-react';

const DiagnosticosCie10 = () => {
  const [diagnosticos, setDiagnosticos] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isImporting, setIsImporting] = useState(false);
  
  const [newDiag, setNewDiag] = useState({
    codigo: '',
    descripcion: ''
  });
  
  const fileInputRef = useRef(null);

  const fetchDiagnosticos = () => {
    fetch(API_URL + '/diagnosticos/')
      .then(res => res.json())
      .then(data => setDiagnosticos(data))
      .catch(err => console.error("Error cargando diagnosticos", err));
  };

  useEffect(() => {
    fetchDiagnosticos();
  }, []);

  const handleAdd = (e) => {
    e.preventDefault();
    fetch(API_URL + '/diagnosticos/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(newDiag)
    })
    .then(res => {
      if(!res.ok) throw new Error("Error al guardar");
      return res.json();
    })
    .then(() => {
      fetchDiagnosticos();
      setIsModalOpen(false);
      setNewDiag({ codigo: '', descripcion: '' });
    })
    .catch(err => {
      alert("Error al guardar el diagnóstico (Verifica que el código no exista).");
      console.error(err);
    });
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
    .then(res => res.json())
    .then(data => {
      setIsImporting(false);
      alert(data.message || "Importación completada");
      fetchDiagnosticos();
      if(fileInputRef.current) fileInputRef.current.value = '';
    })
    .catch(err => {
      setIsImporting(false);
      alert("Error en la importación. Asegúrate de usar un archivo Excel con Código en la 1ra columna y Descripción en la 2da.");
      console.error(err);
      if(fileInputRef.current) fileInputRef.current.value = '';
    });
  };

  const filtered = diagnosticos.filter(d => 
    d.codigo.toLowerCase().includes(searchTerm.toLowerCase()) || 
    d.descripcion.toLowerCase().includes(searchTerm.toLowerCase())
  );

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
          
          <button className="btn btn-primary" onClick={() => setIsModalOpen(true)}>
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
                onChange={e => setSearchTerm(e.target.value)} 
              />
            </div>
          </div>
          <div style={{color: 'var(--text-muted)', fontSize: '0.9rem', display: 'flex', alignItems: 'center'}}>
            Total: {diagnosticos.length} registros
          </div>
        </div>

        <div className="table-container">
          <table className="table">
            <thead>
              <tr>
                <th style={{width: '120px'}}>Código</th>
                <th>Descripción / Enfermedad</th>
                <th style={{width: '100px', textAlign: 'center'}}>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map(d => (
                <tr key={d.id}>
                  <td><strong>{d.codigo}</strong></td>
                  <td>{d.descripcion}</td>
                  <td style={{textAlign: 'center'}}>
                    <button className="icon-btn text-danger" onClick={() => handleDelete(d.id)} title="Eliminar">
                      <Trash2 size={18} />
                    </button>
                  </td>
                </tr>
              ))}
              {filtered.length === 0 && (
                <tr>
                  <td colSpan="3" style={{textAlign: 'center', padding: '2rem'}}>No se encontraron diagnósticos</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {isModalOpen && (
        <div className="modal-overlay">
          <div className="modal-content" style={{maxWidth: '500px'}}>
            <h2>Registrar Nuevo Diagnóstico</h2>
            <form onSubmit={handleAdd}>
              <div className="form-group">
                <label>Código CIE-10 (u otro)</label>
                <input 
                  type="text" 
                  className="form-control" 
                  value={newDiag.codigo} 
                  onChange={e => setNewDiag({...newDiag, codigo: e.target.value})} 
                  required 
                />
              </div>
              <div className="form-group">
                <label>Descripción / Enfermedad</label>
                <textarea 
                  className="form-control" 
                  rows="3"
                  value={newDiag.descripcion} 
                  onChange={e => setNewDiag({...newDiag, descripcion: e.target.value})} 
                  required 
                />
              </div>
              <div className="modal-actions">
                <button type="button" className="btn btn-secondary" onClick={() => setIsModalOpen(false)}>Cancelar</button>
                <button type="submit" className="btn btn-primary">Guardar Diagnóstico</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default DiagnosticosCie10;
