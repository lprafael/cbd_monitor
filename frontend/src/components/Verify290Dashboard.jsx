import React, { useState, useRef } from 'react';
import html2canvas from 'html2canvas';
import jsPDF from 'jspdf';
import './Verify290Dashboard.css';

const Verify290Dashboard = ({ data }) => {
    const [expandedFranja, setExpandedFranja] = useState(null);
    const dashboardRef = useRef(null);

    if (!data) return null;

    const {
        month,
        year,
        eot_nombre,
        detalles_troncal,
        resumen_global
    } = data;

    const getMonthName = (m) => {
        const date = new Date(year, m - 1);
        return date.toLocaleString('es-ES', { month: 'long' }).toUpperCase();
    };

    const toggleDesglose = (troncalIdx, franjaIdx) => {
        const key = `${troncalIdx}-${franjaIdx}`;
        setExpandedFranja(expandedFranja === key ? null : key);
    };

    const exportToPDF = async () => {
        if (!dashboardRef.current) return;

        try {
            // Hide buttons temporarily
            const buttons = dashboardRef.current.querySelectorAll('.btn-toggle-desglose, .btn-export-pdf');
            buttons.forEach(btn => btn.style.display = 'none');

            // Capture the dashboard as canvas
            const canvas = await html2canvas(dashboardRef.current, {
                scale: 2,
                useCORS: true,
                logging: false,
                backgroundColor: '#ffffff'
            });

            // Restore buttons
            buttons.forEach(btn => btn.style.display = '');

            // Create PDF
            const imgData = canvas.toDataURL('image/png');
            const pdf = new jsPDF('p', 'mm', 'a4');
            const pdfWidth = pdf.internal.pageSize.getWidth();
            const pdfHeight = pdf.internal.pageSize.getHeight();
            const imgWidth = canvas.width;
            const imgHeight = canvas.height;
            const ratio = Math.min(pdfWidth / imgWidth, pdfHeight / imgHeight);
            const imgX = (pdfWidth - imgWidth * ratio) / 2;
            const imgY = 10;

            pdf.addImage(imgData, 'PNG', imgX, imgY, imgWidth * ratio, imgHeight * ratio);
            pdf.save(`Resolucion_290_${eot_nombre}_${getMonthName(month)}_${year}.pdf`);
        } catch (error) {
            console.error('Error generating PDF:', error);
            alert('Error al generar el PDF. Por favor, intente nuevamente.');
        }
    };

    return (
        <div className="verify290-dashboard" ref={dashboardRef}>
            <div className="verify290-header">
                <h2>📋 Verificación Res. GVMT N° 290/2021</h2>
                <h3>{eot_nombre}</h3>
                <p className="period-subtitle">{getMonthName(month)} {year}</p>
                <button className="btn-export-pdf" onClick={exportToPDF} title="Descargar reporte en PDF">
                    📄 Exportar a PDF
                </button>
            </div>

            {detalles_troncal && detalles_troncal.map((troncal, troncalIdx) => (
                <div key={troncalIdx} className="troncal-section">
                    <div className="troncal-header">
                        <h4>🚌 {troncal.nombre_troncal}</h4>
                    </div>

                    <div className="verify290-table-container">
                        <table className="verify290-table">
                            <thead>
                                <tr>
                                    <th>Franja Operativa</th>
                                    <th className="numeric-cell">Promedio Real (b/h)</th>
                                    <th className="numeric-cell">Promedio Requerido (b/h)</th>
                                    <th className="numeric-cell">Días / Lluvia</th>
                                    <th className="numeric-cell">% Cumplimiento</th>
                                    <th>Estado</th>
                                    <th>Acciones</th>
                                </tr>
                            </thead>
                            <tbody>
                                {troncal.resultados_franjas.map((row, idx) => {
                                    const rendimientoExcedido = row.rendimiento > 100;
                                    const desgloseKey = `${troncalIdx}-${idx}`;
                                    const isExpanded = expandedFranja === desgloseKey;

                                    return (
                                        <React.Fragment key={idx}>
                                            <tr className={!row.cumple ? 'row-critica' : ''}>
                                                <td>
                                                    <div className="franja-main-name">{row.nombre_franja}</div>
                                                </td>
                                                <td className="numeric-cell">
                                                    <div className="main-value">{(row.servicios_realizados || 0).toFixed(2)}</div>
                                                    <div className="sub-value-math">{(row.sum_servicios || 0)} buses / {(row.total_horas || 0)}h</div>
                                                </td>
                                                <td className="numeric-cell">
                                                    <div className="main-value">{(row.exigencia || 0).toFixed(2)}</div>
                                                    <div className="sub-value-meta">Umbral: {(row.umbral || 0)}%</div>
                                                </td>
                                                <td className="numeric-cell">
                                                    <div className="main-value">{(row.dias_contabilizados || 0)}d</div>
                                                    {row.dias_lluvia > 0 && (
                                                        <div className="sub-value-lluvia">🌧️ {row.dias_lluvia} días</div>
                                                    )}
                                                </td>
                                                <td className="numeric-cell">
                                                    <div className="rend-container">
                                                        <span className={`rend-value ${row.cumple ? 'text-success' : 'text-danger'}`}>
                                                            {(row.rendimiento_normalizado || 0).toFixed(1)}%
                                                        </span>
                                                        {rendimientoExcedido && (
                                                            <span className="rend-real-tag">Real: {(row.rendimiento || 0).toFixed(1)}%</span>
                                                        )}
                                                    </div>
                                                </td>
                                                <td>
                                                    <div className="status-container">
                                                        <span className={`badge ${row.cumple ? 'badge-cumple' : 'badge-no-cumple'}`}>
                                                            {row.estado || 'N/A'}
                                                        </span>
                                                        {row.proyeccion_requerida !== null && row.proyeccion_requerida > 0 && (
                                                            <div className={`proj-alert ${!row.cumple ? 'alert-critical animated-pulse' : ''}`}
                                                                title="Esfuerzo necesario en el resto del mes">
                                                                {!row.cumple ? (
                                                                    <>
                                                                        <strong>ALERTA:</strong> Debe realizar <strong>{row.proyeccion_requerida.toFixed(2)} b/h</strong>
                                                                        {row.dias_restantes ? ` en los ${row.dias_restantes} días restantes` : ' restantes'}
                                                                    </>
                                                                ) : (
                                                                    `Proyección: ${row.proyeccion_requerida.toFixed(2)} b/h`
                                                                )}
                                                            </div>
                                                        )}
                                                    </div>
                                                </td>
                                                <td>
                                                    <button
                                                        className="btn-toggle-desglose"
                                                        onClick={() => toggleDesglose(troncalIdx, idx)}
                                                        title="Ver desglose detallado por fecha y hora"
                                                    >
                                                        {isExpanded ? '▲ Ocultar' : '▼ Ver Desglose'}
                                                    </button>
                                                </td>
                                            </tr>
                                            {isExpanded && row.desglose_diario && row.desglose_diario.length > 0 && (
                                                <tr className="desglose-row">
                                                    <td colSpan="7">
                                                        <div className="desglose-container">
                                                            <h5>📊 Desglose Detallado: {row.nombre_franja}</h5>
                                                            <div className="desglose-table-wrapper">
                                                                <table className="desglose-table">
                                                                    <thead>
                                                                        <tr>
                                                                            <th>Fecha</th>
                                                                            <th>Hora</th>
                                                                            <th>Servicios</th>
                                                                        </tr>
                                                                    </thead>
                                                                    <tbody>
                                                                        {row.desglose_diario.map((d, dIdx) => (
                                                                            <tr key={dIdx}>
                                                                                <td>{d.fecha}</td>
                                                                                <td>{d.hora}:00</td>
                                                                                <td className="numeric-cell"><strong>{d.servicios}</strong></td>
                                                                            </tr>
                                                                        ))}
                                                                    </tbody>
                                                                    <tfoot>
                                                                        <tr className="desglose-total">
                                                                            <td colSpan="2"><strong>TOTAL</strong></td>
                                                                            <td className="numeric-cell">
                                                                                <strong>{row.desglose_diario.reduce((sum, d) => sum + d.servicios, 0)}</strong>
                                                                            </td>
                                                                        </tr>
                                                                    </tfoot>
                                                                </table>
                                                            </div>
                                                        </div>
                                                    </td>
                                                </tr>
                                            )}
                                            <tr className="explanation-row">
                                                <td colSpan="7">
                                                    <div className="explanation-bubble">
                                                        <div className="explanation-grid">
                                                            <div className="exp-column">
                                                                <h5>📋 Datos Detectados (Numerador)</h5>
                                                                <ul>
                                                                    <li><strong>Buses totales:</strong> {row.sum_servicios || 0} unidades</li>
                                                                    <li><strong>Horas totales:</strong> {row.total_horas || 0} h (operación en el mes)</li>
                                                                    <li><strong>Promedio Real:</strong> {row.sum_servicios || 0} / {row.total_horas || 1} = <strong>{(row.servicios_realizados || 0).toFixed(2)} b/h</strong></li>
                                                                </ul>
                                                            </div>
                                                            <div className="exp-column">
                                                                <h5>⚖️ Exigencia Normativa (Denominador)</h5>
                                                                <ul>
                                                                    <li><strong>Meta del periodo:</strong> {(row.exigencia || 0).toFixed(2)} b/h</li>
                                                                    <li><strong>Umbral exigido (Art. 2):</strong> {row.umbral || 0}% de cumplimiento</li>
                                                                    <li><strong>Meta mínima aceptable:</strong> {((row.exigencia || 0) * (row.umbral || 0) / 100).toFixed(2)} b/h</li>
                                                                </ul>
                                                            </div>
                                                            <div className="exp-column">
                                                                <h5>📊 Resultado Final</h5>
                                                                <p>
                                                                    Su promedio de <strong>{(row.servicios_realizados || 0).toFixed(2)} b/h</strong> es {row.cumple ? 'superior o igual' : 'inferior'} al mínimo de <strong>{((row.exigencia || 0) * (row.umbral || 0) / 100).toFixed(2)} b/h</strong> necesario para el {row.umbral || 0}% de cumplimiento.
                                                                </p>
                                                            </div>
                                                        </div>
                                                        {row.dias_lluvia > 0 && (
                                                            <div className="rain-note">
                                                                ℹ️ <strong>Nota sobre Clima:</strong> La meta de {(row.exigencia || 0).toFixed(2)} b/h ya incluye la reducción del 50% aplicada en los {row.dias_lluvia} días de lluvia detectados.
                                                            </div>
                                                        )}
                                                    </div>
                                                </td>
                                            </tr>
                                        </React.Fragment>
                                    );
                                })}
                            </tbody>
                        </table>
                    </div>
                </div>
            ))}

            {resumen_global && (
                <div style={{ marginTop: '20px', padding: '15px', backgroundColor: '#f3f4f6', borderRadius: '8px' }}>
                    <strong>Nota:</strong> {resumen_global}
                </div>
            )}
        </div>
    );
};

export default Verify290Dashboard;
