import { useState, useEffect } from 'react';
import { API_URL } from '../config';
import { Search, Plus, Trash2, Edit2, X, Link, Clock, Eye } from 'lucide-react';
import Select from 'react-select';

const Atenciones = () => {
  const [atenciones, setAtenciones] = useState([]);
  const [trabajadores, setTrabajadores] = useState([]);
  const [sistemas, setSistemas] = useState([]);
  const [citas, setCitas] = useState([]);
  const [personalSalud, setPersonalSalud] = useState([]);
  const [medicamentos, setMedicamentos] = useState([]);
  const [empresas, setEmpresas] = useState([]);
  const [diagnosticosCatalog, setDiagnosticosCatalog] = useState([]);
  
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [viewAtencion, setViewAtencion] = useState(null);
  const [printMode, setPrintMode] = useState('ficha');
  const [filters, setFilters] = useState({ search: '', date: '' });
  
  const [newAtencion, setNewAtencion] = useState({
    id: null,
    trabajador_id: '',
    sistema_id: '',
    clasificacion_id: '',
    personal_salud_id: '',
    hora_ingreso: '',
    edad: '',
    residencia: '',
    empresa_id: '',
    cargo: '',
    descripcion: '',
    funciones_biologicas: { apetito: '', sed: '', sueno: '', estado_animo: '', orina: '', deposiciones: '' },
    signos_vitales: { presion_arterial: '', frec_cardiaca: '', frec_respiratoria: '', temperatura: '', spo2: '', peso: '', talla: '' },
    examen_fisico: '',
    examenes_auxiliares: '',
    codigo_diagnostico: '',
    diagnostico: '',
    diagnostico_1: '',
    diagnostico_2: '',
    diagnostico_3: '',
    destino: '',
    observaciones: '',
    tratamiento: '',
    medicamentos: [] // Array of {medicamento_id, cantidad}
  });

  const fetchData = () => {
    fetch(API_URL + '/atenciones/').then(res => res.json()).then(setAtenciones);
    fetch(API_URL + '/trabajadores/').then(res => res.json()).then(setTrabajadores);
    fetch(API_URL + '/sistemas/').then(res => res.json()).then(setSistemas);
    fetch(API_URL + '/citas/').then(res => res.json()).then(setCitas);
    fetch(API_URL + '/personal_salud/').then(res => res.json()).then(setPersonalSalud);
    fetch(API_URL + '/medicamentos/').then(res => res.json()).then(setMedicamentos);
    fetch(API_URL + '/empresas/').then(res => res.json()).then(setEmpresas);
    fetch(API_URL + '/diagnosticos/').then(res => res.json()).then(setDiagnosticosCatalog);
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleAddAtencion = (e) => {
    e.preventDefault();
    const isEditing = newAtencion.id !== null;
    const url = isEditing ? `${API_URL}/atenciones/${newAtencion.id}` : API_URL + '/atenciones/';
    const method = isEditing ? 'PUT' : 'POST';

    const dataToSend = { ...newAtencion };
    delete dataToSend.id;
    
    // Parse ints
    dataToSend.trabajador_id = parseInt(dataToSend.trabajador_id);
    dataToSend.sistema_id = parseInt(dataToSend.sistema_id);
    dataToSend.clasificacion_id = parseInt(dataToSend.clasificacion_id);
    if (dataToSend.cita_id) dataToSend.cita_id = parseInt(dataToSend.cita_id); else delete dataToSend.cita_id;
    if (dataToSend.personal_salud_id) dataToSend.personal_salud_id = parseInt(dataToSend.personal_salud_id); else delete dataToSend.personal_salud_id;
    if (dataToSend.empresa_id) dataToSend.empresa_id = parseInt(dataToSend.empresa_id); else delete dataToSend.empresa_id;

    dataToSend.funciones_biologicas = JSON.stringify(dataToSend.funciones_biologicas);
    dataToSend.signos_vitales = JSON.stringify(dataToSend.signos_vitales);

    // Convert string array to proper integer array
    dataToSend.medicamentos = dataToSend.medicamentos.map(m => ({
      medicamento_id: parseInt(m.medicamento_id),
      cantidad: parseInt(m.cantidad)
    }));

    fetch(url, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(dataToSend)
    }).then(() => {
      fetchData();
      closeModal();
    }).catch(err => {
      alert("Error al guardar la atención.");
      console.error(err);
    });
  };

  const handleDelete = (id) => {
    if (window.confirm('¿Está seguro de eliminar este registro de atención?')) {
      fetch(`${API_URL}/atenciones/${id}`, { method: 'DELETE' })
        .then(() => fetchData());
    }
  };

  const openModal = (atencion = null) => {
    if (atencion) {
      setNewAtencion({
        id: atencion.id,
        trabajador_id: atencion.trabajador?.id || '',
        sistema_id: atencion.sistema?.id || '',
        clasificacion_id: atencion.clasificacion?.id || '',
        personal_salud_id: atencion.personal_salud_id || '',
        hora_ingreso: atencion.hora_ingreso || '',
        edad: atencion.edad || '',
        residencia: atencion.residencia || '',
        empresa_id: atencion.empresa_id || '',
        cargo: atencion.cargo || '',
        descripcion: atencion.descripcion || '',
        funciones_biologicas: atencion.funciones_biologicas ? JSON.parse(atencion.funciones_biologicas) : { apetito: '', sed: '', sueno: '', estado_animo: '', orina: '', deposiciones: '' },
        signos_vitales: atencion.signos_vitales ? JSON.parse(atencion.signos_vitales) : { presion_arterial: '', frec_cardiaca: '', frec_respiratoria: '', temperatura: '', spo2: '', peso: '', talla: '' },
        examen_fisico: atencion.examen_fisico || '',
        examenes_auxiliares: atencion.examenes_auxiliares || '',
        codigo_diagnostico: atencion.codigo_diagnostico || '',
        diagnostico: atencion.diagnostico || '',
        diagnostico_1: atencion.diagnostico_1 || '',
        diagnostico_2: atencion.diagnostico_2 || '',
        diagnostico_3: atencion.diagnostico_3 || '',
        destino: atencion.destino || '',
        observaciones: atencion.observaciones || '',
        tratamiento: atencion.tratamiento || '',
        medicamentos: atencion.medicamentos ? atencion.medicamentos.map(m => ({medicamento_id: m.medicamento_id, cantidad: m.cantidad})) : []
      });
    } else {
      setNewAtencion({
        id: null, trabajador_id: '', sistema_id: '', clasificacion_id: '', personal_salud_id: '',
        hora_ingreso: new Date().toTimeString().substring(0,5), edad: '', residencia: '', empresa_id: '', cargo: '',
        descripcion: '', funciones_biologicas: { apetito: '', sed: '', sueno: '', estado_animo: '', orina: '', deposiciones: '' },
        signos_vitales: { presion_arterial: '', frec_cardiaca: '', frec_respiratoria: '', temperatura: '', spo2: '', peso: '', talla: '' },
        examen_fisico: '', examenes_auxiliares: '', codigo_diagnostico: '', diagnostico: '',
        diagnostico_1: '', diagnostico_2: '', diagnostico_3: '',
        destino: '', observaciones: '', tratamiento: '', medicamentos: []
      });
    }
    setIsModalOpen(true);
  };

  const closeModal = () => setIsModalOpen(false);

  // Auto-fill worker details when worker changes
  const handleTrabajadorChange = (e) => {
    const t_id = e.target.value;
    const trabajador = trabajadores.find(t => t.id === parseInt(t_id));
    
    // Auto-calculate age if fecha_nacimiento exists, else leave empty for manual
    let ageCalc = '';
    if (trabajador && trabajador.fecha_nacimiento) {
      const birth = new Date(trabajador.fecha_nacimiento);
      const diff_ms = Date.now() - birth.getTime();
      const age_dt = new Date(diff_ms); 
      ageCalc = Math.abs(age_dt.getUTCFullYear() - 1970).toString();
    }

    setNewAtencion({
      ...newAtencion,
      trabajador_id: t_id,
      cargo: trabajador ? (trabajador.cargo || '') : '',
      empresa_id: trabajador ? (trabajador.empresa_id || '') : '',
      edad: ageCalc || newAtencion.edad
    });
  };

  // Medicamentos handlers
  const addMedicamento = () => {
    setNewAtencion({...newAtencion, medicamentos: [...newAtencion.medicamentos, {medicamento_id: '', cantidad: 1}]});
  };

  const updateMedicamento = (index, field, value) => {
    const newMeds = [...newAtencion.medicamentos];
    newMeds[index][field] = value;
    setNewAtencion({...newAtencion, medicamentos: newMeds});
  };

  const removeMedicamento = (index) => {
    const newMeds = [...newAtencion.medicamentos];
    newMeds.splice(index, 1);
    setNewAtencion({...newAtencion, medicamentos: newMeds});
  };

  const clasificacionesDisponibles = sistemas.flatMap(s => s.clasificaciones || []);
  
  const filteredAtenciones = atenciones.filter(a => {
    const searchStr = (
      (a.trabajador ? `${a.trabajador.nombre} ${a.trabajador.apellidos}` : '') + 
      (a.sistema ? a.sistema.nombre : '') + 
      (a.clasificacion ? a.clasificacion.nombre : '') + 
      a.descripcion + (a.diagnostico||'')
    ).toLowerCase();
    
    const matchesSearch = searchStr.includes(filters.search.toLowerCase());
    
    let matchesDate = true;
    if (filters.date) {
      const atencionDate = new Date(a.fecha).toISOString().split('T')[0];
      matchesDate = atencionDate === filters.date;
    }

    return matchesSearch && matchesDate;
  });

  const handlePrint = (mode) => {
    setPrintMode(mode);
    setTimeout(() => window.print(), 100);
  };

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <h1>Gestión de Atenciones / Tópico</h1>
        <button className="btn btn-primary" onClick={() => openModal()}>
          <Plus size={18} style={{marginRight: '8px'}} /> Registrar Atención
        </button>
      </div>

      <div className="glass-panel">
        <div className="filter-bar">
          <div className="form-group mb-0" style={{flex: 2}}>
            <div style={{position: 'relative'}}>
              <Search size={18} style={{position: 'absolute', top: '14px', left: '14px', color: 'var(--text-muted)'}} />
              <input 
                className="form-control search-input" 
                style={{paddingLeft: '40px'}}
                placeholder="Buscar por paciente, diagnóstico o descripción..." 
                value={filters.search} 
                onChange={e => setFilters({...filters, search: e.target.value})} 
              />
            </div>
          </div>
          <div className="form-group mb-0" style={{flex: 1}}>
            <input type="date" className="form-control" value={filters.date} onChange={e => setFilters({...filters, date: e.target.value})} />
          </div>
          {(filters.search || filters.date) && (
            <button className="btn btn-secondary" onClick={() => setFilters({search: '', date: ''})}>Limpiar</button>
          )}
        </div>

        <div className="table-container">
          <table className="table">
            <thead>
              <tr>
                <th>N°</th>
                <th>Fecha y Hora</th>
                <th>Paciente</th>
                <th>Diagnóstico / Sistema</th>
                <th>Personal de Salud</th>
                <th style={{textAlign: 'right'}}>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {filteredAtenciones.map(a => (
                <tr key={a.id}>
                  <td style={{fontWeight: 'bold', color: 'var(--primary-color)'}}>#{a.id.toString().padStart(4, '0')}</td>
                  <td>
                    <div style={{fontWeight: '500'}}>{new Date(a.fecha).toLocaleDateString()}</div>
                    <div className="text-muted" style={{fontSize: '0.8rem'}}>
                      {a.hora_ingreso || new Date(a.fecha).toLocaleTimeString().substring(0,5)}
                    </div>
                  </td>
                  <td>
                    <div style={{fontWeight: '500'}}>{a.trabajador ? `${a.trabajador.nombre} ${a.trabajador.apellidos}` : 'N/A'}</div>
                  </td>
                  <td>
                    <div style={{fontWeight: '500'}}>{a.diagnostico || 'No registrado'}</div>
                    <div className="text-muted" style={{fontSize: '0.8rem'}}>
                      {a.sistema ? a.sistema.nombre : ''} {a.clasificacion ? `> ${a.clasificacion.nombre}` : ''}
                    </div>
                  </td>
                  <td>{a.personal_salud ? `Dr(a). ${a.personal_salud.apellidos}` : 'N/A'}</td>
                  <td style={{textAlign: 'right', whiteSpace: 'nowrap'}}>
                    <button className="action-btn view" style={{color: '#4caf50', marginRight: '5px'}} onClick={() => setViewAtencion(a)} title="Ver / Imprimir Ficha"><Eye size={18} /></button>
                    <button className="action-btn edit" onClick={() => openModal(a)}><Edit2 size={18} /></button>
                    <button className="action-btn delete" onClick={() => handleDelete(a.id)}><Trash2 size={18} /></button>
                  </td>
                </tr>
              ))}
              {filteredAtenciones.length === 0 && (
                <tr>
                  <td colSpan="6" className="text-center text-muted py-4">No se encontraron atenciones</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {isModalOpen && (
        <div className="modal-overlay" style={{padding: '20px 0'}}>
          <div className="modal-content" style={{maxWidth: '800px', maxHeight: '90vh', overflowY: 'auto'}}>
            <div className="modal-header" style={{position: 'sticky', top: 0, zIndex: 10, background: 'var(--surface-color)'}}>
              <h3>{newAtencion.id ? 'Editar Atención / Tópico' : 'Registrar Nueva Atención'}</h3>
              <button className="close-btn" onClick={closeModal}><X size={24} /></button>
            </div>
            
            <div className="modal-body">
              <form onSubmit={handleAddAtencion}>
                
                <h4 style={{borderBottom: '1px solid var(--border-color)', paddingBottom: '8px', marginBottom: '16px'}}>1. Datos del Paciente e Ingreso</h4>
                <div className="grid grid-cols-2">
                  <div className="form-group">
                    <label className="form-label">Código de Atención</label>
                    <input className="form-control" value={newAtencion.id ? `#${newAtencion.id.toString().padStart(4, '0')}` : '(Autogenerado)'} disabled style={{background: 'rgba(0,0,0,0.05)', fontWeight: 'bold'}} />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Fecha y Hora</label>
                    <div style={{display: 'flex', gap: '10px'}}>
                      <input type="date" className="form-control mb-0" value={newAtencion.fecha ? newAtencion.fecha.substring(0,10) : new Date().toISOString().substring(0,10)} onChange={e => setNewAtencion({...newAtencion, fecha: new Date(e.target.value).toISOString()})} />
                      <input type="time" className="form-control mb-0" value={newAtencion.hora_ingreso} onChange={e => setNewAtencion({...newAtencion, hora_ingreso: e.target.value})} />
                    </div>
                  </div>

                  <div className="form-group">
                    <label className="form-label">Paciente (Trabajador)</label>
                    <select required className="form-control" value={newAtencion.trabajador_id} onChange={handleTrabajadorChange}>
                      <option value="">Seleccione un paciente...</option>
                      {trabajadores.map(t => <option key={t.id} value={t.id}>{t.dni} - {t.nombre} {t.apellidos}</option>)}
                    </select>
                  </div>
                  <div className="form-group">
                    <label className="form-label">DNI</label>
                    <input className="form-control" value={trabajadores.find(t => t.id === parseInt(newAtencion.trabajador_id))?.dni || ''} disabled />
                  </div>

                  <div className="form-group">
                    <label className="form-label">Edad</label>
                    <input className="form-control" value={newAtencion.edad} onChange={e => setNewAtencion({...newAtencion, edad: e.target.value})} placeholder="Ej. 30" />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Personal de Salud</label>
                    <select required className="form-control" value={newAtencion.personal_salud_id} onChange={e => setNewAtencion({...newAtencion, personal_salud_id: e.target.value})}>
                      <option value="">Seleccione...</option>
                      {personalSalud.map(p => <option key={p.id} value={p.id}>{p.especialidad}: {p.nombre} {p.apellidos}</option>)}
                    </select>
                  </div>

                  <div className="form-group" style={{gridColumn: 'span 2'}}>
                    <label className="form-label">Residencia</label>
                    <input className="form-control" value={newAtencion.residencia} onChange={e => setNewAtencion({...newAtencion, residencia: e.target.value})} placeholder="Ej. Lima, Miraflores..." />
                  </div>
                  
                  <div className="form-group">
                    <label className="form-label">Empresa</label>
                    <select className="form-control" value={newAtencion.empresa_id} onChange={e => setNewAtencion({...newAtencion, empresa_id: e.target.value})}>
                      <option value="">Seleccione empresa...</option>
                      {empresas.map(e => <option key={e.id} value={e.id}>{e.nombre}</option>)}
                    </select>
                  </div>
                  <div className="form-group">
                    <label className="form-label">Cargo</label>
                    <input className="form-control" value={newAtencion.cargo} onChange={e => setNewAtencion({...newAtencion, cargo: e.target.value})} />
                  </div>
                </div>

                <h4 style={{borderBottom: '1px solid var(--border-color)', paddingBottom: '8px', margin: '24px 0 16px 0'}}>2. Evaluación Médica</h4>
                
                <div className="form-group mb-4">
                  <label className="form-label">Descripción del Malestar / Anamnesis</label>
                  <textarea required className="form-control" rows="3" value={newAtencion.descripcion} onChange={e => setNewAtencion({...newAtencion, descripcion: e.target.value})}></textarea>
                </div>

                <h5 style={{color: 'var(--primary-color)', marginBottom: '12px'}}>A. Funciones Biológicas</h5>
                <div className="grid grid-cols-3 mb-4 gap-2" style={{background: 'rgba(255,255,255,0.02)', padding: '12px', borderRadius: '8px', border: '1px solid var(--border-color)'}}>
                  {['Apetito', 'Sed', 'Sueño', 'Estado de Ánimo', 'Orina', 'Deposiciones'].map((item, i) => {
                    const keys = ['apetito', 'sed', 'sueno', 'estado_animo', 'orina', 'deposiciones'];
                    return (
                      <div className="form-group mb-0" key={i}>
                        <label className="form-label" style={{fontSize: '0.8rem'}}>{item}</label>
                        <select className="form-control" style={{fontSize: '0.85rem', padding: '6px'}} value={newAtencion.funciones_biologicas[keys[i]]} onChange={e => setNewAtencion({...newAtencion, funciones_biologicas: {...newAtencion.funciones_biologicas, [keys[i]]: e.target.value}})}>
                          <option value="">Seleccione...</option>
                          <option value="Normal">Normal</option>
                          <option value="Aumentado">Aumentado</option>
                          <option value="Disminuido">Disminuido</option>
                        </select>
                      </div>
                    )
                  })}
                </div>

                <h5 style={{color: 'var(--primary-color)', marginBottom: '12px'}}>B. Signos Vitales</h5>
                <div className="grid grid-cols-4 mb-4 gap-2" style={{background: 'rgba(255,255,255,0.02)', padding: '12px', borderRadius: '8px', border: '1px solid var(--border-color)'}}>
                  {['Presión Arterial', 'Frec. Cardiaca', 'Frec. Respiratoria', 'Temperatura', 'SPO2'].map((item, i) => {
                    const keys = ['presion_arterial', 'frec_cardiaca', 'frec_respiratoria', 'temperatura', 'spo2'];
                    return (
                      <div className="form-group mb-0" key={i}>
                        <label className="form-label" style={{fontSize: '0.8rem'}}>{item}</label>
                        <input className="form-control" style={{fontSize: '0.85rem', padding: '6px'}} value={newAtencion.signos_vitales[keys[i]]} onChange={e => setNewAtencion({...newAtencion, signos_vitales: {...newAtencion.signos_vitales, [keys[i]]: e.target.value}})} />
                      </div>
                    )
                  })}
                  <div className="form-group mb-0">
                    <label className="form-label" style={{fontSize: '0.8rem'}}>Peso</label>
                    <input className="form-control" style={{fontSize: '0.85rem', padding: '6px'}} placeholder="Ej. 70 kg" value={newAtencion.signos_vitales.peso} onChange={e => setNewAtencion({...newAtencion, signos_vitales: {...newAtencion.signos_vitales, peso: e.target.value}})} />
                  </div>
                  <div className="form-group mb-0">
                    <label className="form-label" style={{fontSize: '0.8rem'}}>Talla</label>
                    <input className="form-control" style={{fontSize: '0.85rem', padding: '6px'}} placeholder="Ej. 1.70 m" value={newAtencion.signos_vitales.talla} onChange={e => setNewAtencion({...newAtencion, signos_vitales: {...newAtencion.signos_vitales, talla: e.target.value}})} />
                  </div>
                </div>

                <div className="grid grid-cols-2 mb-4">
                  <div className="form-group">
                    <label className="form-label">Examen Físico</label>
                    <textarea className="form-control" rows="3" value={newAtencion.examen_fisico} onChange={e => setNewAtencion({...newAtencion, examen_fisico: e.target.value})}></textarea>
                  </div>
                  <div className="form-group">
                    <label className="form-label">Exámenes Auxiliares</label>
                    <textarea className="form-control" rows="3" value={newAtencion.examenes_auxiliares} onChange={e => setNewAtencion({...newAtencion, examenes_auxiliares: e.target.value})}></textarea>
                  </div>
                </div>

                <h4 style={{borderBottom: '1px solid var(--border-color)', paddingBottom: '8px', margin: '24px 0 16px 0'}}>3. Diagnóstico</h4>
                <div className="grid grid-cols-2">

                  <div className="form-group">
                    <label className="form-label">Sistema Clínico</label>
                    <select required className="form-control" value={newAtencion.sistema_id} onChange={e => setNewAtencion({...newAtencion, sistema_id: e.target.value})}>
                      <option value="">Seleccione un sistema...</option>
                      {sistemas.map(s => <option key={s.id} value={s.id}>{s.nombre}</option>)}
                    </select>
                  </div>
                  <div className="form-group">
                    <label className="form-label">Contingencia</label>
                    <select required className="form-control" value={newAtencion.clasificacion_id} onChange={e => setNewAtencion({...newAtencion, clasificacion_id: e.target.value})}>
                      <option value="">Seleccione una contingencia...</option>
                      {clasificacionesDisponibles.map(c => <option key={c.id} value={c.id}>{c.nombre}</option>)}
                    </select>
                  </div>

                  </div>

                  <div className="form-group" style={{gridColumn: 'span 2'}}>
                    <label className="form-label">Diagnóstico Principal</label>
                    <Select 
                      options={diagnosticosCatalog.map(d => ({ value: `${d.codigo} - ${d.descripcion}`, label: `${d.codigo} - ${d.descripcion}` }))}
                      value={newAtencion.diagnostico_1 ? {label: newAtencion.diagnostico_1, value: newAtencion.diagnostico_1} : null}
                      onChange={opt => setNewAtencion({...newAtencion, diagnostico_1: opt ? opt.value : ''})}
                      isClearable
                      placeholder="Buscar diagnóstico..."
                    />
                  </div>
                  
                  <div className="form-group" style={{gridColumn: 'span 2'}}>
                    <label className="form-label">Diagnóstico Secundario 1</label>
                    <Select 
                      options={diagnosticosCatalog.map(d => ({ value: `${d.codigo} - ${d.descripcion}`, label: `${d.codigo} - ${d.descripcion}` }))}
                      value={newAtencion.diagnostico_2 ? {label: newAtencion.diagnostico_2, value: newAtencion.diagnostico_2} : null}
                      onChange={opt => setNewAtencion({...newAtencion, diagnostico_2: opt ? opt.value : ''})}
                      isClearable
                      placeholder="Buscar diagnóstico secundario..."
                    />
                  </div>

                  <div className="form-group" style={{gridColumn: 'span 2'}}>
                    <label className="form-label">Diagnóstico Secundario 2</label>
                    <Select 
                      options={diagnosticosCatalog.map(d => ({ value: `${d.codigo} - ${d.descripcion}`, label: `${d.codigo} - ${d.descripcion}` }))}
                      value={newAtencion.diagnostico_3 ? {label: newAtencion.diagnostico_3, value: newAtencion.diagnostico_3} : null}
                      onChange={opt => setNewAtencion({...newAtencion, diagnostico_3: opt ? opt.value : ''})}
                      isClearable
                      placeholder="Buscar diagnóstico secundario..."
                    />
                  </div>

                  <div className="form-group" style={{gridColumn: 'span 2', marginTop: '10px'}}>
                    <label className="form-label">Detalles / Tratamiento</label>
                    <textarea className="form-control" rows="3" value={newAtencion.tratamiento} onChange={e => setNewAtencion({...newAtencion, tratamiento: e.target.value})}></textarea>
                  </div>
                </div>

                <h4 style={{borderBottom: '1px solid var(--border-color)', paddingBottom: '8px', margin: '24px 0 16px 0'}}>4. Receta y Destino</h4>

                {/* Receta Médica */}
                <div className="form-group p-4 mb-4" style={{background: 'var(--surface-color)', borderRadius: '12px', border: '1px solid var(--border-color)', boxShadow: '0 2px 8px rgba(0,0,0,0.05)'}}>
                  <div className="flex justify-between items-center mb-4 pb-3" style={{borderBottom: '1px solid var(--border-color)'}}>
                    <h5 className="mb-0" style={{color: 'var(--primary-color)', margin: 0}}>💊 Receta Médica / Medicamentos</h5>
                    <button type="button" className="btn btn-primary" style={{padding: '6px 12px', fontSize: '0.85rem', display: 'flex', alignItems: 'center', gap: '6px'}} onClick={addMedicamento}>
                      <Plus size={16}/> Añadir
                    </button>
                  </div>
                  
                  {newAtencion.medicamentos.length === 0 ? (
                    <div className="text-center text-muted p-4" style={{background: 'rgba(0,0,0,0.02)', borderRadius: '8px'}}>No se han recetado medicamentos.</div>
                  ) : (
                    <div style={{display: 'flex', flexDirection: 'column', gap: '10px'}}>
                      {newAtencion.medicamentos.map((med, index) => (
                        <div key={index} className="flex gap-3 items-center" style={{background: 'rgba(255,255,255,0.02)', padding: '10px', borderRadius: '8px', border: '1px solid var(--border-color)'}}>
                          <div style={{flex: 1}}>
                            <select required className="form-control mb-0" value={med.medicamento_id} onChange={(e) => updateMedicamento(index, 'medicamento_id', e.target.value)}>
                              <option value="">Seleccione medicamento...</option>
                              {medicamentos.map(m => <option key={m.id} value={m.id}>{m.nombre} - {m.presentacion} (Stock: {m.stock_actual})</option>)}
                            </select>
                          </div>
                          <div style={{width: '130px'}}>
                            <div className="flex items-center">
                              <span style={{padding: '0 10px', background: 'rgba(0,0,0,0.05)', height: '38px', display: 'flex', alignItems: 'center', borderTopLeftRadius: '6px', borderBottomLeftRadius: '6px', border: '1px solid var(--border-color)', borderRight: 'none', fontSize: '0.85rem'}}>Cant.</span>
                              <input type="number" required min="1" className="form-control mb-0" style={{borderTopLeftRadius: 0, borderBottomLeftRadius: 0}} value={med.cantidad} onChange={(e) => updateMedicamento(index, 'cantidad', e.target.value)} />
                            </div>
                          </div>
                          {!newAtencion.id && (
                            <button type="button" className="action-btn delete" style={{background: 'rgba(239, 68, 68, 0.1)', padding: '8px', borderRadius: '6px'}} onClick={() => removeMedicamento(index)}>
                              <Trash2 size={18} color="var(--danger-color)"/>
                            </button>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                  {!newAtencion.id && newAtencion.medicamentos.length > 0 && (
                    <div className="text-muted mt-3" style={{fontSize: '0.8rem', textAlign: 'right'}}>* El stock se descontará automáticamente al guardar.</div>
                  )}
                </div>

                <div className="grid grid-cols-2">
                  <div className="form-group">
                    <label className="form-label">Destino</label>
                    <select required className="form-control" value={newAtencion.destino} onChange={e => setNewAtencion({...newAtencion, destino: e.target.value})}>
                      <option value="">Seleccione...</option>
                      <option value="Alta a su puesto">Alta a su puesto</option>
                      <option value="Retorno al trabajo">Retorno al trabajo</option>
                      <option value="Observación en Tópico">Observación en Tópico</option>
                      <option value="Descanso en habitación">Descanso en habitación</option>
                      <option value="Descanso Médico">Descanso Médico</option>
                      <option value="Evacuación médica">Evacuación médica</option>
                      <option value="Referencia a Centro de Salud">Referencia a Centro de Salud</option>
                    </select>
                  </div>
                  <div className="form-group">
                    <label className="form-label">Observaciones Adicionales</label>
                    <input className="form-control" value={newAtencion.observaciones} onChange={e => setNewAtencion({...newAtencion, observaciones: e.target.value})} />
                  </div>
                </div>

                <div style={{display: 'flex', justifyContent: 'flex-end', gap: '12px', marginTop: '32px', borderTop: '1px solid var(--border-color)', paddingTop: '16px'}}>
                  <button type="button" className="btn btn-secondary" onClick={closeModal}>Cancelar</button>
                  <button type="submit" className="btn btn-primary">Guardar Ficha de Atención</button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}

      {/* View / Print Modal */}
      {viewAtencion && (
        <div className="modal-overlay" style={{padding: '20px 0'}}>
          <div className="modal-content" style={{maxWidth: '800px', maxHeight: '90vh', overflowY: 'auto'}}>
            <div className="modal-header hide-on-print" style={{position: 'sticky', top: 0, zIndex: 10, background: 'var(--surface-color)', borderBottom: '1px solid var(--border-color)'}}>
              <h3>Ficha de Atención #{viewAtencion.id.toString().padStart(4, '0')}</h3>
              <div style={{display: 'flex', gap: '10px'}}>
                <button className="btn btn-secondary" style={{background: 'rgba(255,255,255,0.1)'}} onClick={() => handlePrint('receta')}>🖨️ Imprimir Receta</button>
                <button className="btn btn-primary" onClick={() => handlePrint('ficha')}>🖨️ Imprimir Ficha</button>
                <button className="close-btn" onClick={() => setViewAtencion(null)}><X size={24} /></button>
              </div>
            </div>
            
            <div className={`modal-body ${printMode === 'ficha' ? 'ficha-print-mode' : 'receta-print-mode'}`} style={{padding: 0}}>
              {/* Contenedor FICHA */}
              <div className="print-area ficha-content" style={{padding: '30px', background: 'white', color: 'black'}}>
              <div style={{textAlign: 'center', marginBottom: '30px', borderBottom: '2px solid #333', paddingBottom: '15px'}}>
                <img src="/logo.png" alt="MEDGLOBAL" style={{maxHeight: '60px', marginBottom: '10px'}} />
                <h2 style={{fontSize: '18px', margin: 0, fontWeight: 'normal', color: '#555'}}>FICHA DE ATENCIÓN / TÓPICO OCUPACIONAL</h2>
              </div>

              <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '15px', marginBottom: '25px', fontSize: '14px'}}>
                <div><strong>N° de Ficha:</strong> #{viewAtencion.id.toString().padStart(4, '0')}</div>
                <div><strong>Fecha:</strong> {new Date(viewAtencion.fecha).toLocaleDateString()}</div>
                <div><strong>Hora de Atención:</strong> {viewAtencion.hora_ingreso || '--'}</div>
              </div>

              <h4 style={{borderBottom: '1px solid #ccc', paddingBottom: '5px', marginTop: '20px', color: '#333'}}>I. DATOS DEL PACIENTE</h4>
              <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', fontSize: '14px'}}>
                <div><strong>Paciente:</strong> {viewAtencion.trabajador ? `${viewAtencion.trabajador.nombre} ${viewAtencion.trabajador.apellidos}` : '--'}</div>
                <div><strong>DNI:</strong> {viewAtencion.trabajador?.dni || '--'}</div>
                <div><strong>Edad:</strong> {viewAtencion.edad || '--'}</div>
                <div><strong>Residencia:</strong> {viewAtencion.residencia || '--'}</div>
                <div><strong>Empresa:</strong> {viewAtencion.empresa ? viewAtencion.empresa.nombre : '--'}</div>
                <div><strong>Área / Cargo:</strong> {viewAtencion.cargo || '--'}</div>
              </div>

              <h4 style={{borderBottom: '1px solid #ccc', paddingBottom: '5px', marginTop: '25px', color: '#333'}}>II. EVALUACIÓN MÉDICA</h4>
              <div style={{fontSize: '14px', marginBottom: '10px'}}>
                <strong>Anamnesis / Motivo de Consulta:</strong>
                <p style={{marginTop: '5px', whiteSpace: 'pre-wrap', background: '#f9f9f9', padding: '10px', borderRadius: '4px', border: '1px solid #eee'}}>{viewAtencion.descripcion}</p>
              </div>

              <div style={{fontSize: '14px', marginBottom: '10px'}}>
                <strong>Funciones Biológicas:</strong>
                {(() => {
                  let f = {};
                  try { f = JSON.parse(viewAtencion.funciones_biologicas || '{}'); } catch(e){}
                  return (
                    <div style={{display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '5px', marginTop: '5px', padding: '10px', background: '#f9f9f9', border: '1px solid #eee'}}>
                      <div>Apetito: {f.apetito || '--'}</div>
                      <div>Sed: {f.sed || '--'}</div>
                      <div>Sueño: {f.sueno || '--'}</div>
                      <div>E. Ánimo: {f.estado_animo || '--'}</div>
                      <div>Orina: {f.orina || '--'}</div>
                      <div>Deposiciones: {f.deposiciones || '--'}</div>
                    </div>
                  );
                })()}
              </div>

              <div style={{fontSize: '14px', marginBottom: '10px'}}>
                <strong>Signos Vitales:</strong>
                {(() => {
                  let s = {};
                  try { s = JSON.parse(viewAtencion.signos_vitales || '{}'); } catch(e){}
                  return (
                    <div style={{display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '5px', marginTop: '5px', padding: '10px', background: '#f9f9f9', border: '1px solid #eee'}}>
                      <div>P. Arterial: {s.presion_arterial || '--'}</div>
                      <div>F. Cardiaca: {s.frec_cardiaca || '--'}</div>
                      <div>F. Respiratoria: {s.frec_respiratoria || '--'}</div>
                      <div>Temperatura: {s.temperatura || '--'}</div>
                      <div>SPO2: {s.spo2 || '--'}</div>
                      <div>Peso: {s.peso || '--'}</div>
                      <div>Talla: {s.talla || '--'}</div>
                    </div>
                  );
                })()}
              </div>

              <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '15px', fontSize: '14px', marginBottom: '10px'}}>
                <div>
                  <strong>Examen Físico:</strong>
                  <p style={{marginTop: '5px', whiteSpace: 'pre-wrap', minHeight: '40px', background: '#f9f9f9', padding: '10px', border: '1px solid #eee'}}>{viewAtencion.examen_fisico || '--'}</p>
                </div>
                <div>
                  <strong>Exámenes Auxiliares:</strong>
                  <p style={{marginTop: '5px', whiteSpace: 'pre-wrap', minHeight: '40px', background: '#f9f9f9', padding: '10px', border: '1px solid #eee'}}>{viewAtencion.examenes_auxiliares || '--'}</p>
                </div>
              </div>

              <h4 style={{borderBottom: '1px solid #ccc', paddingBottom: '5px', marginTop: '25px', color: '#333'}}>III. DIAGNÓSTICO</h4>
              
              <div style={{display: 'grid', gridTemplateColumns: '1fr', gap: '10px', fontSize: '14px'}}>
                <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px'}}>
                  <div><strong>Sistema:</strong> {viewAtencion.sistema?.nombre || '--'}</div>
                  <div><strong>Contingencia:</strong> {viewAtencion.clasificacion?.nombre || '--'}</div>
                </div>
                
                <div style={{marginTop: '10px', padding: '10px', background: '#f0f4f8', border: '1px solid #dce4ec', borderRadius: '4px'}}>
                  {viewAtencion.codigo_diagnostico && <div style={{marginBottom: '5px'}}><strong>Diag. Anterior:</strong> {viewAtencion.codigo_diagnostico} - {viewAtencion.diagnostico}</div>}
                  {viewAtencion.diagnostico_1 && <div style={{marginBottom: '5px'}}><strong>Diag. Principal:</strong> {viewAtencion.diagnostico_1}</div>}
                  {viewAtencion.diagnostico_2 && <div style={{marginBottom: '5px'}}><strong>Diag. Secundario 1:</strong> {viewAtencion.diagnostico_2}</div>}
                  {viewAtencion.diagnostico_3 && <div style={{marginBottom: '5px'}}><strong>Diag. Secundario 2:</strong> {viewAtencion.diagnostico_3}</div>}
                </div>

                <div>
                  <strong>Detalles / Tratamiento:</strong>
                  <p style={{marginTop: '5px', whiteSpace: 'pre-wrap', background: '#f9f9f9', padding: '10px', border: '1px solid #eee'}}>{viewAtencion.tratamiento || '--'}</p>
                </div>
              </div>

              <h4 style={{borderBottom: '1px solid #ccc', paddingBottom: '5px', marginTop: '25px', color: '#333'}}>IV. RECETA Y DESTINO</h4>
              
              <div style={{fontSize: '14px', marginBottom: '15px'}}>
                <strong>Medicamentos Recetados / Entregados:</strong>
                {viewAtencion.medicamentos && viewAtencion.medicamentos.length > 0 ? (
                  <ul style={{marginTop: '5px', paddingLeft: '20px'}}>
                    {viewAtencion.medicamentos.map((m, i) => (
                      <li key={i}>{m.medicamento?.nombre} {m.medicamento?.presentacion} - <strong>{m.cantidad} unid.</strong></li>
                    ))}
                  </ul>
                ) : (
                  <p style={{marginTop: '5px'}}>No se recetaron medicamentos.</p>
                )}
              </div>

              <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', fontSize: '14px'}}>
                <div><strong>Destino:</strong> {viewAtencion.destino || '--'}</div>
                <div><strong>Observaciones:</strong> {viewAtencion.observaciones || '--'}</div>
              </div>

              <div style={{marginTop: '60px', display: 'flex', justifyContent: 'space-around', textAlign: 'center'}}>
                <div>
                  <div style={{borderBottom: '1px solid black', width: '200px', marginBottom: '5px'}}></div>
                  <div style={{fontSize: '12px'}}>Firma del Paciente</div>
                </div>
                <div>
                  <div style={{borderBottom: '1px solid black', width: '200px', marginBottom: '5px'}}></div>
                  <div style={{fontSize: '12px'}}>
                    {viewAtencion.personal_salud ? `Dr(a). ${viewAtencion.personal_salud.apellidos}` : 'Médico Responsable'}<br/>
                    {viewAtencion.personal_salud?.cmp ? `CMP: ${viewAtencion.personal_salud.cmp}` : ''}
                  </div>
                </div>
              </div>

            </div>
              
              {/* Contenedor RECETA */}
              <div className="print-area receta-content print-only" style={{padding: '30px', background: 'white', color: 'black'}}>
                <div style={{textAlign: 'center', marginBottom: '30px', borderBottom: '2px solid #333', paddingBottom: '15px'}}>
                  <img src="/logo.png" alt="MEDGLOBAL" style={{maxHeight: '60px', marginBottom: '10px'}} />
                  <h2 style={{fontSize: '18px', margin: 0, fontWeight: 'normal', color: '#555'}}>RECETA MÉDICA OCUPACIONAL</h2>
                </div>

                <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '15px', marginBottom: '25px', fontSize: '14px'}}>
                  <div><strong>N° de Atención:</strong> #{viewAtencion.id.toString().padStart(4, '0')}</div>
                  <div><strong>Fecha y Hora:</strong> {new Date(viewAtencion.fecha).toLocaleDateString()} {viewAtencion.hora_ingreso || ''}</div>
                </div>

                <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', fontSize: '14px', marginBottom: '30px'}}>
                  <div style={{gridColumn: 'span 2'}}><strong>Apellidos y Nombres:</strong> {viewAtencion.trabajador ? `${viewAtencion.trabajador.nombre} ${viewAtencion.trabajador.apellidos}` : '--'}</div>
                  <div><strong>Empresa:</strong> {viewAtencion.empresa ? viewAtencion.empresa.nombre : '--'}</div>
                  <div><strong>Cargo:</strong> {viewAtencion.cargo || '--'}</div>
                </div>

                <h4 style={{borderBottom: '1px solid #ccc', paddingBottom: '5px', color: '#333'}}>MEDICAMENTOS INDICADOS</h4>
                <div style={{fontSize: '14px', marginBottom: '40px', minHeight: '200px'}}>
                  {viewAtencion.medicamentos && viewAtencion.medicamentos.length > 0 ? (
                    <ul style={{marginTop: '15px', paddingLeft: '20px', lineHeight: '2'}}>
                      {viewAtencion.medicamentos.map((m, i) => (
                        <li key={i}>
                          <strong>{m.medicamento?.nombre} {m.medicamento?.presentacion}</strong> 
                          <span style={{marginLeft: '20px'}}>Cantidad: {m.cantidad} unid.</span>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p style={{marginTop: '15px'}}>No se recetaron medicamentos.</p>
                  )}
                </div>

                <div style={{marginTop: '80px', display: 'flex', justifyContent: 'space-around', textAlign: 'center'}}>
                  <div>
                    <div style={{borderBottom: '1px solid black', width: '200px', marginBottom: '5px'}}></div>
                    <div style={{fontSize: '12px'}}>Firma del Usuario</div>
                  </div>
                  <div>
                    <div style={{borderBottom: '1px solid black', width: '200px', marginBottom: '5px'}}></div>
                    <div style={{fontSize: '12px'}}>
                      {viewAtencion.personal_salud ? `Dr(a). ${viewAtencion.personal_salud.apellidos}` : 'Médico Responsable'}<br/>
                      {viewAtencion.personal_salud?.cmp ? `CMP: ${viewAtencion.personal_salud.cmp}` : ''}
                    </div>
                  </div>
                </div>
              </div>

            </div>
          </div>
        </div>
      )}
      
      <style>{`
        @media screen {
          .print-only { display: none !important; }
        }
        @media print {
          body * {
            visibility: hidden;
          }
          .print-area, .print-area * {
            visibility: visible;
          }
          .print-area {
            position: absolute;
            left: 0;
            top: 0;
            width: 100%;
          }
          .hide-on-print {
            display: none !important;
          }
          .modal-content {
            box-shadow: none !important;
            border: none !important;
          }
          .ficha-print-mode .receta-content { display: none !important; }
          .receta-print-mode .ficha-content { display: none !important; }
          .receta-print-mode .receta-content { display: block !important; }
        }
      `}</style>
    </div>
  );
};

export default Atenciones;
