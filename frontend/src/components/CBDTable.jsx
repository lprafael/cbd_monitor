/**
 * Componente CBDTable: Tabla para mostrar datos de CBD
 * - Muestra dos filas por cada EOT (servicios_diarios y cbd_detalle_buses)
 * - Columnas dinámicas según franjas operativas o horas
 * - Checks (✓) cuando se cumplen los parámetros mínimos
 */

import React, { useState } from 'react';
import './CBDTable.css';

const CBDTable = ({ cbdData }) => {
  const [isAnalysisModalOpen, setIsAnalysisModalOpen] = useState(false);
  const [analysisFilter, setAnalysisFilter] = useState('all');

  const handleDownload = () => {
    if (!cbdData) return;
    const { fecha, datos_eots } = cbdData;
    
    // 1. Cabeceras del CSV
    const csvHeaders = ["EOT / Empresa", "Gremio", "Fuente de Datos", ...headers.map(h => `${h.label}${h.subtitle ? ' (' + h.subtitle + ')' : ''}`), "Total"];
    
    // 2. Construir filas
    const csvRows = [];
    
    datos_eots.forEach((eot) => {
      // Fila 1: Validaciones
      const rowServicios = [
        `"${(eot.eot_nombre || '').replace(/"/g, '""')}"`,
        `"${(eot.gre_nombre || 'Sin Gremio').replace(/"/g, '""')}"`,
        `"Buses s/Validaciones"`,
        ...headers.map(h => {
          const dato = eot.fila_servicios.datos_por_franja[h.key];
          return dato && dato.cantidad_buses !== undefined ? dato.cantidad_buses : 0;
        }),
        eot.fila_servicios.total || 0
      ];
      
      // Fila 2: GPS
      const rowCbd = [
        `"${(eot.eot_nombre || '').replace(/"/g, '""')}"`,
        `"${(eot.gre_nombre || 'Sin Gremio').replace(/"/g, '""')}"`,
        `"Buses s/GPS"`,
        ...headers.map(h => {
          const dato = eot.fila_cbd.datos_por_franja[h.key];
          return dato && dato.cantidad_buses !== undefined ? dato.cantidad_buses : 0;
        }),
        eot.fila_cbd.total || 0
      ];
      
      csvRows.push(rowServicios.join(','));
      csvRows.push(rowCbd.join(','));
    });
    
    const csvContent = [csvHeaders.join(','), ...csvRows].join('\n');
    const blob = new Blob(["\ufeff" + csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.setAttribute("href", url);
    link.setAttribute("download", `CBD_Resultados_${fecha}.csv`);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  if (!cbdData) {
    return (
      <div className="empty-state">
        <p>📊 Seleccione los parámetros y haga clic en "Obtener Datos" para ver los datos</p>
      </div>
    );
  }

  const { fecha, nombre_tipo_dia, modo_visualizacion, franjas_operativas, datos_eots, parametros_minimos } = cbdData;

  // Debug: verificar parámetros mínimos
  console.log('=== DEBUG PARÁMETROS MÍNIMOS ===');
  console.log('Parámetros mínimos recibidos:', parametros_minimos);
  console.log('Franjas operativas:', franjas_operativas);
  if (parametros_minimos) {
    console.log('Keys en parametros_minimos:', Object.keys(parametros_minimos));
    Object.keys(parametros_minimos).forEach(key => {
      const param = parametros_minimos[key];
      console.log(`  id_franja ${key}:`, {
        cbd_minimo_franja: param.cbd_minimo_franja,
        cbd_minimo_hora: param.cbd_minimo_hora
      });
    });
  }

  // Generar encabezados de columnas
  const generateHeaders = () => {
    if (modo_visualizacion === 'franja') {
      return franjas_operativas.map(franja => {
        const paramMin = parametros_minimos && parametros_minimos[franja.id_franja];
        // Para modo franja, usar cbd_minimo_franja
        // Verificar que el valor exista (puede ser 0, que es válido)
        // Usar typeof para verificar que sea un número (incluyendo 0)
        let minimo = null;
        if (paramMin) {
          const valorMinimo = paramMin.cbd_minimo_franja;
          if (typeof valorMinimo === 'number') {
            minimo = valorMinimo;
          }
        }
        console.log(`Franja ${franja.id_franja} (${franja.denominacion}): minimo =`, minimo, 'paramMin =', paramMin, 'cbd_minimo_franja =', paramMin?.cbd_minimo_franja, 'tipo:', typeof paramMin?.cbd_minimo_franja);
        return {
          key: String(franja.id_franja),
          label: franja.denominacion,
          subtitle: `${franja.hora_inicio} - ${franja.hora_fin}`,
          minimo: minimo
        };
      });
    } else {
      // Obtener horas mínima y máxima de las franjas operativas
      const horasFranjas = franjas_operativas.flatMap(f => {
        const horaInicio = parseInt(f.hora_inicio.split(':')[0]);
        const horaFin = f.hora_fin === '24:00:00' ? 24 : parseInt(f.hora_fin.split(':')[0]);
        return [horaInicio, horaFin];
      });

      const horaMin = Math.min(...horasFranjas);
      const horaMax = Math.max(...horasFranjas);

      // Generar solo las horas dentro del rango
      return Array.from({ length: horaMax - horaMin + 1 }, (_, i) => {
        const hora = horaMin + i;
        const horaDisplay = hora === 24 ? '24:00' : `${hora}:00`;

        // Buscar el mínimo para esta hora (buscar en las franjas que contengan esta hora)
        let minimo = null;
        if (parametros_minimos) {
          for (const franja of franjas_operativas) {
            const horaInicio = parseInt(franja.hora_inicio.split(':')[0]);
            // Para hora_fin, si es "04:59:59", parseamos como 4
            // Pero "04:59:59" significa que la hora 4 está incluida (hasta antes de las 5:00)
            // Entonces la hora 4 está incluida, pero la hora 5 NO
            let horaFin = parseInt(franja.hora_fin.split(':')[0]);
            if (franja.hora_fin === '24:00:00' || franja.hora_fin.startsWith('24:')) {
              horaFin = 24;
            }
            // La hora está incluida si: hora >= horaInicio && hora < horaFin+1
            // Ejemplo: "03:00:00 - 04:59:59" (horaInicio=3, horaFin=4) incluye horas 3 y 4
            // hora 3: 3 >= 3 && 3 < 5 ✓
            // hora 4: 4 >= 3 && 4 < 5 ✓
            // hora 5: 5 >= 3 && 5 < 5 ✗
            if (hora >= horaInicio && hora < (horaFin + 1)) {
              const paramMin = parametros_minimos[franja.id_franja];
              // Verificar que el valor exista (puede ser 0, que es válido)
              // Usar typeof para verificar que sea un número (incluyendo 0)
              if (paramMin) {
                const valorMinimo = paramMin.cbd_minimo_hora;
                if (typeof valorMinimo === 'number') {
                  minimo = valorMinimo;
                  console.log(`Hora ${hora}:00 - Encontrado mínimo ${minimo} en franja ${franja.id_franja} (${franja.denominacion}), rango: ${franja.hora_inicio} - ${franja.hora_fin}`);
                  break;
                } else {
                  console.log(`Hora ${hora}:00 - Franja ${franja.id_franja} (${franja.denominacion}) no tiene cbd_minimo_hora válido. Valor:`, valorMinimo, 'tipo:', typeof valorMinimo);
                }
              } else {
                console.log(`Hora ${hora}:00 - Franja ${franja.id_franja} (${franja.denominacion}) no tiene paramMin.`);
              }
            }
          }
          if (minimo === null) {
            console.log(`Hora ${hora}:00 - No se encontró mínimo. Franjas disponibles:`,
              franjas_operativas.map(f => {
                const hInicio = parseInt(f.hora_inicio.split(':')[0]);
                let hFin = parseInt(f.hora_fin.split(':')[0]);
                if (f.hora_fin === '24:00:00' || f.hora_fin.startsWith('24:')) {
                  hFin = 24;
                }
                const contieneHora = hora >= hInicio && hora < (hFin + 1);
                return {
                  id: f.id_franja,
                  nombre: f.denominacion,
                  inicio: f.hora_inicio,
                  fin: f.hora_fin,
                  hInicio,
                  hFin,
                  contieneHora,
                  paramMin: parametros_minimos[f.id_franja],
                  tieneMinimo: parametros_minimos[f.id_franja]?.cbd_minimo_hora !== null && parametros_minimos[f.id_franja]?.cbd_minimo_hora !== undefined
                };
              }));
          }
        } else {
          console.log(`Hora ${hora}:00 - parametros_minimos es null/undefined`);
        }

        return {
          key: String(hora),
          label: horaDisplay,
          subtitle: '',
          minimo: minimo
        };
      });
    }
  };
  const headers = generateHeaders();

  // Renderizar celda con datos (individual)
  const renderCelda = (dato, cumpleConjunto = null) => {
    console.log('Datos en renderCelda:', dato); // Para depuración

    // Si no hay dato, usar 0 como valor por defecto
    const cantidad = (dato && dato.cantidad_buses !== undefined) ? dato.cantidad_buses : 0;
    const parametroMinimo = dato ? dato.parametro_minimo : null;

    // Determinar si esta celda individual cumple (para el icono)
    const cumpleIndividual = dato && dato.cumple_parametro === true;

    // Usar cumpleConjunto para el color (si está definido), sino usar el individual
    const claseColor = (cumpleConjunto !== null ? cumpleConjunto : cumpleIndividual) ? 'cumple' : 'no-cumple';

    return (
      <td className={`celda-datos ${claseColor}`}>
        <div className="celda-content">
          <span className="cantidad">{cantidad}</span>
          {cumpleIndividual && (
            <span className="check-icon" title="Cumple parámetro mínimo">✓</span>
          )}
          {!cumpleIndividual && parametroMinimo !== null && (
            <span className="warning-icon" title={`Mínimo requerido: ${parametroMinimo}`}>⚠️</span>
          )}
        </div>
      </td>
    );
  };

  // Renderizar par de celdas (servicios y GPS) con color conjunto
  const renderParCeldas = (datoServicios, datoCbd, headerKey) => {
    // Determinar si al menos una cumple
    // Si no hay dato, considerar como false (no cumple)
    const cumpleServicios = datoServicios && datoServicios.cumple_parametro === true;
    const cumpleCbd = datoCbd && datoCbd.cumple_parametro === true;
    // Si al menos una cumple, ambas verdes; si ninguna cumple, ambas rojas
    const cumpleConjunto = cumpleServicios || cumpleCbd;

    return {
      celdaServicios: renderCelda(datoServicios, cumpleConjunto),
      celdaCbd: renderCelda(datoCbd, cumpleConjunto)
    };
  };

  return (
    <div className="cbd-table-container">
      <div className="table-header-info">
        <h2>Resultados de CBD</h2>
        <div className="info-badges">
          <span className="badge badge-date">
            📅 {fecha}
          </span>
          <span className="badge badge-tipo-dia">
            {nombre_tipo_dia}
          </span>
          <span className="badge badge-modo">
            📊 {modo_visualizacion === 'franja' ? 'Por Franja' : 'Por Hora'}
          </span>
        </div>
      </div>

      <div className="table-wrapper">
        <table className="cbd-table">
          <thead>
            <tr>
              <th rowSpan="2" className="sticky-col">EOT / Empresa</th>
              <th rowSpan="2" className="sticky-col-2">Fuente de Datos</th>
              <th colSpan={headers.length} className="header-group">
                {modo_visualizacion === 'franja' ? 'Franjas Operativas' : 'Horas del Día'}
              </th>
              <th rowSpan="2">Total</th>
            </tr>
            <tr>
              {headers.map((header) => (
                <th key={header.key} className="header-franja">
                  <div className="header-content">
                    <strong>{header.label}</strong>
                    {header.subtitle && <small>{header.subtitle}</small>}
                    {(header.minimo !== null && header.minimo !== undefined && typeof header.minimo === 'number') && (
                      <div className="header-minimo">Mín: {header.minimo}</div>
                    )}
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {datos_eots.map((eot) => (
              <React.Fragment key={eot.eot_id}>
                {/* Fila de Servicios Diarios */}
                <tr className="fila-servicios">
                  <td rowSpan="2" className="sticky-col eot-name">
                    <strong>{eot.eot_nombre}</strong>
                    {eot.gre_nombre && <small>{eot.gre_nombre}</small>}
                  </td>
                  <td className="sticky-col-2 tipo-fila">
                    Buses s/Validaciones
                  </td>
                  {headers.map((header) => {
                    const datoServicios = eot.fila_servicios.datos_por_franja[header.key];
                    const datoCbd = eot.fila_cbd.datos_por_franja[header.key];
                    const parCeldas = renderParCeldas(datoServicios, datoCbd, header.key);
                    return parCeldas.celdaServicios;
                  })}
                  <td className="total-cell">
                    <strong>{eot.fila_servicios.total}</strong>
                  </td>
                </tr>

                {/* Fila de CBD Detalle Buses */}
                <tr className="fila-cbd">
                  <td className="sticky-col-2 tipo-fila">
                    Buses s/GPS
                  </td>
                  {headers.map((header) => {
                    const datoServicios = eot.fila_servicios.datos_por_franja[header.key];
                    const datoCbd = eot.fila_cbd.datos_por_franja[header.key];
                    const parCeldas = renderParCeldas(datoServicios, datoCbd, header.key);
                    return parCeldas.celdaCbd;
                  })}
                  <td className="total-cell">
                    <strong>{eot.fila_cbd.total}</strong>
                  </td>
                </tr>
              </React.Fragment>
            ))}
          </tbody>
        </table>
      </div>

      <div className="table-footer">
        <div className="legend">
          <h3>Leyenda:</h3>
          <div className="legend-items">
            <div className="legend-item">
              <span className="check-icon">✓</span>
              <span>Cumple parámetro CBD Mínimo</span>
            </div>
            <div className="legend-item">
              <span className="warning-icon">⚠️</span>
              <span>No cumple parámetro CBD Mínimo</span>
            </div>
          </div>
        </div>
        <div className="analysis-actions" style={{ gap: '1rem' }}>
          <button className="btn-descargar-tabla" onClick={handleDownload}>
            📥 Descargar CSV
          </button>
          <button className="btn-analizar-operativa" onClick={() => setIsAnalysisModalOpen(true)}>
            📊 Analizar operativa
          </button>
        </div>
      </div>

      {isAnalysisModalOpen && (() => {
        // Find last closed period
        const determineLastClosedKey = () => {
          const currentHour = new Date().getHours();
          if (modo_visualizacion === 'hora') {
            const targetHour = currentHour - 1;
            const found = headers.find(h => h.key === String(targetHour));
            return found ? found.key : null;
          } else {
            const now = new Date();
            const currentTotalMinutes = now.getHours() * 60 + now.getMinutes();
            let lastClosed = null;
            if (franjas_operativas) {
              for (const f of franjas_operativas) {
                let [hFin, mFin] = f.hora_fin.split(':').map(Number);
                if (hFin === 24) { hFin = 23; mFin = 59; }
                const endTotalMinutes = hFin * 60 + mFin;
                if (currentTotalMinutes > endTotalMinutes) {
                  lastClosed = String(f.id_franja);
                }
              }
            }
            return lastClosed;
          }
        };

        const lastClosedKey = determineLastClosedKey();

        const categorizeEots = () => {
          const listOperaron = [];
          const listBajoNivel = [];
          const listNoOperaron = [];

          (cbdData?.datos_eots || []).forEach(eot => {
            if (analysisFilter === 'all') {
              const total = eot.fila_servicios.total > 0 || eot.fila_cbd.total > 0;
              if (!total) {
                listNoOperaron.push(eot);
              } else {
                let meetsAtLeastOne = false;
                headers.forEach(h => {
                  const serv = eot.fila_servicios.datos_por_franja[h.key];
                  const cbd = eot.fila_cbd.datos_por_franja[h.key];
                  if (serv?.cumple_parametro || cbd?.cumple_parametro) {
                    meetsAtLeastOne = true;
                  }
                });
                if (meetsAtLeastOne) {
                  listOperaron.push(eot);
                } else {
                  listBajoNivel.push(eot);
                }
              }
            } else {
              const filterKey = analysisFilter === 'last_closed' ? lastClosedKey : analysisFilter;
              if (!filterKey) return;
              
              const serv = eot.fila_servicios.datos_por_franja[filterKey];
              const cbd = eot.fila_cbd.datos_por_franja[filterKey];
              const valServ = serv?.cantidad_buses || 0;
              const valCbd = cbd?.cantidad_buses || 0;
              const cumpleServ = serv?.cumple_parametro === true;
              const cumpleCbd = cbd?.cumple_parametro === true;

              const operated = valServ > 0 || valCbd > 0;
              const cumple = cumpleServ || cumpleCbd;

              if (!operated) {
                listNoOperaron.push(eot);
              } else if (cumple) {
                listOperaron.push(eot);
              } else {
                listBajoNivel.push(eot);
              }
            }
          });

          return { listOperaron, listBajoNivel, listNoOperaron };
        };

        const { listOperaron, listBajoNivel, listNoOperaron } = categorizeEots();

        const getBusesForEot = (eot) => {
          if (analysisFilter === 'all') {
            return Math.max(eot.fila_servicios.total || 0, eot.fila_cbd.total || 0);
          } else {
            const filterKey = analysisFilter === 'last_closed' ? lastClosedKey : analysisFilter;
            if (!filterKey) return 0;
            const valServ = eot.fila_servicios.datos_por_franja[filterKey]?.cantidad_buses || 0;
            const valCbd = eot.fila_cbd.datos_por_franja[filterKey]?.cantidad_buses || 0;
            return Math.max(valServ, valCbd);
          }
        };

        const getGremioSummary = (list) => {
          const summary = {};
          list.forEach(eot => {
            const gremio = eot.gre_nombre || 'Sin Gremio';
            if (!summary[gremio]) {
              summary[gremio] = { empresas: 0, buses: 0 };
            }
            summary[gremio].empresas += 1;
            summary[gremio].buses += getBusesForEot(eot);
          });
          return Object.entries(summary).sort((a, b) => b[1].empresas - a[1].empresas);
        };

        return (
          <div className="modal-overlay">
            <div className="modal-content analysis-modal">
              <button className="modal-close" onClick={() => setIsAnalysisModalOpen(false)}>×</button>
              <h2>Análisis de Operativa</h2>
              
              <div className="analysis-controls">
                <label htmlFor="analysis-filter">Período de análisis:</label>
                <select 
                  id="analysis-filter" 
                  value={analysisFilter} 
                  onChange={(e) => setAnalysisFilter(e.target.value)}
                  className="analysis-select"
                >
                  <option value="all">Todo el día</option>
                  {lastClosedKey && (
                    <option value="last_closed">
                      Última {modo_visualizacion === 'hora' ? 'hora' : 'franja'} cerrada ({headers.find(h => h.key === lastClosedKey)?.label || lastClosedKey})
                    </option>
                  )}
                  <optgroup label={modo_visualizacion === 'hora' ? "Por hora específica" : "Por franja específica"}>
                    {headers.map(h => (
                      <option key={h.key} value={h.key}>
                        {h.label} {h.subtitle ? `(${h.subtitle})` : ''}
                      </option>
                    ))}
                  </optgroup>
                </select>
              </div>
            
              <div className="analysis-summary">
                <div className="summary-card operaron">
                  <h3>Operaron</h3>
                  <span className="summary-number">{listOperaron.length}</span>
                  <span className="summary-label">empresas</span>
                  <div className="gremio-breakdown">
                    {getGremioSummary(listOperaron).map(([gremio, data]) => (
                      <div key={gremio} className="gremio-item">
                        <strong>{gremio}</strong>: {data.empresas} empresas / {data.buses} buses
                      </div>
                    ))}
                  </div>
                </div>
                <div className="summary-card bajo-nivel">
                  <h3>Bajo nivel (&lt; Mínimo)</h3>
                  <span className="summary-number">{listBajoNivel.length}</span>
                  <span className="summary-label">empresas</span>
                  <div className="gremio-breakdown">
                    {getGremioSummary(listBajoNivel).map(([gremio, data]) => (
                      <div key={gremio} className="gremio-item">
                        <strong>{gremio}</strong>: {data.empresas} empresas / {data.buses} buses
                      </div>
                    ))}
                  </div>
                </div>
                <div className="summary-card no-operaron">
                  <h3>No Operaron</h3>
                  <span className="summary-number">{listNoOperaron.length}</span>
                  <span className="summary-label">empresas</span>
                  <div className="gremio-breakdown">
                    {getGremioSummary(listNoOperaron).map(([gremio, data]) => (
                      <div key={gremio} className="gremio-item">
                        <strong>{gremio}</strong>: {data.empresas} empresas / {data.buses} buses
                      </div>
                    ))}
                  </div>
                </div>
              </div>
              
              <div className="analysis-details">
                <div className="detail-section">
                  <h4 className="success-text">Operaron (Cumplen)</h4>
                  <div className="company-list-container">
                    <ul className="company-list">
                      {listOperaron.map(empresa => (
                        <li key={empresa.eot_id}>
                          <span className="empresa-nombre">{empresa.eot_nombre}</span>
                          {empresa.gre_nombre && <span className="empresa-gremio">{empresa.gre_nombre}</span>}
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
                <div className="detail-section">
                  <h4 className="warning-text">Bajo nivel</h4>
                  <div className="company-list-container">
                    <ul className="company-list">
                      {listBajoNivel.map(empresa => (
                        <li key={empresa.eot_id}>
                          <span className="empresa-nombre">{empresa.eot_nombre}</span>
                          {empresa.gre_nombre && <span className="empresa-gremio">{empresa.gre_nombre}</span>}
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
                <div className="detail-section">
                  <h4 className="danger-text">NO operaron</h4>
                  <div className="company-list-container">
                    <ul className="company-list">
                      {listNoOperaron.map(empresa => (
                        <li key={empresa.eot_id}>
                          <span className="empresa-nombre">{empresa.eot_nombre}</span>
                          {empresa.gre_nombre && <span className="empresa-gremio">{empresa.gre_nombre}</span>}
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>
            </div>
          </div>
        );
      })()}
    </div>
  );
};

export default CBDTable;
