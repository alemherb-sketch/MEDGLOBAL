import { useState, useEffect } from 'react';
import { Calendar, momentLocalizer } from 'react-big-calendar';
import moment from 'moment';
import 'moment/locale/es';
import 'react-big-calendar/lib/css/react-big-calendar.css';
import { Plus, X, Trash2, Edit2 } from 'lucide-react';

// Setup moment locale to Spanish
moment.locale('es');
const localizer = momentLocalizer(moment);

const Citas = () => {
  const [citas, setCitas] = useState([]);
  const [pacientes, setPacientes] = useState([]);
  const [personalSalud, setPersonalSalud] = useState([]);
  
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [formData, setFormData] = useState({
    id: null,
    paciente_id: '',
    personal_salud_id: '',
    fecha: '',
    hora: '',
    motivo: '',
    estado: 'PENDIENTE'
  });

  const fetchData = () => {
    fetch((import.meta.env.VITE_API_URL ? (import.meta.env.VITE_API_URL.startsWith('http') ? import.meta.env.VITE_API_URL : 'https://' + import.meta.env.VITE_API_URL) : '${(import.meta.env.VITE_API_URL ? (import.meta.env.VITE_API_URL.startsWith('http') ? import.meta.env.VITE_API_URL : 'https://' + import.meta.env.VITE_API_URL) : 'http://localhost:8000')}') + '/citas/').then(res => res.json()).then(setCitas);
    fetch((import.meta.env.VITE_API_URL ? (import.meta.env.VITE_API_URL.startsWith('http') ? import.meta.env.VITE_API_URL : 'https://' + import.meta.env.VITE_API_URL) : '${(import.meta.env.VITE_API_URL ? (import.meta.env.VITE_API_URL.startsWith('http') ? import.meta.env.VITE_API_URL : 'https://' + import.meta.env.VITE_API_URL) : 'http://localhost:8000')}') + '/trabajadores/').then(res => res.json()).then(setPacientes);
    fetch((import.meta.env.VITE_API_URL ? (import.meta.env.VITE_API_URL.startsWith('http') ? import.meta.env.VITE_API_URL : 'https://' + import.meta.env.VITE_API_URL) : '${(import.meta.env.VITE_API_URL ? (import.meta.env.VITE_API_URL.startsWith('http') ? import.meta.env.VITE_API_URL : 'https://' + import.meta.env.VITE_API_URL) : 'http://localhost:8000')}') + '/personal_salud/').then(res => res.json()).then(setPersonalSalud);
  };

  useEffect(() => {
    fetchData();
  }, []);

  // Format events for calendar
  const events = citas.map(c => {
    const startDate = new Date(c.fecha_hora);
    const endDate = new Date(startDate.getTime() + 30 * 60000); // 30 min duration default
    
    return {
      id: c.id,
      title: `${c.paciente?.nombre} ${c.paciente?.apellidos} - ${c.personal_salud?.especialidad}`,
      start: startDate,
      end: endDate,
      resource: c
    };
  });

  const handleSelectEvent = (event) => {
    const c = event.resource;
    const dateObj = new Date(c.fecha_hora);
    
    // Format YYYY-MM-DD
    const fecha = dateObj.toISOString().split('T')[0];
    // Format HH:MM
    const hora = dateObj.toTimeString().substring(0, 5);

    setFormData({
      id: c.id,
      paciente_id: c.paciente_id,
      personal_salud_id: c.personal_salud_id,
      fecha,
      hora,
      motivo: c.motivo || '',
      estado: c.estado || 'PENDIENTE'
    });
    setIsModalOpen(true);
  };

  const handleSelectSlot = ({ start }) => {
    const dateObj = new Date(start);
    const fecha = dateObj.toISOString().split('T')[0];
    const hora = dateObj.toTimeString().substring(0, 5);

    setFormData({
      id: null,
      paciente_id: '',
      personal_salud_id: '',
      fecha,
      hora,
      motivo: '',
      estado: 'PENDIENTE'
    });
    setIsModalOpen(true);
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    const isEditing = formData.id !== null;
    const url = isEditing ? `${(import.meta.env.VITE_API_URL ? (import.meta.env.VITE_API_URL.startsWith('http') ? import.meta.env.VITE_API_URL : 'https://' + import.meta.env.VITE_API_URL) : 'http://localhost:8000')}/citas/${formData.id}` : (import.meta.env.VITE_API_URL ? (import.meta.env.VITE_API_URL.startsWith('http') ? import.meta.env.VITE_API_URL : 'https://' + import.meta.env.VITE_API_URL) : '${(import.meta.env.VITE_API_URL ? (import.meta.env.VITE_API_URL.startsWith('http') ? import.meta.env.VITE_API_URL : 'https://' + import.meta.env.VITE_API_URL) : 'http://localhost:8000')}') + '/citas/';
    const method = isEditing ? 'PUT' : 'POST';

    // Combine date and time
    const fecha_hora = new Date(`${formData.fecha}T${formData.hora}:00`).toISOString();

    const dataToSend = {
      paciente_id: parseInt(formData.paciente_id),
      personal_salud_id: parseInt(formData.personal_salud_id),
      fecha_hora: fecha_hora,
      motivo: formData.motivo,
      estado: formData.estado
    };

    fetch(url, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(dataToSend)
    }).then(async res => {
      if (!res.ok) throw new Error(await res.text());
      fetchData();
      setIsModalOpen(false);
    }).catch(err => alert("Error al guardar: " + err.message));
  };

  const handleDelete = () => {
    if (window.confirm('¿Eliminar esta cita médica?')) {
      fetch(`${(import.meta.env.VITE_API_URL ? (import.meta.env.VITE_API_URL.startsWith('http') ? import.meta.env.VITE_API_URL : 'https://' + import.meta.env.VITE_API_URL) : 'http://localhost:8000')}/citas/${formData.id}`, { method: 'DELETE' })
        .then(() => {
          fetchData();
          setIsModalOpen(false);
        });
    }
  };

  // Custom styling for calendar events based on state
  const eventStyleGetter = (event) => {
    const estado = event.resource.estado;
    let backgroundColor = 'var(--primary-color)'; // PENDIENTE
    if (estado === 'CONFIRMADA') backgroundColor = '#3b82f6';
    if (estado === 'ATENDIDA') backgroundColor = '#10b981';
    if (estado === 'CANCELADA') backgroundColor = '#ef4444';

    return {
      style: {
        backgroundColor,
        borderRadius: '4px',
        opacity: 0.9,
        color: 'white',
        border: '0px',
        display: 'block'
      }
    };
  };

  return (
    <div style={{ height: 'calc(100vh - 40px)', display: 'flex', flexDirection: 'column' }}>
      <div className="flex justify-between items-center mb-4">
        <div>
          <h1 style={{marginBottom: '0'}}>Programación de Citas</h1>
          <div className="flex gap-4 mt-2" style={{fontSize: '0.85rem'}}>
            <span className="flex items-center gap-1"><span style={{width:12, height:12, background:'var(--primary-color)', borderRadius:2}}></span> Pendiente</span>
            <span className="flex items-center gap-1"><span style={{width:12, height:12, background:'#3b82f6', borderRadius:2}}></span> Confirmada</span>
            <span className="flex items-center gap-1"><span style={{width:12, height:12, background:'#10b981', borderRadius:2}}></span> Atendida</span>
            <span className="flex items-center gap-1"><span style={{width:12, height:12, background:'#ef4444', borderRadius:2}}></span> Cancelada</span>
          </div>
        </div>
        <button className="btn btn-primary" onClick={() => handleSelectSlot({start: new Date()})}>
          <Plus size={18} style={{marginRight: '8px'}} /> Nueva Cita
        </button>
      </div>

      <div className="glass-panel" style={{ flex: 1, padding: '20px', overflow: 'hidden' }}>
        <Calendar
          localizer={localizer}
          events={events}
          startAccessor="start"
          endAccessor="end"
          style={{ height: '100%' }}
          onSelectEvent={handleSelectEvent}
          onSelectSlot={handleSelectSlot}
          selectable
          eventPropGetter={eventStyleGetter}
          messages={{
            next: "Siguiente",
            previous: "Anterior",
            today: "Hoy",
            month: "Mes",
            week: "Semana",
            day: "Día",
            agenda: "Agenda",
            date: "Fecha",
            time: "Hora",
            event: "Cita",
            noEventsInRange: "No hay citas en este rango."
          }}
        />
      </div>

      {isModalOpen && (
        <div className="modal-overlay" style={{zIndex: 1000}}>
          <div className="modal-content">
            <div className="modal-header">
              <h3>{formData.id ? 'Detalles de la Cita' : 'Agendar Nueva Cita'}</h3>
              <button className="close-btn" onClick={() => setIsModalOpen(false)}><X size={24} /></button>
            </div>
            <div className="modal-body">
              <form onSubmit={handleSubmit}>
                
                <div className="form-group">
                  <label className="form-label">Paciente (Colaborador)</label>
                  <select required className="form-control" value={formData.paciente_id} onChange={e => setFormData({...formData, paciente_id: e.target.value})}>
                    <option value="">Seleccione un paciente...</option>
                    {pacientes.map(p => <option key={p.id} value={p.id}>{p.dni} - {p.nombre} {p.apellidos}</option>)}
                  </select>
                </div>

                <div className="form-group">
                  <label className="form-label">Médico Tratante (Personal de Salud)</label>
                  <select required className="form-control" value={formData.personal_salud_id} onChange={e => setFormData({...formData, personal_salud_id: e.target.value})}>
                    <option value="">Seleccione médico...</option>
                    {personalSalud.map(p => <option key={p.id} value={p.id}>{p.especialidad}: Dr. {p.nombre} {p.apellidos}</option>)}
                  </select>
                </div>

                <div className="grid grid-cols-2">
                  <div className="form-group">
                    <label className="form-label">Fecha</label>
                    <input type="date" required className="form-control" value={formData.fecha} onChange={e => setFormData({...formData, fecha: e.target.value})} />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Hora</label>
                    <input type="time" required className="form-control" value={formData.hora} onChange={e => setFormData({...formData, hora: e.target.value})} />
                  </div>
                </div>

                <div className="form-group">
                  <label className="form-label">Estado de la Cita</label>
                  <select className="form-control" value={formData.estado} onChange={e => setFormData({...formData, estado: e.target.value})}>
                    <option value="PENDIENTE">Pendiente</option>
                    <option value="CONFIRMADA">Confirmada</option>
                    <option value="ATENDIDA">Atendida</option>
                    <option value="CANCELADA">Cancelada</option>
                  </select>
                </div>

                <div className="form-group">
                  <label className="form-label">Motivo de consulta / Notas</label>
                  <textarea className="form-control" rows="3" value={formData.motivo} onChange={e => setFormData({...formData, motivo: e.target.value})}></textarea>
                </div>

                <div style={{display: 'flex', justifyContent: 'space-between', marginTop: '24px'}}>
                  {formData.id ? (
                    <button type="button" className="btn btn-secondary" style={{color: 'var(--danger-color)', borderColor: 'rgba(239, 68, 68, 0.3)'}} onClick={handleDelete}>
                      <Trash2 size={18} style={{marginRight: '8px'}} /> Eliminar Cita
                    </button>
                  ) : <div></div>}
                  
                  <div className="flex gap-2">
                    <button type="button" className="btn btn-secondary" onClick={() => setIsModalOpen(false)}>Cancelar</button>
                    <button type="submit" className="btn btn-primary">Guardar Cita</button>
                  </div>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Citas;
