import React, { useState, useEffect, useCallback } from 'react';
import './SystemIFODashboard.css';
import CalculationMethodologyModal from './CalculationMethodologyModal';
import { API_BASE_URL } from '../config';

const SystemIFODashboard = ({ year, month }) => {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [isMethodologyModalOpen, setIsMethodologyModalOpen] = useState(false);
    const [expandedEots, setExpandedEots] = useState({}); // { eot_id: { loading, data, error } }

    const fetchSystemIFO = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            const response = await fetch(`${API_BASE_URL}/reports/res120/system-ifo-breakdown/${year}/${month}`);
            if (!response.ok) {
                throw new Error('Error al obtener datos del IFO Sistema');
            }
            const result = await response.json();
            setData(result);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    }, [year, month]);

    useEffect(() => {
        if (year && month) {
            fetchSystemIFO();
            setExpandedEots({}); // Reset expanded states on month change
        }
    }, [year, month, fetchSystemIFO]);

    const toggleEotExpansion = async (eotId) => {
        if (expandedEots[eotId] && expandedEots[eotId].data) { // If already expanded and data loaded, just collapse
            const newExpanded = { ...expandedEots };
            delete newExpanded[eotId];
            setExpandedEots(newExpanded);
            return;
        }

        setExpandedEots(prev => ({
            ...prev,
            [eotId]: { loading: true, data: null, error: null }
        }));

        try {
            const response = await fetch(`${API_BASE_URL}/reports/res120/eot-monthly-breakdown/${eotId}/${year}/${month}`);
            if (!response.ok) throw new Error('Error al cargar desglose');
            const breakdownData = await response.json();

            setExpandedEots(prev => ({
                ...prev,
                [eotId]: { loading: false, data: breakdownData, error: null }
            }));
        } catch (err) {
            setExpandedEots(prev => ({
                ...prev,
                [eotId]: { loading: false, data: null, error: err.message }
            }));
        }
    };

    const getMonthName = (m) => {
        const months = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
            'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'];
        return months[m - 1];
    };

    if (!data && !loading && !error) {
        return null;
    }

    if (loading) {
        return (
            <div className="system-ifo-dashboard">
                <div className="loading-message">
                    <div className="spinner"></div>
                    <p>Cargando datos del IFO Sistema...</p>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="system-ifo-dashboard">
                <div className="error-message">
                    <h3>❌ Error</h3>
                    <p>{error}</p>
                </div>
            </div>
        );
    }

    if (!data) return null;

    return (
        <div className="system-ifo-dashboard">
            <div className="dashboard-header">
                <div className="header-content">
                    <div className="header-text-row">
                        <span className="main-title">📊 Desglose del IFO Sistema</span>
                        <span className="period-badge">{getMonthName(data.month)} {data.year}</span>
                        <button
                            className="methodology-button"
                            onClick={() => setIsMethodologyModalOpen(true)}
                            title="Ver metodología de cálculo detallada"
                        >
                            📖 Ver Metodología
                        </button>
                    </div>
                </div>
            </div>

            <div className="summary-section">
                <div className="summary-cards">
                    <div className="summary-card primary">
                        <span className="card-label">IFO Sistema</span>
                        <span className="card-value">{data.ifo_sistema.toFixed(2)}%</span>
                        <span className="card-desc">Promedio de todas las EOTs</span>
                    </div>
                    <div className="summary-card secondary">
                        <span className="card-label">IFO Sistema (Topeado)</span>
                        <span className="card-value">{data.ifo_sistema_topeado.toFixed(2)}%</span>
                        <span className="card-desc">Limitado a 110%</span>
                    </div>
                    <div className="summary-card info">
                        <span className="card-label">EOTs con Datos</span>
                        <span className="card-value">{data.total_eots}</span>
                        <span className="card-desc">Empresas incluidas</span>
                    </div>
                    <div className="summary-card highlight">
                        <span className="card-label">Umbral Obligatorio del IFO (Mes n+1)</span>
                        <span className="card-value">≥ {data.umbral_obligatorio_mes_siguiente?.toFixed(2) || (data.ifo_sistema_topeado).toFixed(2)}%</span>
                        <span className="card-desc">Según Res. 120/2025</span>
                    </div>
                </div>
            </div>

            <div className="exclusions-section">
                <div className="section-title-row">
                    <span className="icon">📅</span>
                    <h3>Días Atípicos y Feriados del Período(Incluidos)</h3>
                </div>
                <div className="exclusions-grid">
                    <div className="exclusion-item">
                        <span className="exclusion-label">🗓️ Domingos:</span>
                        <span className="exclusion-count">{new Set(data.dias_excluidos.domingos).size} días</span>
                    </div>
                    <div className="exclusion-item">
                        <span className="exclusion-label">🎉 Feriados:</span>
                        <span className="exclusion-count">{new Set(data.dias_excluidos.feriados).size} días</span>
                    </div>
                    <div className="exclusion-item">
                        <span className="exclusion-label">⚠️ Días Atípicos:</span>
                        <span className="exclusion-count">{new Set(data.dias_excluidos.atipicos).size} días</span>
                    </div>
                </div>

                <div className="exclusions-list-container">
                    {data.dias_excluidos.feriados.length > 0 && (
                        <div className="exclusion-list-group">
                            <span className="list-label">Feriados:</span>
                            <div className="date-tags">
                                {[...new Set(data.dias_excluidos.feriados)].map(d => <span key={d} className="date-tag holiday">{d}</span>)}
                            </div>
                        </div>
                    )}
                    {data.dias_excluidos.atipicos.length > 0 && (
                        <div className="exclusion-list-group">
                            <span className="list-label">Días Atípicos:</span>
                            <div className="date-tags">
                                {[...new Set(data.dias_excluidos.atipicos)].map(d => <span key={d} className="date-tag atypical">{d}</span>)}
                            </div>
                        </div>
                    )}
                </div>
            </div>

            <div className="eots-section">
                <div className="section-title-row">
                    <span className="icon">🏢</span>
                    <h3>Desglose por Empresa Operadora (EOT)</h3>
                </div>
                <div className="table-responsive">
                    <table className="eots-table">
                        <thead>
                            <tr>
                                <th></th>
                                <th>#</th>
                                <th>Empresa</th>
                                <th>IFO Mensual</th>
                                <th>IFO Topeado</th>
                                <th>Días Válidos</th>
                            </tr>
                        </thead>
                        <tbody>
                            {data.eots.map((eot, idx) => (
                                <React.Fragment key={eot.id_eot_vmt_hex}>
                                    <tr
                                        className={`eot-row ${expandedEots[eot.id_eot_vmt_hex] ? 'expanded' : ''}`}
                                        onClick={() => toggleEotExpansion(eot.id_eot_vmt_hex)}
                                    >
                                        <td className="expand-cell">
                                            <span className={`arrow ${expandedEots[eot.id_eot_vmt_hex] ? 'down' : 'right'}`}>▶</span>
                                        </td>
                                        <td>{idx + 1}</td>
                                        <td className="eot-name">{eot.eot_nombre}</td>
                                        <td className={`ifo-value ${eot.ifo_mensual >= 90 ? 'good' : eot.ifo_mensual >= 80 ? 'warning' : 'bad'}`}>
                                            <div className="value-box">
                                                {eot.ifo_mensual.toFixed(2)}%
                                            </div>
                                        </td>
                                        <td className="ifo-value-topeado">
                                            {eot.ifo_mensual_topeado.toFixed(2)}%
                                        </td>
                                        <td className="dias-count">{eot.dias_validos}</td>
                                    </tr>
                                    {expandedEots[eot.id_eot_vmt_hex] && (
                                        <tr className="detail-row">
                                            <td colSpan="6">
                                                <div className="eot-detail-container">
                                                    {expandedEots[eot.id_eot_vmt_hex].loading && <p className="detail-loading">Cargando desglose...</p>}
                                                    {expandedEots[eot.id_eot_vmt_hex].error && <p className="detail-error">{expandedEots[eot.id_eot_vmt_hex].error}</p>}
                                                    {expandedEots[eot.id_eot_vmt_hex].data && (
                                                        <div className="detail-table-wrapper">
                                                            <table className="detail-table">
                                                                <thead>
                                                                    <tr>
                                                                        <th>Fecha</th>
                                                                        <th>Día</th>
                                                                        <th>IFO Día</th>
                                                                        <th>Ajustes</th>
                                                                        {expandedEots[eot.id_eot_vmt_hex].data[0]?.franjas.map(f => (
                                                                            <th key={f.id_franja}>{f.denominacion}</th>
                                                                        ))}
                                                                    </tr>
                                                                </thead>
                                                                <tbody>
                                                                    {expandedEots[eot.id_eot_vmt_hex].data.map(dia => (
                                                                        <tr key={dia.fecha} className={dia.es_excluido ? 'special-day' : ''}>
                                                                            <td className="date-cell">
                                                                                {dia.fecha}
                                                                                {dia.motivo_exclusion && <span className="exclusion-tag" title={dia.motivo_exclusion}>{dia.motivo_exclusion}</span>}
                                                                            </td>
                                                                            <td>{new Intl.DateTimeFormat('es-PY', { weekday: 'long' }).format(new Date(dia.fecha + 'T00:00:00'))}</td>
                                                                            <td className="ifo-day-val">{dia.ifo_dia.toFixed(2)}%</td>
                                                                            <td className="adjustments-cell-compact">
                                                                                {dia.ajustes && dia.ajustes.length > 0 ? (
                                                                                    <div className="adjustments-tags">
                                                                                        {dia.ajustes.map((a, i) => (
                                                                                            <span key={i} className="adj-tag" title={a}>
                                                                                                {a.split(' ')[0]}
                                                                                            </span>
                                                                                        ))}
                                                                                    </div>
                                                                                ) : '-'}
                                                                            </td>
                                                                            {dia.franjas.map(f => (
                                                                                <td key={f.id_franja} className="franja-val">{f.ifo.toFixed(2)}%</td>
                                                                            ))}
                                                                        </tr>
                                                                    ))}
                                                                </tbody>
                                                            </table>
                                                        </div>
                                                    )}
                                                </div>
                                            </td>
                                        </tr>
                                    )}
                                </React.Fragment>
                            ))}
                        </tbody>
                        <tfoot>
                            <tr className="total-row">
                                <td colSpan="3"><strong>PROMEDIO SISTEMA</strong></td>
                                <td className="ifo-value"><strong>{data.ifo_sistema.toFixed(2)}%</strong></td>
                                <td className="ifo-value-topeado"><strong>{data.ifo_sistema_topeado.toFixed(2)}%</strong></td>
                                <td>-</td>
                            </tr>
                        </tfoot>
                    </table>
                </div>
            </div>

            <div className="methodology-note">
                <h4>📖 Metodología de Cálculo</h4>
                <ol>
                    <li><strong>IFO Franja:</strong> Valor base almacenado en la base de datos</li>
                    <li><strong>IFO Día:</strong> Promedio de IFO Franja por día</li>
                    <li><strong>IFO Mensual EOT:</strong> Promedio de IFO Día (incluyendo todos los días del mes sin exclusión)</li>
                    <li><strong>IFO Sistema:</strong> Promedio de IFO Mensual de todas las EOTs</li>
                </ol>
                <p className="formula">
                    <strong>Umbral Obligatorio (mes n+1) se define según el IFO Sistema Topeado (mes n):</strong>
                    <br />
                    - Si &gt;= 95% → Umbral &gt;= 95%
                    <br />
                    - Si &lt;= 90% → Umbral &lt;= 90%
                    <br />
                    - Si 90% &lt; IFO Sistema &lt; 95% → Umbral = IFO Sistema
                </p>
            </div>

            <CalculationMethodologyModal
                isOpen={isMethodologyModalOpen}
                onClose={() => setIsMethodologyModalOpen(false)}
            />
        </div>
    );
};

export default SystemIFODashboard;
