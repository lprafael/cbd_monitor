// authFetch.js
// Helper para fetch que maneja autenticación JWT

export async function authFetch(url, options = {}) {
  // Obtener el token actual
  let token = localStorage.getItem('token');
  
  // Configurar headers iniciales
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
    ...(token ? { 'Authorization': `Bearer ${token}` } : {})
  };

  // Construir la URL completa
  const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://172.16.222.222:5001';
  const requestUrl = url.startsWith('http') ? url : `${API_BASE_URL}${url.startsWith('/') ? '' : '/'}${url}`;
  
  // Realizar la petición
  let response = await fetch(requestUrl, { ...options, headers });

  // Si recibimos 401, limpiar y redirigir
  if (response.status === 401) {
    localStorage.removeItem('token');
    localStorage.removeItem('refreshToken');
    localStorage.removeItem('user');
    window.location.reload();
    return Promise.reject(new Error('Sesión expirada. Por favor inicia sesión nuevamente.'));
  }

  // Si hay un error diferente a 401, manejarlo
  if (!response.ok) {
    const error = new Error(`Error ${response.status}: ${response.statusText}`);
    error.response = response;
    error.status = response.status;
    throw error;
  }

  return response;
}
