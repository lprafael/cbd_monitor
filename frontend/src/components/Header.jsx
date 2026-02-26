/**
 * Componente Header: Barra superior con controles de selección
 * - Selector de EOTs (múltiple)
 * - Selector de fecha
 * - Radio buttons para modo de visualización (hora/franja)
 * - Selector de tema
 * - Botón "Obtener Datos"
 */

import React from 'react';
import './Header.css';

const Header = ({
  eots,
  selectedEots,
  setSelectedEots,
  fecha,
  setFecha,
  modoVisualizacion,
  setModoVisualizacion,
  viewMode,
  setViewMode,
  onObtenerCBD,
  loading,
  theme,
  setTheme,
  onLogout,
  user
}) => {
  const handleEotChange = (e) => {
    const options = e.target.options;
    const selected = [];

    if (viewMode === 'system-ifo' || viewMode === 'visual-charts') {
      // No se requiere selección de EOT para IFO Sistema o Gráficos
      return;
    }

    if (viewMode === 'monthly' || viewMode === 'verify290' || viewMode === 'cbd-objetivo') {
      setSelectedEots([parseInt(e.target.value)]);
      return;
    }

    for (let i = 0; i < options.length; i++) {
      if (options[i].selected) {
        selected.push(parseInt(options[i].value));
      }
    }
    setSelectedEots(selected);
  };

  const handleSubmit = (e) => {
    e.preventDefault();

    // Para IFO Sistema y Gráficos no se requiere selección de EOT
    if (viewMode !== 'system-ifo' && viewMode !== 'visual-charts' && selectedEots.length === 0) {
      alert('Por favor seleccione al menos una EOT');
      return;
    }

    if (!fecha) {
      alert('Por favor seleccione una fecha');
      return;
    }
    onObtenerCBD();
  };

  const themes = [
    { value: 'mopc', label: '🏛️ MOPC', description: 'Tema institucional oficial' },
    { value: 'institucional', label: '💼 Institucional', description: 'Azul corporativo' },
    { value: 'ejecutivo', label: '⚫ Ejecutivo', description: 'Gris profesional' },
    { value: 'claro', label: '⚪ Claro', description: 'Minimalista' },
    { value: 'nocturno', label: '🌙 Nocturno', description: 'Modo oscuro' }
  ];

  return (
    <header className="header">
      <div className="header-container">
        <div className="header-top">
          <h1 className="header-title">
            {/* 🚌 Monitor de Control de Buses Distintos (CBD) */}
            {/* iCONO DE ESTADISTICA */}
            🚌 Monitor de Indicadores de Desempeño (CBD/IFO) 📊
          </h1>

          <div className="header-top-right">
            {/* Selector de tema */}
            <div className="theme-selector">
              <label htmlFor="theme-select" className="theme-label">
                🎨 Tema:
              </label>
              <select
                id="theme-select"
                value={theme}
                onChange={(e) => setTheme(e.target.value)}
                className="theme-select"
              >
                {themes.map(t => (
                  <option key={t.value} value={t.value}>
                    {t.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Información del usuario y botones */}
            {user && (
              <div className="user-info">
                <span className="user-name">{user.nombre_completo || user.username}</span>
                <button
                  type="button"
                  onClick={() => {
                    window.location.hash = user.rol === 'admin' ? '#/admin/users' : '#/users';
                    window.location.reload();
                  }}
                  className={user.rol === 'admin' ? "admin-button" : "profile-button"}
                  title={user.rol === 'admin' ? "Administración" : "Mi Perfil"}
                  style={user.rol !== 'admin' ? {
                    background: 'rgba(255, 255, 255, 0.1)',
                    border: '1px solid rgba(255, 255, 255, 0.2)',
                    color: 'white',
                    padding: '6px 12px',
                    borderRadius: '8px',
                    fontSize: '0.85rem',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    marginLeft: '10px'
                  } : {}}
                >
                  {user.rol === 'admin' ? '⚙️ Administración' : '👤 Mi Perfil'}
                </button>
                <button
                  type="button"
                  onClick={onLogout}
                  className="logout-button"
                  title="Cerrar sesión"
                >
                  🚪 Salir
                </button>
              </div>
            )}
          </div>
        </div>

        <form className="header-form" onSubmit={handleSubmit}>
          <div className="form-row">
            <div className="form-group form-group-eot">
              <label htmlFor="eot-select">
                Empresas Operadoras (EOT):
              </label>
              <select
                id="eot-select"
                multiple={viewMode !== 'monthly' && viewMode !== 'verify290' && viewMode !== 'system-ifo' && viewMode !== 'visual-charts' && viewMode !== 'cbd-objetivo'}
                value={(viewMode === 'monthly' || viewMode === 'verify290' || viewMode === 'cbd-objetivo') && selectedEots.length > 0 ? selectedEots[0] : selectedEots.map(String)}
                onChange={handleEotChange}
                className="form-control eot-select"
                size="5"
                disabled={viewMode === 'system-ifo' || viewMode === 'visual-charts'}
                style={viewMode === 'system-ifo' || viewMode === 'visual-charts' ? { opacity: 0.5, cursor: 'not-allowed' } : {}}
              >
                {eots.map((eot) => (
                  <option key={eot.cod_catalogo} value={eot.cod_catalogo}>
                    {eot.eot_nombre} {eot.gre_nombre ? `(${eot.gre_nombre})` : ''}
                  </option>
                ))}
              </select>
              <small className="form-hint">
                {viewMode === 'system-ifo' || viewMode === 'visual-charts'
                  ? 'No se requiere selección de EOT (incluye todas)'
                  : (viewMode === 'monthly' || viewMode === 'verify290' || viewMode === 'cbd-objetivo')
                    ? 'Seleccione una sola empresa para el reporte'
                    : 'Mantén presionado Ctrl (Windows) o Cmd (Mac) para seleccionar múltiples'}
              </small>
            </div>

            <div className="form-controls-column">
              <div className="form-group">
                <label htmlFor="fecha-input">
                  {viewMode === 'monthly' || viewMode === 'verify290' || viewMode === 'system-ifo' || viewMode === 'visual-charts' ? 'Mes y Año:' : 'Fecha:'}
                </label>
                <input
                  id="fecha-input"
                  key={viewMode === 'monthly' || viewMode === 'verify290' || viewMode === 'system-ifo' || viewMode === 'visual-charts' ? 'month' : 'date'}
                  type={viewMode === 'monthly' || viewMode === 'verify290' || viewMode === 'system-ifo' || viewMode === 'visual-charts' ? "month" : "date"}
                  value={
                    (viewMode === 'monthly' || viewMode === 'verify290' || viewMode === 'system-ifo' || viewMode === 'visual-charts')
                      ? (fecha && String(fecha).length >= 7
                        ? String(fecha).slice(0, 7)
                        : `${new Date().getFullYear()}-${String(new Date().getMonth() + 1).padStart(2, '0')}`)
                      : fecha
                  }
                  onChange={(e) => {
                    const v = e.target.value;
                    if (viewMode === 'monthly' || viewMode === 'verify290' || viewMode === 'system-ifo' || viewMode === 'visual-charts') {
                      setFecha(v.length === 7 ? v + '-01' : v);
                    } else {
                      setFecha(v);
                    }
                  }}
                  className="form-control"
                  required
                />
              </div>

              <div className="form-group">
                <label>Tipo de Vista:</label>
                <div className="radio-group">
                  <label className="radio-label">
                    <input
                      type="radio"
                      name="viewMode"
                      value="live"
                      checked={viewMode === 'live'}
                      onChange={(e) => setViewMode(e.target.value)}
                    />
                    <span>📊 Cant. Buses</span>
                  </label>
                  <label className="radio-label">
                    <input
                      type="radio"
                      name="viewMode"
                      value="indices"
                      checked={viewMode === 'indices'}
                      onChange={(e) => setViewMode(e.target.value)}
                    />
                    <span>📉 Tablero de Índices</span>
                  </label>
                  <label className="radio-label">
                    <input
                      type="radio"
                      name="viewMode"
                      value="performance"
                      checked={viewMode === 'performance'}
                      onChange={(e) => setViewMode(e.target.value)}
                    />
                    <span>📈 Desempeño Diario</span>
                  </label>
                  <label className="radio-label">
                    <input
                      type="radio"
                      name="viewMode"
                      value="monthly"
                      checked={viewMode === 'monthly'}
                      onChange={(e) => setViewMode(e.target.value)}
                    />
                    <span>📅 Desempeño Mensual</span>
                  </label>
                  <label className="radio-label">
                    <input
                      type="radio"
                      name="viewMode"
                      value="cbd-objetivo"
                      checked={viewMode === 'cbd-objetivo'}
                      onChange={(e) => setViewMode(e.target.value)}
                    />
                    <span>📊 CBD Objetivo</span>
                  </label>
                  {user && user.rol !== 'viewer' && (
                    <>
                      <label className="radio-label">
                        <input
                          type="radio"
                          name="viewMode"
                          value="system-ifo"
                          checked={viewMode === 'system-ifo'}
                          onChange={(e) => setViewMode(e.target.value)}
                        />
                        <span>📊 IFO Sistema</span>
                      </label>
                      <label className="radio-label">
                        <input
                          type="radio"
                          name="viewMode"
                          value="visual-charts"
                          checked={viewMode === 'visual-charts'}
                          onChange={(e) => setViewMode(e.target.value)}
                        />
                        <span>📈 Gráficos Visuales</span>
                      </label>
                    </>
                  )}
                  {/* <label className="radio-label">
                   <input
                      type="radio"
                      name="viewMode"
                      value="verify290"
                      checked={viewMode === 'verify290'}
                      onChange={(e) => setViewMode(e.target.value)}
                    />
                    <span>📋 Verificar 290</span>
                  </label> */}
                </div>
              </div>

              {viewMode === 'live' && (
                <div className="form-group">
                  <label>Agrupación (En Vivo):</label>
                  <div className="radio-group">
                    <label className="radio-label">
                      <input
                        type="radio"
                        name="modo"
                        value="franja"
                        checked={modoVisualizacion === 'franja'}
                        onChange={(e) => setModoVisualizacion(e.target.value)}
                      />
                      <span>Por Franja</span>
                    </label>
                    <label className="radio-label">
                      <input
                        type="radio"
                        name="modo"
                        value="hora"
                        checked={modoVisualizacion === 'hora'}
                        onChange={(e) => setModoVisualizacion(e.target.value)}
                      />
                      <span>Por Hora</span>
                    </label>
                  </div>
                </div>
              )}

              <button
                type="submit"
                className="btn-submit"
                disabled={loading}
              >
                {loading ? '⏳ Cargando...' : '🔍 Obtener Datos'}
              </button>
            </div>
          </div>
        </form>
      </div>
    </header>
  );
};

export default Header;
