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
    const loginTime = Date.now();
    localStorage.setItem('login_time', loginTime.toString());
    localStorage.setItem('last_activity', loginTime.toString());
    setUser(data.user);
    setIsAuthenticated(true);
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('refreshToken');
    localStorage.removeItem('user');
    localStorage.removeItem('login_time');
    localStorage.removeItem('last_activity');
    setUser(null);
    setIsAuthenticated(false);
  };

  // Lógica de Autocierre de Sesión (Inactividad y Tiempo Total)
  useEffect(() => {
    if (!isAuthenticated) return;

    const INACTIVITY_LIMIT = 10 * 60 * 1000; // 10 minutos
    const ABSOLUTE_LIMIT = 60 * 60 * 1000;   // 60 minutos

    const checkTimeout = () => {
      const now = Date.now();
      const loginTime = parseInt(localStorage.getItem('login_time') || '0');
      const lastActivity = parseInt(localStorage.getItem('last_activity') || now.toString());

      // 1. Verificar límite absoluto (60 min desde login)
      if (now - loginTime > ABSOLUTE_LIMIT) {
        console.log('Sesión expirada (Límite absoluto 60 min)');
        handleLogout();
        return;
      }

      // 2. Verificar inactividad (10 min)
      if (now - lastActivity > INACTIVITY_LIMIT) {
        console.log('Sesión cerrada por inactividad (10 min)');
        handleLogout();
        return;
      }
    };

    const updateActivity = () => {
      localStorage.setItem('last_activity', Date.now().toString());
    };

    // Eventos para detectar actividad
    const events = ['mousedown', 'mousemove', 'keypress', 'scroll', 'touchstart'];
    events.forEach(event => window.addEventListener(event, updateActivity));

    // Verificar cada minuto
    const interval = setInterval(checkTimeout, 30000); // Verificar cada 30 segundos para mayor precisión

    return () => {
      events.forEach(event => window.removeEventListener(event, updateActivity));
      clearInterval(interval);
    };
  }, [isAuthenticated]);

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
