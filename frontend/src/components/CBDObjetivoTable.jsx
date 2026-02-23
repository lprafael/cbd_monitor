import React from 'react';
import './CBDTable.css'; // Reutilizamos estilos si es posible o creamos uno nuevo

const CBDObjetivoTable = ({ data }) => {
    if (!data) return null;

    const { eot_nombre, modo, fechas, columnas, datos } = data;

    return (
        <div className="cbd-table-container">
            <div className="table-header-info">
                <h2>CBD Objetivo - {eot_nombre}</h2>
                <div className="info-badges">
                    <span className="badge badge-modo">
                        📊 Modo: {modo === 'franja' ? 'Por Franja' : 'Por Hora'}
                    </span>
                    <span className="badge badge-date">
                        📅 Próximos 7 días
                    </span>
                </div>
                <p className="table-description">
                    Esta tabla muestra la cantidad de buses que la empresa debe operar para mantener un <b>IFO del 100%</b> el próximo día equivalente.
                </p>
            </div>

            <div className="table-wrapper">
                <table className="cbd-table">
                    <thead>
                        <tr>
                            <th className="sticky-col">Fecha</th>
                            {columnas.map(col => (
                                <th key={col}>{col}</th>
                            ))}
                        </tr>
                    </thead>
                    <tbody>
                        {fechas.map(fecha => (
                            <tr key={fecha}>
                                <td className="sticky-col">
                                    <strong>{fecha}</strong>
                                </td>
                                {columnas.map(col => (
                                    <td key={col} className="celda-datos cumple">
                                        <div className="celda-content">
                                            <span className="cantidad">{datos[fecha][col]}</span>
                                        </div>
                                    </td>
                                ))}
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

            <div className="table-footer">
                <div className="legend">
                    <h3>Nota:</h3>
                    <p>Los valores indicados son el mínimo necesario (B_dist ajustado) para alcanzar el Nivel A.</p>
                </div>
            </div>
        </div>
    );
};

export default CBDObjetivoTable;
