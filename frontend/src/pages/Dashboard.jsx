import { useState, useEffect } from 'react';
import { Users, Stethoscope, Pill, AlertTriangle } from 'lucide-react';

const Dashboard = () => {
  const [kpis, setKpis] = useState({
    total_atenciones: 0,
    total_trabajadores: 0,
    total_medicamentos: 0,
    medicamentos_stock_bajo: 0
  });

  useEffect(() => {
    fetch((import.meta.env.VITE_API_URL ? (import.meta.env.VITE_API_URL.startsWith('http') ? import.meta.env.VITE_API_URL : 'https://' + import.meta.env.VITE_API_URL) : 'http://localhost:8000') + '/dashboard/kpis')
      .then(res => res.json())
      .then(data => setKpis(data))
      .catch(err => console.error(err));
  }, []);

  return (
    <div>
      <h1 className="mb-4">Dashboard</h1>
      
      <div className="grid grid-cols-4 mb-4">
        <div className="glass-panel">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="form-label">Atenciones Hoy</h3>
              <h2>{kpis.total_atenciones}</h2>
            </div>
            <Stethoscope size={40} color="var(--primary-color)" />
          </div>
        </div>

        <div className="glass-panel">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="form-label">Personal Activo</h3>
              <h2>{kpis.total_trabajadores}</h2>
            </div>
            <Users size={40} color="var(--secondary-color)" />
          </div>
        </div>

        <div className="glass-panel">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="form-label">Medicamentos</h3>
              <h2>{kpis.total_medicamentos}</h2>
            </div>
            <Pill size={40} color="var(--success-color)" />
          </div>
        </div>

        <div className="glass-panel" style={{ borderLeft: '4px solid var(--danger-color)' }}>
          <div className="flex items-center justify-between">
            <div>
              <h3 className="form-label">Stock Bajo</h3>
              <h2 style={{ color: 'var(--danger-color)' }}>{kpis.medicamentos_stock_bajo}</h2>
            </div>
            <AlertTriangle size={40} color="var(--danger-color)" />
          </div>
        </div>
      </div>
      
      <div className="glass-panel">
        <h2>Resumen Rápido</h2>
        <p className="mt-2 text-muted">El sistema MEDGLOBAL está operando correctamente. Monitorea las atenciones diarias y mantén el stock actualizado para un funcionamiento óptimo de la farmacia y tópico.</p>
      </div>
    </div>
  );
};

export default Dashboard;
