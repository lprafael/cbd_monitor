import React, { useState, useEffect } from 'react';
import { authFetch } from '../utils/authFetch';
import { API_BASE_URL } from '../config';
import './UserManagement.css';

const UserManagement = () => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [passwordFields, setPasswordFields] = useState({
    current_password: '', new_password: '', confirm_password: ''
  });

  const roles = [
    { value: 'admin', label: 'Administrador' },
    { value: 'manager', label: 'Gerente' },
    { value: 'user', label: 'Usuario' },
    { value: 'viewer', label: 'Visualizador' }
  ];

  const fetchUser = async () => {
    try {
      const response = await authFetch(`${API_BASE_URL}/auth/me`);
      if (response.ok) {
        const data = await response.json();
        setUser(data);
      } else {
        setError('No se pudo cargar tu perfil');
      }
    } catch (err) {
      setError('Error al cargar datos');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUser();
  }, []);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setPasswordFields((prev) => ({ ...prev, [name]: value }));
  };

  const handleChangePassword = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      if (!passwordFields.new_password) {
        alert('Por favor ingrese la nueva contraseña');
        setLoading(false);
        return;
      }
      if (passwordFields.new_password !== passwordFields.confirm_password) {
        alert('Las contraseñas no coinciden');
        setLoading(false);
        return;
      }
      
      const response = await authFetch(`${API_BASE_URL}/auth/change-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          current_password: passwordFields.current_password,
          new_password: passwordFields.new_password
        })
      });

      if (response.ok) {
        alert('Contraseña actualizada correctamente');
        setPasswordFields({ current_password: '', new_password: '', confirm_password: '' });
      } else {
        const data = await response.json();
        alert(data.detail || 'Error al cambiar contraseña');
      }
    } catch (err) {
      alert('Error en la operación');
    } finally {
      setLoading(false);
    }
  };

  if (loading && !user) return <div className="loading">Cargando...</div>;
  if (error) return <div className="error-message">{error}</div>;

  return (
    <div className="fade-in">
      <div className="user-management-header">
        <h1 style={{ fontSize: '1.5rem', fontWeight: 700 }}>Mi Perfil</h1>
      </div>
      
      <div className="info-banner" style={{ background: '#e0f2fe', padding: '16px', borderRadius: '8px', marginBottom: '20px', borderLeft: '4px solid #0ea5e9' }}>
        <strong>Aviso:</strong> La gestión y asignación de usuarios para el sistema CBD Monitor se realiza centralizadamente desde el <strong>Sistema de Catálogos</strong>. 
        Aquí únicamente puedes ver tu información básica y modificar tu contraseña.
      </div>

      <div style={{ maxWidth: '600px', margin: '0 auto', background: 'white', padding: '24px', borderRadius: '12px', boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)' }}>
        <div style={{ marginBottom: '24px' }}>
          <h2 style={{ fontSize: '1.25rem', marginBottom: '16px', borderBottom: '1px solid #e2e8f0', paddingBottom: '8px' }}>Información Personal</h2>
          <div style={{ display: 'grid', gap: '12px' }}>
            <div><strong style={{ color: '#64748b' }}>Usuario:</strong> {user.username}</div>
            <div><strong style={{ color: '#64748b' }}>Nombre:</strong> {user.nombre_completo}</div>
            <div><strong style={{ color: '#64748b' }}>Email:</strong> {user.email}</div>
            <div>
              <strong style={{ color: '#64748b' }}>Rol en CBD Monitor: </strong> 
              <span className={`role-badge role-${user.rol}`}>
                {roles.find(r => r.value === user.rol)?.label || user.rol}
              </span>
            </div>
          </div>
        </div>

        <form onSubmit={handleChangePassword} style={{ marginTop: '20px', padding: '16px', background: '#f8fafc', borderRadius: '12px' }}>
          <h2 style={{ fontSize: '1.25rem', marginBottom: '16px', borderBottom: '1px solid #e2e8f0', paddingBottom: '8px' }}>Cambiar Contraseña</h2>
          
          <div className="form-group" style={{ marginBottom: '12px' }}>
            <label style={{ display: 'block', marginBottom: '4px', fontSize: '0.875rem', fontWeight: 600 }}>Contraseña Actual</label>
            <input 
              type="password" 
              name="current_password" 
              value={passwordFields.current_password}
              onChange={handleChange} 
              required
              style={{ width: '100%', padding: '8px', borderRadius: '6px', border: '1px solid #cbd5e1' }}
            />
          </div>
          
          <div className="form-group" style={{ marginBottom: '12px' }}>
            <label style={{ display: 'block', marginBottom: '4px', fontSize: '0.875rem', fontWeight: 600 }}>Nueva Contraseña</label>
            <input 
              type="password" 
              name="new_password" 
              value={passwordFields.new_password}
              onChange={handleChange} 
              required
              style={{ width: '100%', padding: '8px', borderRadius: '6px', border: '1px solid #cbd5e1' }}
            />
          </div>
          
          <div className="form-group" style={{ marginBottom: '20px' }}>
            <label style={{ display: 'block', marginBottom: '4px', fontSize: '0.875rem', fontWeight: 600 }}>Confirmar Nueva Contraseña</label>
            <input 
              type="password" 
              name="confirm_password" 
              value={passwordFields.confirm_password}
              onChange={handleChange} 
              required
              style={{ width: '100%', padding: '8px', borderRadius: '6px', border: '1px solid #cbd5e1' }}
            />
          </div>
          
          <button 
            type="submit" 
            className="btn btn-primary" 
            disabled={loading}
            style={{ width: '100%', padding: '10px' }}
          >
            {loading ? 'Guardando...' : 'Actualizar Contraseña'}
          </button>
        </form>
      </div>
    </div>
  );
};

export default UserManagement;
