import { API_URL } from './config';

const TOKEN_KEY = 'medglobal_token';

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

export function isAuthenticated() {
  return !!getToken();
}

/** Reemplazo casi directo de fetch(API_URL + path, options): agrega el
 * header Authorization y, si el servidor responde 401 (sesion vencida o
 * ausente), limpia el token y manda a /login en vez de dejar que cada
 * pagina lo maneje por su cuenta. */
export async function apiFetch(path, options = {}) {
  const token = getToken();
  const headers = { ...(options.headers || {}) };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  const isFormData = typeof FormData !== 'undefined' && options.body instanceof FormData;
  if (options.body && !isFormData && !headers['Content-Type']) {
    headers['Content-Type'] = 'application/json';
  }

  const response = await fetch(API_URL + path, { ...options, headers });
  if (response.status === 401) {
    clearToken();
    if (!window.location.hash.startsWith('#/login')) {
      window.location.hash = '#/login';
    }
  }
  if (response.status === 403) await _redirigirSiFaltaLicencia(response);
  return response;
}

/** El backend de escritorio responde 403 con motivo "sin_licencia" cuando la
 * PC no esta habilitada. Sin esto, ese 403 se mostraba como un error generico
 * en cada pantalla y no habia forma de llegar a la activacion.
 *
 * Se lee sobre una copia: quien llamo a apiFetch todavia tiene que poder
 * consumir el cuerpo de la respuesta original. Y solo redirige por ese motivo
 * concreto, porque 403 tambien es "se requiere rol de administrador". */
async function _redirigirSiFaltaLicencia(response) {
  const datos = await response.clone().json().catch(() => ({}));
  if (datos?.motivo !== 'sin_licencia') return false;
  if (!window.location.hash.startsWith('#/activar-licencia')) {
    window.location.hash = '#/activar-licencia';
  }
  return true;
}

/** Saca el mensaje para el usuario de una respuesta con error.
 *
 * FastAPI devuelve {"detail": "..."} y las paginas muestran `err.message` en un
 * alert. Sin esto el usuario veia el JSON entero en pantalla
 * ({"detail":"Stock insuficiente..."}) en vez de la frase. Cuando `detail` es
 * la lista de errores de validacion de Pydantic, se arma una linea legible en
 * lugar de volcar la estructura. */
export async function mensajeDeError(response) {
  const texto = await response.text().catch(() => '');
  if (!texto) return `Error ${response.status}`;
  try {
    const { detail } = JSON.parse(texto);
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail)) {
      const campos = detail
        .map((d) => (Array.isArray(d?.loc) ? d.loc[d.loc.length - 1] : null))
        .filter(Boolean);
      return campos.length
        ? `Revise estos campos: ${campos.join(', ')}.`
        : 'Los datos enviados no son válidos.';
    }
  } catch {
    // No era JSON: se muestra el cuerpo tal cual.
  }
  return texto;
}

/** Como apiFetch, pero ya parsea el JSON y lanza un Error legible si la
 * respuesta no fue exitosa -- para el patron .then(res => res.json())
 * que ya usan las paginas hoy. */
export async function apiJson(path, options = {}) {
  const response = await apiFetch(path, options);
  if (!response.ok) {
    throw new Error(await mensajeDeError(response));
  }
  const text = await response.text();
  return text ? JSON.parse(text) : null;
}

/** Login: el backend espera x-www-form-urlencoded (OAuth2PasswordRequestForm
 * de FastAPI), no JSON -- por eso es una funcion aparte de apiFetch/apiJson. */
export async function login(username, password) {
  const body = new URLSearchParams();
  body.set('username', username);
  body.set('password', password);
  let response;
  try {
    response = await fetch(API_URL + '/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body,
    });
  } catch {
    throw new Error(
      'No se pudo contactar el servidor local. Cierre MEDGLOBAL y vuelve a abrirlo. Si el problema continua, reinstalle la version de escritorio.'
    );
  }
  // Un 403 por licencia NO es una clave equivocada. Decir "usuario o
  // contraseña incorrectos" ahi mandaba al usuario a probar claves una y otra
  // vez por un problema que no tenia nada que ver.
  if (response.status === 403 && (await _redirigirSiFaltaLicencia(response))) {
    const datos = await response.json().catch(() => ({}));
    throw new Error(datos.detail || 'Esta PC no tiene una licencia activa.');
  }
  if (!response.ok) {
    throw new Error('Usuario o contraseña incorrectos');
  }
  const data = await response.json();
  setToken(data.access_token);
  return data;
}

export function logout() {
  clearToken();
  window.location.hash = '#/login';
}
