import { useState, useEffect } from 'react';
import { Search, Plus, Edit2, Trash2, X } from 'lucide-react';

const Planilla = () => {
  const [trabajadores, setTrabajadores] = useState([]);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [formData, setFormData] = useState({
    id: null, nombre: '', apellidos: '', dni: '', tipo_contrato: '', afp_onp: '', rol: '',
    codigo_trabajador: '', cargo: '', fecha_ingreso: '', fecha_cese: '', estado_trabajador: 'ACTIVO',
    subdivision_sede: '', centro_costo: '', tipo_calculo_nomina: '', area_personal: '',
    grupo_personal: '', nivel_org_1: '', nivel_org_2: '', nivel_org_3: '', nivel_org_4: '',
    nivel_org_5: '', fecha_nacimiento: '', genero: '', jefe_inmediato: '', telefono: '', correo_electronico: ''
  });
  const [filters, setFilters] = useState({ search: '' });

  const fetchTrabajadores = () => {
    fetch((import.meta.env.VITE_API_URL ? (import.meta.env.VITE_API_URL.startsWith('http') ? import.meta.env.VITE_API_URL : 'https://' + import.meta.env.VITE_API_URL) : 'http://localhost:8000') + '/trabajadores/')
      .then(res => res.json())
      .then(data => setTrabajadores(data));
  };

  useEffect(() => {
    fetchTrabajadores();
  }, []);

  const handleSubmit = (e) => {
    e.preventDefault();
    const isEditing = formData.id !== null;
    const url = isEditing ? `http://localhost:8000/trabajadores/${formData.id}` : (import.meta.env.VITE_API_URL ? (import.meta.env.VITE_API_URL.startsWith('http') ? import.meta.env.VITE_API_URL : 'https://' + import.meta.env.VITE_API_URL) : 'http://localhost:8000') + '/trabajadores/';
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
      fetchTrabajadores();
      closeModal();
    }).catch(err => {
      alert("Error al guardar: " + err.message);
    });
  };

  const handleDelete = (id) => {
    if (window.confirm('¿Está seguro de eliminar este trabajador?')) {
      fetch(`http://localhost:8000/trabajadores/${id}`, { method: 'DELETE' })
        .then(() => fetchTrabajadores());
    }
  };

  const openModal = (trabajador = null) => {
    if (trabajador) {
      setFormData({
        id: trabajador.id,
        nombre: trabajador.nombre || '', apellidos: trabajador.apellidos || '', dni: trabajador.dni || '',
        tipo_contrato: trabajador.tipo_contrato || '', afp_onp: trabajador.afp_onp || '', rol: trabajador.rol || '',
        codigo_trabajador: trabajador.codigo_trabajador || '', cargo: trabajador.cargo || '', fecha_ingreso: trabajador.fecha_ingreso || '',
        fecha_cese: trabajador.fecha_cese || '', estado_trabajador: trabajador.estado_trabajador || 'ACTIVO',
        subdivision_sede: trabajador.subdivision_sede || '', centro_costo: trabajador.centro_costo || '',
        tipo_calculo_nomina: trabajador.tipo_calculo_nomina || '', area_personal: trabajador.area_personal || '',
        grupo_personal: trabajador.grupo_personal || '', nivel_org_1: trabajador.nivel_org_1 || '',
        nivel_org_2: trabajador.nivel_org_2 || '', nivel_org_3: trabajador.nivel_org_3 || '',
        nivel_org_4: trabajador.nivel_org_4 || '', nivel_org_5: trabajador.nivel_org_5 || '',
        fecha_nacimiento: trabajador.fecha_nacimiento || '', genero: trabajador.genero || '',
        jefe_inmediato: trabajador.jefe_inmediato || '', telefono: trabajador.telefono || '', correo_electronico: trabajador.correo_electronico || ''
      });
    } else {
      setFormData({
        id: null, nombre: '', apellidos: '', dni: '', tipo_contrato: '', afp_onp: '', rol: '',
        codigo_trabajador: '', cargo: '', fecha_ingreso: '', fecha_cese: '', estado_trabajador: 'ACTIVO',
        subdivision_sede: '', centro_costo: '', tipo_calculo_nomina: '', area_personal: '',
        grupo_personal: '', nivel_org_1: '', nivel_org_2: '', nivel_org_3: '', nivel_org_4: '',
        nivel_org_5: '', fecha_nacimiento: '', genero: '', jefe_inmediato: '', telefono: '', correo_electronico: ''
      });
    }
    setIsModalOpen(true);
  };

  const closeModal = () => setIsModalOpen(false);

  const filteredTrabajadores = trabajadores.filter(t => {
    const searchMatch = ((t.codigo_trabajador||'') + ' ' + t.nombre + ' ' + t.apellidos + ' ' + t.dni).toLowerCase().includes(filters.search.toLowerCase());
    return searchMatch;
  });

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <h1>Gestión de Planilla</h1>
        <button className="btn btn-primary" onClick={() => openModal()}>
          <Plus size={18} style={{marginRight: '8px'}} /> Agregar Trabajador
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
                placeholder="Buscar por código, nombre, apellidos o DNI..." 
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
                <th>DNI</th>
                <th>Nombre Completo</th>
                <th>Cargo / Rol</th>
                <th>Sede</th>
                <th>Estado</th>
                <th style={{textAlign: 'right'}}>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {filteredTrabajadores.map(t => (
                <tr key={t.id}>
                  <td>{t.codigo_trabajador || '-'}</td>
                  <td>{t.dni}</td>
                  <td>{t.nombre} {t.apellidos}</td>
                  <td>
                    {t.cargo && <div>{t.cargo}</div>}
                    <div style={{fontSize: '0.8rem', color: 'var(--primary-color)'}}>{t.rol}</div>
                  </td>
                  <td>{t.subdivision_sede || '-'}</td>
                  <td>
                    <span style={{
                      padding: '4px 8px', borderRadius: '4px', fontSize: '0.85rem', fontWeight: 'bold',
                      background: t.estado_trabajador === 'ACTIVO' ? 'rgba(16, 185, 129, 0.2)' : 'rgba(239, 68, 68, 0.2)',
                      color: t.estado_trabajador === 'ACTIVO' ? 'var(--success-color)' : 'var(--danger-color)'
                    }}>
                      {t.estado_trabajador || 'ACTIVO'}
                    </span>
                  </td>
                  <td style={{textAlign: 'right'}}>
                    <button className="action-btn edit" onClick={() => openModal(t)}><Edit2 size={18} /></button>
                    <button className="action-btn delete" onClick={() => handleDelete(t.id)}><Trash2 size={18} /></button>
                  </td>
                </tr>
              ))}
              {filteredTrabajadores.length === 0 && (
                <tr>
                  <td colSpan="7" className="text-center text-muted py-4">No se encontraron trabajadores</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {isModalOpen && (
        <div className="modal-overlay">
          <div className="modal-content" style={{maxWidth: '800px'}}>
            <div className="modal-header">
              <h3>{formData.id ? 'Editar Trabajador' : 'Nuevo Trabajador'}</h3>
              <button className="close-btn" onClick={closeModal}><X size={24} /></button>
            </div>
            <div className="modal-body" style={{maxHeight: '75vh', overflowY: 'auto'}}>
              <form onSubmit={handleSubmit}>
                <h4 style={{borderBottom: '1px solid var(--border-color)', paddingBottom: '8px', marginBottom: '16px', color: 'var(--primary-color)'}}>Datos Personales</h4>
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
                    <label className="form-label">DNI</label>
                    <input required className="form-control" maxLength="20" value={formData.dni} onChange={e => setFormData({...formData, dni: e.target.value})} />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Fecha de Nacimiento</label>
                    <input type="date" className="form-control" value={formData.fecha_nacimiento} onChange={e => setFormData({...formData, fecha_nacimiento: e.target.value})} />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Género</label>
                    <select className="form-control" value={formData.genero} onChange={e => setFormData({...formData, genero: e.target.value})}>
                      <option value="">Seleccione...</option>
                      <option value="M">Masculino</option>
                      <option value="F">Femenino</option>
                      <option value="O">Otro</option>
                    </select>
                  </div>
                  <div className="form-group">
                    <label className="form-label">Nº Teléfono</label>
                    <input className="form-control" value={formData.telefono} onChange={e => setFormData({...formData, telefono: e.target.value})} />
                  </div>
                  <div className="form-group" style={{gridColumn: 'span 2'}}>
                    <label className="form-label">Correo electrónico</label>
                    <input type="email" className="form-control" value={formData.correo_electronico} onChange={e => setFormData({...formData, correo_electronico: e.target.value})} />
                  </div>
                </div>

                <h4 style={{borderBottom: '1px solid var(--border-color)', paddingBottom: '8px', marginBottom: '16px', marginTop: '24px', color: 'var(--primary-color)'}}>Datos Corporativos</h4>
                <div className="grid grid-cols-2">
                  <div className="form-group">
                    <label className="form-label">Código de Trabajador</label>
                    <input className="form-control" value={formData.codigo_trabajador} onChange={e => setFormData({...formData, codigo_trabajador: e.target.value})} />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Estado del trabajador</label>
                    <select className="form-control" value={formData.estado_trabajador} onChange={e => setFormData({...formData, estado_trabajador: e.target.value})}>
                      <option value="ACTIVO">Activo</option>
                      <option value="CESADO">Cesado</option>
                      <option value="VACACIONES">Vacaciones</option>
                      <option value="DESCANSO_MEDICO">Descanso Médico</option>
                    </select>
                  </div>
                  <div className="form-group">
                    <label className="form-label">Rol en Sistema</label>
                    <select required className="form-control" value={formData.rol} onChange={e => setFormData({...formData, rol: e.target.value})}>
                      <option value="">Seleccione...</option>
                      <option value="Médico">Médico</option>
                      <option value="Enfermera">Enfermera</option>
                      <option value="Farmacéutico">Farmacéutico</option>
                      <option value="Administrativo">Administrativo</option>
                    </select>
                  </div>
                  <div className="form-group">
                    <label className="form-label">Cargo</label>
                    <input className="form-control" value={formData.cargo} onChange={e => setFormData({...formData, cargo: e.target.value})} />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Jefe inmediato</label>
                    <input className="form-control" value={formData.jefe_inmediato} onChange={e => setFormData({...formData, jefe_inmediato: e.target.value})} />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Fecha de Ingreso</label>
                    <input type="date" className="form-control" value={formData.fecha_ingreso} onChange={e => setFormData({...formData, fecha_ingreso: e.target.value})} />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Fecha de Cese</label>
                    <input type="date" className="form-control" value={formData.fecha_cese} onChange={e => setFormData({...formData, fecha_cese: e.target.value})} />
                  </div>
                </div>

                <h4 style={{borderBottom: '1px solid var(--border-color)', paddingBottom: '8px', marginBottom: '16px', marginTop: '24px', color: 'var(--primary-color)'}}>Estructura Organizativa</h4>
                <div className="grid grid-cols-2">
                  <div className="form-group">
                    <label className="form-label">Subdivisión - Sede</label>
                    <input className="form-control" value={formData.subdivision_sede} onChange={e => setFormData({...formData, subdivision_sede: e.target.value})} />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Centro de Costo (Código)</label>
                    <input className="form-control" value={formData.centro_costo} onChange={e => setFormData({...formData, centro_costo: e.target.value})} />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Área de Personal</label>
                    <input className="form-control" value={formData.area_personal} onChange={e => setFormData({...formData, area_personal: e.target.value})} />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Grupo de personal</label>
                    <input className="form-control" value={formData.grupo_personal} onChange={e => setFormData({...formData, grupo_personal: e.target.value})} />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Nivel organizativo 1</label>
                    <input className="form-control" value={formData.nivel_org_1} onChange={e => setFormData({...formData, nivel_org_1: e.target.value})} />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Nivel organizativo 2</label>
                    <input className="form-control" value={formData.nivel_org_2} onChange={e => setFormData({...formData, nivel_org_2: e.target.value})} />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Nivel organizativo 3</label>
                    <input className="form-control" value={formData.nivel_org_3} onChange={e => setFormData({...formData, nivel_org_3: e.target.value})} />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Nivel organizativo 4</label>
                    <input className="form-control" value={formData.nivel_org_4} onChange={e => setFormData({...formData, nivel_org_4: e.target.value})} />
                  </div>
                  <div className="form-group" style={{gridColumn: 'span 2'}}>
                    <label className="form-label">Nivel organizativo 5</label>
                    <input className="form-control" value={formData.nivel_org_5} onChange={e => setFormData({...formData, nivel_org_5: e.target.value})} />
                  </div>
                </div>

                <h4 style={{borderBottom: '1px solid var(--border-color)', paddingBottom: '8px', marginBottom: '16px', marginTop: '24px', color: 'var(--primary-color)'}}>Nómina</h4>
                <div className="grid grid-cols-2">
                  <div className="form-group">
                    <label className="form-label">Tipo de cálculo de nómina (Label)</label>
                    <input className="form-control" value={formData.tipo_calculo_nomina} onChange={e => setFormData({...formData, tipo_calculo_nomina: e.target.value})} />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Sistema Pensiones (AFP/ONP)</label>
                    <input className="form-control" value={formData.afp_onp} onChange={e => setFormData({...formData, afp_onp: e.target.value})} />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Tipo Contrato</label>
                    <input className="form-control" value={formData.tipo_contrato} onChange={e => setFormData({...formData, tipo_contrato: e.target.value})} />
                  </div>
                </div>

                <div style={{display: 'flex', justifyContent: 'flex-end', gap: '12px', marginTop: '32px', position: 'sticky', bottom: '-24px', background: 'var(--panel-bg)', padding: '16px 0', borderTop: '1px solid var(--border-color)', zIndex: 10}}>
                  <button type="button" className="btn btn-secondary" onClick={closeModal}>Cancelar</button>
                  <button type="submit" className="btn btn-primary">Guardar Trabajador</button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Planilla;
