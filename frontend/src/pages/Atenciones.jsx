import { useState, useEffect } from 'react';
import { Search, Plus, Trash2, Edit2, X, Link, Clock, Eye } from 'lucide-react';

const Atenciones = () => {
  const [atenciones, setAtenciones] = useState([]);
  const [trabajadores, setTrabajadores] = useState([]);
  const [sistemas, setSistemas] = useState([]);
  const [citas, setCitas] = useState([]);
  const [personalSalud, setPersonalSalud] = useState([]);
  const [medicamentos, setMedicamentos] = useState([]);
  
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [viewAtencion, setViewAtencion] = useState(null);
  const [filters, setFilters] = useState({ search: '', date: '' });
  
  const [newAtencion, setNewAtencion] = useState({
    id: null,
    trabajador_id: '',
    sistema_id: '',
    clasificacion_id: '',
    cita_id: '',
    personal_salud_id: '',
    hora_ingreso: '',
    hora_salida: '',
    tiempo_topico: '',
    descripcion: '',
    diagnostico: '',
    tratamiento: '',
    destino: '',
    sede_atencion: '',
    jefe_inmediato: '',
    observaciones: '',
    medicamentos: [] // Array of {medicamento_id, cantidad}
  });

  const fetchData = () => {
    fetch((import.meta.env.VITE_API_URL ? (import.meta.env.VITE_API_URL.startsWith('http') ? import.meta.env.VITE_API_URL : 'https://' + import.meta.env.VITE_API_URL) : 'http://localhost:8000') + '/atenciones/').then(res => res.json()).then(setAtenciones);
    fetch((import.meta.env.VITE_API_URL ? (import.meta.env.VITE_API_URL.startsWith('http') ? import.meta.env.VITE_API_URL : 'https://' + import.meta.env.VITE_API_URL) : 'http://localhost:8000') + '/trabajadores/').then(res => res.json()).then(setTrabajadores);
    fetch((import.meta.env.VITE_API_URL ? (import.meta.env.VITE_API_URL.startsWith('http') ? import.meta.env.VITE_API_URL : 'https://' + import.meta.env.VITE_API_URL) : 'http://localhost:8000') + '/sistemas/').then(res => res.json()).then(setSistemas);
    fetch((import.meta.env.VITE_API_URL ? (import.meta.env.VITE_API_URL.startsWith('http') ? import.meta.env.VITE_API_URL : 'https://' + import.meta.env.VITE_API_URL) : 'http://localhost:8000') + '/citas/').then(res => res.json()).then(setCitas);
    fetch((import.meta.env.VITE_API_URL ? (import.meta.env.VITE_API_URL.startsWith('http') ? import.meta.env.VITE_API_URL : 'https://' + import.meta.env.VITE_API_URL) : 'http://localhost:8000') + '/personal_salud/').then(res => res.json()).then(setPersonalSalud);
    fetch((import.meta.env.VITE_API_URL ? (import.meta.env.VITE_API_URL.startsWith('http') ? import.meta.env.VITE_API_URL : 'https://' + import.meta.env.VITE_API_URL) : 'http://localhost:8000') + '/medicamentos/').then(res => res.json()).then(setMedicamentos);
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleAddAtencion = (e) => {
    e.preventDefault();
    const isEditing = newAtencion.id !== null;
    const url = isEditing ? `http://localhost:8000/atenciones/${newAtencion.id}` : (import.meta.env.VITE_API_URL ? (import.meta.env.VITE_API_URL.startsWith('http') ? import.meta.env.VITE_API_URL : 'https://' + import.meta.env.VITE_API_URL) : 'http://localhost:8000') + '/atenciones/';
    const method = isEditing ? 'PUT' : 'POST';

    const dataToSend = { ...newAtencion };
    delete dataToSend.id;
    
    // Parse ints
    dataToSend.trabajador_id = parseInt(dataToSend.trabajador_id);
    dataToSend.sistema_id = parseInt(dataToSend.sistema_id);
    dataToSend.clasificacion_id = parseInt(dataToSend.clasificacion_id);
    if (dataToSend.cita_id) dataToSend.cita_id = parseInt(dataToSend.cita_id); else delete dataToSend.cita_id;
    if (dataToSend.personal_salud_id) dataToSend.personal_salud_id = parseInt(dataToSend.personal_salud_id); else delete dataToSend.personal_salud_id;

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
      fetch(`http://localhost:8000/atenciones/${id}`, { method: 'DELETE' })
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
        cita_id: atencion.cita_id || '',
        personal_salud_id: atencion.personal_salud_id || '',
        hora_ingreso: atencion.hora_ingreso || '',
        hora_salida: atencion.hora_salida || '',
        tiempo_topico: atencion.tiempo_topico || '',
        descripcion: atencion.descripcion || '',
        diagnostico: atencion.diagnostico || '',
        tratamiento: atencion.tratamiento || '',
        destino: atencion.destino || '',
        sede_atencion: atencion.sede_atencion || '',
        jefe_inmediato: atencion.jefe_inmediato || '',
        observaciones: atencion.observaciones || '',
        medicamentos: atencion.medicamentos ? atencion.medicamentos.map(m => ({medicamento_id: m.medicamento_id, cantidad: m.cantidad})) : []
      });
    } else {
      setNewAtencion({
        id: null, trabajador_id: '', sistema_id: '', clasificacion_id: '', cita_id: '', personal_salud_id: '',
        hora_ingreso: '', hora_salida: '', tiempo_topico: '', descripcion: '', diagnostico: '',
        tratamiento: '', destino: '', sede_atencion: '', jefe_inmediato: '', observaciones: '', medicamentos: []
      });
    }
    setIsModalOpen(true);
  };

  const closeModal = () => setIsModalOpen(false);

  // Auto-fill patient when a cita is selected
  const handleCitaSelect = (e) => {
    const selectedCitaId = e.target.value;
    const cita = citas.find(c => c.id === parseInt(selectedCitaId));
    
    if (cita) {
      const trabajador = trabajadores.find(t => t.id === cita.paciente_id);
      setNewAtencion({
        ...newAtencion,
        cita_id: selectedCitaId,
        trabajador_id: cita.paciente_id,
        personal_salud_id: cita.personal_salud_id || '',
        jefe_inmediato: trabajador ? trabajador.jefe_inmediato : '',
        descripcion: cita.motivo ? `Motivo de cita: ${cita.motivo}\n\nEvolución: ` : ''
      });
    } else {
      setNewAtencion({ ...newAtencion, cita_id: '' });
    }
  };

  // Auto-fill Jefe Inmediato when worker changes
  const handleTrabajadorChange = (e) => {
    const t_id = e.target.value;
    const trabajador = trabajadores.find(t => t.id === parseInt(t_id));
    setNewAtencion({
      ...newAtencion,
      trabajador_id: t_id,
      jefe_inmediato: trabajador ? (trabajador.jefe_inmediato || '') : ''
    });
  };

  // Calculate time automatically
  const calculateTime = (ingreso, salida) => {
    if (!ingreso || !salida) return '';
    const [h1, m1] = ingreso.split(':').map(Number);
    const [h2, m2] = salida.split(':').map(Number);
    const date1 = new Date(2000, 0, 1, h1, m1);
    let date2 = new Date(2000, 0, 1, h2, m2);
    if (date2 < date1) date2.setDate(date2.getDate() + 1); // Crosses midnight
    
    const diffMs = date2 - date1;
    const diffMins = Math.round(diffMs / 60000);
    
    if (diffMins < 60) return `${diffMins} min`;
    const h = Math.floor(diffMins / 60);
    const m = diffMins % 60;
    return `${h}h ${m}m`;
  };

  const handleHoraIngresoChange = (e) => {
    const v = e.target.value;
    const t = calculateTime(v, newAtencion.hora_salida);
    setNewAtencion({...newAtencion, hora_ingreso: v, tiempo_topico: t || newAtencion.tiempo_topico});
  };

  const handleHoraSalidaChange = (e) => {
    const v = e.target.value;
    const t = calculateTime(newAtencion.hora_ingreso, v);
    setNewAtencion({...newAtencion, hora_salida: v, tiempo_topico: t || newAtencion.tiempo_topico});
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

  const selectedSistema = sistemas.find(s => s.id === parseInt(newAtencion.sistema_id));
  const clasificacionesDisponibles = selectedSistema ? selectedSistema.clasificaciones : [];
  
  const citasPendientes = citas.filter(c => c.estado === 'PENDIENTE' || c.estado === 'CONFIRMADA' || c.id === newAtencion.cita_id);

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
                      {a.hora_ingreso || new Date(a.fecha).toLocaleTimeString().substring(0,5)} {a.hora_salida ? `- ${a.hora_salida}` : ''}
                    </div>
                  </td>
                  <td>
                    <div style={{fontWeight: '500'}}>{a.trabajador ? `${a.trabajador.nombre} ${a.trabajador.apellidos}` : 'N/A'}</div>
                    {a.cita_id && <span style={{fontSize: '0.75rem', color: 'var(--primary-color)', display: 'flex', alignItems: 'center', gap: '4px', marginTop: '4px'}}><Link size={12}/> Cita Vinculada</span>}
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
                
                {/* Opcional: Cita */}
                {!newAtencion.id && (
                  <div className="form-group p-3 mb-4" style={{background: 'rgba(59, 130, 246, 0.1)', borderRadius: '8px', border: '1px dashed rgba(59, 130, 246, 0.5)'}}>
                    <label className="form-label" style={{color: 'var(--primary-color)'}}>
                      <Link size={16} style={{display: 'inline', marginRight: '6px', verticalAlign: 'text-bottom'}}/>
                      Vincular a Cita Programada (Opcional)
                    </label>
                    <select className="form-control" value={newAtencion.cita_id || ''} onChange={handleCitaSelect}>
                      <option value="">Seleccione una cita programada...</option>
                      {citasPendientes.map(c => {
                        const citaDate = new Date(c.fecha_hora);
                        return (
                          <option key={c.id} value={c.id}>
                            {citaDate.toLocaleDateString()} {citaDate.toLocaleTimeString().substring(0,5)} - Paciente: {c.paciente?.nombre} {c.paciente?.apellidos}
                          </option>
                        );
                      })}
                    </select>
                  </div>
                )}

                <h4 style={{borderBottom: '1px solid var(--border-color)', paddingBottom: '8px', marginBottom: '16px'}}>1. Datos del Paciente e Ingreso</h4>
                <div className="grid grid-cols-2">
                  <div className="form-group">
                    <label className="form-label">Paciente (Trabajador)</label>
                    <select required className="form-control" value={newAtencion.trabajador_id} onChange={handleTrabajadorChange}>
                      <option value="">Seleccione un paciente...</option>
                      {trabajadores.map(t => <option key={t.id} value={t.id}>{t.dni} - {t.nombre} {t.apellidos}</option>)}
                    </select>
                  </div>
                  <div className="form-group">
                    <label className="form-label">Jefe Inmediato</label>
                    <input className="form-control" value={newAtencion.jefe_inmediato} onChange={e => setNewAtencion({...newAtencion, jefe_inmediato: e.target.value})} placeholder="Se autocompleta..." />
                  </div>
                  
                  <div className="form-group">
                    <label className="form-label">Sede de Atención</label>
                    <select required className="form-control" value={newAtencion.sede_atencion} onChange={e => setNewAtencion({...newAtencion, sede_atencion: e.target.value})}>
                      <option value="">Seleccione sede...</option>
                      <option value="Sede Principal">Sede Principal</option>
                      <option value="Sede Norte">Sede Norte</option>
                      <option value="Sede Sur">Sede Sur</option>
                    </select>
                  </div>
                  <div className="form-group">
                    <label className="form-label">Personal de Salud</label>
                    <select required className="form-control" value={newAtencion.personal_salud_id} onChange={e => setNewAtencion({...newAtencion, personal_salud_id: e.target.value})}>
                      <option value="">Seleccione...</option>
                      {personalSalud.map(p => <option key={p.id} value={p.id}>{p.especialidad}: {p.nombre} {p.apellidos}</option>)}
                    </select>
                  </div>

                  <div className="form-group">
                    <label className="form-label">Hora de Ingreso</label>
                    <input type="time" className="form-control" value={newAtencion.hora_ingreso} onChange={handleHoraIngresoChange} />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Hora de Salida</label>
                    <input type="time" className="form-control" value={newAtencion.hora_salida} onChange={handleHoraSalidaChange} />
                  </div>
                  <div className="form-group">
                    <label className="form-label"><Clock size={14} style={{display:'inline', marginRight:4}}/> Tiempo en Tópico</label>
                    <input className="form-control" value={newAtencion.tiempo_topico} onChange={e => setNewAtencion({...newAtencion, tiempo_topico: e.target.value})} placeholder="Ej: 30 min" />
                  </div>
                </div>

                <h4 style={{borderBottom: '1px solid var(--border-color)', paddingBottom: '8px', margin: '24px 0 16px 0'}}>2. Evaluación Médica</h4>
                <div className="grid grid-cols-2">
                  <div className="form-group" style={{gridColumn: 'span 2'}}>
                    <label className="form-label">Descripción del Malestar / Anamnesis</label>
                    <textarea required className="form-control" rows="3" value={newAtencion.descripcion} onChange={e => setNewAtencion({...newAtencion, descripcion: e.target.value})}></textarea>
                  </div>

                  <div className="form-group">
                    <label className="form-label">Sistema Clínico</label>
                    <select required className="form-control" value={newAtencion.sistema_id} onChange={e => setNewAtencion({...newAtencion, sistema_id: e.target.value, clasificacion_id: ''})}>
                      <option value="">Seleccione un sistema...</option>
                      {sistemas.map(s => <option key={s.id} value={s.id}>{s.nombre}</option>)}
                    </select>
                  </div>
                  <div className="form-group">
                    <label className="form-label">Clasificación</label>
                    <select required className="form-control" value={newAtencion.clasificacion_id} onChange={e => setNewAtencion({...newAtencion, clasificacion_id: e.target.value})}>
                      <option value="">Seleccione una clasificación...</option>
                      {clasificacionesDisponibles.map(c => <option key={c.id} value={c.id}>{c.nombre}</option>)}
                    </select>
                  </div>

                  <div className="form-group" style={{gridColumn: 'span 2'}}>
                    <label className="form-label">Diagnóstico</label>
                    <input className="form-control" value={newAtencion.diagnostico} onChange={e => setNewAtencion({...newAtencion, diagnostico: e.target.value})} />
                  </div>
                </div>

                <h4 style={{borderBottom: '1px solid var(--border-color)', paddingBottom: '8px', margin: '24px 0 16px 0'}}>3. Tratamiento y Destino</h4>
                <div className="form-group">
                  <label className="form-label">Tratamiento en Tópico</label>
                  <textarea className="form-control" rows="2" value={newAtencion.tratamiento} onChange={e => setNewAtencion({...newAtencion, tratamiento: e.target.value})}></textarea>
                </div>

                {/* Receta Médica */}
                <div className="form-group p-3 mb-4" style={{background: 'rgba(255, 255, 255, 0.03)', borderRadius: '8px', border: '1px solid var(--border-color)'}}>
                  <div className="flex justify-between items-center mb-2">
                    <label className="form-label mb-0" style={{color: 'var(--primary-color)'}}>Medicamentos (Receta / Entrega)</label>
                    <button type="button" className="btn btn-secondary" style={{padding: '4px 8px', fontSize: '0.8rem'}} onClick={addMedicamento}>+ Añadir Medicamento</button>
                  </div>
                  {newAtencion.medicamentos.length === 0 && <div className="text-muted" style={{fontSize: '0.85rem'}}>No se han recetado medicamentos.</div>}
                  
                  {newAtencion.medicamentos.map((med, index) => (
                    <div key={index} className="flex gap-2 mb-2 items-center">
                      <select required className="form-control" value={med.medicamento_id} onChange={(e) => updateMedicamento(index, 'medicamento_id', e.target.value)} style={{flex: 2}}>
                        <option value="">Seleccione medicamento...</option>
                        {medicamentos.map(m => <option key={m.id} value={m.id}>{m.nombre} - {m.presentacion} (Stock: {m.stock_actual})</option>)}
                      </select>
                      <input type="number" required min="1" className="form-control" value={med.cantidad} onChange={(e) => updateMedicamento(index, 'cantidad', e.target.value)} style={{width: '100px'}} placeholder="Cant." title="Cantidad" />
                      {!newAtencion.id && (
                        <button type="button" className="action-btn delete" onClick={() => removeMedicamento(index)}><Trash2 size={18}/></button>
                      )}
                    </div>
                  ))}
                  {!newAtencion.id && newAtencion.medicamentos.length > 0 && (
                    <div className="text-muted mt-2" style={{fontSize: '0.8rem'}}>* Guardar esta atención descontará estos medicamentos del inventario automáticamente.</div>
                  )}
                </div>

                <div className="grid grid-cols-2">
                  <div className="form-group">
                    <label className="form-label">Destino</label>
                    <select required className="form-control" value={newAtencion.destino} onChange={e => setNewAtencion({...newAtencion, destino: e.target.value})}>
                      <option value="">Seleccione...</option>
                      <option value="Alta a su puesto">Alta a su puesto</option>
                      <option value="Observación en Tópico">Observación en Tópico</option>
                      <option value="Descanso Médico">Descanso Médico</option>
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
                <button className="btn btn-primary" onClick={() => window.print()}>🖨️ Imprimir Ficha</button>
                <button className="close-btn" onClick={() => setViewAtencion(null)}><X size={24} /></button>
              </div>
            </div>
            
            <div className="modal-body print-area" style={{padding: '30px', background: 'white', color: 'black'}}>
              <div style={{textAlign: 'center', marginBottom: '30px', borderBottom: '2px solid #333', paddingBottom: '15px'}}>
                <h1 style={{fontSize: '24px', margin: '0 0 5px 0', color: 'black'}}>MEDGLOBAL</h1>
                <h2 style={{fontSize: '18px', margin: 0, fontWeight: 'normal', color: '#555'}}>FICHA DE ATENCIÓN / TÓPICO OCUPACIONAL</h2>
              </div>

              <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '15px', marginBottom: '25px', fontSize: '14px'}}>
                <div><strong>N° de Ficha:</strong> #{viewAtencion.id.toString().padStart(4, '0')}</div>
                <div><strong>Fecha:</strong> {new Date(viewAtencion.fecha).toLocaleDateString()}</div>
                <div><strong>Hora de Ingreso:</strong> {viewAtencion.hora_ingreso || '--'}</div>
                <div><strong>Hora de Salida:</strong> {viewAtencion.hora_salida || '--'}</div>
                <div><strong>Sede:</strong> {viewAtencion.sede_atencion || '--'}</div>
                <div><strong>Tiempo en Tópico:</strong> {viewAtencion.tiempo_topico || '--'}</div>
              </div>

              <h4 style={{borderBottom: '1px solid #ccc', paddingBottom: '5px', marginTop: '20px', color: '#333'}}>I. DATOS DEL PACIENTE</h4>
              <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', fontSize: '14px'}}>
                <div><strong>Paciente:</strong> {viewAtencion.trabajador ? `${viewAtencion.trabajador.nombre} ${viewAtencion.trabajador.apellidos}` : '--'}</div>
                <div><strong>DNI:</strong> {viewAtencion.trabajador?.dni || '--'}</div>
                <div><strong>Área / Cargo:</strong> {viewAtencion.trabajador?.cargo || '--'}</div>
                <div><strong>Jefe Inmediato:</strong> {viewAtencion.jefe_inmediato || '--'}</div>
              </div>

              <h4 style={{borderBottom: '1px solid #ccc', paddingBottom: '5px', marginTop: '25px', color: '#333'}}>II. EVALUACIÓN MÉDICA</h4>
              <div style={{fontSize: '14px', marginBottom: '10px'}}>
                <strong>Anamnesis / Motivo de Consulta:</strong>
                <p style={{marginTop: '5px', whiteSpace: 'pre-wrap', background: '#f9f9f9', padding: '10px', borderRadius: '4px', border: '1px solid #eee'}}>{viewAtencion.descripcion}</p>
              </div>
              
              <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', fontSize: '14px'}}>
                <div><strong>Sistema:</strong> {viewAtencion.sistema?.nombre || '--'}</div>
                <div><strong>Clasificación:</strong> {viewAtencion.clasificacion?.nombre || '--'}</div>
                <div style={{gridColumn: 'span 2'}}><strong>Diagnóstico:</strong> {viewAtencion.diagnostico || '--'}</div>
              </div>

              <h4 style={{borderBottom: '1px solid #ccc', paddingBottom: '5px', marginTop: '25px', color: '#333'}}>III. TRATAMIENTO Y DESTINO</h4>
              <div style={{fontSize: '14px', marginBottom: '10px'}}>
                <strong>Tratamiento en Tópico:</strong>
                <p style={{marginTop: '5px', whiteSpace: 'pre-wrap'}}>{viewAtencion.tratamiento || 'Ninguno'}</p>
              </div>
              
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
          </div>
        </div>
      )}
      
      <style>{`
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
        }
      `}</style>
    </div>
  );
};

export default Atenciones;
