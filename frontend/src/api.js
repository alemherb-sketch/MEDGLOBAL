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
  return response;
}

/** Como apiFetch, pero ya parsea el JSON y lanza un Error legible si la
 * respuesta no fue exitosa -- para el patron .then(res => res.json())
 * que ya usan las paginas hoy. */
export async function apiJson(path, options = {}) {
  const response = await apiFetch(path, options);
  if (!response.ok) {
    const text = await response.text().catch(() => '');
    throw new Error(text || `Error ${response.status}`);
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
  const response = await fetch(API_URL + '/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body,
  });
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
