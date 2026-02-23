import React from 'react';
import './CBDTable.css';

const CBDObjetivoTable = ({ data }) => {
    if (!data) return null;

    const { eot_nombre, fechas, horas_label, franjas_metadata, datos } = data;

    return (
        <div className="cbd-table-container">
            <div className="table-header-info">
                <h2>CBD Objetivo - {eot_nombre}</h2>
                <div className="info-badges">
                    <span className="badge badge-modo">
                        📊 Vista Dual (Hora y Franja)
                    </span>
                    <span className="badge badge-date">
                        📅 Próximos 7 días
                    </span>
                </div>
                <p className="table-description">
                    Esta tabla muestra la cantidad de buses necesaria para mantener un <b>IFO del 100%</b>.
                    Se muestran dos filas por fecha: la primera con el objetivo <b>por hora</b> y la segunda con el objetivo consolidado <b>por franja</b>.
                </p>
            </div>

            <div className="table-wrapper">
                <table className="cbd-table">
                    <thead>
                        <tr>
                            <th className="sticky-col">Fecha / Tipo</th>
                            {horas_label.map(h => (
                                <th key={h} className="header-franja">
                                    <div className="header-content">
                                        <strong>{h}:00</strong>
                                    </div>
                                </th>
                            ))}
                        </tr>
                    </thead>
                    <tbody>
                        {fechas.map(fecha => {
                            const metadata = franjas_metadata[fecha];
                            const diaDatos = datos[fecha];

                            return (
                                <React.Fragment key={fecha}>
                                    {/* Fila POR HORA */}
                                    <tr className="fila-servicios">
                                        <td className="sticky-col">
                                            <strong>{fecha}</strong> <br />
                                            <small>(Por Hora)</small>
                                        </td>
                                        {horas_label.map(h => (
                                            <td key={h} className="celda-datos cumple">
                                                <div className="celda-content">
                                                    <span className="cantidad">{diaDatos.horas[h]}</span>
                                                </div>
                                            </td>
                                        ))}
                                    </tr>

                                    {/* Fila POR FRANJA (usando colspan para alinear) */}
                                    <tr className="fila-cbd">
                                        <td className="sticky-col">
                                            <small>(Por Franja)</small>
                                        </td>
                                        {metadata.map((fr, idx) => {
                                            // Calcular cuántas horas abarca esta franja dentro de nuestro rango (4-23)
                                            const inicio = Math.max(4, fr.hora_inicio);
                                            const fin = Math.min(23, fr.hora_fin);
                                            const span = fin - inicio + 1;

                                            if (span <= 0) return null;

                                            return (
                                                <td
                                                    key={fr.id_franja}
                                                    colSpan={span}
                                                    className="celda-datos cumple"
                                                    style={{ borderLeft: '2px solid var(--border-color)', borderRight: '2px solid var(--border-color)' }}
                                                >
                                                    <div className="celda-content" style={{ flexDirection: 'column', gap: '2px' }}>
                                                        <span className="cantidad" style={{ fontSize: '1.1rem', fontWeight: 'bold' }}>
                                                            {diaDatos.franjas[fr.id_franja]}
                                                        </span>
                                                        <small style={{ fontSize: '0.7rem', opacity: 0.8, textAlign: 'center' }}>
                                                            {fr.denominacion}
                                                        </small>
                                                    </div>
                                                </td>
                                            );
                                        })}
                                    </tr>

                                    {/* Separador visual entre fechas */}
                                    <tr style={{ height: '10px', background: 'transparent' }}>
                                        <td colSpan={horas_label.length + 1}></td>
                                    </tr>
                                </React.Fragment>
                            );
                        })}
                    </tbody>
                </table>
            </div>

            <div className="table-footer">
                <div className="legend">
                    <h3>Nota metodológica:</h3>
                    <p>
                        • <b>Fila Superior:</b> Cantidad de buses distintos por hora.<br />
                        • <b>Fila Inferior:</b> Cantidad de buses distintos necesarios en el conjunto de la franja.
                    </p>
                </div>
            </div>
        </div>
    );
};

export default CBDObjetivoTable;
