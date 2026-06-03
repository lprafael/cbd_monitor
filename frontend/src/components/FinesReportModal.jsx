import React, { useState, useEffect } from 'react';
import { API_BASE_URL } from '../config';
import './FinesReportModal.css';

const FinesReportModal = ({ isOpen, onClose, fecha }) => {
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (isOpen && fecha) {
      fetchFinesData();
    }
  }, [isOpen, fecha]);

  const fetchFinesData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [year, month] = fecha.split('-');
      const resp = await fetch(`${API_BASE_URL}/fines-report`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          month: parseInt(month, 10),
          year: parseInt(year, 10)
        })
      });
      
      if (!resp.ok) {
        throw new Error('Error al obtener el reporte de multas');
      }
      
      const json = await resp.json();
      setData(json);
    } catch (err) {
      console.error(err);
      setError(err.message || 'Error de conexión');
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('es-PY', { style: 'currency', currency: 'PYG', maximumFractionDigits: 0 }).format(amount);
  };

  const handlePrint = () => {
    window.print();
  };

  let grandTotalJornales = 0;
  let grandTotalMonto = 0;

  if (data && data.reporte) {
    data.reporte.forEach(empresa => {
      if (empresa.total_jornales) grandTotalJornales += empresa.total_jornales;
      if (empresa.total_guaranies) grandTotalMonto += empresa.total_guaranies;
    });
  }

  return (
    <div className="fines-modal-overlay">
      <div className="fines-modal-container">
        <header className="fines-modal-header">
          <div className="header-info">
            <h2>📜 Reporte de Multas (Res. 21/2026)</h2>
            <span className="current-date">Mes de Referencia: {fecha}</span>
          </div>
          <div>
            <button className="print-btn" onClick={handlePrint} title="Imprimir o Guardar como PDF">🖨️ Generar PDF</button>
            <button className="close-btn" onClick={onClose} title="Cerrar">✖</button>
          </div>
        </header>

        <div className="fines-modal-body">
          {loading ? (
            <div className="loader-container">
              <div className="spinner" style={{ borderTopColor: '#ef4444', borderLeftColor: '#ef4444' }}></div>
              <p>Generando reporte, por favor espere...</p>
            </div>
          ) : error ? (
            <div className="error-container">
              <p>⚠️ {error}</p>
            </div>
          ) : data && data.reporte ? (
            data.reporte.length === 0 ? (
              <p className="no-data">No se encontraron datos para este mes.</p>
            ) : (
              <>
                {data.reporte.map((empresa, idx) => (
                  <div key={idx} className="eot-fines-card">
                    <div className="eot-fines-header">
                      <h3>{empresa.eot_nombre}</h3>
                      {empresa.infracciones.length > 0 && (
                        <div className="fines-totals">
                          <span className="total-jornales">Total Jornales: {empresa.total_jornales}</span>
                          <span className="total-guaranies">Total Gs: {formatCurrency(empresa.total_guaranies)}</span>
                        </div>
                      )}
                    </div>
                    
                    {empresa.infracciones.length === 0 ? (
                      <div className="no-fines">✅ Sin Infracciones detectadas este mes.</div>
                    ) : (
                      <table className="fines-table">
                        <thead>
                          <tr>
                            <th>Fecha</th>
                            <th>Infracción</th>
                            <th>Descripción</th>
                            <th className="td-right">Jornales</th>
                            <th className="td-right">Monto (Gs)</th>
                          </tr>
                        </thead>
                        <tbody>
                          {empresa.infracciones.map((inf, i) => (
                            <tr key={i}>
                              <td>{inf.fecha}</td>
                              <td>{inf.base}</td>
                              <td>{inf.desc}</td>
                              <td className="td-right">{inf.jornales}</td>
                              <td className="td-right">{formatCurrency(inf.monto)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    )}
                  </div>
                ))}

                {grandTotalJornales > 0 && (
                  <div className="grand-totals">
                    <h3>Total General Consolidado</h3>
                    <div className="grand-totals-values">
                      <span className="total-jornales">Jornales: {grandTotalJornales}</span>
                      <span className="total-guaranies">Gs: {formatCurrency(grandTotalMonto)}</span>
                    </div>
                  </div>
                )}
              </>
            )
          ) : null}
        </div>
      </div>
    </div>
  );
};

export default FinesReportModal;
