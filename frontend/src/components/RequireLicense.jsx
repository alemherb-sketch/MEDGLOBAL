import { useEffect, useState } from 'react';
import { Navigate } from 'react-router-dom';
import { API_URL } from '../config';

// Consulta unica al montar: si el API no exige licencia (web VPS) deja pasar.
// Si la exige y no hay, manda a activar.
const RequireLicense = ({ children }) => {
  const [estado, setEstado] = useState(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let activo = true;
    fetch(API_URL + '/licencias/estado')
      .then((r) => r.json())
      .then((data) => { if (activo) setEstado(data); })
      .catch(() => { if (activo) setError(true); });
    return () => { activo = false; };
  }, []);

  if (error) {
    // Si el endpoint falla (build muy viejo del API), no bloquear el uso web.
    return children;
  }

  if (!estado) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <p style={{ color: 'var(--text-muted)' }}>Cargando…</p>
      </div>
    );
  }

  if (estado.requerido && !estado.valida) {
    return <Navigate to="/activar-licencia" replace />;
  }

  return children;
};

export default RequireLicense;
