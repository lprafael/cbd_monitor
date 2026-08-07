import React from 'react';
import './MonthlyPerformanceDashboard.css';

const MonthlyPerformanceDashboard = ({ data, user }) => {
    if (!data) return null;

    const {
        month,
        year,
        eot_nombre,
        ifo_mensual_eot,
        ifo_mensual_eot_topeado,
        iccbdm_mensual_eot,
        ifo_sistema_anterior,
        ifo_sistema_anterior_topeado,
        umbral_objetivo,
        infraccion,
        sancion,
        ifo_diarios
    } = data;

    const getMonthName = (m) => {
        const date = new Date(year, m - 1);
        return date.toLocaleString('es-ES', { month: 'long' }).toUpperCase();
    };

    // ICCBDM está por definición estrictamente topeado a 100% (1.0 max por franja/día)
    const iccbdm_mensual_val = Math.min(iccbdm_mensual_eot !== undefined ? iccbdm_mensual_eot : ifo_mensual_eot, 100);

    // Use 110 as top for daily IFO, use 100 for daily ICCBDM
    const capped_ifo_diarios = ifo_diarios ? ifo_diarios.map(d => ({
        ...d,
        iccbdm_val: Math.min(d.iccbdm !== undefined ? d.iccbdm : d.ifo, 100),
        ifo_topeado: Math.min(d.ifo, 110)
    })) : [];

    return (
        <div className="monthly-dashboard">
            <div className="monthly-header">
                <h2>📅 Reporte de Desempeño Mensual (IFO)</h2>
                <h3>{eot_nombre}</h3>
                <p className="period-subtitle">{getMonthName(month)} {year}</p>
            </div>

            <div className={`status-card ${infraccion ? 'status-danger' : 'status-success'}`}>
                <div className="status-icon">
                    {infraccion ? '⚠️' : '✅'}
                </div>
                <div className="status-content">
                    <h4>Estado de Cumplimiento</h4>
                    <p className="status-result">
                        {infraccion ? 'INFRACCIÓN DETECTADA' : 'CUMPLE CON EL DESEMPEÑO'}
                    </p>
                    <p className="status-sancion">{sancion}</p>
                </div>
            </div>

            <div className="metrics-grid">

                {user?.rol !== 'viewer' && (
                    <div className="metric-card secondary">
                        <span className="metric-label">IFO Sistema (Mes n-1)</span>
                        <span className="metric-value">{ifo_sistema_anterior_topeado.toFixed(2)}%</span>
                        <span className="metric-value-capped">Real: {ifo_sistema_anterior.toFixed(2)}%</span>
                        <span className="metric-desc">Referencia Sistema (Topeado)</span>
                    </div>
                )}

                <div className="metric-card highlight">
                    <span className="metric-label">Umbral Obligatorio</span>
                    <span className="metric-value">≥ {umbral_objetivo.toFixed(2)}%</span>
                    <span className="metric-desc">Res. 120/2025</span>
                </div>

                <div className="metric-card primary">
                    <span className="metric-label">IFO Mensual (EOT)</span>
                    <span className="metric-value">{ifo_mensual_eot_topeado.toFixed(2)}%</span>
                    {user?.rol !== 'viewer' && (
                        <span className="metric-value-capped">Real: {ifo_mensual_eot.toFixed(2)}%</span>
                    )}
                    <span className="metric-desc">Promedio mensual topeado</span>
                </div>

                <div className="metric-card iccbdm">
                    <span className="metric-label">ICCBDM Mensual</span>
                    <span className="metric-value">{iccbdm_mensual_val.toFixed(2)}%</span>
                    <div className={`subsidio-badge ${iccbdm_mensual_val >= 95 ? 'subsidio-ok' : 'subsidio-alert'}`}>
                        {iccbdm_mensual_val >= 95 ? '✓ Subsidio Habilitado (≥ 95%)' : '⚠️ Subsidio en Riesgo (< 95%)'}
                    </div>
                    <span className="metric-desc" title="Promedio de los índices diarios registrados en el mes. Por definición del indicador CBD, el ICCBDM por franja y día está topeado a 100%.">
                        Promedio diario (Máx. 100%)
                    </span>
                </div>

            </div>

            {ifo_diarios && ifo_diarios.length > 0 && (
                <div className="daily-detail-section">
                    <div className="section-header-with-info">
                        <h4>Desglose Diario</h4>
                        <span className="vigencia-tag" title="Vigencia parcial: solo franjas picos y pospicos de lunes a viernes, y franja pico de sábados">
                            ℹ️ Vigencia Parcial (Etapa 2)
                        </span>
                    </div>
                    <div className="table-responsive">
                        <table className="daily-table">
                            <thead>
                                <tr>
                                    <th>Fecha</th>
                                    <th>Día</th>
                                    <th title="Promedio de los índices obtenidos en todas las franjas operativas del día (ICCBDM diario = 1/n ∑ ICCBDM franja, topeado a 100%)">
                                        ICCBDM Diario ℹ️
                                    </th>
                                    <th>IFO Diario (Topeado)</th>
                                    <th>Ajustes</th>
                                    <th>Estado</th>
                                </tr>
                            </thead>
                            <tbody>
                                {capped_ifo_diarios.map((d, idx) => (
                                    <tr key={idx}>
                                        <td>{d.fecha}</td>
                                        <td>{new Intl.DateTimeFormat('es-PY', { weekday: 'long' }).format(new Date(d.fecha + 'T00:00:00'))}</td>
                                        <td className="iccbdm-cell">{d.iccbdm_val.toFixed(2)}%</td>
                                        <td>{d.ifo_topeado.toFixed(2)}%</td>
                                        <td className="adjustments-cell">
                                            {d.ajustes && d.ajustes.length > 0 ? (
                                                <div className="adjustments-list">
                                                    {d.ajustes.map((a, i) => (
                                                        <span key={i} className="adjustment-tag" title={a}>
                                                            {a.split(' ')[0]} {/* Mostrar solo el nombre principal, el resto en tooltip */}
                                                        </span>
                                                    ))}
                                                </div>
                                            ) : (
                                                <span className="no-adjustments">-</span>
                                            )}
                                        </td>
                                        <td>
                                            <span className={`badge ${d.ifo_topeado < umbral_objetivo ? 'badge-danger' : 'badge-success'}`}>
                                                {d.ifo_topeado < umbral_objetivo ? 'Bajo Umbral' : 'Ok'}
                                            </span>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}
        </div>
    );
};

export default MonthlyPerformanceDashboard;
