/**
 * URL base de la API.
 * - Build: usa REACT_APP_API_URL si está definida.
 * - En el navegador: si no es localhost, usa el mismo host con puerto 8000.
 * - Por defecto (también desde localhost): servidor conocido para evitar ERR_CONNECTION_REFUSED.
 */
// const SERVER_API_URL = 'http://172.16.222.222:5001';
const SERVER_API_URL = ''; // Usar proxy de package.json en desarrollo

function getApiBaseUrl() {
  if (typeof process !== 'undefined' && process.env && process.env.REACT_APP_API_URL) {
    return process.env.REACT_APP_API_URL.replace(/\/$/, '');
  }
  if (typeof window !== 'undefined' && window.location && window.location.hostname) {
    const host = window.location.hostname;
    if (host !== 'localhost' && host !== '127.0.0.1') {
      return `http://${host}:8000`;
    }
  }
  return SERVER_API_URL;
}

// export const API_BASE_URL = getApiBaseUrl();
// Detectar si estamos en la subcarpeta /cbd_monitor (dominio MOPC) o en la raíz (IP directa)
const pathPrefix = window.location.pathname.includes('/cbd_monitor') ? '/cbd_monitor' : '';
export const API_BASE_URL = window.location.origin + pathPrefix + '/api';