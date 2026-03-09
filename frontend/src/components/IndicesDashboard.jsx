/**
 * IndicesDashboard.jsx
 * Dashboard para mostrar los índices de CBD e IFO por franja con popups de desglose
 */

import React, { useState } from 'react';
import './IndicesDashboard.css';

import { API_BASE_URL } from '../config';

/**
 * Formatea una fecha ISO (YYYY-MM-DD) a un formato largo con el día de la semana
 * Ejemplo: "Lunes, 06-03-2026"
 */
const formatDateLong = (dateStr) => {
  if (!dateStr) return '';

  // Forzamos el parseo como hora local añadiendo T00:00:00
  const dateObj = new Date(dateStr + 'T00:00:00');

  const days = ['Domingo', 'Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado'];
  const dayName = days[dateObj.getDay()];

  // Formatear DD-MM-YYYY
  const day = String(dateObj.getDate()).padStart(2, '0');
  const month = String(dateObj.getMonth() + 1).padStart(2, '0');
  const year = dateObj.getFullYear();

  return `${dayName}, ${day}-${month}-${year}`;
};

const IndicesDashboard = ({ performanceData, fecha }) => {
  const [activeTab, setActiveTab] = useState('cbd'); // 'cbd' | 'ifo'
  const [modalData, setModalData] = useState(null);
  const [modalType, setModalType] = useState(null); // 'cbd' | 'ifo'
  const [loading, setLoading] = useState(false);

  if (!performanceData || !performanceData.resultados_eots || performanceData.resultados_eots.length === 0) {
    return (
      <div className="empty-state">
        <div className="icon">📊</div>
        <p>No hay datos de desempeño disponibles. Seleccione EOTs y fecha, luego haga clic en "Consultar".</p>
      </div>
    );
  }

  const { resultados_eots } = performanceData;

  // Obtener todas las franjas únicas
  const franjas = resultados_eots[0]?.resultados_franjas?.map(r => ({
    id_franja: r.id_franja,
    denominacion: r.denominacion_franja
  })) || [];

  // Obtener el valor del índice según el tab activo
  const getIndexValue = (resultado) => {
    if (activeTab === 'cbd') {
      return resultado.cbd_cumplimiento_franja_indice;
    } else {
      return resultado.ifo_franja_calculado / 100; // Convertir de % a decimal
    }
  };

  // Obtener el estado de cumplimiento
  const getEstado = (resultado) => {
    if (activeTab === 'cbd') {
      return resultado.cbd_estado_cumplimiento;
    } else {
      return resultado.ifo_estado_cumplimiento;
    }
  };

  // Clase CSS según el estado
  const getStatusClass = (estado) => {
    if (!estado) return 'sin-datos';
    const estadoLower = estado.toLowerCase();

    // Mapeo para nuevos niveles A, B, C
    if (estadoLower === 'nivel a') return 'cumple';
    if (estadoLower === 'nivel b') return 'leve';
    if (estadoLower === 'nivel c') return 'no-cumple';

    // Compatibilidad con estados anteriores
    if (estadoLower === 'cumple') return 'cumple';
    if (estadoLower === 'leve') return 'leve';
    if (estadoLower === 'intermedia') return 'intermedia';
    if (estadoLower === 'grave') return 'grave';
    if (estadoLower === 'no cumple') return 'no-cumple';

    return 'sin-datos';
  };

  // Manejar clic en celda
  const handleCellClick = async (eot, resultado) => {
    setLoading(true);
    setModalType(activeTab);

    try {
      const endpoint = activeTab === 'cbd'
        ? '/api/performance-detail/cbd'
        : '/api/performance-detail/ifo';

      const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          fecha: fecha,
          eot_id: eot.eot_id,
          id_franja: resultado.id_franja
        })
      });

      if (!response.ok) {
        throw new Error('Error al obtener desglose');
      }

      const data = await response.json();
      setModalData(data);
    } catch (err) {
      console.error('Error:', err);
      alert('Error al cargar el desglose: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  // Cerrar modal
  const closeModal = () => {
    setModalData(null);
    setModalType(null);
  };

  const handleEmailSend = async (eotNombre, data, type) => {
    if (window.confirm(`¿Confirma que desea enviar el desglose a la empresa ${eotNombre}?`)) {
      setLoading(true);
      try {
        const response = await fetch(`${API_BASE_URL}/api/performance-detail/send-email`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            type: type,
            data: data
          })
        });

        const resData = await response.json();

        if (!response.ok) {
          throw new Error(resData.detail || 'Error al enviar el correo');
        }

        alert(`Desglose enviado correctamente. ${resData.message}`);
      } catch (err) {
        console.error('Error:', err);
        alert('Error al enviar el correo: ' + err.message);
      } finally {
        setLoading(false);
      }
    }
  };

  const handlePrint = () => {
    window.print();
  };

  const handleDownloadPDF = () => {
    window.print();
  };

  return (
    <div className="indices-dashboard">
      <div className="dashboard-header">
        <h2>
          📊 Tablero de Índices de Desempeño
        </h2>
        <div className="dashboard-tabs">
          <button
            className={`tab-btn ${activeTab === 'cbd' ? 'active' : ''}`}
            onClick={() => setActiveTab('cbd')}
          >
            📈 Índice CCBDM
          </button>
          <button
            className={`tab-btn ${activeTab === 'ifo' ? 'active' : ''}`}
            onClick={() => setActiveTab('ifo')}
          >
            📉 Índice IFO
          </button>
        </div>
      </div>

      <div className="indices-table-container">
        <table className="indices-table">
          <thead>
            <tr>
              <th className="eot-header">EOT</th>
              {franjas.map(f => (
                <th key={f.id_franja} className="franja-header">
                  {f.denominacion}
                </th>
              ))}
              {activeTab === 'ifo' && <th className="franja-header special-column">IFO Dia</th>}
            </tr>
          </thead>
          <tbody>
            {resultados_eots.map(eot => (
              <tr key={eot.eot_id}>
                <td className="eot-cell">
                  <div className="eot-name">{eot.eot_nombre}</div>
                  <div className="gremio-name">{eot.gre_nombre || 'Sin gremio'}</div>
                </td>
                {eot.resultados_franjas.map(resultado => {
                  const valor = getIndexValue(resultado);
                  const estado = getEstado(resultado);

                  let statusClass;
                  if (activeTab === 'cbd') {
                    // CBD: 100% es verde (Cumple), cualquier cosa menor es rojo (No Cumple)
                    // Usamos 0.9995 para que coincida con el redondeo a 1 decimal (99.95% -> 100.0%)
                    statusClass = valor >= 0.9995 ? 'cumple' : 'no-cumple';
                  } else {
                    // IFO: Mantiene lógica de 3 colores
                    statusClass = getStatusClass(estado);
                  }

                  return (
                    <td key={resultado.id_franja}>
                      <div
                        className={`index-cell ${statusClass}`}
                        onClick={() => handleCellClick(eot, resultado)}
                        title={`Click para ver desglose - ${estado}`}
                      >
                        {(valor * 100).toFixed(2)}%
                      </div>
                    </td>
                  );
                })}
                {activeTab === 'ifo' && (() => {
                  const ifoDia = eot.resultados_franjas.length > 0
                    ? eot.resultados_franjas.reduce((acc, r) => acc + (r.ifo_franja_calculado || 0), 0) / eot.resultados_franjas.length
                    : 0;

                  const estadoPromedio = ifoDia >= 90 ? 'Nivel A' : ifoDia >= 80 ? 'Nivel B' : 'Nivel C';
                  const statusClassAlt = getStatusClass(estadoPromedio);

                  return (
                    <td key="ifo-dia">
                      <div className={`index-cell ${statusClassAlt} ifo-dia-cell`}>
                        <div className="ifo-dia-main">
                          {ifoDia.toFixed(2)}%
                        </div>
                        {(() => {
                          // Aseguramos que los valores sean numéricos y filtramos nulos
                          const totalHoras = eot.resultados_franjas.reduce((acc, r) => acc + (Number(r.cant_horas) || 0), 0);
                          const sumHorasIfo = eot.resultados_franjas.reduce((acc, r) => acc + ((Number(r.ifo_franja_calculado) || 0) * (Number(r.cant_horas) || 0)), 0);
                          const ifoHoraAvg = totalHoras > 0 ? sumHorasIfo / totalHoras : 0;

                          const tooltipText = `IFO Real (Promedio ponderado por horas)\nTotal horas analizadas: ${totalHoras}\nIFO = (Sumatoria IFO_franja * Horas_franja) / Total_horas`;

                          return (
                            <div className="ifo-dia-sub" title={tooltipText}>
                              H: {ifoHoraAvg.toFixed(2)}%
                            </div>
                          );
                        })()}
                      </div>
                    </td>
                  );
                })()}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Modal de Desglose */}
      {(modalData || loading) && (
        <div className="detail-modal-overlay" onClick={closeModal}>
          <div className="detail-modal" onClick={e => e.stopPropagation()}>
            {loading ? (
              <div className="loading-spinner">
                <div className="spinner"></div>
                <p>Cargando desglose...</p>
              </div>
            ) : modalType === 'cbd' ? (
              <CBDDetailModal
                data={modalData}
                onClose={closeModal}
                onEmail={() => handleEmailSend(modalData.eot_nombre, modalData, 'cbd')}
                onPrint={handlePrint}
                onDownload={handleDownloadPDF}
              />
            ) : (
              <IFODetailModal
                data={modalData}
                onClose={closeModal}
                onEmail={() => handleEmailSend(modalData.eot_nombre, modalData, 'ifo')}
                onPrint={handlePrint}
                onDownload={handleDownloadPDF}
              />
            )}
          </div>
        </div>
      )}
    </div>
  );
};

// Botones de acción para los modales
const ModalActions = ({ onEmail, onPrint, onDownload }) => (
  <div className="modal-actions no-print">
    <button className="action-btn email-btn" onClick={onEmail} title="Enviar por Correo">
      ✉️ Enviar correo
    </button>
    <button className="action-btn print-btn" onClick={onPrint} title="Imprimir">
      🖨️ Imprimir
    </button>
    <button className="action-btn pdf-btn" onClick={onDownload} title="Descargar PDF">
      📄 Descargar PDF
    </button>
  </div>
);

const ModalFooter = () => (
  <div className="modal-footer-info">
    <p>Reporte generado automáticamente por el Sistema de Monitoreo de Indicadores de Desempeño.</p>
    <p>VMT - CID | Resolución GVMT Nº 120/2025</p>
  </div>
);

/**
 * Modal de desglose de CBD
 */
const CBDDetailModal = ({ data, onClose, onEmail, onPrint, onDownload }) => {
  if (!data) return null;

  return (
    <>
      <div className="modal-header">
        <div>
          <h3>📊 Desglose del Índice de Cumplimiento CBD Mínimo</h3>
          <div className="eot-info">
            {data.eot_nombre} • {data.denominacion_franja} • {formatDateLong(data.fecha)}
          </div>
        </div>
        <div className="header-right">
          <ModalActions onEmail={onEmail} onPrint={onPrint} onDownload={onDownload} />
          <button className="close-btn" onClick={onClose}>✕</button>
        </div>
      </div>

      <div className="modal-body">
        {/* Parámetros */}
        <div className="params-section">
          <h4>📋 Parámetros</h4>
          <div className="params-grid">
            <div className="param-item">
              <span className="param-label">CBD Mínimo por Hora</span>
              <span className="param-value">{data.cbd_minimo_hora}</span>
            </div>
            <div className="param-item">
              <span className="param-label">CBD Mínimo por Franja</span>
              <span className="param-value">{data.cbd_minimo_franja}</span>
            </div>
          </div>
        </div>

        {/* Tabla de CBD por hora */}
        <div className="hours-table-container">
          <h4>🕐 CBD por Hora</h4>
          <table className="hours-table">
            <thead>
              <tr>
                <th>Hora</th>
                <th>CBD Observado</th>
                <th>CBD Mínimo</th>
                <th>Índice (Ratio)</th>
                <th>Fórmula</th>
              </tr>
            </thead>
            <tbody>
              {data.horas_data.map(hora => (
                <tr key={hora.hora}>
                  <td><strong>{hora.hora}:00</strong></td>
                  <td>{hora.cbd_observado}</td>
                  <td>{hora.cbd_minimo_hora}</td>
                  <td>{(hora.ratio_hora || 0).toFixed(2)}</td>
                  <td className="formula-cell">
                    =MIN({hora.cbd_observado}/{hora.cbd_minimo_hora}, 1)
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Tabla de CBD por franja */}
        <div className="hours-table-container">
          <h4>🏢 CBD por Franja</h4>
          <table className="hours-table">
            <thead>
              <tr>
                <th>Nivel</th>
                <th>CBD Observado</th>
                <th>CBD Mínimo</th>
                <th>Índice (Ratio)</th>
                <th>Fórmula</th>
              </tr>
            </thead>
            <tbody>
              <tr style={{ background: 'rgba(102, 126, 234, 0.1)' }}>
                <td><strong>FRANJA</strong></td>
                <td><strong>{data.cbd_franja_observado}</strong></td>
                <td><strong>{data.cbd_minimo_franja}</strong></td>
                <td><strong>{(data.ratio_franja || 0).toFixed(2)}</strong></td>
                <td className="formula-cell">
                  =MIN({data.cbd_franja_observado}/{data.cbd_minimo_franja}, 1)
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        {/* Cálculo del Índice */}
        <div className="calculation-section">
          <h4>🧮 Cálculo del Índice de Cumplimiento CBD Mínimo</h4>
          <table className="calc-table">
            <thead>
              <tr>
                <th>Componente</th>
                <th>Valor</th>
                <th>Peso</th>
                <th>Resultado</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>Promedio Ratio Hora (I_H)</td>
                <td>{(data.promedio_ratio_hora || 0).toFixed(2)}</td>
                <td>× 0.7</td>
                <td>{(data.componente_hora || 0).toFixed(2)}</td>
              </tr>
              <tr>
                <td>Ratio Franja (I_F)</td>
                <td>{(data.ratio_franja || 0).toFixed(2)}</td>
                <td>× 0.3</td>
                <td>{(data.componente_franja || 0).toFixed(2)}</td>
              </tr>
              <tr className="calc-result-row">
                <td colSpan="3">ÍNDICE DE CUMPLIMIENTO CBD MÍNIMO</td>
                <td>
                  <span className={`resultado-badge ${data.indice_cbd >= 0.99995 ? 'cumple' : 'no-cumple'}`}>
                    {((data.indice_cbd || 0) * 100).toFixed(2)}%
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <ModalFooter />
      </div>
    </>
  );
};

/**
 * Modal de desglose de IFO
 */
const IFODetailModal = ({ data, onClose, onEmail, onPrint, onDownload }) => {
  if (!data) return null;

  const fechasHistoricasOrdenadas = (data.fechas_historicas || [])
    .slice()
    .sort((a, b) => new Date(a) - new Date(b));

  return (
    <>
      <div className="modal-header">
        <div>
          <h3>📉 Desglose del IFO (Índice de Flota Operativa)</h3>
          <div className="eot-info">
            {data.eot_nombre} • {data.denominacion_franja} • {formatDateLong(data.fecha)}
          </div>
        </div>
        <div className="header-right">
          <ModalActions onEmail={onEmail} onPrint={onPrint} onDownload={onDownload} />
          <button className="close-btn" onClick={onClose}>✕</button>
        </div>
      </div>

      <div className="modal-body">
        {/* Ajuste aplicado */}
        {data.ajuste_aplicado !== 'Ninguno' && (
          <div className="ajuste-highlight">
            <span className="ajuste-icon">⚠️</span>
            <span className="ajuste-text">
              <strong>Ajuste aplicado:</strong> {data.ajuste_aplicado} (Factor: {data.factor_ajuste})
            </span>
          </div>
        )}

        {/* Parámetros */}
        <div className="params-section">
          <h4>📋 Información del Cálculo</h4>
          <div className="params-grid">
            <div className="param-item">
              <span className="param-label">Tipo de Día</span>
              <span className="param-value">{data.tipo_dia}</span>
            </div>
            <div className="param-item">
              <span className="param-label">Factor de Ajuste</span>
              <span className="param-value">{data.factor_ajuste}</span>
            </div>
          </div>
        </div>

        {/* Fechas históricas */}
        <div className="historico-section">
          <h5>📅 Fechas históricas (verdes usadas • rojas descartadas)</h5>
          <div className="historico-dates">
            {(data.fechas_historicas_todas || data.fechas_historicas.map(fecha => ({ fecha, usada: true })))
              .slice()
              .sort((a, b) => new Date(a.fecha) - new Date(b.fecha))
              .map((item, idx) => (
                <span
                  key={idx}
                  className={`historico-date-tag ${item.usada ? 'historico-date-used' : 'historico-date-discarded'}`}
                >
                  {formatDateLong(item.fecha)}
                </span>
              ))}
          </div>
        </div>

        {/* Tabla de IFO por hora con detalle histórico */}
        <div className="hours-table-container" style={{ marginTop: '20px' }}>
          <h4>🕐 IFO por Hora - Detalle con históricos</h4>
          <div style={{ overflowX: 'auto' }}>
            <table className="hours-table">
              <thead>
                <tr>
                  <th rowSpan="2">Hora</th>
                  <th rowSpan="2" style={{ background: 'rgba(102, 126, 234, 0.3)' }}>CBD Día<br />Analizado</th>
                  <th colSpan={data.fechas_historicas.length} style={{ textAlign: 'center', background: 'rgba(246, 173, 85, 0.2)' }}>
                    CBD Fechas Históricas
                  </th>
                  <th rowSpan="2">Promedio<br />Histórico</th>
                  <th rowSpan="2">Prom. × Factor<br />({data.factor_ajuste})</th>
                  <th rowSpan="2">IFO Hora<br />(%)</th>
                </tr>
                <tr>
                  {fechasHistoricasOrdenadas.map((fecha, idx) => (
                    <th key={idx} style={{ fontSize: '0.75rem', background: 'rgba(246, 173, 85, 0.1)' }}>
                      {fecha}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {data.horas_data.map(hora => {
                  // Calcular promedio sin ajuste para mostrar
                  const promedioSinAjuste = hora.historico_detalle && hora.historico_detalle.length > 0
                    ? hora.historico_detalle.reduce((sum, h) => sum + h.cbd_observado, 0) / hora.historico_detalle.length
                    : 0;

                  const historicoPorFecha = (hora.historico_detalle || []).reduce((acc, hist) => {
                    acc[hist.fecha] = hist.cbd_observado;
                    return acc;
                  }, {});

                  return (
                    <tr key={hora.hora}>
                      <td><strong>{hora.hora}:00</strong></td>
                      <td style={{ background: 'rgba(102, 126, 234, 0.1)', fontWeight: 'bold' }}>
                        {hora.cbd_dia_analizado}
                      </td>
                      {fechasHistoricasOrdenadas.map((fecha, idx) => (
                        <td key={idx} style={{ background: 'rgba(246, 173, 85, 0.05)' }}>
                          {historicoPorFecha[fecha] ?? '-'}
                        </td>
                      ))}
                      <td>{(promedioSinAjuste || 0).toFixed(2)}</td>
                      <td>{(hora.b_dist_ajustado || 0).toFixed(2)}</td>
                      <td>
                        <span style={{
                          color: hora.ifo_hora >= 90 ? '#48bb78' :
                            hora.ifo_hora >= 80 ? '#ecc94b' : '#fc8181',
                          fontWeight: 'bold'
                        }}>
                          {((hora.ifo_hora || 0)).toFixed(2)}%
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* Resultado final */}
        <div className="calculation-section">
          <h4>🧮 Cálculo del IFO Franja</h4>
          <table className="calc-table">
            <thead>
              <tr>
                <th>Descripción</th>
                <th>Fórmula</th>
                <th>Resultado</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>IFO por hora</td>
                <td className="formula-cell">CBD_hora / Denominador_ajustado × 100</td>
                <td>Ver tabla arriba</td>
              </tr>
              <tr className="calc-result-row">
                <td colSpan="2">IFO FRANJA (Promedio de IFO_hora)</td>
                <td>
                  <span className={`resultado-badge ${data.ifo_franja >= 90 ? 'cumple' : data.ifo_franja >= 80 ? 'leve' : 'no-cumple'}`}>
                    {(data.ifo_franja || 0).toFixed(2)}%
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <ModalFooter />
      </div>
    </>
  );
};

export default IndicesDashboard;
