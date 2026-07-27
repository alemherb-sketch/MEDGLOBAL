import { useEffect, useState } from 'react';
import { Wifi, WifiOff, AlertTriangle, RefreshCw } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { es } from 'date-fns/locale';
import { apiJson } from '../api';

const POLL_MS = 15000;

const ESTILOS_POR_ESTADO = {
  en_linea: { icon: Wifi, color: 'var(--success-color)', texto: 'En línea' },
  fuera_de_linea: { icon: WifiOff, color: 'var(--warning-color)', texto: 'Sin conexión — trabajando localmente' },
  error: { icon: AlertTriangle, color: 'var(--danger-color)', texto: 'Error de sincronización' },
};

const MENSAJE_POR_MOTIVO = {
  en_curso: 'Ya hay una sincronización en curso, espere a que termine.',
  credenciales: 'El servidor rechazó el usuario o la contraseña de sincronización.',
  sin_conexion: 'No se pudo conectar con el servidor. Sus datos siguen guardados en esta PC.',
  no_configurado: 'Esta instalación no tiene configurada la sincronización.',
};

/** Resume el resultado de un ciclo en una frase para el usuario. */
const resumir = ({ subidos, bajados, conflictos }) => {
  if (!subidos && !bajados) return 'Todo estaba al día, no había cambios pendientes.';
  const partes = [];
  if (subidos) partes.push(`${subidos} ${subidos === 1 ? 'registro subido' : 'registros subidos'}`);
  if (bajados) partes.push(`${bajados} ${bajados === 1 ? 'recibido' : 'recibidos'}`);
  let texto = partes.join(' y ') + '.';
  if (conflictos) {
    texto += ` ${conflictos} ${conflictos === 1 ? 'registro quedó' : 'registros quedaron'} en revisión por haberse editado en dos equipos a la vez.`;
  }
  return texto;
};

const SyncStatus = () => {
  const [estado, setEstado] = useState(null);
  const [sincronizando, setSincronizando] = useState(false);
  const [resultado, setResultado] = useState(null);

  const consultarEstado = () => apiJson('/sync/estado').then(setEstado).catch(() => {});

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

  const sincronizarAhora = async () => {
    setSincronizando(true);
    setResultado(null);
    try {
      // Sin timeout del lado del navegador a proposito: la primera
      // sincronizacion despues de varios dias sin internet puede mover miles
      // de registros y tardar. Cortarla aca dejaria al usuario sin saber si
      // subio o no.
      const r = await apiJson('/sync/ahora', { method: 'POST' });
      setResultado(r.ok
        ? { tipo: 'ok', texto: resumir(r), recargar: r.bajados > 0 }
        : {
            tipo: 'error',
            texto: MENSAJE_POR_MOTIVO[r.motivo] || 'La sincronización falló. Sus datos siguen guardados en esta PC.',
            // El detalle tecnico va aparte y en chico: al usuario le alcanza
            // con el mensaje de arriba, pero sin esto no habia nada que
            // pasarle a soporte para saber si es el certificado, el DNS, un
            // proxy o el servidor caido.
            detalle: r.detalle,
          });
    } catch (e) {
      setResultado({ tipo: 'error', texto: 'No se pudo completar la sincronización. Sus datos siguen guardados en esta PC.' });
    } finally {
      setSincronizando(false);
      consultarEstado();
    }
  };

  // En el servidor web sync_client no esta instalado y /sync/estado responde
  // "desactivado": ahi no se muestra ni el indicador ni el boton.
  if (!estado || estado.estado === 'desactivado') return null;

  const cfg = ESTILOS_POR_ESTADO[estado.estado];
  if (!cfg) return null;
  const Icono = cfg.icon;

  const ultima = estado.ultima_sincronizacion
    ? formatDistanceToNow(new Date(estado.ultima_sincronizacion), { addSuffix: true, locale: es })
    : null;

  return (
    <div style={{ margin: '0 0 8px' }}>
      <div
        title={estado.ultimo_error || undefined}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          padding: '8px 10px',
          borderRadius: '8px 8px 0 0',
          border: '1px solid var(--border-color)',
          borderBottom: 'none',
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

      <button
        type="button"
        onClick={sincronizarAhora}
        disabled={sincronizando}
        style={{
          width: '100%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '8px',
          padding: '9px 10px',
          borderRadius: '0 0 8px 8px',
          border: '1px solid var(--border-color)',
          background: 'rgba(255,255,255,0.04)',
          color: sincronizando ? 'var(--text-muted)' : 'inherit',
          fontSize: '12px',
          fontWeight: 500,
          cursor: sincronizando ? 'wait' : 'pointer',
        }}
      >
        <RefreshCw
          size={14}
          style={{ flexShrink: 0, animation: sincronizando ? 'medglobal-girar 1s linear infinite' : 'none' }}
        />
        {sincronizando ? 'Sincronizando…' : 'Sincronizar ahora'}
      </button>

      {resultado && (
        <div
          style={{
            marginTop: '6px',
            padding: '8px 10px',
            borderRadius: '8px',
            fontSize: '11.5px',
            lineHeight: 1.4,
            border: '1px solid var(--border-color)',
            color: resultado.tipo === 'ok' ? 'var(--success-color)' : 'var(--danger-color)',
          }}
        >
          {resultado.texto}
          {resultado.detalle && (
            <div style={{ marginTop: '5px', color: 'var(--text-muted)', fontSize: '10.5px', wordBreak: 'break-word' }}>
              Detalle: {resultado.detalle}
            </div>
          )}
          {resultado.recargar && (
            <button
              type="button"
              onClick={() => window.location.reload()}
              style={{
                display: 'block',
                marginTop: '6px',
                background: 'none',
                border: 'none',
                padding: 0,
                color: 'var(--primary-color)',
                textDecoration: 'underline',
                cursor: 'pointer',
                fontSize: '11.5px',
              }}
            >
              Actualizar la vista para ver los datos nuevos
            </button>
          )}
        </div>
      )}

      {/* La recarga es manual a proposito: recargar solo dejaria a medias
          cualquier ficha que el usuario tenga abierta sin guardar. */}
      <style>{`@keyframes medglobal-girar { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
};

export default SyncStatus;
