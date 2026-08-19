import React, { useState, useEffect } from 'react';
import { API_BASE_URL } from '../config';
import { generateActaPdf } from '../utils/generateActaPdf';
import { generateNotificacionesWord } from '../utils/generateNotificacionesWord';
import './FinesReportModal.css';

const FinesReportModal = ({ isOpen, onClose, fecha }) => {
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [reincidencias, setReincidencias] = useState({});
  const [actaModalOpen, setActaModalOpen] = useState(false);
  const [selectedEmpresa, setSelectedEmpresa] = useState(null);
  const [numeroActa, setNumeroActa] = useState("");
  const [fechaEmision, setFechaEmision] = useState("");
  const [isFechaBlanco, setIsFechaBlanco] = useState(false);

  const handleOpenActaModal = (empresa) => {
    setSelectedEmpresa(empresa);
    setNumeroActa("");
    setFechaEmision("");
    setIsFechaBlanco(false);
    setActaModalOpen(true);
  };

  const handleConfirmActa = () => {
    if (selectedEmpresa) {
      generateActaPdf(selectedEmpresa, fecha, numeroActa, fechaEmision, isFechaBlanco);
    }
    setActaModalOpen(false);
  };

  const handleReincidenciaChange = (eot_hex, checked) => {
    setReincidencias(prev => ({ ...prev, [eot_hex]: checked }));
  };

  const handleToggleAllReincidencias = (checked) => {
    if (!data || !data.reporte) return;
    const filtered = data.reporte.filter(empresa => !empresa.eot_nombre.toUpperCase().includes('ARAPOTI'));
    const nextState = { ...reincidencias };
    filtered.forEach(empresa => {
      nextState[empresa.eot_hex] = checked;
    });
    setReincidencias(nextState);
  };

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

  let grandTotalJornales = 0;
  let grandTotalMonto = 0;

  let processedReporte = [];
  if (data && data.reporte) {
    const filtered = data.reporte.filter(empresa => !empresa.eot_nombre.toUpperCase().includes('ARAPOTI'));
    
    processedReporte = filtered.map(empresa => {
      const isReincidente = reincidencias[empresa.eot_hex];
      let newInfracciones = [];
      let newTotalJornales = 0;
      let newTotalGuaranies = 0;

      if (isReincidente) {
        newInfracciones = empresa.infracciones.map(inf => {
          if (inf.base === 'Art. 15.1') {
            return {
              ...inf,
              base: 'Art. 16.1',
              desc: inf.desc.replace('IFO Mensual', 'Reincidencia IFO Mensual'),
              jornales: 224.9,
              monto: 25076796
            };
          } else if (inf.base === 'Art. 15.2') {
            return {
              ...inf,
              base: 'Art. 16.2',
              desc: inf.desc.replace('Acumulación 5 Franjas Pico', 'Reincidencia Acumulación 5 Franjas Pico'),
              jornales: 20,
              monto: 2230040
            };
          } else if (inf.base === 'Art. 15.4') {
            return {
              ...inf,
              base: 'Art. 16.4',
              desc: inf.desc.replace('Acumulación 5 Franjas Pos Pico', 'Reincidencia Acumulación 5 Franjas Pos Pico'),
              jornales: 20,
              monto: 2230040
            };
          }
          return inf;
        });
      } else {
        newInfracciones = empresa.infracciones;
      }

      newInfracciones.forEach(inf => {
        newTotalJornales += inf.jornales;
        newTotalGuaranies += inf.monto;
      });

      return {
        ...empresa,
        infracciones: newInfracciones,
        total_jornales: newTotalJornales,
        total_guaranies: newTotalGuaranies
      };
    });

    processedReporte.forEach(empresa => {
      if (empresa.total_jornales) grandTotalJornales += empresa.total_jornales;
      if (empresa.total_guaranies) grandTotalMonto += empresa.total_guaranies;
    });
  }

  const allReincidentes = processedReporte.length > 0 && processedReporte.every(empresa => !!reincidencias[empresa.eot_hex]);

  const handlePrint = () => {
    window.print();
    if (processedReporte && processedReporte.length > 0) {
      generateNotificacionesWord(processedReporte, fecha);
    }
  };

  return (
    <div className="fines-modal-overlay">
      <div className="fines-modal-container">
        <header className="fines-modal-header">
          <div className="header-info">
            <h2>📜 Reporte de Multas (Res. 21/2026)</h2>
            <span className="current-date">Mes de Referencia: {fecha}</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
            {processedReporte.length > 0 && (
              <label className="reincidencia-label-all" style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px', cursor: 'pointer', fontWeight: 'bold', color: '#dc2626', background: '#fee2e2', padding: '6px 12px', borderRadius: '6px', border: '1px solid #fca5a5' }}>
                <input 
                  type="checkbox" 
                  checked={allReincidentes}
                  onChange={(e) => handleToggleAllReincidencias(e.target.checked)}
                />
                Marcar todos c/reincidencia
              </label>
            )}
            <button className="print-btn" onClick={handlePrint} title="Imprimir PDF y Descargar Notificaciones (Word)">🖨️ Generar PDF y Notificaciones</button>
            <button className="close-btn" onClick={onClose} title="Cerrar">✖</button>
          </div>
        </header>

        <div className="fines-modal-body">
          <table className="print-layout-table">
            <thead className="print-only">
              <tr>
                <td>
                  <div className="print-header-content">
                    <img src={process.env.PUBLIC_URL + '/imagenes/Logo MOPC VMT.png'} alt="MOPC VMT" />
                    <hr />
                    <h2 style={{ fontSize: '18px', margin: '10px 0', textAlign: 'center' }}>Reporte de Multas (Res. 21/2026) - Mes de Referencia: {fecha}</h2>
                  </div>
                </td>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>
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
            processedReporte.length === 0 ? (
              <p className="no-data">No se encontraron datos para este mes.</p>
            ) : (
              <>
                {processedReporte.map((empresa, idx) => (
                  <div key={idx} className="eot-fines-card">
                    <div className="eot-fines-header">
                      <h3>{empresa.eot_nombre}</h3>
                      <div className="eot-header-actions">
                        {empresa.infracciones.length > 0 && (
                          <div className="fines-totals">
                            <span className="total-jornales">Total Jornales: {empresa.total_jornales}</span>
                            <span className="total-guaranies">Total Gs: {formatCurrency(empresa.total_guaranies)}</span>
                          </div>
                        )}
                        <label className="reincidencia-label" style={{ display: 'flex', alignItems: 'center', gap: '5px', fontSize: '13px', cursor: 'pointer', fontWeight: 'bold', color: '#dc2626' }}>
                          <input 
                            type="checkbox" 
                            checked={!!reincidencias[empresa.eot_hex]}
                            onChange={(e) => handleReincidenciaChange(empresa.eot_hex, e.target.checked)}
                          />
                          c/reincidencia
                        </label>
                        <button 
                          className="generate-acta-btn" 
                          onClick={() => handleOpenActaModal(empresa)}
                          title="Generar Acta de Infracción"
                        >
                          📄 Generar Acta
                        </button>
                      </div>
                    </div>

                    {empresa.alerta_sumario && empresa.motivos_sumario && (
                      <div className="eot-alertas" style={{ padding: '8px 12px', backgroundColor: '#fee2e2', color: '#b91c1c', borderLeft: '4px solid #ef4444', marginTop: '10px', marginBottom: '10px', fontSize: '13px', fontWeight: 'bold', borderRadius: '4px' }}>
                        {empresa.motivos_sumario.map((motivo, mi) => (
                          <div key={mi}>⚠️ {motivo}</div>
                        ))}
                      </div>
                    )}
                    
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
                </td>
              </tr>
            </tbody>
            <tfoot className="print-only">
              <tr>
                <td>
                  <div className="print-footer-content">
                    <hr />
                    <p><strong>Misión:</strong> "Somos un organismo que elabora, propone y ejecuta políticas en materia de infraestructura pública, transporte, minería y energía, para la integración y desarrollo económico de la población".</p>
                    <p><strong>Visión:</strong> "Ser reconocidos por nuestra idoneidad en planificación y ejecución de políticas y proyectos, garantizando la conectividad a través de infraestructuras públicas innovadoras, gestionadas de forma eficiente, transparente y enfocadas al ciudadano".</p>
                  </div>
                </td>
              </tr>
            </tfoot>
          </table>
        </div>
      </div>

      {actaModalOpen && (
        <div className="acta-modal-overlay">
          <div className="acta-modal-content">
            <h3>Datos del Acta - {selectedEmpresa?.eot_nombre}</h3>
            
            <div className="form-group">
              <label>Número de Acta:</label>
              <input 
                type="text" 
                placeholder="Ej: 123/2026" 
                value={numeroActa} 
                onChange={(e) => setNumeroActa(e.target.value)} 
              />
              <small>Si se deja en blanco se imprimirá "___/2026"</small>
            </div>

            <div className="form-group">
              <label>Fecha de Emisión:</label>
              <input 
                type="date" 
                value={fechaEmision} 
                onChange={(e) => setFechaEmision(e.target.value)} 
                disabled={isFechaBlanco}
              />
              <small>Si no ingresa, usará la fecha actual.</small>
            </div>

            <div className="form-group-checkbox">
              <label>
                <input 
                  type="checkbox" 
                  checked={isFechaBlanco} 
                  onChange={(e) => setIsFechaBlanco(e.target.checked)} 
                />
                Dejar fecha en blanco
              </label>
            </div>

            <div className="acta-modal-actions">
              <button className="btn-cancel" onClick={() => setActaModalOpen(false)}>Cancelar</button>
              <button className="btn-confirm" onClick={handleConfirmActa}>Generar PDF</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default FinesReportModal;
