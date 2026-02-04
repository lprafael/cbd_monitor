/**
 * URL base de la API.
 * - Build: usa REACT_APP_API_URL si está definida.
 * - En el navegador: si no es localhost, usa el mismo host con puerto 5001.
 * - Por defecto (también desde localhost): servidor conocido para evitar ERR_CONNECTION_REFUSED.
 */
const SERVER_API_URL = 'http://172.16.222.222:5001';

function getApiBaseUrl() {
  if (typeof process !== 'undefined' && process.env && process.env.REACT_APP_API_URL) {
    return process.env.REACT_APP_API_URL.replace(/\/$/, '');
  }
  if (typeof window !== 'undefined' && window.location && window.location.hostname) {
    const host = window.location.hostname;
    if (host !== 'localhost' && host !== '127.0.0.1') {
      return `http://${host}:5001`;
    }
  }
  return SERVER_API_URL;
}

export const API_BASE_URL = getApiBaseUrl();
