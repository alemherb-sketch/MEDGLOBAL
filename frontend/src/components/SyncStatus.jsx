import { useEffect, useState } from 'react';
import { Wifi, WifiOff, AlertTriangle } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { es } from 'date-fns/locale';
import { apiJson } from '../api';

const POLL_MS = 15000;

const ESTILOS_POR_ESTADO = {
  en_linea: { icon: Wifi, color: 'var(--success-color)', texto: 'En línea' },
  fuera_de_linea: { icon: WifiOff, color: 'var(--warning-color)', texto: 'Sin conexión — trabajando localmente' },
  error: { icon: AlertTriangle, color: 'var(--danger-color)', texto: 'Error de sincronización' },
};

const SyncStatus = () => {
  const [estado, setEstado] = useState(null);

  useEffect(() => {
    let activo = true;
    const consultar = () => {
      apiJson('/sync/estado')
        .then((data) => { if (activo) setEstado(data); })
        .catch(() => {});
    };
    consultar();
    const id = setInterval(consultar, POLL_MS);
    return () => { activo = false; clearInterval(id); };
  }, []);

  if (!estado || estado.estado === 'desactivado') return null;

  const cfg = ESTILOS_POR_ESTADO[estado.estado];
  if (!cfg) return null;
  const Icono = cfg.icon;

  const ultima = estado.ultima_sincronizacion
    ? formatDistanceToNow(new Date(estado.ultima_sincronizacion), { addSuffix: true, locale: es })
    : null;

  return (
    <div
      title={estado.ultimo_error || undefined}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '8px',
        padding: '8px 10px',
        margin: '0 0 8px',
        borderRadius: '8px',
        border: '1px solid var(--border-color)',
        fontSize: '12px',
        color: cfg.color,
      }}
    >
      <Icono size={14} style={{ flexShrink: 0 }} />
      <div style={{ display: 'flex', flexDirection: 'column', lineHeight: 1.3, overflow: 'hidden' }}>
        <span>{cfg.texto}</span>
        {ultima && <span style={{ color: 'var(--text-muted)' }}>Última sync: {ultima}</span>}
      </div>
    </div>
  );
};

export default SyncStatus;
