/**
 * Componente principal de la aplicación
 * Gestiona el estado y las llamadas a la API
 */

import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import CBDTable from './components/CBDTable';
import PerformanceDashboard from './components/PerformanceDashboard';
import IndicesDashboard from './components/IndicesDashboard';
import MonthlyPerformanceDashboard from './components/MonthlyPerformanceDashboard';
import Verify290Dashboard from './components/Verify290Dashboard';
import SystemIFODashboard from './components/SystemIFODashboard';
import UserManagement from './components/UserManagement';
import AuditSystem from './components/AuditSystem';
import './App.css';
import { API_BASE_URL } from './config';

function App({ onLogout, user }) {
  // Estados
  const [eots, setEots] = useState([]);
  const [selectedEots, setSelectedEots] = useState([]);
  const [fecha, setFecha] = useState('');
  const [modoVisualizacion, setModoVisualizacion] = useState('franja');
  const [viewMode, setViewMode] = useState('live'); // 'live' | 'performance' | 'indices'
  const [cbdData, setCbdData] = useState(null);
  const [performanceData, setPerformanceData] = useState(null);
  const [monthlyData, setMonthlyData] = useState(null);
  const [verify290Data, setVerify290Data] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [theme, setTheme] = useState('ejecutivo'); // 'mopc' | 'institucional' | 'ejecutivo' | 'claro' | 'nocturno'
  const [currentView, setCurrentView] = useState('dashboard'); // 'dashboard' | 'users' | 'audit'
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [adminTab, setAdminTab] = useState('users'); // 'users' | 'audit'

  // Detectar cambio de hash para navegación
  useEffect(() => {
    const handleHashChange = () => {
      const hash = window.location.hash.replace('#', '');
      if (hash === '/users' || hash === '/admin/users') {
        setCurrentView('users');
        setAdminTab('users');
      } else if (hash === '/audit' || hash === '/admin/audit') {
        setCurrentView('audit');
        setAdminTab('audit');
      } else {
        setCurrentView('dashboard');
      }
    };

    handleHashChange(); // Verificar hash inicial
    window.addEventListener('hashchange', handleHashChange);
    return () => window.removeEventListener('hashchange', handleHashChange);
  }, []);

  // Verificar si el usuario es admin
  const isAdmin = user && user.rol === 'admin';

  // Cargar EOTs al montar el componente
  useEffect(() => {
    if (currentView === 'dashboard') {
      fetchEots();
      // Fecha por defecto: yyyy-MM-DD para input date; para input month usamos slice(0,7) -> yyyy-MM
      const today = new Date().toISOString().split('T')[0];
      setFecha(today);
    }

    // Cargar tema guardado
    const savedTheme = localStorage.getItem('cbd-theme') || 'ejecutivo';
    setTheme(savedTheme);
    document.documentElement.setAttribute('data-theme', savedTheme);
  }, [currentView]);

  // Guardar tema cuando cambia
  useEffect(() => {
    localStorage.setItem('cbd-theme', theme);
    document.documentElement.setAttribute('data-theme', theme);
  }, [theme]);

  /**
   * Obtener lista de EOTs desde la API
   */
  const fetchEots = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/eots`);

      if (!response.ok) {
        throw new Error('Error al cargar EOTs');
      }

      const data = await response.json();
      setEots(data);
    } catch (err) {
      console.error('Error al cargar EOTs:', err);
      setError('No se pudieron cargar las empresas operadoras. Verifique que la API esté ejecutándose.');
    }
  };

  /**
   * Obtener datos según el modo seleccionado
   */
  const handleConsulta = async () => {
    // Si es modo system-ifo, no hacemos nada aquí, el dashboard se renderiza directamente
    if (viewMode === 'system-ifo') {
      return;
    }

    setLoading(true);
    setError(null);
    setCbdData(null);
    setPerformanceData(null);
    setMonthlyData(null);
    setVerify290Data(null);

    try {
      let endpoint = '';
      let body = {};

      if (viewMode === 'live') {
        endpoint = '/api/cbd-data';
        body = {
          eot_ids: selectedEots,
          fecha: fecha,
          modo_visualizacion: modoVisualizacion,
        };
      } else if (viewMode === 'performance' || viewMode === 'indices') {
        endpoint = '/api/performance';
        body = {
          eot_ids: selectedEots,
          fecha: fecha,
        };
      } else if (viewMode === 'monthly') {
        endpoint = '/api/monthly-performance';
        const [yearStr, monthStr] = fecha.split('-');
        body = {
          eot_id: selectedEots[0],
          month: parseInt(monthStr),
          year: parseInt(yearStr)
        };
      } else if (viewMode === 'verify290') {
        endpoint = '/api/verify-290';
        const [yearStr, monthStr] = fecha.split('-');
        body = {
          eot_id: selectedEots[0],
          month: parseInt(monthStr),
          year: parseInt(yearStr)
        };
      }

      const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(body),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Error al obtener datos');
      }

      const data = await response.json();

      if (viewMode === 'live') {
        setCbdData(data);
      } else if (viewMode === 'monthly') {
        setMonthlyData(data);
      } else if (viewMode === 'verify290') {
        setVerify290Data(data);
      } else {
        setPerformanceData(data);
      }
    } catch (err) {
      console.error('Error en consulta:', err);
      setError(err.message || 'Error al obtener datos. Verifique la conexión con la API.');
    } finally {
      setLoading(false);
    }
  };

  // Si estamos en la vista de administración (usuarios o auditoría)
  if (currentView === 'users' || currentView === 'audit') {
    return (
      <div className="app">
        <Header
          eots={eots}
          selectedEots={selectedEots}
          setSelectedEots={setSelectedEots}
          fecha={fecha}
          setFecha={setFecha}
          modoVisualizacion={modoVisualizacion}
          setModoVisualizacion={setModoVisualizacion}
          viewMode={viewMode}
          setViewMode={setViewMode}
          onObtenerCBD={handleConsulta}
          loading={loading}
          theme={theme}
          setTheme={setTheme}
          onLogout={onLogout}
          user={user}
        />
        <div className="content-wrapper">
          {isAdmin && (
            <aside className={`admin-sidebar ${sidebarCollapsed ? 'collapsed' : ''}`}>
              <div className="sidebar-header">
                {!sidebarCollapsed && <h2>Administración</h2>}
                <button
                  className="sidebar-toggle"
                  onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
                  title={sidebarCollapsed ? "Mostrar menú" : "Ocultar menú"}
                >
                  {sidebarCollapsed ? "➡️" : "⬅️"}
                </button>
              </div>
              <nav className="sidebar-nav">
                <button
                  className={`sidebar-item ${adminTab === 'users' ? 'active' : ''}`}
                  onClick={() => {
                    setAdminTab('users');
                    setCurrentView('users');
                    window.location.hash = '#/admin/users';
                  }}
                  title={sidebarCollapsed ? "Gestión de Usuarios" : ""}
                >
                  <span className="icon">👤</span>
                  {!sidebarCollapsed && <span>Gestión de Usuarios</span>}
                </button>
                <button
                  className={`sidebar-item ${adminTab === 'audit' ? 'active' : ''}`}
                  onClick={() => {
                    setAdminTab('audit');
                    setCurrentView('audit');
                    window.location.hash = '#/admin/audit';
                  }}
                  title={sidebarCollapsed ? "Auditoría" : ""}
                >
                  <span className="icon">📊</span>
                  {!sidebarCollapsed && <span>Auditoría</span>}
                </button>
                <button
                  className="sidebar-item"
                  onClick={() => {
                    setCurrentView('dashboard');
                    window.location.hash = '#';
                  }}
                  title={sidebarCollapsed ? "Volver al Dashboard" : ""}
                >
                  <span className="icon">🏠</span>
                  {!sidebarCollapsed && <span>Volver al Dashboard</span>}
                </button>
              </nav>
            </aside>
          )}
          <main className="main-content">
            {currentView === 'users' && <UserManagement />}
            {currentView === 'audit' && <AuditSystem />}
          </main>
        </div>
        <footer className="app-footer">
          <p>
            Monitoreo de Indicadores de Desempeño (CBD/IFO) | Resolución GVMT Nº 120/2025 | CID - VMT
          </p>
        </footer>
      </div>
    );
  }

  return (
    <div className="app">
      <Header
        eots={eots}
        selectedEots={selectedEots}
        setSelectedEots={setSelectedEots}
        fecha={fecha}
        setFecha={setFecha}
        modoVisualizacion={modoVisualizacion}
        setModoVisualizacion={setModoVisualizacion}
        viewMode={viewMode}
        setViewMode={setViewMode}
        onObtenerCBD={handleConsulta}
        loading={loading}
        theme={theme}
        setTheme={setTheme}
        onLogout={onLogout}
        user={user}
      />

      <main className="main-content">
        {error && (
          <div className="error-message">
            <h3>⚠️ Error</h3>
            <p>{error}</p>
          </div>
        )}

        {loading && (
          <div className="loading-spinner">
            <div className="spinner"></div>
            <p>Cargando datos de CBD...</p>
          </div>
        )}

        {!loading && !error && viewMode === 'live' && (
          <CBDTable cbdData={cbdData} />
        )}

        {!loading && !error && viewMode === 'performance' && (
          <PerformanceDashboard performanceData={performanceData} />
        )}

        {!loading && !error && viewMode === 'indices' && (
          <IndicesDashboard performanceData={performanceData} fecha={fecha} />
        )}

        {!loading && !error && viewMode === 'monthly' && (
          <MonthlyPerformanceDashboard data={monthlyData} />
        )}

        {!loading && !error && viewMode === 'verify290' && (
          <Verify290Dashboard data={verify290Data} />
        )}

        {viewMode === 'system-ifo' && (
          <SystemIFODashboard
            year={fecha ? parseInt(fecha.split('-')[0]) : new Date().getFullYear()}
            month={fecha ? parseInt(fecha.split('-')[1]) : new Date().getMonth() + 1}
          />
        )}
      </main>

      <footer className="app-footer">
        <p>
          {/* Monitor de CBD - Control de Buses Distintos |
          Desarrollado con FastAPI + React */}
          {/* Sistema Integral de Control y Monitoreo | CID - Viceministerio de Transporte | Res. GVMT Nº 120/2025 */}
          Monitoreo de Indicadores de Desempeño (CBD/IFO) | Resolución GVMT Nº 120/2025 | CID - VMT
        </p>
      </footer>
    </div>
  );
}

export default App;
