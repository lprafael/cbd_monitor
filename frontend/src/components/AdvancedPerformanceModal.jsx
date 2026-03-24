import React, { useState, useEffect, useMemo } from 'react';
import { 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, 
  LineChart, Line, AreaChart, Area, Cell, ReferenceLine, PieChart, Pie
} from 'recharts';
import './AdvancedPerformanceModal.css';

const AdvancedPerformanceModal = ({ isOpen, onClose, fecha, theme }) => {
  const [activeTab, setActiveTab] = useState('daily'); // 'daily' | 'monthly'
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState(null);
  const [monthlyData, setMonthlyData] = useState(null);
  const [selectedEot, setSelectedEot] = useState(null); // null = Sistema AMA
  const [eotBreakdown, setEotBreakdown] = useState(null);
  const [loadingBreakdown, setLoadingBreakdown] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (isOpen && fecha) {
      if (activeTab === 'daily') {
        fetchDailyData();
      } else {
        fetchMonthlyData();
      }
    }
  }, [isOpen, fecha, activeTab]);

  useEffect(() => {
    if (selectedEot && activeTab === 'monthly' && fecha) {
      fetchEotMonthlyBreakdown(selectedEot.id_eot_vmt_hex);
    } else {
      setEotBreakdown(null);
    }
  }, [selectedEot, activeTab, fecha]);

  const fetchDailyData = async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await fetch(`/api/reports/res120/advanced-daily-report/${fecha}`);
      if (!resp.ok) throw new Error('Error al obtener datos diarios avanzados');
      const json = await resp.json();
      setData(json);
      setSelectedEot(null);
    } catch (err) {
      console.error(err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const fetchMonthlyData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [year, month] = fecha.split('-');
      const resp = await fetch(`/api/reports/res120/system-ifo-breakdown/${year}/${parseInt(month)}`);
      if (!resp.ok) throw new Error('Error al obtener datos mensuales');
      const json = await resp.json();
      setMonthlyData(json);
      setSelectedEot(null);
    } catch (err) {
      console.error(err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const fetchEotMonthlyBreakdown = async (eotId) => {
    setLoadingBreakdown(true);
    try {
      const [year, month] = fecha.split('-');
      const resp = await fetch(`/api/reports/res120/eot-monthly-breakdown/${eotId}/${year}/${parseInt(month)}`);
      if (!resp.ok) throw new Error('Error al obtener historial de la empresa');
      const json = await resp.json();
      setEotBreakdown(json);
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingBreakdown(false);
    }
  };

  const currentEotRanking = useMemo(() => {
    if (activeTab === 'daily') return data?.ranking_eots || [];
    return monthlyData?.eots || [];
  }, [activeTab, data, monthlyData]);

  if (!isOpen) return null;

  const GREEN = '#10b981';
  const RED = '#ef4444';
  const GRAY = '#94a3b8';

  return (
    <div className={`advanced-modal-overlay theme-light`}>
      <div className="advanced-modal-container">
        <header className="advanced-modal-header">
          <div className="header-info">
            <h2>📊 Reporte Ejecutivo de Desempeño</h2>
            <span className="current-date">Fecha de Referencia: {fecha}</span>
          </div>
          <div className="tab-controls">
            <button 
              className={`tab-btn ${activeTab === 'daily' ? 'active' : ''}`}
              onClick={() => setActiveTab('daily')}
            >
              📅 Por Fecha
            </button>
            <button 
              className={`tab-btn ${activeTab === 'monthly' ? 'active' : ''}`}
              onClick={() => setActiveTab('monthly')}
            >
              📈 Por Mes
            </button>
          </div>
          <button className="close-btn" onClick={onClose}>✖</button>
        </header>

        <div className="advanced-modal-body">
          <aside className="advanced-sidebar">
            <div className="sidebar-header">
              <h4>Listado de Empresas</h4>
              <button 
                className={`system-select-btn ${selectedEot === null ? 'active' : ''}`}
                onClick={() => setSelectedEot(null)}
              >
                🌍 SISTEMA AMA (Global)
              </button>
            </div>
            <div className="sidebar-list">
              {currentEotRanking.map((eot, idx) => {
                const isSelected = selectedEot?.id_eot_vmt_hex === eot.id_eot_vmt_hex || selectedEot?.name === eot.name;
                const val = eot.ifo !== undefined ? eot.ifo : eot.ifo_mensual;
                return (
                  <div 
                    key={idx} 
                    className={`sidebar-item ${isSelected ? 'active' : ''}`}
                    onClick={() => setSelectedEot(eot)}
                  >
                    <span className="eot-name">{eot.name || eot.eot_nombre}</span>
                    <span className={`eot-badge ${val >= (data?.ifo_objetivo || 90) ? 'good' : 'bad'}`}>
                      {val.toFixed(1)}%
                    </span>
                  </div>
                );
              })}
            </div>
          </aside>

          <main className="advanced-main-content">
            {loading ? (
              <div className="loader-container">
                <div className="spinner"></div>
                <p>Cargando datos...</p>
              </div>
            ) : error ? (
              <div className="error-container">
                <p>⚠️ {error}</p>
              </div>
            ) : (
              <div className="advanced-grid">
                {activeTab === 'daily' && data && (
                  <>
                    {!selectedEot ? (
                      <>
                        <div className="kpi-row">
                          <div className="kpi-card border-shadow">
                            <h3>IFO Promedio Sistema</h3>
                            <div className="kpi-value" style={{color: data.ifo_sistema >= data.ifo_objetivo ? GREEN : RED}}>
                              {data.ifo_sistema.toFixed(2)}%
                            </div>
                            <div className={`kpi-indicator ${data.ifo_sistema >= data.ifo_objetivo ? 'pos' : 'neg'}`}>
                              {data.ifo_sistema >= data.ifo_objetivo ? 'CUMPLE META' : 'BAJO META'}
                            </div>
                          </div>
                          <div className="kpi-card border-shadow">
                            <h3>Meta Vigente</h3>
                            <div className="kpi-value" style={{color: '#475569'}}>{data.ifo_objetivo.toFixed(2)}%</div>
                            <div className="kpi-sub">Umbral Res. 120/25</div>
                          </div>
                        </div>

                        <div className="chart-row stretch">
                          <div className="chart-card border-shadow">
                            <h4>Ranking por Empresa (IFO %)</h4>
                            <ResponsiveContainer width="100%" height={300}>
                              <BarChart data={data.ranking_eots} layout="vertical" margin={{left: 20}}>
                                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                                <XAxis type="number" domain={[0, 110]} />
                                <YAxis dataKey="name" type="category" width={120} fontSize={10} />
                                <Tooltip cursor={{fill: 'rgba(0,0,0,0.05)'}} />
                                <Bar dataKey="ifo" radius={[0, 4, 4, 0]}>
                                  {data.ranking_eots.map((entry, index) => (
                                    <Cell key={`cell-${index}`} fill={entry.ifo >= data.ifo_objetivo ? GREEN : RED} />
                                  ))}
                                </Bar>
                                <ReferenceLine x={data.ifo_objetivo} stroke="#f59e0b" strokeDasharray="5 5" label={{position: 'top', value: 'META', fontSize: 10, fill: '#f59e0b'}} />
                              </BarChart>
                            </ResponsiveContainer>
                          </div>
                          <div className="chart-card border-shadow">
                            <h4>Buses Observados vs Base (AMA)</h4>
                            <ResponsiveContainer width="100%" height={300}>
                              <AreaChart data={data.buses_by_hour}>
                                <CartesianGrid strokeDasharray="3 3" />
                                <XAxis dataKey="hour" label={{value: 'Hora', position: 'bottom', fontSize: 10}} />
                                <YAxis />
                                <Tooltip />
                                <Area type="monotone" dataKey="real" name="Obs. Real" stroke="#2563eb" fill="#2563eb" fillOpacity={0.1} strokeWidth={2} />
                                <Line type="stepAfter" dataKey="base" name="Base CBD" stroke={GRAY} strokeDasharray="5 5" dot={false} />
                              </AreaChart>
                            </ResponsiveContainer>
                          </div>
                        </div>
                      </>
                    ) : (
                      <div className="eot-detail-view">
                        <div className="kpi-row">
                          <div className="kpi-card border-shadow">
                            <h3>Resultado Empresa: {selectedEot.name}</h3>
                            <div className="kpi-value" style={{color: selectedEot.ifo >= data.ifo_objetivo ? GREEN : RED}}>
                              {selectedEot.ifo.toFixed(2)}%
                            </div>
                          </div>
                        </div>
                        <div className="chart-row full-width">
                          <div className="chart-card border-shadow">
                            <h4>Desempeño por Franja Horaria</h4>
                            {(() => {
                              const detail = data.franjas_by_eot.find(f => f.eot === selectedEot.name);
                              if (!detail) return <p className="no-data">No hay datos de franjas para esta fecha.</p>;
                              return (
                                <ResponsiveContainer width="100%" height={350}>
                                  <BarChart data={detail.franjas}>
                                    <CartesianGrid strokeDasharray="3 3" vertical={false} />
                                    <XAxis dataKey="denominacion" />
                                    <YAxis domain={[0, 110]} />
                                    <Tooltip cursor={{fill: 'rgba(0,0,0,0.05)'}} />
                                    <Bar dataKey="ifo" name="IFO %" radius={[4, 4, 0, 0]}>
                                      {detail.franjas.map((f, i) => (
                                        <Cell key={i} fill={f.ifo >= 90 ? GREEN : RED} />
                                      ))}
                                    </Bar>
                                    <ReferenceLine y={90} stroke="#f59e0b" strokeDasharray="3 3" />
                                  </BarChart>
                                </ResponsiveContainer>
                              );
                            })()}
                          </div>
                        </div>
                      </div>
                    )}
                  </>
                )}

                {activeTab === 'monthly' && monthlyData && (
                  <>
                    {!selectedEot ? (
                      <>
                        <div className="kpi-row">
                          <div className="kpi-card border-shadow">
                            <h3>IFO Promedio Mensual (Tope 110%)</h3>
                            <div className="kpi-value" style={{color: GREEN}}>{monthlyData.ifo_sistema_topeado.toFixed(2)}%</div>
                          </div>
                          <div className="kpi-card border-shadow">
                            <h3>Umbral Objetivo</h3>
                            <div className="kpi-value" style={{color: '#475569'}}>{monthlyData.umbral_obligatorio_mes_siguiente.toFixed(2)}%</div>
                          </div>
                        </div>
                        <div className="chart-row full-width">
                          <div className="chart-card border-shadow">
                            <h4>Evolución Diaria del Sistema (%)</h4>
                            <ResponsiveContainer width="100%" height={350}>
                              <LineChart data={monthlyData.daily_averages}>
                                <CartesianGrid strokeDasharray="3 3" />
                                <XAxis dataKey="fecha" tickFormatter={v => v.split('-')[2]} />
                                <YAxis domain={[0, 110]} />
                                <Tooltip />
                                <Line type="monotone" dataKey="promedio" name="Sistema" stroke={GREEN} strokeWidth={3} dot={{r: 4, fill: GREEN}} />
                                <Line type="monotone" dataKey="minimo" name="Mínimo" stroke={RED} strokeDasharray="5 5" dot={false} />
                                <ReferenceLine y={90} stroke="#f59e0b" strokeDasharray="3 3" />
                              </LineChart>
                            </ResponsiveContainer>
                          </div>
                        </div>
                      </>
                    ) : (
                      <div className="eot-detail-view">
                        <div className="kpi-row">
                          <div className="kpi-card border-shadow">
                            <h3>Histórico Mensual: {selectedEot.eot_nombre}</h3>
                            <div className="kpi-value" style={{color: selectedEot.ifo_mensual_topeado >= 90 ? GREEN : RED}}>
                              {selectedEot.ifo_mensual_topeado.toFixed(2)}%
                            </div>
                            <div className="kpi-sub">{selectedEot.dias_validos} días operados</div>
                          </div>
                        </div>
                        <div className="chart-row full-width">
                          <div className="chart-card border-shadow">
                            <h4>Rendimiento Diario en el Mes</h4>
                            {loadingBreakdown ? (
                              <div className="mini-loader">Consultando historial...</div>
                            ) : eotBreakdown ? (
                              <ResponsiveContainer width="100%" height={350}>
                                <BarChart data={eotBreakdown}>
                                  <CartesianGrid strokeDasharray="3 3" vertical={false} />
                                  <XAxis dataKey="fecha" tickFormatter={v => v.split('-')[2]} />
                                  <YAxis domain={[0, 110]} />
                                  <Tooltip cursor={{fill: 'rgba(0,0,0,0.05)'}} />
                                  <Bar dataKey="ifo_dia" name="IFO Diario" radius={[4, 4, 0, 0]}>
                                    {eotBreakdown.map((d, i) => (
                                      <Cell key={i} fill={d.ifo_dia >= 90 ? GREEN : RED} />
                                    ))}
                                  </Bar>
                                  <ReferenceLine y={90} stroke="#f59e0b" strokeDasharray="3 3" />
                                </BarChart>
                              </ResponsiveContainer>
                            ) : <p className="no-data">No se pudo recuperar el historial mensual.</p>}
                          </div>
                        </div>
                      </div>
                    )}
                  </>
                )}
              </div>
            )}
          </main>
        </div>
      </div>
    </div>
  );
};

export default AdvancedPerformanceModal;
