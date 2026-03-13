import React from 'react';
import './CalculationMethodologyModal.css';

const CalculationMethodologyModal = ({ isOpen, onClose }) => {
    if (!isOpen) return null;

    const handleOverlayClick = (e) => {
        if (e.target.className === 'methodology-modal-overlay') {
            onClose();
        }
    };

    return (
        <div className="methodology-modal-overlay" onClick={handleOverlayClick}>
            <div className="methodology-modal">
                <div className="modal-header">
                    <h2>📖 Metodología de Cálculo del IFO Sistema</h2>
                    <button className="close-button" onClick={onClose}>✕</button>
                </div>

                <div className="modal-content">
                    <section className="methodology-section">
                        <h3>📌 Definición</h3>
                        <p>
                            El <strong>IFO Sistema</strong> es el promedio del Índice de Flota Operativa de todas
                            las Empresas Operadoras de Transporte (EOT) del sistema de transporte público durante
                            un mes calendario específico.
                        </p>
                        <p>
                            Este indicador se utiliza como <strong>base de referencia</strong> para calcular el{' '}
                            <strong>Umbral Obligatorio del IFO</strong> del mes siguiente, que es el umbral mínimo obligatorio
                            que cada EOT debe cumplir.
                        </p>
                    </section>

                    <section className="methodology-section">
                        <h3>🔢 Jerarquía de Cálculo</h3>
                        <p>El cálculo del IFO Sistema sigue una jerarquía de agregación en <strong>4 niveles</strong>:</p>

                        <div className="hierarchy-diagram">
                            <div className="hierarchy-level level-1">
                                <div className="level-number">1</div>
                                <div className="level-content">
                                    <h4>IFO Franja</h4>
                                    <p>Nivel base - Datos precalculados en la base de datos</p>
                                </div>
                            </div>
                            <div className="hierarchy-arrow">↓</div>
                            <div className="hierarchy-level level-2">
                                <div className="level-number">2</div>
                                <div className="level-content">
                                    <h4>IFO Día</h4>
                                    <p>Promedio de IFO Franja (Topeado al 110%)</p>
                                    <code>IFO Día = MIN(AVG(IFO Franja), 1.10)</code>
                                </div>
                            </div>
                            <div className="hierarchy-arrow">↓</div>
                            <div className="hierarchy-level level-3">
                                <div className="level-number">3</div>
                                <div className="level-content">
                                    <h4>IFO Mensual EOT</h4>
                                    <p>Promedio de IFO Día por empresa</p>
                                    <code>IFO Mensual = AVG(IFO Día) × 100</code>
                                </div>
                            </div>
                            <div className="hierarchy-arrow">↓</div>
                            <div className="hierarchy-level level-4">
                                <div className="level-number">4</div>
                                <div className="level-content">
                                    <h4>IFO Sistema</h4>
                                    <p>Promedio de todas las EOTs</p>
                                    <code>IFO Sistema = AVG(IFO Mensual EOT)</code>
                                </div>
                            </div>
                        </div>
                    </section>

                    <section className="methodology-section">
                        <h3>📌 Consideraciones del Período</h3>
                        <div className="exclusions-info">
                            <div className="exclusion-card highlight">
                                <h4>Días Atípicos y Feriados</h4>
                                <p><strong>Nota importante:</strong> Según el requerimiento actual, estos días <strong>SI</strong> se consideran en el promedio mensual, aunque se mantienen identificados visualmente para auditoría:</p>
                                <ul>
                                    <li><strong>Domingos:</strong> Incluidos en el promedio</li>
                                    <li><strong>Feriados:</strong> Incluidos en el promedio</li>
                                    <li><strong>Días Atípicos:</strong> Incluidos en el promedio</li>
                                </ul>
                            </div>
                            <div className="exclusion-card">
                                <h4>Franjas Incluidas</h4>
                                <ul>
                                    <li>✅ Madrugada</li>
                                    <li>✅ Pico Mañana</li>
                                    <li>✅ Entre Picos</li>
                                    <li>✅ Pico Tarde</li>
                                    <li>✅ Pos Pico</li>
                                    <li>✅ Nocturna</li>
                                </ul>
                            </div>
                            <div className="exclusion-card">
                                <h4>EOTs Incluidas</h4>
                                <ul>
                                    <li>✅ Todas las EOTs activas con datos</li>
                                    <li>❌ EOT 72 (excluida por configuración)</li>
                                </ul>
                            </div>
                        </div>
                    </section>

                    <section className="methodology-section">
                        <h3>🎯 Cálculo del Umbral Obligatorio del IFO</h3>
                        <div className="formula-box">
                            <div className="formula-title">Reglas del Umbral Obligatorio</div>
                            <div className="formula-content" style={{ fontSize: '0.9rem' }}>
                                • Si IFO Sistema &gt; 95% → Umbral = 95%
                                <br />
                                • Si IFO Sistema &lt; 90% → Umbral = 90%
                                <br />
                                • Si 90% ≤ IFO Sistema ≤ 95% → Umbral = IFO Sistema
                            </div>
                        </div>

                        <div className="example-box">
                            <h4>Ejemplo Práctico</h4>
                            <table className="example-table">
                                <tbody>
                                    <tr>
                                        <td><strong>Mes anterior (noviembre 2025):</strong></td>
                                        <td>IFO Sistema = 106.35%</td>
                                    </tr>
                                    <tr>
                                        <td><strong>Mes actual (diciembre 2025):</strong></td>
                                        <td>Umbral Obligatorio = <strong>≥ 95.00%</strong></td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>

                        <div className="infraction-box">
                            <h4>⚖️ Regla de Validación (Infracción 15.1)</h4>
                            <p>
                                Si <code>IFO Mensual EOT &lt; Umbral Obligatorio</code> → <strong>Infracción Gravísima</strong> (173 jornales)
                            </p>
                            <p className="legal-reference">
                                Base legal: Artículo 15.1, Resolución GVMT N° 120/2025
                            </p>
                        </div>
                    </section>

                    <section className="methodology-section">
                        <h3>💾 Implementación SQL</h3>
                        <div className="sql-box">
                            <pre><code>{`-- Nivel 4: IFO Sistema
SELECT 
    AVG(eot_monthly_ifo) as ifo_sistema,
    AVG(eot_monthly_ifo_topeado) as ifo_sistema_topeado
FROM (
    -- Nivel 3: IFO Mensual por EOT (Promedio de promedios diarios)
    SELECT 
        id_eot_vmt_hex,
        AVG(daily_ifo) * 100 as eot_monthly_ifo,
        AVG(daily_ifo) * 100 as eot_monthly_ifo_topeado
    FROM (
        -- Nivel 2: IFO Día (Topeado al 110% según Art 2°)
        SELECT 
            id_eot_vmt_hex,
            fecha, 
            LEAST(AVG(franja_avg), 1.1) as daily_ifo
        FROM (
            -- Nivel 1: IFO Franja
            SELECT 
                id_eot_vmt_hex,
                fecha, 
                h.id_franja,
                AVG(ifo) as franja_avg
            FROM control_metricas.ifo_historico h
            JOIN control_metricas.franjas_operativas f 
                ON h.id_franja = f.id_franja
            WHERE h.fecha BETWEEN :inicio_mes AND :fin_mes
            -- Nota: Se incluyen domingos, feriados y atípicos en el cálculo
            GROUP BY id_eot_vmt_hex, fecha, h.id_franja
        ) franja_level
        GROUP BY id_eot_vmt_hex, fecha
    ) daily_avgs
    GROUP BY id_eot_vmt_hex
) eot_avgs;`}</code></pre>
                        </div>
                    </section>

                    <section className="methodology-section">
                        <h3>🔍 Variante: IFO Sistema Topeado</h3>
                        <p>Para ciertos análisis, se calcula también el <strong>IFO Sistema Topeado</strong>:</p>
                        <div className="formula-box secondary">
                            <div className="formula-content">
                                IFO Mensual EOT Topeado = AVG(MIN(IFO Día, 1.1))
                                <br />
                                IFO Sistema Topeado = AVG(IFO Mensual EOT Topeado)
                            </div>
                        </div>
                        <div className="purpose-box">
                            <h4>Propósito</h4>
                            <ul>
                                <li>Limita el impacto de valores excepcionalmente altos (&gt;110%)</li>
                                <li>Proporciona una visión más conservadora del rendimiento del sistema</li>
                                <li>Útil para análisis de tendencias y comparaciones históricas</li>
                            </ul>
                        </div>
                    </section>

                    <section className="methodology-section">
                        <h3>📚 Referencias Legales</h3>
                        <ul className="legal-list">
                            <li><strong>Resolución GVMT N° 120/2025:</strong> Marco normativo del IFO</li>
                            <li><strong>Artículo 6.1:</strong> Definición del IFO Objetivo</li>
                            <li><strong>Artículo 15.1:</strong> Infracción por incumplimiento del IFO Mensual</li>
                            <li><strong>Artículo 22:</strong> Período de socialización y capacitación</li>
                        </ul>
                    </section>

                    <div className="footer-note">
                        <p><strong>Coordinación de Innovación y Desarrollo (CID)</strong></p>
                        <p>Dirección de Monitoreo del Transporte - Viceministerio de Transporte</p>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default CalculationMethodologyModal;
