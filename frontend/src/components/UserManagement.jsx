import React, { useState, useEffect } from 'react';
import { authFetch } from '../utils/authFetch';
import { API_BASE_URL } from '../config';
import './UserManagement.css';

const UserManagement = () => {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [editUser, setEditUser] = useState(null);
  const [newUser, setNewUser] = useState({
    username: '', email: '', nombre_completo: '', rol: 'user'
  });
  const [passwordFields, setPasswordFields] = useState({
    current_password: '', new_password: '', confirm_password: ''
  });

  const roles = [
    { value: 'admin', label: 'Administrador' },
    { value: 'manager', label: 'Gerente' },
    { value: 'user', label: 'Usuario' },
    { value: 'viewer', label: 'Visualizador' }
  ];

  const currentUser = JSON.parse(localStorage.getItem('user') || '{}');
  const isAdmin = currentUser && currentUser.rol === 'admin';

  const fetchUsers = async () => {
    try {
      const endpoint = isAdmin ? `/auth/users` : `/auth/me`;
      const response = await authFetch(`${API_BASE_URL}${endpoint}`);
      if (response.ok) {
        const data = await response.json();
        // /auth/me retorna un objeto simple, /auth/users retorna un array
        setUsers(isAdmin ? data : [data]);
      } else {
        setError(isAdmin ? 'No tienes permisos para ver usuarios' : 'No se pudo cargar tu perfil');
      }
    } catch (err) {
      setError('Error al cargar datos');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // Todos los usuarios pueden entrar. 
    // fetchUsers ya maneja el endpoint correcto basado en el rol.
    fetchUsers();
  }, []);

  const handleEditClick = (user) => {
    setEditUser({ ...user });
    setShowEditModal(true);
  };

  const handleChange = (e, setter) => {
    const { name, value } = e.target;
    setter((prev) => ({ ...prev, [name]: value }));
  };

  const handleCreateUser = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const response = await authFetch(`${API_BASE_URL}/auth/users`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newUser)
      });
      if (response.ok) {
        setShowCreateForm(false);
        setNewUser({ username: '', email: '', nombre_completo: '', rol: 'user' });
        fetchUsers();
        alert('Usuario creado exitosamente.');
      } else {
        const data = await response.json();
        alert(data.detail || 'Error al crear usuario');
      }
    } catch (err) {
      alert('Error de conexión');
    } finally {
      setLoading(false);
    }
  };

  const handleEditUser = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      // 1. Manejar cambio de contraseña (para cualquier usuario editando su propio perfil)
      if (currentUser.id === editUser.id && passwordFields.new_password) {
        if (passwordFields.new_password !== passwordFields.confirm_password) {
          alert('Las contraseñas no coinciden');
          setLoading(false);
          return;
        }
        const pwResponse = await authFetch(`${API_BASE_URL}/auth/change-password`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            current_password: passwordFields.current_password,
            new_password: passwordFields.new_password
          })
        });

        if (!pwResponse.ok) {
          const pwData = await pwResponse.json();
          alert(pwData.detail || 'Error al cambiar contraseña');
          setLoading(false);
          return;
        }
      }

      // 2. Manejar actualización de perfil (SOLO si es admin)
      if (isAdmin) {
        const response = await authFetch(`${API_BASE_URL}/auth/users/${editUser.id}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            email: editUser.email,
            nombre_completo: editUser.nombre_completo,
            rol: editUser.rol,
          })
        });

        if (response.ok) {
          alert('Usuario actualizado correctamente');
          setShowEditModal(false);
          fetchUsers();
        } else {
          const data = await response.json();
          alert(data.detail || 'Error al actualizar usuario');
        }
      } else {
        // Si no es admin, solo pudo haber cambiado la contraseña o guardado sin cambios
        if (passwordFields.new_password) {
          alert('Contraseña actualizada correctamente');
        } else {
          alert('Perfil visualizado correctamente');
        }
        setShowEditModal(false);
        setPasswordFields({ current_password: '', new_password: '', confirm_password: '' });
      }
    } catch (err) {
      alert('Error en la operación');
    } finally {
      setLoading(false);
    }
  };

  const handleResendPassword = async () => {
    if (!window.confirm(`¿Seguro que deseas generar y enviar una nueva contraseña temporal a ${editUser.username}?`)) return;

    setLoading(true);
    try {
      const response = await authFetch(`${API_BASE_URL}/notify/resend-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: editUser.username })
      });

      if (response.ok) {
        alert('Se ha enviado una nueva contraseña temporal al usuario por email.');
      } else {
        const data = await response.json();
        alert(data.detail || 'Error al reenviar contraseña');
      }
    } catch (err) {
      alert('Error de conexión');
    } finally {
      setLoading(false);
    }
  };

  const handleStatusChange = async (user, action) => {
    const actionText = action === 'reactivate' ? 'activar' : 'desactivar';
    if (!window.confirm(`¿Seguro que deseas ${actionText} a ${user.username}?`)) return;

    setLoading(true);
    try {
      if (action === 'reactivate') {
        const response = await authFetch(`${API_BASE_URL}/auth/users/${user.id}/reactivate`, {
          method: 'POST'
        });
        if (response.ok) {
          fetchUsers();
          alert('Usuario activado exitosamente');
        } else {
          const data = await response.json();
          alert(data.detail || 'Error al activar usuario');
        }
      } else {
        const response = await authFetch(`${API_BASE_URL}/auth/users/${user.id}`, {
          method: 'DELETE'
        });
        if (response.ok) {
          fetchUsers();
          alert('Usuario desactivado exitosamente');
        } else {
          const data = await response.json();
          alert(data.detail || 'Error al desactivar usuario');
        }
      }
    } catch (err) {
      alert('Error en la operación');
    } finally {
      setLoading(false);
    }
  };


  if (loading && users.length === 0) return <div className="loading">Cargando...</div>;


  return (
    <div className="fade-in">
      <div className="user-management-header">
        <h1 style={{ fontSize: '1.5rem', fontWeight: 700 }}>
          {isAdmin ? 'Gestión de Usuarios' : 'Mi Perfil'}
        </h1>
        {isAdmin && (
          <button className="btn btn-primary" onClick={() => setShowCreateForm(true)}>
            ➕ Crear Usuario
          </button>
        )}
      </div>

      <div className="table-container">
        <table>
          <thead>
            <tr>
              <th>Usuario</th>
              <th>Email</th>
              <th>Nombre</th>
              <th>Rol</th>
              <th>Estado</th>
              <th>Acciones</th>
            </tr>
          </thead>
          <tbody>
            {users.map(user => (
              <tr key={user.id}>
                <td style={{ fontWeight: 600 }}>{user.username}</td>
                <td>{user.email}</td>
                <td>{user.nombre_completo}</td>
                <td><span className={`role-badge role-${user.rol}`}>{roles.find(r => r.value === user.rol)?.label}</span></td>
                <td><span className={`status-badge ${user.activo ? 'active' : 'inactive'}`}>{user.activo ? 'Activo' : 'Inactivo'}</span></td>
                <td>
                  <div className="actions-cell">
                    <button className="action-btn action-btn-edit" onClick={() => handleEditClick(user)} title="Editar Perfil">✏️</button>
                    {isAdmin && user.username !== 'admin' && (
                      user.activo ?
                        <button className="action-btn action-btn-delete" onClick={() => handleStatusChange(user, 'soft')} title="Desactivar">🚫</button> :
                        <button className="action-btn action-btn-edit" style={{ color: '#22c55e' }} onClick={() => handleStatusChange(user, 'reactivate')} title="Reactivar">✅</button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {(showCreateForm || showEditModal) && (

        <div className="modal-overlay">
          <div className="modal fade-in">
            <div className="modal-header">
              <h3>{showCreateForm ? 'Crear Nuevo Usuario' : 'Editar Usuario'}</h3>
              <button className="close-btn" onClick={() => { setShowCreateForm(false); setShowEditModal(false); }}>×</button>
            </div>
            <form onSubmit={showCreateForm ? handleCreateUser : handleEditUser} className="create-user-form">
              {showCreateForm && (
                <div className="form-group">
                  <label className="form-label">Usuario</label>
                  <input name="username" value={newUser.username} onChange={(e) => handleChange(e, setNewUser)} required />
                </div>
              )}
              <div className="form-group">
                <label className="form-label">Email</label>
                <input
                  name="email"
                  value={showCreateForm ? newUser.email : editUser.email}
                  onChange={(e) => handleChange(e, showCreateForm ? setNewUser : setEditUser)}
                  required
                  disabled={!showCreateForm && !isAdmin}
                />
              </div>
              <div className="form-group">
                <label className="form-label">Nombre Completo</label>
                <input
                  name="nombre_completo"
                  value={showCreateForm ? newUser.nombre_completo : editUser.nombre_completo}
                  onChange={(e) => handleChange(e, showCreateForm ? setNewUser : setEditUser)}
                  required
                  disabled={!showCreateForm && !isAdmin}
                />
              </div>
              <div className="form-group">
                <label className="form-label">Rol</label>
                <select
                  name="rol"
                  value={showCreateForm ? newUser.rol : editUser.rol}
                  onChange={(e) => handleChange(e, showCreateForm ? setNewUser : setEditUser)}
                  disabled={!isAdmin}
                >
                  {roles.map(r => <option key={r.value} value={r.value}>{r.label}</option>)}
                </select>
              </div>
              {!showCreateForm && currentUser.id === editUser?.id && (
                <div style={{ marginTop: '20px', padding: '16px', background: '#f8fafc', borderRadius: '12px' }}>
                  <p style={{ fontWeight: 600, fontSize: '0.875rem', marginBottom: '12px' }}>Cambiar Contraseña</p>
                  <div className="form-group"><input type="password" name="current_password" placeholder="Actual" onChange={(e) => handleChange(e, setPasswordFields)} /></div>
                  <div className="form-group"><input type="password" name="new_password" placeholder="Nueva" onChange={(e) => handleChange(e, setPasswordFields)} /></div>
                  <div className="form-group"><input type="password" name="confirm_password" placeholder="Confirmar" onChange={(e) => handleChange(e, setPasswordFields)} /></div>
                </div>
              )}
              {!showCreateForm && isAdmin && currentUser.id !== editUser?.id && (
                <div style={{ marginTop: '20px', padding: '16px', background: '#fff7ed', borderRadius: '12px', border: '1px solid #ffedd5' }}>
                  <p style={{ fontWeight: 600, fontSize: '0.875rem', marginBottom: '8px', color: '#9a3412' }}>Seguridad</p>
                  <p style={{ fontSize: '0.8125rem', color: '#c2410c', marginBottom: '12px' }}>
                    Si el usuario olvidó su contraseña, puedes enviarle una nueva temporal por correo electrónico.
                  </p>
                  <button
                    type="button"
                    className="btn btn-secondary"
                    style={{ width: '100%', background: '#ffedd5', color: '#9a3412', borderColor: '#fed7aa' }}
                    onClick={handleResendPassword}
                    disabled={loading}
                  >
                    📧 Reenviar Contraseña Temporal
                  </button>
                </div>
              )}
              <div className="modal-actions">
                <button type="button" className="btn btn-secondary" onClick={() => { setShowCreateForm(false); setShowEditModal(false); }}>Cancelar</button>
                <button type="submit" className="btn btn-primary">{showCreateForm ? 'Crear' : 'Guardar'}</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default UserManagement;
