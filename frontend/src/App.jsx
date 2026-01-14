/**
 * Componente principal de la aplicación
 * Gestiona el estado y las llamadas a la API
 */

import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import CBDTable from './components/CBDTable';
import PerformanceDashboard from './components/PerformanceDashboard';
import IndicesDashboard from './components/IndicesDashboard';
import './App.css';

// URL base de la API - Cambiar según el entorno
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

function App() {
  // Estados
  const [eots, setEots] = useState([]);
  const [selectedEots, setSelectedEots] = useState([]);
  const [fecha, setFecha] = useState('');
  const [modoVisualizacion, setModoVisualizacion] = useState('franja');
  const [viewMode, setViewMode] = useState('live'); // 'live' | 'performance' | 'indices'
  const [cbdData, setCbdData] = useState(null);
  const [performanceData, setPerformanceData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [theme, setTheme] = useState('ejecutivo'); // 'mopc' | 'institucional' | 'ejecutivo' | 'claro' | 'nocturno'

  // Cargar EOTs al montar el componente
  useEffect(() => {
    fetchEots();
    // Establecer fecha actual por defecto
    const today = new Date().toISOString().split('T')[0];
    setFecha(today);

    // Cargar tema guardado
    const savedTheme = localStorage.getItem('cbd-theme') || 'ejecutivo';
    setTheme(savedTheme);
    document.documentElement.setAttribute('data-theme', savedTheme);
  }, []);

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
    setLoading(true);
    setError(null);
    setCbdData(null);
    setPerformanceData(null);

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
      </main>

      <footer className="app-footer">
        <p>
          Monitor de CBD - Control de Buses Distintos |
          Desarrollado con FastAPI + React
        </p>
      </footer>
    </div>
  );
}

export default App;
