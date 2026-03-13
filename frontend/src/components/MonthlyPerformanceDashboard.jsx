import React from 'react';
import './MonthlyPerformanceDashboard.css';

const MonthlyPerformanceDashboard = ({ data }) => {
    if (!data) return null;

    const {
        month,
        year,
        eot_nombre,
        ifo_mensual_eot,
        ifo_mensual_eot_topeado,
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

    // Use 110 as top for daily display
    const capped_ifo_diarios = ifo_diarios ? ifo_diarios.map(d => ({
        ...d,
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
                <div className="metric-card primary">
                    <span className="metric-label">IFO Mensual (EOT)</span>
                    <span className="metric-value">{ifo_mensual_eot_topeado.toFixed(2)}%</span>
                    <span className="metric-value-capped">Real: {ifo_mensual_eot.toFixed(2)}%</span>
                    <span className="metric-desc">Promedio mensual topeado</span>
                </div>

                <div className="metric-card secondary">
                    <span className="metric-label">IFO Sistema (Mes n-1)</span>
                    <span className="metric-value">{ifo_sistema_anterior_topeado.toFixed(2)}%</span>
                    <span className="metric-value-capped">Real: {ifo_sistema_anterior.toFixed(2)}%</span>
                    <span className="metric-desc">Referencia Sistema (Topeado)</span>
                </div>

                <div className="metric-card highlight">
                    <span className="metric-label">Umbral Obligatorio</span>
                    <span className="metric-value">≥ {umbral_objetivo.toFixed(2)}%</span>
                    <span className="metric-desc">Res. 120/2025</span>
                </div>
            </div>

            {ifo_diarios && ifo_diarios.length > 0 && (
                <div className="daily-detail-section">
                    <h4>Desglose Diario</h4>
                    <div className="table-responsive">
                        <table className="daily-table">
                            <thead>
                                <tr>
                                    <th>Fecha</th>
                                    <th>Día</th>
                                    <th>IFO Diario</th>
                                    <th>IFO Diario(Topeado)</th>
                                    <th>Estado</th>
                                </tr>
                            </thead>
                            <tbody>
                                {capped_ifo_diarios.map((d, idx) => (
                                    <tr key={idx}>
                                        <td>{d.fecha}</td>
                                        <td>{new Intl.DateTimeFormat('es-PY', { weekday: 'long' }).format(new Date(d.fecha + 'T00:00:00'))}</td>
                                        <td>{d.ifo.toFixed(2)}%</td>
                                        <td>{d.ifo_topeado.toFixed(2)}%</td>
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
