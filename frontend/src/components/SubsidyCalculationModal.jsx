import React, { useState, useEffect, useCallback } from 'react';
import './SubsidyCalculationModal.css';
import { API_BASE_URL } from '../config';

const SubsidyCalculationModal = ({ isOpen, onClose, fecha }) => {
    const [year, setYear] = useState(() => fecha ? parseInt(fecha.split('-')[0]) : new Date().getFullYear());
    const [month, setMonth] = useState(() => fecha ? parseInt(fecha.split('-')[1]) : new Date().getMonth() + 1);

    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [expandedEots, setExpandedEots] = useState({});

    // Sincronizar fecha al abrir o cambiar prop
    useEffect(() => {
        if (fecha) {
            const parts = fecha.split('-');
            if (parts.length >= 2) {
                setYear(parseInt(parts[0]));
                setMonth(parseInt(parts[1]));
            }
        }
    }, [fecha, isOpen]);

    const fetchSubsidyData = useCallback(async () => {
        if (!isOpen) return;
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
    }, [isOpen, year, month]);

    useEffect(() => {
        if (isOpen && year && month) {
            fetchSubsidyData();
            setExpandedEots({});
        }
    }, [isOpen, year, month, fetchSubsidyData]);

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

    if (!isOpen) return null;

    return (
        <div className="subsidy-modal-overlay" onClick={onClose}>
            <div className="subsidy-modal-container" onClick={(e) => e.stopPropagation()}>
                {/* Header */}
                <div className="subsidy-modal-header">
                    <div className="title-area">
                        <h2>💰 Cálculo para Habilitación de Subsidio (ICCBDM)</h2>
                        <p className="subtitle">Monitoreo de umbral 95% para cobro de subsidio (Res. 120/2025)</p>
                    </div>

                    <div className="header-controls">
                        <button 
                            className="general-report-btn" 
                            onClick={handleGenerateGeneralReport}
                            title="Generar cuadro e imprimir reporte general de todas las empresas"
                        >
                            📄 Generar Reporte General
                        </button>
                        <div className="period-selectors">
                            <select
                                value={month}
                                onChange={(e) => setMonth(parseInt(e.target.value))}
                                className="period-select"
                            >
                                {Array.from({ length: 12 }, (_, i) => i + 1).map(m => (
                                    <option key={m} value={m}>{getMonthName(m)}</option>
                                ))}
                            </select>
                            <select
                                value={year}
                                onChange={(e) => setYear(parseInt(e.target.value))}
                                className="period-select"
                            >
                                {[2024, 2025, 2026, 2027].map(y => (
                                    <option key={y} value={y}>{y}</option>
                                ))}
                            </select>
                        </div>
                        <button className="close-modal-btn" onClick={onClose} title="Cerrar ventana">✕</button>
                    </div>
                </div>

                {/* Body */}
                <div className="subsidy-modal-body">
                    {loading && (
                        <div className="loading-state">
                            <div className="spinner"></div>
                            <p>Cargando índices ICCBDM para subsidio...</p>
                        </div>
                    )}

                    {error && (
                        <div className="error-state">
                            <h3>❌ Error</h3>
                            <p>{error}</p>
                        </div>
                    )}

                    {!loading && !error && data && (
                        <>
                            {/* Summary Cards */}
                            <div className="subsidy-summary-grid">
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

                            {/* Legend */}
                            <div className="subsidy-legend">
                                <span className="legend-item legend-green">🟢 100%: Cumplimiento Total</span>
                                <span className="legend-item legend-yellow">🟡 95% - 99.9%: Subsidio Habilitado</span>
                                <span className="legend-item legend-red">🔴 &lt; 95%: Subsidio No Habilitado</span>
                            </div>

                            {/* Table */}
                            <div className="subsidy-table-responsive">
                                <table className="subsidy-eots-table">
                                    <thead>
                                        <tr>
                                            <th></th>
                                            <th>#</th>
                                            <th>Empresa Operadora (EOT)</th>
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
                                                    className={`subsidy-eot-row ${expandedEots[eot.id_eot_vmt_hex] ? 'expanded' : ''}`}
                                                    onClick={() => toggleEotExpansion(eot.id_eot_vmt_hex)}
                                                >
                                                    <td className="expand-cell">
                                                        <span className={`arrow ${expandedEots[eot.id_eot_vmt_hex] ? 'down' : 'right'}`}>▶</span>
                                                    </td>
                                                    <td>{idx + 1}</td>
                                                    <td className="eot-name">{eot.eot_nombre}</td>
                                                    <td className="iccbdm-value-col">
                                                        <div className={`value-pill ${eot.estado_color}`}>
                                                            {eot.iccbdm_mensual.toFixed(2)}%
                                                        </div>
                                                    </td>
                                                    <td>
                                                        <span className={`subsidy-status-badge badge-${eot.estado_color}`}>
                                                            {eot.estado_color === 'green' && '✓ Habilitado (100%)'}
                                                            {eot.estado_color === 'yellow' && '✓ Habilitado (≥ 95%)'}
                                                            {eot.estado_color === 'red' && '❌ No Cumple (< 95%)'}
                                                        </span>
                                                    </td>
                                                    <td className="dias-count">{eot.dias_validos}</td>
                                                    <td className="actions-cell">
                                                        <button 
                                                            className="cro-btn"
                                                            onClick={(e) => handleGenerateCRO(eot, e)}
                                                            title={`Generar Constancia de Rendimiento Operativo (CRO) para ${eot.eot_nombre}`}
                                                        >
                                                            📜 Generar CRO
                                                        </button>
                                                    </td>
                                                </tr>

                                                {/* Expanded row for daily and franja breakdown */}
                                                {expandedEots[eot.id_eot_vmt_hex] && (
                                                    <tr className="detail-row">
                                                        <td colSpan="6">
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
                                                                                                <span className={`day-pill ${diaColor}`}>
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
                                    <tfoot>
                                        <tr className="total-row">
                                            <td colSpan="3"><strong>PROMEDIO SISTEMA (ICCBDM)</strong></td>
                                            <td className="iccbdm-value-col">
                                                <div className="value-pill">
                                                    <strong>{data.promedio_sistema.toFixed(2)}%</strong>
                                                </div>
                                            </td>
                                            <td colSpan="2">-</td>
                                        </tr>
                                    </tfoot>
                                </table>
                            </div>
                        </>
                    )}
                </div>
            </div>
        </div>
    );
};

export default SubsidyCalculationModal;
