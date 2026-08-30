import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { API_URL } from '../config';

/**
 * Activacion de licencia de la app de escritorio.
 * En la version web del VPS /licencias/estado marca requerido=false y esta
 * pantalla redirige al login.
 */
const ActivarLicencia = () => {
  const navigate = useNavigate();
  const [estado, setEstado] = useState(null);
  const [codigo, setCodigo] = useState('');
  const [error, setError] = useState('');
  const [ok, setOk] = useState('');
  const [loading, setLoading] = useState(false);
  const [copiado, setCopiado] = useState(false);

  useEffect(() => {
    let activo = true;
    fetch(API_URL + '/licencias/estado')
      .then((r) => r.json())
      .then((data) => {
        if (!activo) return;
        setEstado(data);
        if (!data.requerido || data.valida) {
          navigate('/login', { replace: true });
        }
      })
      .catch(() => {
        if (activo) setError('No se pudo consultar el estado de la licencia.');
      });
    return () => { activo = false; };
  }, [navigate]);

  const copiarId = async () => {
    if (!estado?.machine_id) return;
    try {
      await navigator.clipboard.writeText(estado.machine_id);
      setCopiado(true);
      setTimeout(() => setCopiado(false), 2000);
    } catch {
      setError('No se pudo copiar. Seleccione el ID manualmente.');
    }
  };

  const activar = async (e) => {
    e.preventDefault();
    setError('');
    setOk('');
    setLoading(true);
    try {
      const response = await fetch(API_URL + '/licencias/activar', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ codigo: codigo.trim() }),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok || data.ok === false) {
        throw new Error(data.detalle || data.detail || 'No se pudo activar la licencia.');
      }
      setOk(data.detalle || 'Licencia activada.');
      setTimeout(() => navigate('/login', { replace: true }), 800);
    } catch (err) {
      setError(err.message || 'No se pudo activar la licencia.');
    } finally {
      setLoading(false);
    }
  };

  if (!estado) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <p style={{ color: 'var(--text-muted)' }}>Comprobando licencia…</p>
      </div>
    );
  }

  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '24px' }}>
      <div className="glass-panel" style={{ width: '100%', maxWidth: '480px', padding: '32px' }}>
        <div style={{ textAlign: 'center', marginBottom: '20px' }}>
          <img src="/logo.png" alt="MEDGLOBAL" style={{ maxHeight: '48px', objectFit: 'contain' }} />
        </div>
        <h1 style={{ fontSize: '1.2rem', textAlign: 'center', marginBottom: '8px' }}>Activar licencia</h1>
        <p style={{ fontSize: '0.9rem', color: 'var(--text-muted)', textAlign: 'center', marginBottom: '20px', lineHeight: 1.45 }}>
          Esta instalacion de escritorio requiere una licencia por PC.
          Envie el ID de equipo a su administrador y pegue el codigo recibido.
        </p>

        <div className="form-group">
          <label className="form-label">ID de este equipo (machine_id)</label>
          <div style={{ display: 'flex', gap: '8px' }}>
            <input
              className="form-control"
              readOnly
              value={estado.machine_id || ''}
              style={{ fontFamily: 'monospace', fontSize: '0.85rem' }}
            />
            <button type="button" className="btn btn-secondary" onClick={copiarId} style={{ whiteSpace: 'nowrap' }}>
              {copiado ? 'Copiado' : 'Copiar'}
            </button>
          </div>
        </div>

        <form onSubmit={activar}>
          <div className="form-group">
            <label className="form-label">Codigo de licencia</label>
            <textarea
              className="form-control"
              required
              rows={4}
              value={codigo}
              onChange={(e) => setCodigo(e.target.value)}
              placeholder="Pegue aqui el codigo completo de la licencia"
              style={{ fontFamily: 'monospace', fontSize: '0.8rem', resize: 'vertical' }}
            />
          </div>

          {error && (
            <p style={{ color: 'var(--danger-color)', fontSize: '0.9rem', marginBottom: '12px' }}>{error}</p>
          )}
          {ok && (
            <p style={{ color: 'var(--success-color)', fontSize: '0.9rem', marginBottom: '12px' }}>{ok}</p>
          )}

          <button type="submit" className="btn btn-primary" style={{ width: '100%' }} disabled={loading}>
            {loading ? 'Activando…' : 'Activar en esta PC'}
          </button>
        </form>
      </div>
    </div>
  );
};

export default ActivarLicencia;
