import React from 'react';
import './PerformanceDashboard.css';

const PerformanceDashboard = ({ performanceData }) => {
  if (!performanceData) {
    return (
      <div className="empty-state">
        <p>No hay datos de desempeño para mostrar. Seleccione una fecha y empresas, y haga clic en "Consultar".</p>
      </div>
    );
  }

  const { fecha_analisis, tipo_dia, resultados_eots = [] } = performanceData;

  if (resultados_eots.length === 0) {
    return (
      <div className="empty-state">
        <p>La consulta no retornó resultados para los filtros seleccionados.</p>
      </div>
    );
  }

  const getComplianceClass = (status) => {
    switch (status) {
      case 'Cumple': return 'badge-cumple';
      case 'Nivel A': return 'badge-cumple'; // Verde
      case 'Leve': return 'badge-leve';
      case 'Nivel B': return 'badge-leve'; // Amarillo
      case 'Intermedia': return 'badge-intermedia';
      case 'Grave': return 'badge-grave';
      case 'Nivel C': return 'badge-no-cumple'; // Rojo
      case 'No Cumple': return 'badge-no-cumple';
      default: return '';
    }
  };

  const getCbdStatus = (status) => {
    const isCompliant = status === 'Cumple' || status === 'Nivel A';
    return {
      text: isCompliant ? 'Cumple' : 'Incumple',
      className: isCompliant ? 'badge-cumple' : 'badge-no-cumple'
    };
  };

  const handleEmailSend = (eotNombre) => {
    if (window.confirm(`¿Confirma que desea enviar el desglose a la empresa ${eotNombre}?`)) {
      alert(`Desglose enviado correctamente a la empresa ${eotNombre}`);
    }
  };

  const handlePrint = () => {
    window.print();
  };

  const handleDownloadPDF = () => {
    window.print();
  };

  return (
    <div className="performance-dashboard">
      <h2>📊 Reporte de Desempeño Diario</h2>
      <div className="report-meta">
        <p><strong>Fecha Analizada:</strong> {fecha_analisis}</p>
        <p><strong>Tipo de Día:</strong> {tipo_dia}</p>
      </div>

      {resultados_eots.map((eot) => {
        const ifoPromedio = eot.resultados_franjas.length > 0
          ? eot.resultados_franjas.reduce((acc, row) => acc + (row.ifo_franja_calculado || 0), 0) / eot.resultados_franjas.length
          : 0;

        return (
          <div key={eot.eot_id} className="eot-section">
            <div className="eot-header">
              <div>
                <h3>{eot.eot_nombre}</h3>
                <span className="eot-meta">{eot.gre_nombre || 'Sin Gremio'}</span>
              </div>
              <div className="eot-actions no-print">
                <button className="action-btn email-btn" onClick={() => handleEmailSend(eot.eot_nombre)} title="Enviar por Correo">
                  ✉️ Enviar correo
                </button>
                <button className="action-btn print-btn" onClick={handlePrint} title="Imprimir">
                  🖨️ Imprimir
                </button>
                <button className="action-btn pdf-btn" onClick={handleDownloadPDF} title="Descargar PDF">
                  📄 Descargar PDF
                </button>
              </div>
            </div>

            <div className="performance-table-container">
              <table className="performance-table">
                <thead>
                  <tr>
                    <th>Franja</th>

                    <th>Índice Cumpl. CBD</th>
                    <th>Estado CBD</th>
                    <th>IFO Calc</th>
                    <th>Nivel de servicio</th>
                    <th>Ajuste</th>
                  </tr>
                </thead>
                <tbody>
                  {eot.resultados_franjas.map((row, idx) => (
                    <tr key={idx}>
                      <td>{row.denominacion_franja}</td>

                      <td className="metric-value">{(row.cbd_cumplimiento_franja_indice * 100).toFixed(1)}%</td>
                      <td>
                        {(() => {
                          const status = getCbdStatus(row.cbd_estado_cumplimiento);
                          return (
                            <span className={`badge ${status.className}`}>
                              {status.text}
                            </span>
                          );
                        })()}
                      </td>
                      <td className="metric-value">{row.ifo_franja_calculado.toFixed(1)}%</td>
                      <td>
                        <span className={`badge ${getComplianceClass(row.ifo_estado_cumplimiento)}`}>
                          {row.ifo_estado_cumplimiento}
                        </span>
                      </td>
                      <td className="source-tag">{row.ajuste_aplicado}</td>
                    </tr>
                  ))}
                </tbody>
                <tfoot>
                  <tr className="summary-row">
                    <td colSpan="3" className="summary-label">IFO DIA (Promedio):</td>
                    <td className="metric-value summary-value">{ifoPromedio.toFixed(1)}%</td>
                    <td colSpan="2"></td>
                  </tr>
                </tfoot>
              </table>
            </div>
          </div>
        );
      })}
    </div>
  );
};

export default PerformanceDashboard;
