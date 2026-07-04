import { useState, useEffect } from 'react';
import { API_URL } from '../config';
import { Users, Stethoscope, Pill, AlertTriangle } from 'lucide-react';

const Dashboard = () => {
  const [kpis, setKpis] = useState({
    total_atenciones: 0,
    total_trabajadores: 0,
    total_medicamentos: 0,
    medicamentos_stock_bajo: 0
  });

  useEffect(() => {
    fetch(API_URL + '/dashboard/kpis')
      .then(res => res.json())
      .then(data => setKpis(data))
      .catch(err => console.error(err));
  }, []);

  return (
    <div>
      <div className="flex items-center mb-8">
        <div className="logo-container" style={{marginRight: '20px'}}>
          <img src="/logo.png" alt="MEDGLOBAL Logo" style={{height: '45px', display: 'block'}} />
        </div>
        <div>
          <h1 style={{margin: 0, fontSize: '2.2rem', textShadow: '0 2px 10px rgba(0,0,0,0.3)'}}>Dashboard</h1>
          <p className="text-muted" style={{margin: 0, fontSize: '1.1rem'}}>Visión general del sistema</p>
        </div>
      </div>
      <div className="grid grid-cols-4 mb-4">
        <div className="glass-panel">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="form-label" style={{textTransform: 'uppercase', letterSpacing: '1px', fontSize: '0.8rem'}}>Atenciones Hoy</h3>
              <h2 style={{fontSize: '2.5rem', margin: 0, fontWeight: '700'}}>{kpis.total_atenciones}</h2>
            </div>
            <div style={{padding: '16px', background: 'rgba(14,165,233,0.1)', borderRadius: '16px', boxShadow: 'inset 0 0 0 1px rgba(14,165,233,0.2)'}}>
              <Stethoscope size={32} color="var(--primary-color)" />
            </div>
          </div>
        </div>

        <div className="glass-panel">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="form-label" style={{textTransform: 'uppercase', letterSpacing: '1px', fontSize: '0.8rem'}}>Personal Activo</h3>
              <h2 style={{fontSize: '2.5rem', margin: 0, fontWeight: '700'}}>{kpis.total_trabajadores}</h2>
            </div>
            <div style={{padding: '16px', background: 'rgba(139,92,246,0.1)', borderRadius: '16px', boxShadow: 'inset 0 0 0 1px rgba(139,92,246,0.2)'}}>
              <Users size={32} color="var(--secondary-color)" />
            </div>
          </div>
        </div>

        <div className="glass-panel">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="form-label" style={{textTransform: 'uppercase', letterSpacing: '1px', fontSize: '0.8rem'}}>Medicamentos</h3>
              <h2 style={{fontSize: '2.5rem', margin: 0, fontWeight: '700'}}>{kpis.total_medicamentos}</h2>
            </div>
            <div style={{padding: '16px', background: 'rgba(16,185,129,0.1)', borderRadius: '16px', boxShadow: 'inset 0 0 0 1px rgba(16,185,129,0.2)'}}>
              <Pill size={32} color="var(--success-color)" />
            </div>
          </div>
        </div>

        <div className="glass-panel" style={{ borderLeft: '4px solid var(--danger-color)', position: 'relative', overflow: 'hidden' }}>
          <div className="flex items-center justify-between">
            <div>
              <h3 className="form-label" style={{textTransform: 'uppercase', letterSpacing: '1px', fontSize: '0.8rem'}}>Stock Bajo</h3>
              <h2 style={{fontSize: '2.5rem', margin: 0, fontWeight: '700', color: 'var(--danger-color)'}}>{kpis.medicamentos_stock_bajo}</h2>
            </div>
            <div style={{padding: '16px', background: 'rgba(239,68,68,0.1)', borderRadius: '16px', boxShadow: 'inset 0 0 0 1px rgba(239,68,68,0.2)'}}>
              <AlertTriangle size={32} color="var(--danger-color)" />
            </div>
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
