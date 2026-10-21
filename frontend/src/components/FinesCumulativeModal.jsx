import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { API_BASE_URL } from '../config';
import './FinesCumulativeModal.css';

const MESES = [
  { id: 1, nombre: 'Enero' },
  { id: 2, nombre: 'Febrero' },
  { id: 3, nombre: 'Marzo' },
  { id: 4, nombre: 'Abril' },
  { id: 5, nombre: 'Mayo' },
  { id: 6, nombre: 'Junio' },
  { id: 7, nombre: 'Julio' },
  { id: 8, nombre: 'Agosto' },
  { id: 9, nombre: 'Setiembre' },
  { id: 10, nombre: 'Octubre' },
  { id: 11, nombre: 'Noviembre' },
  { id: 12, nombre: 'Diciembre' }
];

const ANIOS = [2026, 2025, 2024];

const FinesCumulativeModal = ({ isOpen, onClose, initialStartMonth = 7, initialStartYear = 2026, initialEndMonth = 9, initialEndYear = 2026 }) => {
  // Rango de fechas
  const [startMonth, setStartMonth] = useState(initialStartMonth);
  const [startYear, setStartYear] = useState(initialStartYear);
  const [endMonth, setEndMonth] = useState(initialEndMonth);
  const [endYear, setEndYear] = useState(initialEndYear);

  // Parámetros normativos
  const [evaluarReincidencia, setEvaluarReincidencia] = useState(true);
  const [excluirNivelB, setExcluirNivelB] = useState(false);
  const [aplicarNonBisInIdem, setAplicarNonBisInIdem] = useState(true);
  const [excluirArapoti, setExcluirArapoti] = useState(true);

  // Estado de datos
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [cumulativeData, setCumulativeData] = useState(null);

  // Filtros y UI
  const [activeTab, setActiveTab] = useState('matriz'); // 'matriz', 'ranking', 'evolucion', 'articulos'
  const [searchTerm, setSearchTerm] = useState('');
  const [sortField, setSortField] = useState('total_jornales');
  const [sortDirection, setSortDirection] = useState('desc'); // 'asc' | 'desc'
  const [selectedEmpresaDetalle, setSelectedEmpresaDetalle] = useState(null);

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('es-PY', { style: 'currency', currency: 'PYG', maximumFractionDigits: 0 }).format(amount || 0);
  };

  const formatNumber = (num) => {
    return new Intl.NumberFormat('es-PY').format(num || 0);
  };

  // Función para obtener la lista de meses entre start y end
  const getMonthsList = useCallback(() => {
    const list = [];
    let curY = parseInt(startYear, 10);
    let curM = parseInt(startMonth, 10);
    const stopY = parseInt(endYear, 10);
    const stopM = parseInt(endMonth, 10);

    while (curY < stopY || (curY === stopY && curM <= stopM)) {
      const mesObj = MESES.find(m => m.id === curM);
      list.push({
        year: curY,
        month: curM,
        key: `${curY}-${String(curM).padStart(2, '0')}`,
        label: `${mesObj ? mesObj.nombre : curM} ${curY}`,
        shortLabel: `${mesObj ? mesObj.nombre.slice(0, 3) : curM} ${curY.toString().slice(-2)}`
      });
      if (curM === 12) {
        curY += 1;
        curM = 1;
      } else {
        curM += 1;
      }
    }
    return list;
  }, [startMonth, startYear, endMonth, endYear]);

  // Función principal de carga (con backend directo o fallback client-side)
  const fetchCumulativeData = useCallback(async () => {
    if (!isOpen) return;

    // Validar orden de fechas
    if (startYear > endYear || (startYear === endYear && startMonth > endMonth)) {
      setError('El mes de inicio no puede ser posterior al mes de fin.');
      return;
    }

    setLoading(true);
    setError(null);

    const payload = {
      start_month: parseInt(startMonth, 10),
      start_year: parseInt(startYear, 10),
      end_month: parseInt(endMonth, 10),
      end_year: parseInt(endYear, 10),
      evaluar_reincidencia: evaluarReincidencia,
      excluir_nivel_b: excluirNivelB,
      aplicar_non_bis_in_idem: aplicarNonBisInIdem
    };

    try {
      // 1. Intentar endpoint dedicado
      const resp = await fetch(`${API_BASE_URL}/fines-report/cumulative`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (resp.ok) {
        const json = await resp.json();
        setCumulativeData(json);
        setLoading(false);
        return;
      }

      console.warn('Endpoint /fines-report/cumulative respondió con error o no existe, usando fallback...');
      // 2. Fallback: Consultar cada mes individualmente y consolidar client-side
      const monthsList = getMonthsList();
      const monthPromises = monthsList.map(async (m) => {
        const mResp = await fetch(`${API_BASE_URL}/fines-report`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            month: m.month,
            year: m.year,
            evaluar_reincidencia: evaluarReincidencia,
            excluir_nivel_b: excluirNivelB,
            aplicar_non_bis_in_idem: aplicarNonBisInIdem
          })
        });
        if (!mResp.ok) throw new Error(`Error en mes ${m.label}`);
        const mJson = await mResp.json();
        return {
          ...m,
          reporte: mJson.reporte || []
        };
      });

      const monthResults = await Promise.all(monthPromises);

      // Consolidar datos client-side
      const mesesResumen = [];
      const empresasMap = {};

      monthResults.forEach(mr => {
        const filteredReporte = mr.reporte.filter(e => !excluirArapoti || !e.eot_nombre.toUpperCase().includes('ARAPOTI'));
        const mJornales = filteredReporte.reduce((sum, e) => sum + (e.total_jornales || 0), 0);
        const mMonto = filteredReporte.reduce((sum, e) => sum + (e.total_guaranies || 0), 0);

        mesesResumen.push({
          year: mr.year,
          month: mr.month,
          key: mr.key,
          label: mr.label,
          shortLabel: mr.shortLabel,
          total_jornales: mJornales,
          total_guaranies: mMonto,
          empresas_sancionadas: filteredReporte.length
        });

        filteredReporte.forEach(emp => {
          const hex = emp.eot_hex;
          if (!empresasMap[hex]) {
            empresasMap[hex] = {
              eot_nombre: emp.eot_nombre,
              eot_hex: hex,
              total_jornales: 0,
              total_guaranies: 0,
              total_infracciones: 0,
              meses: {},
              por_articulo: {},
              alerta_sumario: false,
              motivos_sumario: [],
              infracciones: []
            };
          }

          const eEntry = empresasMap[hex];
          eEntry.total_jornales += emp.total_jornales || 0;
          eEntry.total_guaranies += emp.total_guaranies || 0;
          eEntry.total_infracciones += emp.total_infracciones || 0;

          if (emp.alerta_sumario) {
            eEntry.alerta_sumario = true;
            (emp.motivos_sumario || []).forEach(mot => {
              if (!eEntry.motivos_sumario.includes(mot)) eEntry.motivos_sumario.push(mot);
            });
          }

          eEntry.meses[mr.key] = {
            jornales: emp.total_jornales || 0,
            monto: emp.total_guaranies || 0,
            infracciones: emp.total_infracciones || 0
          };

          (emp.infracciones || []).forEach(inf => {
            eEntry.infracciones.push({
              ...inf,
              mes: mr.key,
              mes_label: mr.label
            });
            const base = inf.base || 'Otros';
            if (!eEntry.por_articulo[base]) {
              eEntry.por_articulo[base] = { jornales: 0, monto: 0, conteo: 0 };
            }
            eEntry.por_articulo[base].jornales += inf.jornales || 0;
            eEntry.por_articulo[base].monto += inf.monto || 0;
            eEntry.por_articulo[base].conteo += 1;
          });
        });
      });

      const listaEmpresas = Object.values(empresasMap);
      listaEmpresas.forEach(e => {
        mesesResumen.forEach(mr => {
          if (!e.meses[mr.key]) {
            e.meses[mr.key] = { jornales: 0, monto: 0, infracciones: 0 };
          }
        });
      });

      listaEmpresas.sort((a, b) => b.total_jornales - a.total_jornales);

      const granTotalJornales = listaEmpresas.reduce((sum, e) => sum + e.total_jornales, 0);
      const granTotalGuaranies = listaEmpresas.reduce((sum, e) => sum + e.total_guaranies, 0);
      const granTotalInfracciones = listaEmpresas.reduce((sum, e) => sum + e.total_infracciones, 0);

      const articulosGlobal = {};
      listaEmpresas.forEach(e => {
        Object.entries(e.por_articulo).forEach(([art, vals]) => {
          if (!articulosGlobal[art]) {
            articulosGlobal[art] = { jornales: 0, monto: 0, conteo: 0 };
          }
          articulosGlobal[art].jornales += vals.jornales;
          articulosGlobal[art].monto += vals.monto;
          articulosGlobal[art].conteo += vals.conteo;
        });
      });

      setCumulativeData({
        periodo: {
          start_year: parseInt(startYear, 10),
          start_month: parseInt(startMonth, 10),
          end_year: parseInt(endYear, 10),
          end_month: parseInt(endMonth, 10),
          total_meses: mesesResumen.length
        },
        meses: mesesResumen,
        totales_generales: {
          total_jornales: granTotalJornales,
          total_guaranies: granTotalGuaranies,
          total_infracciones: granTotalInfracciones,
          empresas_sancionadas: listaEmpresas.length,
          empresas_sumario: listaEmpresas.filter(e => e.alerta_sumario).length,
          por_articulo: articulosGlobal,
          top_empresas: listaEmpresas.slice(0, 10).map(e => ({
            eot_nombre: e.eot_nombre,
            eot_hex: e.eot_hex,
            total_jornales: e.total_jornales,
            total_guaranies: e.total_guaranies
          }))
        },
        empresas: listaEmpresas
      });

    } catch (err) {
      console.error(err);
      setError(err.message || 'Error al calcular las estadísticas acumuladas');
    } finally {
      setLoading(false);
    }
  }, [isOpen, startMonth, startYear, endMonth, endYear, evaluarReincidencia, excluirNivelB, aplicarNonBisInIdem, excluirArapoti, getMonthsList]);

  // Cargar datos al abrir el modal
  useEffect(() => {
    if (isOpen) {
      fetchCumulativeData();
    }
  }, [isOpen, fetchCumulativeData]);

  // Preset de botones rápidos
  const handleQuickPreset = (sM, sY, eM, eY) => {
    setStartMonth(sM);
    setStartYear(sY);
    setEndMonth(eM);
    setEndYear(eY);
  };

  // Filtrado y ordenamiento de empresas en memoria
  const filteredEmpresas = useMemo(() => {
    if (!cumulativeData || !cumulativeData.empresas) return [];
    let list = cumulativeData.empresas;

    // Filtro Arapotí si aplica
    if (excluirArapoti) {
      list = list.filter(e => !e.eot_nombre.toUpperCase().includes('ARAPOTI'));
    }

    // Filtro por texto de búsqueda
    if (searchTerm.trim()) {
      const q = searchTerm.toLowerCase();
      list = list.filter(e => e.eot_nombre.toLowerCase().includes(q) || e.eot_hex.toLowerCase().includes(q));
    }

    // Ordenamiento
    list = [...list].sort((a, b) => {
      let valA, valB;
      if (sortField === 'eot_nombre') {
        valA = a.eot_nombre.toLowerCase();
        valB = b.eot_nombre.toLowerCase();
        return sortDirection === 'asc' ? valA.localeCompare(valB) : valB.localeCompare(valA);
      } else if (sortField === 'total_jornales') {
        valA = a.total_jornales;
        valB = b.total_jornales;
      } else if (sortField === 'total_guaranies') {
        valA = a.total_guaranies;
        valB = b.total_guaranies;
      } else if (sortField === 'total_infracciones') {
        valA = a.total_infracciones;
        valB = b.total_infracciones;
      } else if (sortField.startsWith('mes_')) {
        const mKey = sortField.replace('mes_', '');
        valA = (a.meses[mKey] && a.meses[mKey].jornales) || 0;
        valB = (b.meses[mKey] && b.meses[mKey].jornales) || 0;
      } else {
        valA = a.total_jornales;
        valB = b.total_jornales;
      }

      if (sortDirection === 'asc') return valA > valB ? 1 : -1;
      return valA < valB ? 1 : -1;
    });

    return list;
  }, [cumulativeData, searchTerm, sortField, sortDirection, excluirArapoti]);

  const handleSort = (field) => {
    if (sortField === field) {
      setSortDirection(prev => prev === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('desc');
    }
  };

  // Exportar a CSV
  const handleExportCSV = () => {
    if (!cumulativeData || !filteredEmpresas.length) return;
    const meses = cumulativeData.meses || [];
    
    // Encabezados
    const headers = [
      'Empresa',
      'Código Hex',
      ...meses.map(m => `Jornales ${m.label}`),
      'Total Jornales Acumulados',
      'Total Monto Gs.',
      'Total Infracciones',
      'Alerta Sumario (Art. 18.2)'
    ];

    const rows = filteredEmpresas.map(emp => {
      return [
        `"${emp.eot_nombre}"`,
        `"${emp.eot_hex}"`,
        ...meses.map(m => (emp.meses[m.key] ? emp.meses[m.key].jornales : 0)),
        emp.total_jornales,
        emp.total_guaranies,
        emp.total_infracciones,
        emp.alerta_sumario ? 'SÍ' : 'NO'
      ];
    });

    const csvContent = 'data:text/csv;charset=utf-8,\uFEFF' + [headers.join(';'), ...rows.map(r => r.join(';'))].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `Multas_Acumuladas_${startYear}_${startMonth}_a_${endYear}_${endMonth}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  if (!isOpen) return null;

  const mesesHeaders = (cumulativeData && cumulativeData.meses) || [];
  const maxJornalesEmpresa = filteredEmpresas.length > 0 ? Math.max(...filteredEmpresas.map(e => e.total_jornales)) : 1;

  return (
    <div className="fines-cumulative-overlay" id="fines-cumulative-modal">
      <div className="fines-cumulative-container">
        
        {/* HEADER */}
        <header className="fines-cumulative-header">
          <div className="header-left">
            <span className="header-badge">📊 AUDITORÍA MULTI-MES</span>
            <h2>Reporte Estadístico Acumulado de Multas</h2>
            <p className="header-sub">
              Consolidación periódica de infracciones y cálculo acumulado por empresa bajo Resolución GVMT Nº 120/2025 y 104/2026
            </p>
          </div>
          <div className="header-right">
            <button className="cum-btn-close" onClick={onClose} title="Cerrar ventana">✖</button>
          </div>
        </header>

        {/* CONTROLES Y FILTROS */}
        <section className="fines-cumulative-controls">
          <div className="controls-row">
            
            {/* SELECTOR DE RANGO */}
            <div className="filter-group-date">
              <span className="filter-label"><i className="fa-solid fa-calendar-range"></i> Periodo de Análisis:</span>
              
              <div className="date-selectors-box">
                <div className="date-select-item">
                  <label>Desde:</label>
                  <select 
                    id="select-start-month"
                    value={startMonth} 
                    onChange={(e) => setStartMonth(parseInt(e.target.value, 10))}
                  >
                    {MESES.map(m => (
                      <option key={m.id} value={m.id}>{m.nombre}</option>
                    ))}
                  </select>
                  <select 
                    id="select-start-year"
                    value={startYear} 
                    onChange={(e) => setStartYear(parseInt(e.target.value, 10))}
                  >
                    {ANIOS.map(y => (
                      <option key={y} value={y}>{y}</option>
                    ))}
                  </select>
                </div>

                <div className="date-separator">&rarr;</div>

                <div className="date-select-item">
                  <label>Hasta:</label>
                  <select 
                    id="select-end-month"
                    value={endMonth} 
                    onChange={(e) => setEndMonth(parseInt(e.target.value, 10))}
                  >
                    {MESES.map(m => (
                      <option key={m.id} value={m.id}>{m.nombre}</option>
                    ))}
                  </select>
                  <select 
                    id="select-end-year"
                    value={endYear} 
                    onChange={(e) => setEndYear(parseInt(e.target.value, 10))}
                  >
                    {ANIOS.map(y => (
                      <option key={y} value={y}>{y}</option>
                    ))}
                  </select>
                </div>
              </div>
            </div>

            {/* BOTONES RÁPIDOS */}
            <div className="preset-buttons">
              <span className="preset-label">Accesos rápidos:</span>
              <button 
                id="btn-preset-t3"
                className={`btn-preset ${startMonth === 7 && endMonth === 9 && startYear === 2026 && endYear === 2026 ? 'active' : ''}`}
                onClick={() => handleQuickPreset(7, 2026, 9, 2026)}
              >
                📅 T3 2026 (Jul - Set)
              </button>
              <button 
                id="btn-preset-ultimos2"
                className={`btn-preset ${startMonth === 8 && endMonth === 9 && startYear === 2026 && endYear === 2026 ? 'active' : ''}`}
                onClick={() => handleQuickPreset(8, 2026, 9, 2026)}
              >
                📅 Ago - Set 2026
              </button>
              <button 
                id="btn-preset-etapa2"
                className={`btn-preset ${startMonth === 5 && endMonth === 10 && startYear === 2026 && endYear === 2026 ? 'active' : ''}`}
                onClick={() => handleQuickPreset(5, 2026, 10, 2026)}
              >
                📅 Etapa 2 (May - Oct 2026)
              </button>
            </div>

            {/* BOTÓN CONSULTAR */}
            <button 
              id="btn-submit-cumulative"
              className="btn-fetch-cum" 
              onClick={fetchCumulativeData}
              disabled={loading}
            >
              {loading ? 'Calculando...' : '🔄 Actualizar'}
            </button>
          </div>

          {/* CHECKBOXES NORMATIVOS */}
          <div className="options-row">
            <label className="checkbox-pill reincidencia">
              <input
                type="checkbox"
                checked={evaluarReincidencia}
                onChange={(e) => setEvaluarReincidencia(e.target.checked)}
              />
              Calcular con reincidencia (Art. 16)
            </label>
            <label className="checkbox-pill nivel-b">
              <input
                type="checkbox"
                checked={excluirNivelB}
                onChange={(e) => setExcluirNivelB(e.target.checked)}
              />
              Excluir Nivel B (15.2 y 15.4)
            </label>
            <label className="checkbox-pill non-bis">
              <input
                type="checkbox"
                checked={aplicarNonBisInIdem}
                onChange={(e) => setAplicarNonBisInIdem(e.target.checked)}
              />
              Res. 104/2026 (Consolidación)
            </label>
            <label className="checkbox-pill arapoti">
              <input
                type="checkbox"
                checked={excluirArapoti}
                onChange={(e) => setExcluirArapoti(e.target.checked)}
              />
              Excluir Arapotí (Intervención)
            </label>
          </div>
        </section>

        {/* CONTENIDO PRINCIPAL */}
        <div className="fines-cumulative-body">
          {loading ? (
            <div className="cum-loader-box">
              <div className="cum-spinner"></div>
              <h3>Consolidando métricas de multas periódicas...</h3>
              <p>Procesando franjas, días atípicos y reincidencias para los meses seleccionados.</p>
            </div>
          ) : error ? (
            <div className="cum-error-box">
              <h3>⚠️ Ocurrió un error</h3>
              <p>{error}</p>
              <button className="btn-preset active" onClick={fetchCumulativeData}>Reintentar consulta</button>
            </div>
          ) : cumulativeData ? (
            <>
              {/* TARJETAS KPI RESUMEN */}
              <div className="cum-kpi-grid">
                <div className="cum-kpi-card highlight-green">
                  <div className="kpi-icon">💰</div>
                  <div className="kpi-content">
                    <span className="kpi-title">Monto Total Acumulado</span>
                    <span className="kpi-val">{formatCurrency(cumulativeData.totales_generales.total_guaranies)}</span>
                    <span className="kpi-sub">{mesesHeaders.length} meses analizados</span>
                  </div>
                </div>

                <div className="cum-kpi-card highlight-blue">
                  <div className="kpi-icon">⚖️</div>
                  <div className="kpi-content">
                    <span className="kpi-title">Total Jornales Acumulados</span>
                    <span className="kpi-val">{formatNumber(cumulativeData.totales_generales.total_jornales)} <small>jornales</small></span>
                    <span className="kpi-sub">Valor ref: Gs. 117.077 / día</span>
                  </div>
                </div>

                <div className="cum-kpi-card highlight-purple">
                  <div className="kpi-icon">🏢</div>
                  <div className="kpi-content">
                    <span className="kpi-title">Empresas con Sanciones</span>
                    <span className="kpi-val">{filteredEmpresas.length} <small>empresas</small></span>
                    <span className="kpi-sub">Con al menos 1 falta registrada</span>
                  </div>
                </div>

                <div className="cum-kpi-card highlight-amber">
                  <div className="kpi-icon">🚨</div>
                  <div className="kpi-content">
                    <span className="kpi-title">Total de Infracciones</span>
                    <span className="kpi-val">{formatNumber(cumulativeData.totales_generales.total_infracciones)} <small>hechos</small></span>
                    <span className="kpi-sub">Franjas C + IFO Mes + Nivel B</span>
                  </div>
                </div>

                {cumulativeData.totales_generales.empresas_sumario > 0 && (
                  <div className="cum-kpi-card highlight-red">
                    <div className="kpi-icon">⚠️</div>
                    <div className="kpi-content">
                      <span className="kpi-title">Alerta de Sumario (Art. 18.2)</span>
                      <span className="kpi-val text-red">{cumulativeData.totales_generales.empresas_sumario} <small>empresas</small></span>
                      <span className="kpi-sub">&ge; 3 fallas IFO o &ge; 20 multas trim.</span>
                    </div>
                  </div>
                )}
              </div>

              {/* BARRA DE ACCIONES Y PESTAÑAS */}
              <div className="cum-view-tabs-bar">
                <div className="cum-tabs">
                  <button 
                    id="tab-matriz"
                    className={`cum-tab-btn ${activeTab === 'matriz' ? 'active' : ''}`}
                    onClick={() => setActiveTab('matriz')}
                  >
                    🏢 Matriz Acumulada por Empresa
                  </button>
                  <button 
                    id="tab-ranking"
                    className={`cum-tab-btn ${activeTab === 'ranking' ? 'active' : ''}`}
                    onClick={() => setActiveTab('ranking')}
                  >
                    🏆 Ranking Top Infractoras
                  </button>
                  <button 
                    id="tab-evolucion"
                    className={`cum-tab-btn ${activeTab === 'evolucion' ? 'active' : ''}`}
                    onClick={() => setActiveTab('evolucion')}
                  >
                    📈 Evolución Mes a Mes
                  </button>
                  <button 
                    id="tab-articulos"
                    className={`cum-tab-btn ${activeTab === 'articulos' ? 'active' : ''}`}
                    onClick={() => setActiveTab('articulos')}
                  >
                    ⚖️ Desglose por Artículo
                  </button>
                </div>

                <div className="cum-actions-group">
                  <button 
                    id="btn-export-csv"
                    className="cum-btn-secondary" 
                    onClick={handleExportCSV}
                    title="Descargar tabla en formato CSV para Excel"
                  >
                    📥 Exportar CSV
                  </button>
                  <button 
                    id="btn-print-summary"
                    className="cum-btn-secondary" 
                    onClick={() => window.print()}
                    title="Imprimir resumen ejecutivo"
                  >
                    🖨️ Imprimir
                  </button>
                </div>
              </div>

              {/* VISTA 1: MATRIZ POR EMPRESA */}
              {activeTab === 'matriz' && (
                <div className="cum-tab-content">
                  {/* Buscador */}
                  <div className="cum-search-bar">
                    <div className="search-input-wrapper">
                      <span className="search-icon">🔍</span>
                      <input 
                        id="input-search-empresa"
                        type="text" 
                        placeholder="Buscar empresa por nombre o código..."
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                      />
                      {searchTerm && (
                        <button className="clear-search" onClick={() => setSearchTerm('')}>✖</button>
                      )}
                    </div>
                    <span className="search-count">Mostrando {filteredEmpresas.length} empresas</span>
                  </div>

                  {/* Tabla Matriz */}
                  <div className="cum-table-wrapper">
                    <table className="cum-table" id="tabla-multas-acumuladas">
                      <thead>
                        <tr>
                          <th className="th-center sortable" onClick={() => handleSort('ranking')}>#</th>
                          <th className="th-left sortable" onClick={() => handleSort('eot_nombre')}>
                            Empresa {sortField === 'eot_nombre' && (sortDirection === 'asc' ? '▲' : '▼')}
                          </th>
                          {mesesHeaders.map(m => (
                            <th 
                              key={m.key} 
                              className="th-right sortable th-month"
                              onClick={() => handleSort(`mes_${m.key}`)}
                              title={`Ordenar por jornales de ${m.label}`}
                            >
                              {m.shortLabel} {sortField === `mes_${m.key}` && (sortDirection === 'asc' ? '▲' : '▼')}
                            </th>
                          ))}
                          <th className="th-right sortable th-total" onClick={() => handleSort('total_jornales')}>
                            Total Jornales {sortField === 'total_jornales' && (sortDirection === 'asc' ? '▲' : '▼')}
                          </th>
                          <th className="th-right sortable th-monto" onClick={() => handleSort('total_guaranies')}>
                            Total Monto (Gs.) {sortField === 'total_guaranies' && (sortDirection === 'asc' ? '▲' : '▼')}
                          </th>
                          <th className="th-center">Infracciones Detectadas</th>
                          <th className="th-center">Acciones</th>
                        </tr>
                      </thead>
                      <tbody>
                        {filteredEmpresas.length === 0 ? (
                          <tr>
                            <td colSpan={mesesHeaders.length + 6} className="td-empty">
                              No se encontraron registros para el filtro aplicado.
                            </td>
                          </tr>
                        ) : (
                          filteredEmpresas.map((emp, idx) => {
                            const barPct = Math.min(Math.round((emp.total_jornales / maxJornalesEmpresa) * 100), 100);
                            return (
                              <tr key={emp.eot_hex} className={emp.alerta_sumario ? 'row-alert-sumario' : ''}>
                                <td className="td-center td-rank">{idx + 1}</td>
                                <td className="td-left td-name">
                                  <strong>{emp.eot_nombre}</strong>
                                  <div className="eot-meta-sub">Hex: {emp.eot_hex}</div>
                                  {emp.alerta_sumario && (
                                    <span className="badge-sumario" title={emp.motivos_sumario.join('\n')}>
                                      ⚠️ Alerta Sumario Art. 18.2
                                    </span>
                                  )}
                                </td>

                                {/* Columnas por mes */}
                                {mesesHeaders.map(m => {
                                  const mData = emp.meses[m.key] || { jornales: 0, monto: 0 };
                                  return (
                                    <td key={m.key} className="td-right td-month-val">
                                      {mData.jornales > 0 ? (
                                        <div className="month-val-box">
                                          <span className="m-jornales">{mData.jornales} j</span>
                                          <span className="m-guaranies">{formatCurrency(mData.monto)}</span>
                                        </div>
                                      ) : (
                                        <span className="zero-val">—</span>
                                      )}
                                    </td>
                                  );
                                })}

                                {/* Total Jornales Acumulados */}
                                <td className="td-right td-total-jornales">
                                  <div className="total-jornal-badge">{emp.total_jornales} j</div>
                                  <div className="micro-bar-bg" title={`${barPct}% respecto al máximo`}>
                                    <div className="micro-bar-fill" style={{ width: `${barPct}%` }}></div>
                                  </div>
                                </td>

                                {/* Total Monto Gs */}
                                <td className="td-right td-total-monto">
                                  <strong>{formatCurrency(emp.total_guaranies)}</strong>
                                </td>

                                {/* Desglose badges */}
                                <td className="td-center td-badges">
                                  <div className="articulos-badges-group">
                                    {Object.entries(emp.por_articulo || {}).map(([art, vals]) => {
                                      if (vals.conteo === 0) return null;
                                      return (
                                        <span key={art} className="badge-art" title={`${art}: ${vals.conteo} falta(s), ${vals.jornales} jornales`}>
                                          {art}: {vals.conteo}
                                        </span>
                                      );
                                    })}
                                  </div>
                                </td>

                                {/* Botón ver detalle */}
                                <td className="td-center td-actions">
                                  <button 
                                    className="btn-view-detail"
                                    onClick={() => setSelectedEmpresaDetalle(emp)}
                                    title="Ver todas las faltas individuales de esta empresa"
                                  >
                                    👁️ Detalle ({emp.infracciones.length})
                                  </button>
                                </td>
                              </tr>
                            );
                          })
                        )}
                      </tbody>
                      <tfoot>
                        <tr className="tr-footer-totals">
                          <td colSpan={2} className="td-left">
                            <strong>TOTAL GENERAL CONSOLIDADO</strong>
                          </td>
                          {mesesHeaders.map(m => (
                            <td key={m.key} className="td-right">
                              <strong>{m.total_jornales} j</strong>
                              <div className="footer-monto">{formatCurrency(m.total_guaranies)}</div>
                            </td>
                          ))}
                          <td className="td-right">
                            <strong className="footer-grand-jornales">
                              {cumulativeData.totales_generales.total_jornales} j
                            </strong>
                          </td>
                          <td className="td-right">
                            <strong className="footer-grand-monto">
                              {formatCurrency(cumulativeData.totales_generales.total_guaranies)}
                            </strong>
                          </td>
                          <td colSpan={2} className="td-center">
                            {cumulativeData.totales_generales.total_infracciones} faltas totales
                          </td>
                        </tr>
                      </tfoot>
                    </table>
                  </div>
                </div>
              )}

              {/* VISTA 2: RANKING TOP EMPRESAS */}
              {activeTab === 'ranking' && (
                <div className="cum-tab-content">
                  <div className="ranking-panel">
                    <h3>🏆 Ranking de Empresas con Mayor Sanción Acumulada ({mesesHeaders.map(m => m.label).join(' - ')})</h3>
                    <p className="ranking-sub">Las 10 empresas con mayor volumen de sanciones representan el impacto financiero predominante del sistema.</p>

                    <div className="ranking-bars-list">
                      {filteredEmpresas.slice(0, 10).map((emp, i) => {
                        const pctMax = Math.round((emp.total_jornales / maxJornalesEmpresa) * 100);
                        const pctTotal = ((emp.total_jornales / cumulativeData.totales_generales.total_jornales) * 100).toFixed(1);
                        return (
                          <div key={emp.eot_hex} className="ranking-bar-item">
                            <div className="ranking-item-header">
                              <span className="rank-pos">#{i + 1}</span>
                              <strong className="rank-name">{emp.eot_nombre}</strong>
                              <span className="rank-jornales">{emp.total_jornales} jornales</span>
                              <span className="rank-monto">{formatCurrency(emp.total_guaranies)}</span>
                              <span className="rank-share">{pctTotal}% del total</span>
                            </div>
                            <div className="rank-bar-track">
                              <div className="rank-bar-progress" style={{ width: `${pctMax}%` }}>
                                <span className="rank-bar-label">{emp.total_jornales} j</span>
                              </div>
                            </div>
                            {/* Desglose mini de meses */}
                            <div className="rank-months-pills">
                              {mesesHeaders.map(m => {
                                const mJ = (emp.meses[m.key] && emp.meses[m.key].jornales) || 0;
                                return (
                                  <span key={m.key} className={`pill-m ${mJ > 0 ? 'has-fines' : 'no-fines'}`}>
                                    {m.shortLabel}: {mJ} j
                                  </span>
                                );
                              })}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </div>
              )}

              {/* VISTA 3: EVOLUCIÓN MES A MES */}
              {activeTab === 'evolucion' && (
                <div className="cum-tab-content">
                  <div className="evolucion-panel">
                    <h3>📈 Evolución Temporal del Sistema de Multas</h3>
                    <p className="evolucion-sub">Comparativa mensual de sanciones totales, montos e intensidad regulatoria.</p>

                    <div className="months-evolution-grid">
                      {mesesHeaders.map((m, idx) => {
                        const prevM = idx > 0 ? mesesHeaders[idx - 1] : null;
                        const diffJ = prevM ? m.total_jornales - prevM.total_jornales : 0;
                        const diffPct = prevM && prevM.total_jornales > 0 ? ((diffJ / prevM.total_jornales) * 100).toFixed(1) : null;

                        return (
                          <div key={m.key} className="month-card-stat">
                            <div className="month-card-header">
                              <h4>{m.label}</h4>
                              <span className="month-emp-count">{m.empresas_sancionadas} empresas</span>
                            </div>

                            <div className="month-stat-val">
                              {m.total_jornales} <small>jornales</small>
                            </div>

                            <div className="month-stat-monto">
                              {formatCurrency(m.total_guaranies)}
                            </div>

                            {diffPct !== null && (
                              <div className={`month-diff-pill ${diffJ <= 0 ? 'diff-down' : 'diff-up'}`}>
                                {diffJ <= 0 ? '▼' : '▲'} {diffJ > 0 ? `+${diffJ}` : diffJ} j ({diffPct}%) vs mes anterior
                              </div>
                            )}

                            {/* Barra proporcional */}
                            <div className="month-bar-wrapper">
                              <div 
                                className="month-bar-fill" 
                                style={{ width: `${Math.min(Math.round((m.total_jornales / (cumulativeData.totales_generales.total_jornales || 1)) * 100), 100)}%` }}
                              ></div>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </div>
              )}

              {/* VISTA 4: DESGLOSE POR ARTÍCULO */}
              {activeTab === 'articulos' && (
                <div className="cum-tab-content">
                  <div className="articulos-panel">
                    <h3>⚖️ Distribución Acumulada por Tipo de Infracción</h3>
                    <p className="articulos-sub">Total de sanciones categorizadas según el tipo de falta normativa.</p>

                    <div className="articulos-grid">
                      {Object.entries(cumulativeData.totales_generales.por_articulo || {}).map(([art, vals]) => {
                        const pctJornales = ((vals.jornales / cumulativeData.totales_generales.total_jornales) * 100).toFixed(1);
                        return (
                          <div key={art} className="articulo-card">
                            <div className="art-card-top">
                              <span className="art-title">{art}</span>
                              <span className="art-count">{vals.conteo} hechos</span>
                            </div>

                            <div className="art-jornales">
                              {vals.jornales} <small>jornales ({pctJornales}%)</small>
                            </div>

                            <div className="art-monto">
                              {formatCurrency(vals.monto)}
                            </div>

                            <div className="art-bar-bg">
                              <div className="art-bar-fill" style={{ width: `${pctJornales}%` }}></div>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </div>
              )}

            </>
          ) : null}
        </div>

        {/* MODAL SECUNDARIO: DETALLE DE FALTAS DE UNA EMPRESA */}
        {selectedEmpresaDetalle && (
          <div className="cum-drilldown-overlay">
            <div className="cum-drilldown-modal">
              <div className="drilldown-header">
                <div>
                  <span className="drilldown-badge">HISTORIAL DE SANCIONES</span>
                  <h3>{selectedEmpresaDetalle.eot_nombre}</h3>
                  <p>Código: {selectedEmpresaDetalle.eot_hex} &bull; Total Acumulado: <strong>{selectedEmpresaDetalle.total_jornales} jornales</strong> ({formatCurrency(selectedEmpresaDetalle.total_guaranies)})</p>
                </div>
                <button className="cum-btn-close" onClick={() => setSelectedEmpresaDetalle(null)}>✖</button>
              </div>

              <div className="drilldown-body">
                {selectedEmpresaDetalle.infracciones.length === 0 ? (
                  <p className="text-center py-4">No hay infracciones registradas.</p>
                ) : (
                  <table className="drilldown-table">
                    <thead>
                      <tr>
                        <th>Fecha</th>
                        <th>Mes</th>
                        <th>Artículo</th>
                        <th>Descripción Técnica</th>
                        <th className="th-right">Jornales</th>
                        <th className="th-right">Monto (Gs.)</th>
                      </tr>
                    </thead>
                    <tbody>
                      {selectedEmpresaDetalle.infracciones.map((inf, i) => (
                        <tr key={i}>
                          <td><strong>{inf.fecha}</strong></td>
                          <td><span className="pill-mes-tag">{inf.mes_label || inf.mes}</span></td>
                          <td><span className="pill-art-tag">{inf.base}</span></td>
                          <td>{inf.desc}</td>
                          <td className="th-right"><strong>{inf.jornales}</strong></td>
                          <td className="th-right">{formatCurrency(inf.monto)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>

              <div className="drilldown-footer">
                <button className="btn-preset active" onClick={() => setSelectedEmpresaDetalle(null)}>Cerrar Detalle</button>
              </div>
            </div>
          </div>
        )}

      </div>
    </div>
  );
};

export default FinesCumulativeModal;
