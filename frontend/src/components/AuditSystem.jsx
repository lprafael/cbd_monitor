import React, { useState, useEffect } from 'react';
import { authFetch } from '../utils/authFetch';
import { API_BASE_URL } from '../config';
import './AuditSystem.css';

const AuditSystem = () => {
    const [activeTab, setActiveTab] = useState('audit'); // 'audit', 'access', 'sessions'
    const [data, setData] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [selectedItem, setSelectedItem] = useState(null);

    // Filtros
    const [filters, setFilters] = useState({
        username: '',
        limit: 100
    });

    const fetchData = async () => {
        setLoading(true);
        setError('');
        try {
            let endpoint = '';
            if (activeTab === 'audit') endpoint = `/auditoria/logs`;
            else if (activeTab === 'access') endpoint = `/auth/logs`;
            else if (activeTab === 'sessions') endpoint = `/auditoria/sesiones`;

            const params = new URLSearchParams();
            if (filters.username) params.append('username', filters.username);
            params.append('limit', filters.limit);

            const response = await authFetch(`${API_BASE_URL}${endpoint}?${params.toString()}`);
            if (response.ok) {
                const result = await response.json();
                setData(result);
            } else {
                setError('Error al obtener datos. Verifica tus permisos.');
            }
        } catch (err) {
            setError('Error de conexión con el servidor.');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData();
    }, [activeTab, filters.limit]);

    const handleFilterChange = (e) => {
        setFilters({ ...filters, [e.target.name]: e.target.value });
    };

    const handleSearch = (e) => {
        e.preventDefault();
        fetchData();
    };

    const formatFecha = (fechaStr) => {
        if (!fechaStr) return '-';
        return new Date(fechaStr).toLocaleString('es-PY');
    };

    const renderAuditTable = () => (
        <table className="audit-table">
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Usuario</th>
                    <th>Acción</th>
                    <th>Tabla</th>
                    <th>Registro ID</th>
                    <th>Fecha</th>
                    <th>Detalles</th>
                </tr>
            </thead>
            <tbody>
                {data.map(item => (
                    <tr key={item.id}>
                        <td>{item.id}</td>
                        <td style={{ fontWeight: 600 }}>{item.username}</td>
                        <td><span className="status-label" style={{ background: '#e0f2fe', color: '#0369a1' }}>{item.accion}</span></td>
                        <td>{item.tabla}</td>
                        <td>{item.registro_id || '-'}</td>
                        <td>{formatFecha(item.fecha)}</td>
                        <td>
                            {(item.datos_anteriores || item.datos_nuevos) ? (
                                <div className="audit-json-viewer" onClick={() => setSelectedItem(item)}>
                                    Ver cambios
                                </div>
                            ) : '-'}
                        </td>
                    </tr>
                ))}
                {data.length === 0 && <tr><td colSpan="7" style={{ textAlign: 'center', padding: '20px' }}>No hay registros</td></tr>}
            </tbody>
        </table>
    );

    const renderAccessTable = () => (
        <table className="audit-table">
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Usuario</th>
                    <th>Acción</th>
                    <th>IP</th>
                    <th>Resultado</th>
                    <th>Fecha</th>
                    <th>User Agent</th>
                </tr>
            </thead>
            <tbody>
                {data.map(item => (
                    <tr key={item.id}>
                        <td>{item.id}</td>
                        <td style={{ fontWeight: 600 }}>{item.username}</td>
                        <td>{item.accion}</td>
                        <td>{item.ip_address || '-'}</td>
                        <td>
                            <span className={`status-label ${item.exitoso ? 'status-success' : 'status-failed'}`}>
                                {item.exitoso ? 'Exitoso' : 'Fallido'}
                            </span>
                        </td>
                        <td>{formatFecha(item.fecha)}</td>
                        <td style={{ maxWidth: '200px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={item.user_agent || ''}>
                            {item.user_agent || '-'}
                        </td>
                    </tr>
                ))}
                {data.length === 0 && <tr><td colSpan="7" style={{ textAlign: 'center', padding: '20px' }}>No hay registros</td></tr>}
            </tbody>
        </table>
    );

    const renderSessionsTable = () => (
        <table className="audit-table">
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Usuario</th>
                    <th>IP</th>
                    <th>Estado</th>
                    <th>Inicio</th>
                    <th>Expiración</th>
                    <th>Cierre</th>
                </tr>
            </thead>
            <tbody>
                {data.map(item => (
                    <tr key={item.id}>
                        <td>{item.id}</td>
                        <td style={{ fontWeight: 600 }}>{item.username || '-'}</td>
                        <td>{item.ip_address || '-'}</td>
                        <td>
                            <span className={`status-label ${item.activa ? 'status-success' : 'status-failed'}`}>
                                {item.activa ? 'Activa' : 'Cerrada'}
                            </span>
                        </td>
                        <td>{formatFecha(item.fecha_inicio)}</td>
                        <td>{formatFecha(item.fecha_expiracion)}</td>
                        <td>{formatFecha(item.fecha_cierre)}</td>
                    </tr>
                ))}
                {data.length === 0 && <tr><td colSpan="7" style={{ textAlign: 'center', padding: '20px' }}>No hay sesiones registradas</td></tr>}
            </tbody>
        </table>
    );

    return (
        <div className="audit-container fade-in">
            <div className="user-management-header">
                <h1 style={{ fontSize: '1.5rem', fontWeight: 700 }}>🔍 Auditoría y Control</h1>
            </div>

            <div className="audit-tabs">
                <button
                    className={`audit-tab-btn ${activeTab === 'audit' ? 'active' : ''}`}
                    onClick={() => setActiveTab('audit')}
                >
                    📜 Logs de Auditoría
                </button>
                <button
                    className={`audit-tab-btn ${activeTab === 'access' ? 'active' : ''}`}
                    onClick={() => setActiveTab('access')}
                >
                    🔑 Logs de Acceso
                </button>
                <button
                    className={`audit-tab-btn ${activeTab === 'sessions' ? 'active' : ''}`}
                    onClick={() => setActiveTab('sessions')}
                >
                    💻 Sesiones Activas
                </button>
            </div>

            <div className="audit-filters">
                <form onSubmit={handleSearch} style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                    <input
                        name="username"
                        placeholder="Usuario..."
                        value={filters.username}
                        onChange={handleFilterChange}
                    />
                    <select name="limit" value={filters.limit} onChange={handleFilterChange}>
                        <option value="50">50 registros</option>
                        <option value="100">100 registros</option>
                        <option value="500">500 registros</option>
                    </select>
                    <button type="submit" className="btn btn-secondary">🔍 Buscar</button>
                    <button type="button" className="btn btn-secondary" onClick={fetchData}>🔄 Refrescar</button>
                </form>
                {loading && <span style={{ marginLeft: 'auto', color: 'var(--primary-color)' }}>Actualizando...</span>}
            </div>

            {error && <div className="error-message" style={{ marginBottom: '20px' }}>{error}</div>}

            <div className="audit-table-wrapper">
                {activeTab === 'audit' && renderAuditTable()}
                {activeTab === 'access' && renderAccessTable()}
                {activeTab === 'sessions' && renderSessionsTable()}
            </div>

            {selectedItem && (
                <div className="audit-modal" onClick={() => setSelectedItem(null)}>
                    <div className="audit-modal-content" onClick={e => e.stopPropagation()}>
                        <div className="modal-header">
                            <h3>Detalles del Log #{selectedItem.id}</h3>
                            <button className="close-btn" onClick={() => setSelectedItem(null)}>×</button>
                        </div>

                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', marginBottom: '20px' }}>
                            <div>
                                <p><strong>Usuario:</strong> {selectedItem.username}</p>
                                <p><strong>Acción:</strong> {selectedItem.accion}</p>
                                <p><strong>Tabla:</strong> {selectedItem.tabla}</p>
                            </div>
                            <div>
                                <p><strong>Fecha:</strong> {formatFecha(selectedItem.fecha)}</p>
                                <p><strong>IP:</strong> {selectedItem.ip_address || '-'}</p>
                            </div>
                        </div>

                        {selectedItem.datos_anteriores && (
                            <div>
                                <p><strong>Datos Anteriores:</strong></p>
                                <pre className="json-block">{JSON.stringify(selectedItem.datos_anteriores, null, 2)}</pre>
                            </div>
                        )}

                        {selectedItem.datos_nuevos && (
                            <div style={{ marginTop: '15px' }}>
                                <p><strong>Datos Nuevos:</strong></p>
                                <pre className="json-block">{JSON.stringify(selectedItem.datos_nuevos, null, 2)}</pre>
                            </div>
                        )}

                        {selectedItem.detalles && (
                            <div style={{ marginTop: '15px' }}>
                                <p><strong>Detalles adicionales:</strong></p>
                                <p>{selectedItem.detalles}</p>
                            </div>
                        )}

                        <div className="modal-actions" style={{ marginTop: '20px' }}>
                            <button className="btn btn-secondary" onClick={() => setSelectedItem(null)}>Cerrar</button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default AuditSystem;
