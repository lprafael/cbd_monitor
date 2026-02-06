import React, { useState, useEffect } from 'react';
import { GoogleOAuthProvider } from '@react-oauth/google';
import Login from './Login';
import App from '../App';
import { API_BASE_URL } from '../config';

const AuthWrapper = () => {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [loading, setLoading] = useState(true);
  const [user, setUser] = useState(null);
  const [googleClientId, setGoogleClientId] = useState('');

  // Obtener Google Client ID del backend
  useEffect(() => {
    const fetchGoogleClientId = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/auth/google-client-id`);
        if (response.ok) {
          const data = await response.json();
          setGoogleClientId(data.google_client_id || '');
        }
      } catch (error) {
        console.error('Error obteniendo Google Client ID:', error);
      }
    };
    fetchGoogleClientId();
  }, []);

  // Verificar si hay un token válido al cargar
  useEffect(() => {
    const token = localStorage.getItem('token');
    const userData = localStorage.getItem('user');

    if (token && userData) {
      // Verificar si el token es válido haciendo una petición al backend
      verifyToken(token);
    } else {
      setLoading(false);
    }
  }, []);

  const verifyToken = async (token) => {
    try {
      const response = await fetch(`${API_BASE_URL}/auth/me`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        const userData = await response.json();
        setUser(userData);
        setIsAuthenticated(true);
      } else {
        // Token inválido, limpiar localStorage
        localStorage.removeItem('token');
        localStorage.removeItem('refreshToken');
        localStorage.removeItem('user');
      }
    } catch (error) {
      console.error('Error verificando token:', error);
      localStorage.removeItem('token');
      localStorage.removeItem('refreshToken');
      localStorage.removeItem('user');
    } finally {
      setLoading(false);
    }
  };

  const handleLogin = (data) => {
    setUser(data.user);
    setIsAuthenticated(true);
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('refreshToken');
    localStorage.removeItem('user');
    setUser(null);
    setIsAuthenticated(false);
  };

  // Usar Google Client ID del backend o del .env del frontend como fallback
  const GOOGLE_CLIENT_ID = googleClientId || process.env.REACT_APP_GOOGLE_CLIENT_ID || '';

  // Solo usar GoogleOAuthProvider si hay un Client ID real (evita errores 403 y "client ID not found")
  const LoginComponent = GOOGLE_CLIENT_ID ? (
    <GoogleOAuthProvider clientId={GOOGLE_CLIENT_ID}>
      <Login onLogin={handleLogin} googleClientId={GOOGLE_CLIENT_ID} />
    </GoogleOAuthProvider>
  ) : (
    <Login onLogin={handleLogin} googleClientId="" />
  );

  if (loading) {
    return (
      <div style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        height: '100vh',
        background: 'linear-gradient(135deg, #1e3a8a 0%, #2563eb 100%)'
      }}>
        <div style={{ color: 'white', fontSize: '1.2rem' }}>Cargando...</div>
      </div>
    );
  }

  return (
    <>
      {!isAuthenticated ? (
        LoginComponent
      ) : (
        <App onLogout={handleLogout} user={user} />
      )}
    </>
  );
};

export default AuthWrapper;
