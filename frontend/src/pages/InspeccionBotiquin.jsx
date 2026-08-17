import { useState, useEffect, useMemo, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import Select from 'react-select';
import DatePicker from 'react-datepicker';
import 'react-datepicker/dist/react-datepicker.css';
import * as XLSX from 'xlsx';
import {
  Search, Trash2, X, ClipboardCheck, Download,
  Filter, History, Save, Eye, Edit2, FileText, ImagePlus, Package, PackagePlus
} from 'lucide-react';
import { apiFetch, apiJson } from '../api';
import { API_URL } from '../config';
import {
  TIPOS_EQUIPO_EMERGENCIA,
  AREAS,
  selectStyles,
  labelMedicamento,
  resumenVehiculo,
} from './botiquinShared';

const ESTADOS_INSUMO = [
  { value: 'CONFORME', label: 'Conforme' },
  { value: 'VENCIDO', label: 'Vencido' },
  { value: 'FALTANTE', label: 'Faltante' },
  { value: 'DETERIORADO', label: 'Deteriorado' },
];

// Los tres primeros son estados de inspecciones anteriores: se conservan para
// que sus PDFs e historial sigan leyéndose, pero ya no se ofrecen al registrar.
const ESTADO_LABEL = {
  BUENO: 'Bueno',
  REGULAR: 'Regular',
  MALO: 'Malo',
  ...Object.fromEntries(ESTADOS_INSUMO.map(e => [e.value, e.label])),
};

const ESTADO_EQUIVALENTE = { BUENO: 'CONFORME', REGULAR: 'DETERIORADO', MALO: 'DETERIORADO' };

/** Deja el estado dentro de las opciones vigentes para que el desplegable
 *  siempre muestre una selección válida. */
const normalizarEstado = (estado) => {
  const valor = (estado || '').toUpperCase();
  if (ESTADOS_INSUMO.some(e => e.value === valor)) return valor;
  return ESTADO_EQUIVALENTE[valor] || 'CONFORME';
};

const emptyInspeccionForm = () => ({
  id: null,
  botiquin_id: '',
  responsable_id: '',
  fecha: new Date(),
  observaciones: '',
  imagenes: [],
  insumos: [],
  mode: 'create', // create | edit | view
});

const assetUrl = (path) => {
  if (!path) return '';
  if (/^https?:\/\//i.test(path) || path.startsWith('blob:') || path.startsWith('data:')) return path;
  return `${API_URL || ''}${path}`;
};

const escHtml = (s) => String(s ?? '')
  .replace(/&/g, '&amp;')
  .replace(/</g, '&lt;')
  .replace(/>/g, '&gt;')
  .replace(/"/g, '&quot;');

const InspeccionBotiquin = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const autoOpenDone = useRef(false);
  const [tab, setTab] = useState('botiquines'); // botiquines | historial | reporte
  const [botiquines, setBotiquines] = useState([]);
  const [inspecciones, setInspecciones] = useState([]);
  const [empresas, setEmpresas] = useState([]);
  const [personal, setPersonal] = useState([]);

  const [filters, setFilters] = useState({
    search: '',
    empresa_id: '',
  });

  const [botFilters, setBotFilters] = useState({
    search: '',
    empresa_id: '',
    estado: '',
  });

  const [modalInspeccion, setModalInspeccion] = useState(false);
  const [formInspeccion, setFormInspeccion] = useState(emptyInspeccionForm);
  const [pendingImagenes, setPendingImagenes] = useState([]); // { key, file, preview }
  const [guardando, setGuardando] = useState(false);
  const [cargandoInsumos, setCargandoInsumos] = useState(false);
  const [reposicionModal, setReposicionModal] = useState(null);
  const [reposicionCantidad, setReposicionCantidad] = useState(1);
  const [reponiendo, setReponiendo] = useState(false);
  const soloLectura = formInspeccion.mode === 'view';

  const [reporteFiltros, setReporteFiltros] = useState({
    empresa_id: '',
    botiquin_id: '',
    areas: [],
    tipos_equipo: [],
    fecha_inicio: null,
    fecha_fin: null,
  });
  const [reporte, setReporte] = useState({
    rango_fechas: [],
    insumos: [],
    totales: { sub_total: 0, igv: 0, total: 0 },
  });
  const [loadingReporte, setLoadingReporte] = useState(false);

  const empresaOptions = useMemo(
    () => empresas.map(e => ({ value: String(e.id), label: `${e.nombre}${e.ruc ? ` (${e.ruc})` : ''}` })),
    [empresas]
  );

  const personalOptions = useMemo(
    () => personal
      .filter(p => (p.estado || 'ACTIVO') === 'ACTIVO')
      .map(p => ({
        value: String(p.id),
        label: `${p.nombre || ''} ${p.apellidos || ''}`.trim() + (p.especialidad ? ` — ${p.especialidad}` : ''),
      })),
    [personal]
  );

  const botiquinOptions = useMemo(
    () => botiquines.map(b => ({
      value: String(b.id),
      label: `${b.codigo ? b.codigo + ' · ' : ''}${b.tipo_botiquin?.nombre || b.tipo_equipo}${b.vehiculo ? ` · ${b.vehiculo}` : ''}${b.ubicacion ? ` · ${b.ubicacion}` : ''}`,
    })),
    [botiquines]
  );

  const areaOptions = useMemo(
    () => AREAS.map(a => ({ value: a, label: a })),
    []
  );

  const tipoEquipoOptions = useMemo(
    () => TIPOS_EQUIPO_EMERGENCIA.map(t => ({ value: t, label: t })),
    []
  );

  const mapInsumosFromApi = (list) =>
    (list || []).map(p => ({
      medicamento_id: String(p.medicamento_id),
      cantidad: p.cantidad || 1,
      estado: normalizarEstado(p.estado),
      reposicion: (p.reposicion || 'NO').toUpperCase() === 'SI' ? 'SI' : 'NO',
      label: p.medicamento ? labelMedicamento(p.medicamento) : (p.label || String(p.medicamento_id)),
    }));

  const updateInsumoField = (medicamento_id, field, value) => {
    setFormInspeccion(prev => ({
      ...prev,
      insumos: prev.insumos.map(i => (
        String(i.medicamento_id) === String(medicamento_id)
          ? { ...i, [field]: value }
          : i
      )),
    }));
  };

  const loadCatalogos = () => {
    apiJson('/empresas/').then(setEmpresas).catch(() => setEmpresas([]));
    apiJson('/personal_salud/').then(setPersonal).catch(() => setPersonal([]));
    apiJson('/botiquines/').then(setBotiquines).catch(() => setBotiquines([]));
  };

  const loadInspecciones = () => {
    const params = new URLSearchParams();
    if (filters.empresa_id) params.append('empresa_id', filters.empresa_id);
    if (filters.search) params.append('search', filters.search);
    const q = params.toString();
    apiJson(`/botiquin_inspecciones/${q ? `?${q}` : ''}`)
      .then(setInspecciones)
      .catch(() => setInspecciones([]));
  };

  const loadBotiquinesList = () => {
    const params = new URLSearchParams();
    if (botFilters.empresa_id) params.append('empresa_id', botFilters.empresa_id);
    if (botFilters.estado) params.append('estado', botFilters.estado);
    if (botFilters.search) params.append('search', botFilters.search);
    const q = params.toString();
    apiJson(`/botiquines/${q ? `?${q}` : ''}`)
      .then(setBotiquines)
      .catch(() => setBotiquines([]));
  };

  useEffect(() => {
    loadCatalogos();
  }, []);

  useEffect(() => {
    if (tab === 'historial') loadInspecciones();
    if (tab === 'botiquines') loadBotiquinesList();
  }, [tab, filters, botFilters]);

  const botiquinesFiltrados = useMemo(() => botiquines, [botiquines]);

  const cargarInsumosDeBotiquin = async (botiquinId) => {
    if (!botiquinId) {
      setFormInspeccion(prev => ({ ...prev, botiquin_id: '', insumos: [] }));
      return;
    }
    setCargandoInsumos(true);
    try {
      const insumos = await apiJson(`/botiquines/${botiquinId}/insumos`);
      setFormInspeccion(prev => ({
        ...prev,
        botiquin_id: String(botiquinId),
        insumos: mapInsumosFromApi(insumos),
      }));
    } catch (err) {
      console.error(err);
      const bot = botiquines.find(b => String(b.id) === String(botiquinId));
      const insumosTipo = bot?.tipo_botiquin?.insumos || [];
      setFormInspeccion(prev => ({
        ...prev,
        botiquin_id: String(botiquinId),
        insumos: mapInsumosFromApi(insumosTipo),
      }));
    } finally {
      setCargandoInsumos(false);
    }
  };

  const openNewInspeccion = (botiquinId = '') => {
    setFormInspeccion({
      ...emptyInspeccionForm(),
      botiquin_id: botiquinId ? String(botiquinId) : '',
    });
    setPendingImagenes([]);
    setModalInspeccion(true);
    if (botiquinId) cargarInsumosDeBotiquin(botiquinId);
  };

  // Desde Botiquín → Inspeccionar: /inspeccion?botiquin_id=...
  useEffect(() => {
    const bid = searchParams.get('botiquin_id');
    if (!bid || autoOpenDone.current) return;
    autoOpenDone.current = true;
    setTab('botiquines');
    openNewInspeccion(bid);
    const next = new URLSearchParams(searchParams);
    next.delete('botiquin_id');
    setSearchParams(next, { replace: true });
  }, [searchParams]);

  const openViewInspeccion = (ins) => {
    setFormInspeccion({
      id: ins.id,
      botiquin_id: String(ins.botiquin_id || ''),
      responsable_id: ins.responsable_id ? String(ins.responsable_id) : '',
      fecha: ins.fecha ? new Date(ins.fecha) : new Date(),
      observaciones: ins.observaciones || '',
      imagenes: Array.isArray(ins.imagenes) ? [...ins.imagenes] : [],
      insumos: mapInsumosFromApi(ins.insumos),
      mode: 'view',
    });
    setPendingImagenes([]);
    setModalInspeccion(true);
  };

  /** Última inspección del botiquín (para Ver / Editar / PDF / Eliminar desde el listado). */
  const obtenerUltimaInspeccion = async (botiquinId) => {
    try {
      const list = await apiJson(`/botiquin_inspecciones/?botiquin_id=${encodeURIComponent(botiquinId)}`);
      if (!list || !list.length) {
        alert('Este botiquín no tiene inspecciones registradas.');
        return null;
      }
      return list[0];
    } catch (err) {
      alert('No se pudo obtener la inspección: ' + (err.message || err));
      return null;
    }
  };

  const verUltimaInspeccion = async (botiquinId) => {
    const ins = await obtenerUltimaInspeccion(botiquinId);
    if (ins) openViewInspeccion(ins);
  };

  const editarUltimaInspeccion = async (botiquinId) => {
    const ins = await obtenerUltimaInspeccion(botiquinId);
    if (ins) openEditInspeccion(ins);
  };

  const pdfUltimaInspeccion = async (botiquinId) => {
    const ins = await obtenerUltimaInspeccion(botiquinId);
    if (ins) imprimirInspeccion(ins);
  };

  const eliminarUltimaInspeccion = async (botiquinId) => {
    const ins = await obtenerUltimaInspeccion(botiquinId);
    if (!ins) return;
    if (!window.confirm('¿Eliminar la última inspección de este botiquín?')) return;
    try {
      await apiFetch(`/botiquin_inspecciones/${ins.id}`, { method: 'DELETE' });
      loadBotiquinesList();
      if (tab === 'historial') loadInspecciones();
    } catch (err) {
      alert('Error al eliminar: ' + (err.message || err));
    }
  };

  const openEditInspeccion = (ins) => {
    setFormInspeccion({
      id: ins.id,
      botiquin_id: String(ins.botiquin_id || ''),
      responsable_id: ins.responsable_id ? String(ins.responsable_id) : '',
      fecha: ins.fecha ? new Date(ins.fecha) : new Date(),
      observaciones: ins.observaciones || '',
      imagenes: Array.isArray(ins.imagenes) ? [...ins.imagenes] : [],
      insumos: mapInsumosFromApi(ins.insumos),
      mode: 'edit',
    });
    setPendingImagenes([]);
    setModalInspeccion(true);
  };

  const onSelectImagenes = (e) => {
    const files = Array.from(e.target.files || []).filter(f => f.type.startsWith('image/'));
    if (!files.length) return;
    setPendingImagenes(prev => [
      ...prev,
      ...files.map(file => ({
        key: `${file.name}-${file.size}-${file.lastModified}-${Math.random().toString(36).slice(2)}`,
        file,
        preview: URL.createObjectURL(file),
      })),
    ]);
    e.target.value = '';
  };

  const removeImagenExistente = (url) => {
    setFormInspeccion(prev => ({
      ...prev,
      imagenes: (prev.imagenes || []).filter(u => u !== url),
    }));
  };

  const removeImagenPendiente = (key) => {
    setPendingImagenes(prev => {
      const item = prev.find(p => p.key === key);
      if (item?.preview) URL.revokeObjectURL(item.preview);
      return prev.filter(p => p.key !== key);
    });
  };

  const subirImagenesPendientes = async () => {
    const urls = [];
    for (const item of pendingImagenes) {
      const fd = new FormData();
      fd.append('file', item.file);
      const res = await apiFetch('/botiquin_inspecciones/upload-imagen', {
        method: 'POST',
        body: fd,
      });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      if (data?.url) urls.push(data.url);
    }
    return urls;
  };

  const imprimirInspeccion = (ins) => {
    const bot = ins.botiquin;
    const botLabel = bot
      ? `${bot.codigo ? bot.codigo + ' · ' : ''}${bot.tipo_botiquin?.nombre || bot.tipo_equipo || ''}${bot.ubicacion ? ' · ' + bot.ubicacion : ''}`
      : '—';
    const responsable = ins.responsable
      ? `${ins.responsable.nombre || ''} ${ins.responsable.apellidos || ''}`.trim()
      : '—';
    const fecha = ins.fecha ? new Date(ins.fecha).toLocaleString() : '—';
    const filas = (ins.insumos || []).map(i => `
      <tr>
        <td>${escHtml(i.medicamento?.nombre || i.medicamento_id)}</td>
        <td style="text-align:center">${escHtml(i.cantidad)}</td>
        <td style="text-align:center">${escHtml(ESTADO_LABEL[i.estado] || i.estado || '—')}</td>
        <td style="text-align:center">${i.reposicion === 'SI' ? 'Sí' : 'No'}</td>
      </tr>
    `).join('') || '<tr><td colspan="4" style="text-align:center">Sin insumos</td></tr>';

    let imagenesLista = ins.imagenes;
    if (typeof imagenesLista === 'string') {
      try { imagenesLista = JSON.parse(imagenesLista); } catch { imagenesLista = []; }
    }
    if (!Array.isArray(imagenesLista)) imagenesLista = [];

    // URL absoluta para que la ventana de impresión cargue bien desde el API
    const absUrl = (path) => {
      const u = assetUrl(path);
      if (!u) return '';
      if (/^https?:\/\//i.test(u) || u.startsWith('blob:') || u.startsWith('data:')) return u;
      const origin = (API_URL && /^https?:\/\//i.test(API_URL))
        ? API_URL.replace(/\/$/, '')
        : window.location.origin;
      return `${origin}${u.startsWith('/') ? u : `/${u}`}`;
    };

    const imgsHtml = imagenesLista.length
      ? imagenesLista.map(u =>
          `<figure class="img-card"><img src="${escHtml(absUrl(u))}" alt="Evidencia de inspección" /></figure>`
        ).join('')
      : '<p class="muted">Sin imágenes adjuntas en esta inspección.</p>';

    const html = `<!DOCTYPE html><html lang="es"><head><meta charset="utf-8"/>
      <title>Informe de Inspección</title>
      <style>
        * { box-sizing: border-box; }
        body { font-family: 'Segoe UI', Tahoma, sans-serif; color: #0f172a; margin: 28px; font-size: 13px; }
        h1 { margin: 0 0 4px; font-size: 20px; color: #0c4a6e; }
        h3 { margin: 18px 0 8px; font-size: 14px; color: #0f172a; }
        .sub { color: #64748b; margin-bottom: 18px; }
        .meta { display: grid; grid-template-columns: 1fr 1fr; gap: 8px 20px; margin-bottom: 18px; }
        .meta div { border-bottom: 1px solid #e2e8f0; padding: 6px 0; }
        .meta strong { display: block; font-size: 11px; color: #64748b; text-transform: uppercase; letter-spacing: .03em; }
        table { width: 100%; border-collapse: collapse; margin-top: 8px; }
        th, td { border: 1px solid #cbd5e1; padding: 8px 10px; }
        th { background: #0ea5e9; color: #fff; text-align: left; }
        .obs { margin-top: 16px; padding: 10px 12px; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; }
        .imgs { display: flex; flex-wrap: wrap; gap: 12px; margin-top: 10px; }
        .img-card { margin: 0; border: 1px solid #cbd5e1; border-radius: 8px; overflow: hidden; background: #fff; }
        .img-card img { display: block; width: 220px; height: 160px; object-fit: cover; }
        .muted { color: #94a3b8; font-size: 12px; margin: 6px 0 0; }
        .firma-wrap {
          margin-top: 36px;
          display: flex;
          justify-content: flex-end;
          page-break-inside: avoid;
        }
        .firma-box {
          width: 280px;
          text-align: center;
        }
        .firma-line {
          height: 70px;
          border-bottom: 1.5px solid #0f172a;
          margin-bottom: 8px;
        }
        .firma-label {
          font-size: 11px;
          color: #64748b;
          text-transform: uppercase;
          letter-spacing: .04em;
          margin-bottom: 4px;
        }
        .firma-name { font-weight: 600; font-size: 13px; }
        .firma-hint { font-size: 11px; color: #94a3b8; margin-top: 2px; }
        .footer { margin-top: 28px; font-size: 11px; color: #94a3b8; }
        @media print {
          body { margin: 12mm; }
          .no-print { display: none !important; }
          .img-card img { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
        }
      </style></head><body>
      <div class="no-print" style="margin-bottom:16px">
        <button onclick="window.print()" style="padding:8px 16px;background:#0ea5e9;color:#fff;border:0;border-radius:6px;cursor:pointer;font-weight:600">
          Imprimir / Guardar PDF
        </button>
      </div>
      <h1>MEDGLOBAL — Informe de Inspección de Botiquín</h1>
      <p class="sub">Documento generado el ${escHtml(new Date().toLocaleString())}</p>
      <div class="meta">
        <div><strong>Fecha de inspección</strong>${escHtml(fecha)}</div>
        <div><strong>Responsable</strong>${escHtml(responsable)}</div>
        <div><strong>Botiquín</strong>${escHtml(botLabel)}</div>
        <div><strong>Empresa</strong>${escHtml(bot?.empresa?.nombre || '—')}</div>
        <div><strong>Área</strong>${escHtml(bot?.area || '—')}</div>
        <div><strong>Ubicación</strong>${escHtml(bot?.ubicacion || '—')}</div>
      </div>
      <h3>Lista de insumos</h3>
      <table>
        <thead><tr><th>Insumo</th><th style="width:70px">Cant.</th><th style="width:100px">Estado</th><th style="width:100px">Reposición</th></tr></thead>
        <tbody>${filas}</tbody>
      </table>
      <div class="obs"><strong>Observaciones:</strong><br/>${escHtml(ins.observaciones || '—')}</div>
      <h3>Imagen / evidencias adjuntas</h3>
      <div class="imgs">${imgsHtml}</div>
      <div class="firma-wrap">
        <div class="firma-box">
          <div class="firma-label">Firma del responsable</div>
          <div class="firma-line"></div>
          <div class="firma-name">${escHtml(responsable)}</div>
          <div class="firma-hint">Responsable de la inspección</div>
        </div>
      </div>
      <p class="footer">MEDGLOBAL · Sistema de gestión médica · Inspección ${escHtml(ins.id || '')}</p>
      <script>
        function listoParaImprimir() {
          var imgs = Array.prototype.slice.call(document.images || []);
          if (!imgs.length) { setTimeout(function(){ window.print(); }, 200); return; }
          var pendientes = imgs.length;
          var done = function() {
            pendientes -= 1;
            if (pendientes <= 0) setTimeout(function(){ window.print(); }, 150);
          };
          imgs.forEach(function(img) {
            if (img.complete) return done();
            img.onload = done;
            img.onerror = done;
          });
          setTimeout(function(){ window.print(); }, 4000);
        }
        window.onload = listoParaImprimir;
      </script>
      </body></html>`;

    const w = window.open('', '_blank');
    if (!w) {
      alert('Permita ventanas emergentes para generar el PDF.');
      return;
    }
    w.document.open();
    w.document.write(html);
    w.document.close();
  };

  const saveInspeccion = async (e) => {
    e.preventDefault();
    if (soloLectura) return;
    if (!formInspeccion.botiquin_id) {
      alert('Seleccione un botiquín');
      return;
    }
    if (!formInspeccion.responsable_id) {
      alert('Seleccione el responsable de la inspección');
      return;
    }
    setGuardando(true);
    try {
      const nuevasUrls = await subirImagenesPendientes();
      const imagenes = [...(formInspeccion.imagenes || []), ...nuevasUrls];
      const payload = {
        botiquin_id: formInspeccion.botiquin_id,
        responsable_id: formInspeccion.responsable_id || null,
        fecha: formInspeccion.fecha
          ? new Date(formInspeccion.fecha).toISOString()
          : new Date().toISOString(),
        observaciones: formInspeccion.observaciones || null,
        imagenes,
        insumos: formInspeccion.insumos.map(i => ({
          medicamento_id: i.medicamento_id,
          cantidad: i.cantidad,
          estado: i.estado || 'CONFORME',
          reposicion: i.reposicion || 'NO',
        })),
      };

      const isEdit = formInspeccion.mode === 'edit' && formInspeccion.id;
      const res = await apiFetch(
        isEdit ? `/botiquin_inspecciones/${formInspeccion.id}` : '/botiquin_inspecciones/',
        {
          method: isEdit ? 'PUT' : 'POST',
          body: JSON.stringify(payload),
        }
      );
      if (!res.ok) throw new Error(await res.text());
      pendingImagenes.forEach(p => p.preview && URL.revokeObjectURL(p.preview));
      setPendingImagenes([]);
      setModalInspeccion(false);
      setTab('historial');
      loadInspecciones();
      loadBotiquinesList();
      loadCatalogos();
    } catch (err) {
      alert('Error al guardar inspección: ' + (err.message || err));
    } finally {
      setGuardando(false);
    }
  };

  const abrirReposicion = (insumo) => {
    if (!formInspeccion.botiquin_id) {
      alert('Seleccione un botiquín antes de reponer.');
      return;
    }
    const botiquin = botiquines.find(
      b => String(b.id) === String(formInspeccion.botiquin_id)
    );
    setReposicionModal({
      ...insumo,
      botiquin_codigo: botiquin?.codigo || formInspeccion.botiquin_id,
    });
    setReposicionCantidad(1);
  };

  const ejecutarReposicion = async () => {
    const cantidad = parseInt(reposicionCantidad, 10);
    if (!reposicionModal || !Number.isInteger(cantidad) || cantidad <= 0) {
      alert('Ingrese una cantidad válida.');
      return;
    }

    setReponiendo(true);
    try {
      const res = await apiFetch(
        `/botiquines/${encodeURIComponent(formInspeccion.botiquin_id)}/reponer`,
        {
          method: 'POST',
          body: JSON.stringify({
            medicamento_id: reposicionModal.medicamento_id,
            cantidad,
          }),
        }
      );
      const data = await res.json().catch(() => null);
      if (!res.ok) {
        throw new Error(data?.detail || 'No se pudo registrar la reposición');
      }

      setFormInspeccion(prev => ({
        ...prev,
        insumos: prev.insumos.map(i => (
          String(i.medicamento_id) === String(reposicionModal.medicamento_id)
            ? { ...i, reposicion: 'SI' }
            : i
        )),
      }));
      setReposicionModal(null);
      alert(
        `Reposición registrada. Se descontaron ${cantidad} unidad(es) del almacén para el botiquín ${reposicionModal.botiquin_codigo}.`
      );
    } catch (err) {
      alert('Error al reponer: ' + (err.message || err));
    } finally {
      setReponiendo(false);
    }
  };

  const deleteInspeccion = (id) => {
    if (!window.confirm('¿Eliminar esta inspección?')) return;
    apiFetch(`/botiquin_inspecciones/${id}`, { method: 'DELETE' })
      .then(() => loadInspecciones());
  };

  const buscarReporte = async () => {
    setLoadingReporte(true);
    try {
      const params = new URLSearchParams();
      if (reporteFiltros.empresa_id) params.append('empresa_id', reporteFiltros.empresa_id);
      if (reporteFiltros.botiquin_id) params.append('botiquin_id', reporteFiltros.botiquin_id);
      if ((reporteFiltros.areas || []).length) {
        params.append('area', reporteFiltros.areas.join(','));
      }
      if ((reporteFiltros.tipos_equipo || []).length) {
        params.append('tipo_equipo', reporteFiltros.tipos_equipo.join(','));
      }
      if (reporteFiltros.fecha_inicio) {
        params.append('fecha_inicio', reporteFiltros.fecha_inicio.toISOString().split('T')[0]);
      }
      if (reporteFiltros.fecha_fin) {
        params.append('fecha_fin', reporteFiltros.fecha_fin.toISOString().split('T')[0]);
      }
      const data = await apiJson(`/reportes/consumo-insumos-botiquin?${params.toString()}`);
      setReporte(data);
    } catch (err) {
      console.error(err);
      alert('Error al generar reporte: ' + err.message);
    } finally {
      setLoadingReporte(false);
    }
  };

  const exportarExcel = () => {
    if (!(reporte.insumos || []).length) return;
    const empresa = empresas.find(e => String(e.id) === String(reporteFiltros.empresa_id));
    const aoa = [
      ['Reporte de Consumo de Insumos de Botiquín'],
      ['Empresa: ' + (empresa ? empresa.nombre : 'Todas')],
      ['Área: ' + ((reporteFiltros.areas || []).length ? reporteFiltros.areas.join(', ') : 'Todas')],
      ['Tipo equipo: ' + ((reporteFiltros.tipos_equipo || []).length ? reporteFiltros.tipos_equipo.join(', ') : 'Todos')],
      [],
      ['Código', 'Insumo', 'Presentación', 'Tipo', ...reporte.rango_fechas, 'Cantidad', 'P. Unit.', 'Total (S/.)'],
    ];

    reporte.insumos.forEach(ins => {
      const row = [ins.codigo, ins.nombre, ins.presentacion, ins.tipo || ''];
      reporte.rango_fechas.forEach(f => row.push(ins.consumos[f] || 0));
      row.push(ins.sub_total_cantidad, ins.precio_und, ins.total_soles);
      aoa.push(row);
    });

    aoa.push([]);
    const baseCols = 4 + reporte.rango_fechas.length;
    const totSub = new Array(baseCols + 3).fill('');
    totSub[baseCols + 1] = 'SUB TOTAL';
    totSub[baseCols + 2] = reporte.totales.sub_total;
    const totIgv = new Array(baseCols + 3).fill('');
    totIgv[baseCols + 1] = 'IGV (18%)';
    totIgv[baseCols + 2] = reporte.totales.igv;
    const totGen = new Array(baseCols + 3).fill('');
    totGen[baseCols + 1] = 'TOTAL GENERAL';
    totGen[baseCols + 2] = reporte.totales.total;
    aoa.push(totSub, totIgv, totGen);

    const ws = XLSX.utils.aoa_to_sheet(aoa);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, 'Consumo Botiquín');
    XLSX.writeFile(wb, 'Reporte_Consumo_Insumos_Botiquin.xlsx');
  };

  return (
    <div>
      <div className="flex justify-between items-center mb-4" style={{ flexWrap: 'wrap', gap: 12 }}>
        <div>
          <h1 style={{ margin: 0 }}>Inspección</h1>
          <p style={{ margin: '4px 0 0', color: 'var(--text-muted)' }}>
            Registro de inspecciones de botiquín y consumo de insumos
          </p>
        </div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <button type="button" className="btn btn-primary" onClick={() => openNewInspeccion()}>
            <ClipboardCheck size={18} /> Registrar inspección
          </button>
        </div>
      </div>

      <div className="flex gap-2 mb-4" style={{ flexWrap: 'wrap' }}>
        {[
          { id: 'botiquines', label: 'Botiquines', icon: Package },
          { id: 'historial', label: 'Historial', icon: History },
          { id: 'reporte', label: 'Consumo de insumos', icon: Download },
        ].map(t => (
          <button
            key={t.id}
            type="button"
            className={`btn ${tab === t.id ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setTab(t.id)}
          >
            <t.icon size={16} style={{ marginRight: 6 }} />
            {t.label}
          </button>
        ))}
      </div>

      {tab === 'botiquines' && (
        <div className="glass-panel mb-4" style={{ padding: 16 }}>
          <div className="flex items-center mb-3" style={{ gap: 8 }}>
            <Filter size={18} />
            <strong>Filtros</strong>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12 }}>
            <div className="form-group" style={{ margin: 0 }}>
              <label className="form-label">Buscar</label>
              <div style={{ position: 'relative' }}>
                <Search size={16} style={{ position: 'absolute', left: 10, top: 12, opacity: 0.5 }} />
                <input
                  className="form-control"
                  style={{ paddingLeft: 32 }}
                  placeholder="Código, tipo, empresa..."
                  value={botFilters.search}
                  onChange={e => setBotFilters({ ...botFilters, search: e.target.value })}
                />
              </div>
            </div>
            <div className="form-group" style={{ margin: 0 }}>
              <label className="form-label">Empresa</label>
              <Select
                styles={selectStyles}
                options={empresaOptions}
                isClearable
                placeholder="Buscar empresa..."
                value={empresaOptions.find(o => o.value === botFilters.empresa_id) || null}
                onChange={opt => setBotFilters({ ...botFilters, empresa_id: opt ? opt.value : '' })}
                noOptionsMessage={() => 'Sin resultados'}
              />
            </div>
            <div className="form-group" style={{ margin: 0 }}>
              <label className="form-label">Estado</label>
              <select
                className="form-control"
                value={botFilters.estado}
                onChange={e => setBotFilters({ ...botFilters, estado: e.target.value })}
              >
                <option value="">Todos</option>
                <option value="ACTIVO">Activo</option>
                <option value="INACTIVO">Inactivo</option>
              </select>
            </div>
          </div>
        </div>
      )}

      {tab === 'botiquines' && (
        <div className="glass-panel" style={{ overflowX: 'auto' }}>
          <table className="table">
            <thead>
              <tr>
                <th>Código</th>
                <th>Fecha</th>
                <th>Empresa</th>
                <th>Vehículo</th>
                <th>Ubicación</th>
                <th>Última inspección</th>
                <th style={{ width: 168, textAlign: 'center', whiteSpace: 'nowrap' }}>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {botiquinesFiltrados.length === 0 && (
                <tr>
                  <td colSpan={7} style={{ textAlign: 'center', opacity: 0.7 }}>
                    Sin botiquines registrados
                  </td>
                </tr>
              )}
              {botiquinesFiltrados.map(b => {
                const vehiculoLabel = b.vehiculo
                  || resumenVehiculo({
                    marca: b.marca,
                    modelo: b.modelo,
                    serie: b.serie,
                    placa: b.placa,
                  })
                  || '—';
                const tieneInspeccion = !!b.ultima_inspeccion;
                return (
                  <tr key={b.id}>
                    <td>{b.codigo || '—'}</td>
                    <td>
                      {b.fecha_creacion
                        ? new Date(b.fecha_creacion).toLocaleDateString()
                        : (b.created_at ? new Date(b.created_at).toLocaleDateString() : '—')}
                    </td>
                    <td>{b.empresa?.nombre || '—'}</td>
                    <td>{vehiculoLabel}</td>
                    <td>{b.ubicacion || '—'}</td>
                    <td>
                      {tieneInspeccion
                        ? new Date(b.ultima_inspeccion).toLocaleString()
                        : <span style={{ opacity: 0.55 }}>Sin inspección</span>}
                    </td>
                    <td className="insp-actions-cell">
                      <div className="insp-actions insp-actions--toolbar" role="group" aria-label="Acciones">
                        <button
                          type="button"
                          className="action-btn action-btn--primary"
                          title="Nueva inspección"
                          onClick={() => openNewInspeccion(b.id)}
                        >
                          <ClipboardCheck size={16} />
                        </button>
                        <button
                          type="button"
                          className="action-btn view"
                          title={tieneInspeccion ? 'Ver última inspección' : 'Sin inspecciones'}
                          disabled={!tieneInspeccion}
                          onClick={() => verUltimaInspeccion(b.id)}
                        >
                          <Eye size={16} />
                        </button>
                        <button
                          type="button"
                          className="action-btn edit"
                          title={tieneInspeccion ? 'Editar última inspección' : 'Sin inspecciones'}
                          disabled={!tieneInspeccion}
                          onClick={() => editarUltimaInspeccion(b.id)}
                        >
                          <Edit2 size={16} />
                        </button>
                        <button
                          type="button"
                          className="action-btn pdf"
                          title={tieneInspeccion ? 'PDF / Reporte para firmar' : 'Sin inspecciones'}
                          disabled={!tieneInspeccion}
                          onClick={() => pdfUltimaInspeccion(b.id)}
                        >
                          <FileText size={16} />
                        </button>
                        <button
                          type="button"
                          className="action-btn delete"
                          title={tieneInspeccion ? 'Eliminar última inspección' : 'Sin inspecciones'}
                          disabled={!tieneInspeccion}
                          onClick={() => eliminarUltimaInspeccion(b.id)}
                        >
                          <Trash2 size={16} />
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {tab === 'historial' && (
        <div className="glass-panel mb-4" style={{ padding: 16 }}>
          <div className="flex items-center mb-3" style={{ gap: 8 }}>
            <Filter size={18} />
            <strong>Filtros</strong>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12 }}>
            <div className="form-group" style={{ margin: 0 }}>
              <label className="form-label">Buscar</label>
              <div style={{ position: 'relative' }}>
                <Search size={16} style={{ position: 'absolute', left: 10, top: 12, opacity: 0.5 }} />
                <input
                  className="form-control"
                  style={{ paddingLeft: 32 }}
                  placeholder="Botiquín, ubicación, tipo..."
                  value={filters.search}
                  onChange={e => setFilters({ ...filters, search: e.target.value })}
                />
              </div>
            </div>
            <div className="form-group" style={{ margin: 0 }}>
              <label className="form-label">Empresa</label>
              <Select
                styles={selectStyles}
                options={empresaOptions}
                isClearable
                placeholder="Buscar empresa..."
                value={empresaOptions.find(o => o.value === filters.empresa_id) || null}
                onChange={opt => setFilters({ ...filters, empresa_id: opt ? opt.value : '' })}
                noOptionsMessage={() => 'Sin resultados'}
              />
            </div>
          </div>
        </div>
      )}

      {tab === 'historial' && (
        <div className="glass-panel" style={{ overflowX: 'auto' }}>
          <table className="table">
            <thead>
              <tr>
                <th>Fecha</th>
                <th>Botiquín</th>
                <th>Área</th>
                <th>Empresa</th>
                <th>Responsable</th>
                <th style={{ width: 140, textAlign: 'center' }}>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {inspecciones.length === 0 && (
                <tr><td colSpan={6} style={{ textAlign: 'center', opacity: 0.7 }}>Sin inspecciones</td></tr>
              )}
              {inspecciones.map(ins => (
                <tr key={ins.id}>
                  <td>{ins.fecha ? new Date(ins.fecha).toLocaleString() : '—'}</td>
                  <td>
                    {ins.botiquin
                      ? `${ins.botiquin.codigo ? ins.botiquin.codigo + ' · ' : ''}${ins.botiquin.tipo_botiquin?.nombre || ins.botiquin.tipo_equipo} · ${ins.botiquin.ubicacion || ''}`
                      : '—'}
                  </td>
                  <td>{ins.botiquin?.area || '—'}</td>
                  <td>{ins.botiquin?.empresa?.nombre || '—'}</td>
                  <td>
                    {ins.responsable
                      ? `${ins.responsable.nombre || ''} ${ins.responsable.apellidos || ''}`.trim()
                      : '—'}
                  </td>
                  <td style={{ textAlign: 'center' }}>
                    <div className="insp-actions">
                      <button type="button" className="action-btn view" title="Ver" onClick={() => openViewInspeccion(ins)}>
                        <Eye size={17} />
                      </button>
                      <button type="button" className="action-btn edit" title="Editar" onClick={() => openEditInspeccion(ins)}>
                        <Edit2 size={17} />
                      </button>
                      <button type="button" className="action-btn pdf" title="PDF / Imprimir" onClick={() => imprimirInspeccion(ins)}>
                        <FileText size={17} />
                      </button>
                      <button type="button" className="action-btn delete" title="Eliminar" onClick={() => deleteInspeccion(ins.id)}>
                        <Trash2 size={17} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tab === 'reporte' && (
        <div>
          <div className="glass-panel mb-4" style={{ padding: 16 }}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12, marginBottom: 16 }}>
              <div className="form-group" style={{ margin: 0 }}>
                <label className="form-label">Empresa</label>
                <Select
                  styles={selectStyles}
                  options={empresaOptions}
                  isClearable
                  placeholder="Todas..."
                  value={empresaOptions.find(o => o.value === reporteFiltros.empresa_id) || null}
                  onChange={opt => setReporteFiltros({ ...reporteFiltros, empresa_id: opt ? opt.value : '' })}
                />
              </div>
              <div className="form-group" style={{ margin: 0 }}>
                <label className="form-label">Botiquín</label>
                <Select
                  styles={selectStyles}
                  options={botiquinOptions}
                  isClearable
                  placeholder="Todos..."
                  value={botiquinOptions.find(o => o.value === reporteFiltros.botiquin_id) || null}
                  onChange={opt => setReporteFiltros({ ...reporteFiltros, botiquin_id: opt ? opt.value : '' })}
                />
              </div>
              <div className="form-group" style={{ margin: 0 }}>
                <label className="form-label">Área</label>
                <Select
                  styles={selectStyles}
                  isMulti
                  isClearable
                  isSearchable
                  closeMenuOnSelect={false}
                  hideSelectedOptions={false}
                  options={areaOptions}
                  placeholder="Todas..."
                  noOptionsMessage={() => 'Sin resultados'}
                  value={areaOptions.filter(o => (reporteFiltros.areas || []).includes(o.value))}
                  onChange={(opts) => setReporteFiltros({
                    ...reporteFiltros,
                    areas: (opts || []).map(o => o.value),
                  })}
                />
              </div>
              <div className="form-group" style={{ margin: 0 }}>
                <label className="form-label">Tipo de equipo</label>
                <Select
                  styles={selectStyles}
                  isMulti
                  isClearable
                  isSearchable
                  closeMenuOnSelect={false}
                  hideSelectedOptions={false}
                  options={tipoEquipoOptions}
                  placeholder="Todos..."
                  noOptionsMessage={() => 'Sin resultados'}
                  value={tipoEquipoOptions.filter(o => (reporteFiltros.tipos_equipo || []).includes(o.value))}
                  onChange={(opts) => setReporteFiltros({
                    ...reporteFiltros,
                    tipos_equipo: (opts || []).map(o => o.value),
                  })}
                />
              </div>
              <div className="form-group" style={{ margin: 0 }}>
                <label className="form-label">Desde</label>
                <DatePicker
                  selected={reporteFiltros.fecha_inicio}
                  onChange={d => setReporteFiltros({ ...reporteFiltros, fecha_inicio: d })}
                  dateFormat="dd/MM/yyyy"
                  className="form-control"
                  isClearable
                  placeholderText="Fecha inicio"
                />
              </div>
              <div className="form-group" style={{ margin: 0 }}>
                <label className="form-label">Hasta</label>
                <DatePicker
                  selected={reporteFiltros.fecha_fin}
                  onChange={d => setReporteFiltros({ ...reporteFiltros, fecha_fin: d })}
                  dateFormat="dd/MM/yyyy"
                  className="form-control"
                  isClearable
                  placeholderText="Fecha fin"
                />
              </div>
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              <button type="button" className="btn btn-primary" onClick={buscarReporte} disabled={loadingReporte}>
                <Search size={16} />
                {loadingReporte ? 'Generando...' : 'Generar reporte'}
              </button>
              <button type="button" className="btn btn-secondary" onClick={exportarExcel} disabled={!(reporte.insumos || []).length}>
                <Download size={16} /> Exportar Excel
              </button>
            </div>
          </div>

          <div className="glass-panel" style={{ overflowX: 'auto' }}>
            <table className="table">
              <thead>
                <tr>
                  <th>Código</th>
                  <th>Insumo</th>
                  <th>Presentación</th>
                  {(reporte.rango_fechas || []).map(f => <th key={f}>{f}</th>)}
                  <th>Cantidad</th>
                  <th>P. Unit. (S/.)</th>
                  <th>Total (S/.)</th>
                </tr>
              </thead>
              <tbody>
                {(reporte.insumos || []).length === 0 && (
                  <tr>
                    <td colSpan={6 + (reporte.rango_fechas || []).length} style={{ textAlign: 'center', opacity: 0.7 }}>
                      Sin datos. Genere el reporte con los filtros deseados.
                    </td>
                  </tr>
                )}
                {(reporte.insumos || []).map(ins => (
                  <tr key={ins.id}>
                    <td>{ins.codigo}</td>
                    <td>{ins.nombre}</td>
                    <td>{ins.presentacion}</td>
                    {(reporte.rango_fechas || []).map(f => (
                      <td key={f}>{ins.consumos?.[f] || 0}</td>
                    ))}
                    <td>{ins.sub_total_cantidad}</td>
                    <td>{Number(ins.precio_und || 0).toFixed(2)}</td>
                    <td>{Number(ins.total_soles || 0).toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
              {(reporte.insumos || []).length > 0 && (
                <tfoot>
                  <tr>
                    <td colSpan={3 + (reporte.rango_fechas || []).length} style={{ textAlign: 'right', fontWeight: 600 }}>Subtotal</td>
                    <td colSpan={2}>{Number(reporte.totales?.sub_total || 0).toFixed(2)}</td>
                  </tr>
                  <tr>
                    <td colSpan={3 + (reporte.rango_fechas || []).length} style={{ textAlign: 'right', fontWeight: 600 }}>IGV (18%)</td>
                    <td colSpan={2}>{Number(reporte.totales?.igv || 0).toFixed(2)}</td>
                  </tr>
                  <tr>
                    <td colSpan={3 + (reporte.rango_fechas || []).length} style={{ textAlign: 'right', fontWeight: 700 }}>Total general</td>
                    <td colSpan={2} style={{ fontWeight: 700 }}>{Number(reporte.totales?.total || 0).toFixed(2)}</td>
                  </tr>
                </tfoot>
              )}
            </table>
          </div>
        </div>
      )}

      {modalInspeccion && (
        <div className="modal-overlay">
          <div
            className="modal-content"
            style={{
              maxWidth: 980,
              width: '96%',
              maxHeight: '94vh',
              display: 'flex',
              flexDirection: 'column',
              overflow: 'hidden',
            }}
          >
            <div className="modal-header" style={{ flexShrink: 0 }}>
              <h3>
                {formInspeccion.mode === 'view'
                  ? 'Ver inspección'
                  : formInspeccion.mode === 'edit'
                    ? 'Editar inspección'
                    : 'Registrar inspección'}
              </h3>
              <button className="close-btn" type="button" onClick={() => setModalInspeccion(false)}><X size={24} /></button>
            </div>
            <form onSubmit={saveInspeccion} style={{ display: 'flex', flexDirection: 'column', minHeight: 0, flex: 1 }}>
              <div className="modal-body" style={{ overflowY: 'auto', flex: 1, minHeight: 0 }}>
                <div className="form-group">
                  <label className="form-label">Fecha (automática)</label>
                  <DatePicker
                    selected={formInspeccion.fecha}
                    onChange={d => setFormInspeccion({ ...formInspeccion, fecha: d || new Date() })}
                    showTimeSelect
                    dateFormat="dd/MM/yyyy HH:mm"
                    className="form-control"
                    disabled={soloLectura}
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">Botiquín</label>
                  <Select
                    styles={selectStyles}
                    options={botiquinOptions}
                    placeholder="Buscar botiquín..."
                    value={botiquinOptions.find(o => o.value === formInspeccion.botiquin_id) || null}
                    onChange={opt => {
                      if (soloLectura) return;
                      if (formInspeccion.mode === 'edit') {
                        setFormInspeccion(prev => ({ ...prev, botiquin_id: opt ? opt.value : '' }));
                        if (opt) cargarInsumosDeBotiquin(opt.value);
                      } else {
                        cargarInsumosDeBotiquin(opt ? opt.value : '');
                      }
                    }}
                    isDisabled={soloLectura}
                    noOptionsMessage={() => 'Sin botiquines'}
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">Responsable de la inspección</label>
                  <Select
                    styles={selectStyles}
                    options={personalOptions}
                    placeholder="Buscar personal de salud..."
                    value={personalOptions.find(o => o.value === formInspeccion.responsable_id) || null}
                    onChange={opt => {
                      if (soloLectura) return;
                      setFormInspeccion({ ...formInspeccion, responsable_id: opt ? opt.value : '' });
                    }}
                    isDisabled={soloLectura}
                    noOptionsMessage={() => 'Sin resultados'}
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">
                    Lista de insumos
                    {cargandoInsumos && <span style={{ marginLeft: 8, opacity: 0.7, fontWeight: 400 }}>(cargando del tipo...)</span>}
                  </label>
                  <p style={{ margin: '0 0 10px', fontSize: '0.88rem', opacity: 0.7 }}>
                    Los insumos y cantidades se cargan según el tipo del botiquín. Indique el estado de cada ítem.
                  </p>
                  {formInspeccion.insumos.length > 0 ? (
                    <div className="table-container" style={{ marginTop: 14, overflowX: 'auto' }}>
                      <table className="data-table" style={{ width: '100%', minWidth: 560 }}>
                        <thead>
                          <tr>
                            <th style={{ textAlign: 'left' }}>Insumo</th>
                            <th style={{ width: 90 }}>Cant.</th>
                            <th style={{ width: 160 }}>Estado</th>
                            <th style={{ width: 110 }}>Reposición</th>
                          </tr>
                        </thead>
                        <tbody>
                          {formInspeccion.insumos.map(i => (
                            <tr key={i.medicamento_id}>
                              <td style={{ textAlign: 'left', verticalAlign: 'middle' }}>{i.label}</td>
                              <td style={{ textAlign: 'center', verticalAlign: 'middle' }}>{i.cantidad}</td>
                              <td style={{ textAlign: 'center', verticalAlign: 'middle' }}>
                                {soloLectura ? (
                                  ESTADO_LABEL[i.estado] || i.estado || '—'
                                ) : (
                                  <select
                                    className="form-control"
                                    value={i.estado}
                                    onChange={e => updateInsumoField(i.medicamento_id, 'estado', e.target.value)}
                                  >
                                    {ESTADOS_INSUMO.map(opt => (
                                      <option key={opt.value} value={opt.value}>{opt.label}</option>
                                    ))}
                                  </select>
                                )}
                              </td>
                              <td style={{ textAlign: 'center', verticalAlign: 'middle' }}>
                                {soloLectura ? (
                                  (i.reposicion || 'NO') === 'SI' ? 'Sí' : 'No'
                                ) : (
                                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8 }}>
                                    {(i.reposicion || 'NO') === 'SI' && (
                                      <span style={{ color: '#22c55e', fontSize: '0.82rem', fontWeight: 600 }}>
                                        Repuesto
                                      </span>
                                    )}
                                    <button
                                      type="button"
                                      className="btn btn-primary btn-sm"
                                      onClick={() => abrirReposicion(i)}
                                    >
                                      <PackagePlus size={15} /> Reponer
                                    </button>
                                  </div>
                                )}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ) : (
                    <p style={{ marginTop: 10, opacity: 0.6, fontSize: '0.9rem' }}>
                      {formInspeccion.botiquin_id
                        ? 'Este botiquín no tiene tipo con insumos definidos.'
                        : 'Seleccione un botiquín para cargar sus insumos.'}
                    </p>
                  )}
                </div>
                <div className="form-group">
                  <label className="form-label">Imágenes</label>
                  {!soloLectura && (
                    <label
                      className="btn btn-secondary btn-sm"
                      style={{ display: 'inline-flex', cursor: 'pointer', width: 'fit-content' }}
                    >
                      <ImagePlus size={16} /> Adjuntar imágenes
                      <input
                        type="file"
                        accept="image/*"
                        multiple
                        style={{ display: 'none' }}
                        onChange={onSelectImagenes}
                      />
                    </label>
                  )}
                  <p style={{ margin: '8px 0 0', fontSize: '0.85rem', opacity: 0.65 }}>
                    JPG, PNG, WEBP u otras imágenes (máx. 8 MB c/u).
                  </p>
                  {((formInspeccion.imagenes || []).length > 0 || pendingImagenes.length > 0) ? (
                    <div className="insp-img-grid">
                      {(formInspeccion.imagenes || []).map(url => (
                        <div className="insp-img-thumb" key={url}>
                          <img src={assetUrl(url)} alt="Adjunto" />
                          {!soloLectura && (
                            <button
                              type="button"
                              className="insp-img-remove"
                              title="Quitar"
                              onClick={() => removeImagenExistente(url)}
                            >
                              <X size={14} />
                            </button>
                          )}
                        </div>
                      ))}
                      {pendingImagenes.map(p => (
                        <div className="insp-img-thumb" key={p.key}>
                          <img src={p.preview} alt="Nueva" />
                          <button
                            type="button"
                            className="insp-img-remove"
                            title="Quitar"
                            onClick={() => removeImagenPendiente(p.key)}
                          >
                            <X size={14} />
                          </button>
                        </div>
                      ))}
                    </div>
                  ) : (
                    soloLectura && (
                      <p style={{ marginTop: 8, opacity: 0.6, fontSize: '0.9rem' }}>Sin imágenes adjuntas.</p>
                    )
                  )}
                </div>
                <div className="form-group">
                  <label className="form-label">Observaciones</label>
                  <textarea
                    className="form-control"
                    rows={2}
                    value={formInspeccion.observaciones}
                    disabled={soloLectura}
                    onChange={e => setFormInspeccion({ ...formInspeccion, observaciones: e.target.value })}
                  />
                </div>
              </div>
              <div className="modal-footer" style={{ flexShrink: 0 }}>
                <button type="button" className="btn btn-secondary" onClick={() => setModalInspeccion(false)}>
                  <X size={16} /> {soloLectura ? 'Cerrar' : 'Cancelar'}
                </button>
                {!soloLectura && (
                  <button type="submit" className="btn btn-primary" disabled={guardando}>
                    <Save size={16} /> {guardando ? 'Guardando...' : 'Guardar inspección'}
                  </button>
                )}
                {soloLectura && formInspeccion.id && (
                  <button
                    type="button"
                    className="btn btn-primary"
                    onClick={() => {
                      const found = inspecciones.find(x => x.id === formInspeccion.id);
                      if (found) imprimirInspeccion(found);
                    }}
                  >
                    <FileText size={16} /> PDF
                  </button>
                )}
              </div>
            </form>
          </div>
        </div>
      )}

      {reposicionModal && (
        <div className="modal-overlay" style={{ zIndex: 1100 }}>
          <div className="modal-content" style={{ maxWidth: 480, width: '94%' }}>
            <div className="modal-header">
              <h3>Reponer insumo</h3>
              <button
                className="close-btn"
                type="button"
                onClick={() => !reponiendo && setReposicionModal(null)}
              >
                <X size={24} />
              </button>
            </div>
            <div className="modal-body">
              <div style={{ marginBottom: 16 }}>
                <strong>{reposicionModal.label}</strong>
                <p style={{ margin: '6px 0 0', color: 'var(--text-muted)' }}>
                  Botiquín: {reposicionModal.botiquin_codigo}
                </p>
              </div>
              <div className="form-group">
                <label className="form-label">Cantidad a reponer</label>
                <input
                  type="number"
                  min={1}
                  step={1}
                  className="form-control"
                  value={reposicionCantidad}
                  onChange={e => setReposicionCantidad(e.target.value)}
                  autoFocus
                  disabled={reponiendo}
                />
              </div>
              <p style={{ margin: 0, fontSize: '0.86rem', color: 'var(--text-muted)' }}>
                Al ejecutar se registrará inmediatamente una salida del almacén con la observación
                {' '}“Reposición botiquín {reposicionModal.botiquin_codigo}”.
              </p>
            </div>
            <div className="modal-footer">
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => setReposicionModal(null)}
                disabled={reponiendo}
              >
                <X size={16} /> Cancelar
              </button>
              <button
                type="button"
                className="btn btn-primary"
                onClick={ejecutarReposicion}
                disabled={reponiendo}
              >
                <PackagePlus size={16} /> {reponiendo ? 'Reponiendo...' : 'Ejecutar reposición'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default InspeccionBotiquin;
