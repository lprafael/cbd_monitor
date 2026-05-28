import React, { useState } from 'react';
import { GoogleLogin } from '@react-oauth/google';
import './Login.css';
import { API_BASE_URL } from '../config';

const Login = ({ onLogin, googleClientId }) => {
  const [credentials, setCredentials] = useState({
    username: '',
    password: ''
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [showPassword, setShowPassword] = useState(false);

  const handleChange = (e) => {
    setCredentials({
      ...credentials,
      [e.target.name]: e.target.value
    });
  };

  const togglePasswordVisibility = () => {
    setShowPassword(!showPassword);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const response = await fetch(`${API_BASE_URL}/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ ...credentials, sistema_id: 1 }), // sistema_id 1 para cbd_monitor
      });

      const data = await response.json();

      if (response.ok) {
        // Guardar token, refresh token y datos del usuario
        localStorage.setItem('token', data.access_token);
        if (data.refresh_token) {
          localStorage.setItem('refreshToken', data.refresh_token);
        }
        localStorage.setItem('user', JSON.stringify(data.user));
        onLogin(data);
      } else {
        setError(data.detail || 'Error en el inicio de sesión');
      }
    } catch (err) {
      setError('Error de conexión. Verifica que el servidor esté funcionando.');
    } finally {
      setLoading(false);
    }
  };

  const handleGoogleSuccess = async (credentialResponse) => {
    setLoading(true);
    setError('');
    try {
      const response = await fetch(`${API_BASE_URL}/auth/google-login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ credential: credentialResponse.credential, sistema_id: 1 }), // sistema_id 1 para cbd_monitor
      });

      const data = await response.json();

      if (response.ok) {
        localStorage.setItem('token', data.access_token);
        if (data.refresh_token) {
          localStorage.setItem('refreshToken', data.refresh_token);
        }
        localStorage.setItem('user', JSON.stringify(data.user));
        onLogin(data);
      } else {
        const errorMessage = data.detail || 'Error en la autenticación con Google';
        // Si el usuario está pendiente de aprobación, mostrar mensaje más claro
        if (errorMessage.includes('pendiente de aprobación') || errorMessage.includes('aprobación')) {
          setError('⏳ Tu cuenta está pendiente de aprobación. Un administrador debe activar tu cuenta antes de poder acceder. Se ha enviado una notificación al administrador.');
        } else {
          setError(errorMessage);
        }
      }
    } catch (err) {
      setError('Error de conexión con el servidor');
    } finally {
      setLoading(false);
    }
  };

  const handleForgotPassword = async () => {
    if (!credentials.username) {
      setError('Por favor ingresa tu nombre de usuario');
      return;
    }

    setLoading(true);
    setError('');
    try {
      const response = await fetch(`${API_BASE_URL}/notify/forgot-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: credentials.username })
      });
      const data = await response.json();
      if (response.ok) {
        alert('Se ha notificado al administrador. Pronto se pondrá en contacto contigo.');
      } else {
        if (Array.isArray(data.detail)) {
          setError(data.detail.map(e => e.msg).join(' | '));
        } else if (typeof data.detail === 'object') {
          setError(JSON.stringify(data.detail));
        } else {
          setError(data.detail || 'Error al notificar al administrador');
        }
      }
    } catch (err) {
      setError('Error de conexión');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-container">
      <div className="login-card">
        <div className="login-header">
          <h2>Sistema Integral de Control y Monitoreo</h2>
          <p>Inicia sesión para continuar</p>
        </div>

        <form onSubmit={handleSubmit} className="login-form">
          {error && (
            <div className="error-message">
              {error}
            </div>
          )}

          <div className="form-group">
            <label htmlFor="username">Usuario</label>
            <input
              type="text"
              id="username"
              name="username"
              value={credentials.username}
              onChange={handleChange}
              required
              placeholder="Ingresa tu usuario"
            />
          </div>

          <div className="form-group">
            <label htmlFor="password">Contraseña</label>
            <div className="password-input-container">
              <input
                type={showPassword ? "text" : "password"}
                id="password"
                name="password"
                value={credentials.password}
                onChange={handleChange}
                required
                placeholder="Ingresa tu contraseña"
              />
              <button
                type="button"
                className="password-toggle-btn"
                onClick={togglePasswordVisibility}
                aria-label={showPassword ? "Ocultar contraseña" : "Mostrar contraseña"}
              >
                {showPassword ? (
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path>
                    <line x1="1" y1="1" x2="23" y2="23"></line>
                  </svg>
                ) : (
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
                    <circle cx="12" cy="12" r="3"></circle>
                  </svg>
                )}
              </button>
            </div>
          </div>

          <button
            type="submit"
            className="login-button"
            disabled={loading}
          >
            {loading ? 'Iniciando sesión...' : 'Iniciar Sesión'}
          </button>

          {googleClientId && (
            <>
              <div className="google-login-separator">
                <span>O</span>
              </div>
              <div className="google-login-container">
                <GoogleLogin
                  onSuccess={handleGoogleSuccess}
                  onError={() => setError('Error al iniciar sesión con Google')}
                  // useOneTap
                  theme="outline"
                  size="large"
                  width={320}
                  text="signin_with"
                  locale="es"
                />
              </div>
            </>
          )}
        </form>

        <div className="login-footer">
          <button
            type="button"
            className="forgot-password-link"
            disabled={loading || !credentials.username}
            onClick={handleForgotPassword}
          >
            ¿Olvidaste tu contraseña?
          </button>
        </div>
      </div>
    </div>
  );
};

export default Login;
