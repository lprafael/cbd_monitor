/**
 * URL base de la API.
 * - Build: usa REACT_APP_API_URL si está definida.
 * - En el navegador: si la app no se abre en localhost, usa el mismo host con puerto 5001.
 * Así la versión Docker (p. ej. http://172.16.222.222:8080) llama al backend sin rebuild.
 */
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
  return 'http://localhost:8000';
}

export const API_BASE_URL = getApiBaseUrl();
