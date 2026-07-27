import React, { useState, useEffect, useCallback } from 'react';
import './SubsidyCalculationDashboard.css';
import { API_BASE_URL } from '../config';

const SubsidyCalculationDashboard = ({ year, month }) => {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [expandedEots, setExpandedEots] = useState({});

    const fetchSubsidyData = useCallback(async () => {
        if (!year || !month) return;
        setLoading(true);
        setError(null);
        try {
            const response = await fetch(`${API_BASE_URL}/reports/res120/subsidy-breakdown/${year}/${month}`);
            if (!response.ok) {
                throw new Error('Error al obtener datos de cálculo de subsidio');
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
            fetchSubsidyData();
            setExpandedEots({});
        }
    }, [year, month, fetchSubsidyData]);

    const toggleEotExpansion = async (eotId) => {
        if (expandedEots[eotId] && expandedEots[eotId].data) {
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
            const response = await fetch(`${API_BASE_URL}/reports/res120/eot-subsidy-breakdown/${eotId}/${year}/${month}`);
            if (!response.ok) throw new Error('Error al cargar desglose de subsidio');
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
        return months[m - 1] || '';
    };

    const handleGenerateGeneralReport = () => {
        window.print();
    };

    const handleGenerateCRO = (eot, e) => {
        e.stopPropagation();
        alert(`📜 Generando Constancia de Rendimiento Operativo (CRO)\n\nEmpresa: ${eot.eot_nombre}\nPeríodo: ${getMonthName(month)} ${year}\nICCBDM Mensual: ${eot.iccbdm_mensual.toFixed(2)}%\nEstado: ${eot.cumple_subsidio ? 'HABILITADO PARA SUBSIDIO' : 'NO HABILITADO'}`);
    };

    if (loading) {
        return (
            <div className="subsidy-dashboard">
                <div className="loading-message">
                    <div className="spinner"></div>
                    <p>Cargando datos de cálculo para subsidio (ICCBDM)...</p>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="subsidy-dashboard">
                <div className="error-message">
                    <h3>❌ Error</h3>
                    <p>{error}</p>
                </div>
            </div>
        );
    }

    if (!data) return null;

    return (
        <div className="subsidy-dashboard">
            {/* Header */}
            <div className="dashboard-header">
                <div className="header-content">
                    <div className="header-text-row">
                        <span className="main-title">💰 Cálculo para Habilitación de Subsidio (ICCBDM)</span>
                        <span className="period-badge">{getMonthName(data.month)} {data.year}</span>
                        <button 
                            className="general-report-button"
                            onClick={handleGenerateGeneralReport}
                            title="Generar e imprimir reporte general de todas las empresas"
                        >
                            📄 Generar Reporte General
                        </button>
                    </div>
                </div>
            </div>

            {/* Summary Cards */}
            <div className="summary-section">
                <div className="summary-cards">
                    <div className="summary-card card-green">
                        <span className="card-label">Cumplimiento 100%</span>
                        <span className="card-value">{data.eots_cumplen_100}</span>
                        <span className="card-desc">Empresas con ICCBDM = 100%</span>
                    </div>
                    <div className="summary-card card-yellow">
                        <span className="card-label">Habilitadas (95% - 99.9%)</span>
                        <span className="card-value">{data.eots_cumplen_95}</span>
                        <span className="card-desc">Subsidio habilitado con atención</span>
                    </div>
                    <div className="summary-card card-red">
                        <span className="card-label">En Riesgo / No Cumplen (&lt; 95%)</span>
                        <span className="card-value">{data.eots_bajo_95}</span>
                        <span className="card-desc">Inhabilitadas para subsidio</span>
                    </div>
                    <div className="summary-card card-info">
                        <span className="card-label">Promedio Sistema ICCBDM</span>
                        <span className="card-value">{data.promedio_sistema.toFixed(2)}%</span>
                        <span className="card-desc">{data.total_eots} EOTs en total</span>
                    </div>
                </div>
            </div>

            {/* Legend bar */}
            <div className="subsidy-legend-bar">
                <span className="legend-item legend-green">🟢 100%: Cumplimiento Total</span>
                <span className="legend-item legend-yellow">🟡 95% - 99.9%: Subsidio Habilitado</span>
                <span className="legend-item legend-red">🔴 &lt; 95%: Subsidio No Habilitado</span>
            </div>

            {/* EOTs Table */}
            <div className="eots-section">
                <div className="section-title-row">
                    <span className="icon">🏢</span>
                    <h3>Desglose por Empresa Operadora (EOT)</h3>
                </div>

                <div className="table-responsive">
                    <table className="eots-table subsidy-table">
                        <thead>
                            <tr>
                                <th></th>
                                <th>#</th>
                                <th>Empresa</th>
                                <th>ICCBDM Mensual</th>
                                <th>Estado Subsidio</th>
                                <th>Días Válidos</th>
                                <th>Acciones</th>
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
                                        <td className="iccbdm-col">
                                            <div className={`iccbdm-badge ${eot.estado_color}`}>
                                                {eot.iccbdm_mensual.toFixed(2)}%
                                            </div>
                                        </td>
                                        <td className="status-col">
                                            <span className={`subsidy-status-tag tag-${eot.estado_color}`}>
                                                {eot.estado_color === 'green' && '✓ Habilitado (100%)'}
                                                {eot.estado_color === 'yellow' && '✓ Habilitado (≥ 95%)'}
                                                {eot.estado_color === 'red' && '❌ No Cumple (< 95%)'}
                                            </span>
                                        </td>
                                        <td className="dias-count">{eot.dias_validos}</td>
                                        <td className="actions-col">
                                            <button
                                                className="cro-button"
                                                onClick={(e) => handleGenerateCRO(eot, e)}
                                                title={`Generar Constancia de Rendimiento Operativo (CRO) para ${eot.eot_nombre}`}
                                            >
                                                📜 Generar CRO
                                            </button>
                                        </td>
                                    </tr>

                                    {/* Expanded Detail */}
                                    {expandedEots[eot.id_eot_vmt_hex] && (
                                        <tr className="detail-row">
                                            <td colSpan="7">
                                                <div className="eot-detail-container">
                                                    {expandedEots[eot.id_eot_vmt_hex].loading && (
                                                        <p className="detail-loading">Cargando desglose de ICCBDM diario y franjas...</p>
                                                    )}
                                                    {expandedEots[eot.id_eot_vmt_hex].error && (
                                                        <p className="detail-error">{expandedEots[eot.id_eot_vmt_hex].error}</p>
                                                    )}
                                                    {expandedEots[eot.id_eot_vmt_hex].data && (
                                                        <div className="detail-table-wrapper">
                                                            <table className="detail-table">
                                                                <thead>
                                                                    <tr>
                                                                        <th>Fecha</th>
                                                                        <th>Día</th>
                                                                        <th>ICCBDM Día</th>
                                                                        <th>Ajustes</th>
                                                                        {expandedEots[eot.id_eot_vmt_hex].data[0]?.franjas.map(f => (
                                                                            <th key={f.id_franja}>{f.denominacion}</th>
                                                                        ))}
                                                                    </tr>
                                                                </thead>
                                                                <tbody>
                                                                    {expandedEots[eot.id_eot_vmt_hex].data.map(dia => {
                                                                        const diaColor = dia.iccbdm_dia >= 100 ? 'green' : dia.iccbdm_dia >= 95 ? 'yellow' : 'red';
                                                                        return (
                                                                            <tr key={dia.fecha} className={dia.es_excluido ? 'special-day' : ''}>
                                                                                <td className="date-cell">
                                                                                    {dia.fecha}
                                                                                    {dia.motivo_exclusion && (
                                                                                        <span className="exclusion-tag" title={dia.motivo_exclusion}>
                                                                                            {dia.motivo_exclusion}
                                                                                        </span>
                                                                                    )}
                                                                                </td>
                                                                                <td>{new Intl.DateTimeFormat('es-PY', { weekday: 'long' }).format(new Date(dia.fecha + 'T00:00:00'))}</td>
                                                                                <td className="iccbdm-day-val">
                                                                                    <span className={`day-pill pill-${diaColor}`}>
                                                                                        {dia.iccbdm_dia.toFixed(2)}%
                                                                                    </span>
                                                                                </td>
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
                                                                                {dia.franjas.map(f => {
                                                                                    const fColor = f.iccbdm >= 100 ? 'cell-green' : f.iccbdm >= 95 ? 'cell-yellow' : 'cell-red';
                                                                                    return (
                                                                                        <td key={f.id_franja} className={`franja-val ${fColor}`}>
                                                                                            {f.iccbdm.toFixed(2)}%
                                                                                        </td>
                                                                                    );
                                                                                })}
                                                                            </tr>
                                                                        );
                                                                    })}
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
                    </table>
                </div>
            </div>
        </div>
    );
};

export default SubsidyCalculationDashboard;
