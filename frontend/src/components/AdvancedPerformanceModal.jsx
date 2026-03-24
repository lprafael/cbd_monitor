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

  const fetchDailyData = async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await fetch(`/api/reports/res120/advanced-daily-report/${fecha}`);
      if (!resp.ok) throw new Error('Error al obtener datos diarios avanzados');
      const json = await resp.json();
      setData(json);
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
      // Usamos el endpoint de breakdown mensual existente
      const [year, month] = fecha.split('-');
      const resp = await fetch(`/api/reports/res120/system-ifo-breakdown/${year}/${parseInt(month)}`);
      if (!resp.ok) throw new Error('Error al obtener datos mensuales');
      const json = await resp.json();
      setMonthlyData(json);
    } catch (err) {
      console.error(err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className={`advanced-modal-overlay theme-${theme}`}>
      <div className="advanced-modal-container">
        <header className="advanced-modal-header">
          <div className="header-info">
            <h2>📊 Dashboard de Desempeño Avanzado</h2>
            <span className="current-date">Referencia: {fecha}</span>
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
          <button className="close-btn" onClick={onClose}>✖️</button>
        </header>

        <div className="advanced-modal-content">
          {loading ? (
            <div className="loader-container">
              <div className="spinner"></div>
              <p>Procesando analíticas avanzadas...</p>
            </div>
          ) : error ? (
            <div className="error-container">
              <p>⚠️ {error}</p>
              <button onClick={activeTab === 'daily' ? fetchDailyData : fetchMonthlyData}>Reintentar</button>
            </div>
          ) : (
            <>
              {activeTab === 'daily' && data && (
                <div className="advanced-grid">
                  {/* Fila 1: KPIs */}
                  <div className="kpi-row">
                    <div className="kpi-card glass">
                      <h3>IFO Sistema</h3>
                      <div className="kpi-value">{data.ifo_sistema.toFixed(2)}%</div>
                      <div className={`kpi-indicator ${data.ifo_sistema >= data.ifo_objetivo ? 'pos' : 'neg'}`}>
                        {data.ifo_sistema >= data.ifo_objetivo ? '🚀 Cumple Meta' : '📉 Bajo Meta'}
                      </div>
                    </div>
                    <div className="kpi-card glass">
                      <h3>Meta (IFO Base)</h3>
                      <div className="kpi-value secondary">{data.ifo_objetivo.toFixed(2)}%</div>
                      <div className="kpi-sub">Umbral obligatorio Res. 120/25</div>
                    </div>
                    <div className="kpi-card glass">
                      <h3>Buses Observados</h3>
                      <div className="kpi-value accent">{data.total_buses.toLocaleString()}</div>
                      <div className="kpi-sub">Total flota en operación today</div>
                    </div>
                  </div>

                  {/* Fila 2: Ranking y Buses por Hora */}
                  <div className="chart-row stretch">
                    <div className="chart-card glass">
                      <h4>🏆 Ranking de Desempeño por EOT (IFO %)</h4>
                      <ResponsiveContainer width="100%" height={300}>
                        <BarChart data={data.ranking_eots} layout="vertical">
                          <CartesianGrid strokeDasharray="3 3" opacity={0.1} />
                          <XAxis type="number" domain={[0, 110]} hide />
                          <YAxis dataKey="name" type="category" width={100} fontSize={10} stroke="#888" />
                          <Tooltip 
                            contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 8px 32px rgba(0,0,0,0.2)' }}
                          />
                          <Bar dataKey="ifo" radius={[0, 4, 4, 0]}>
                            {data.ranking_eots.map((entry, index) => (
                              <Cell key={`cell-${index}`} fill={entry.ifo >= data.ifo_objetivo ? '#10b981' : '#ef4444'} />
                            ))}
                          </Bar>
                          <ReferenceLine x={data.ifo_objetivo} stroke="#f59e0b" strokeDasharray="5 5" label={{ position: 'top', value: 'META', fill: '#f59e0b', fontSize: 10 }} />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>

                    <div className="chart-card glass">
                      <h4>🚌 AMA: Buses Observados vs Objetivo (Por Hora)</h4>
                      <ResponsiveContainer width="100%" height={300}>
                        <AreaChart data={data.buses_by_hour}>
                          <defs>
                            <linearGradient id="colorReal" x1="0" y1="0" x2="0" y2="1">
                              <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.8}/>
                              <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                            </linearGradient>
                          </defs>
                          <CartesianGrid strokeDasharray="3 3" opacity={0.1} />
                          <XAxis dataKey="hour" stroke="#888" fontSize={11} label={{ value: 'Hora', position: 'bottom', fontSize: 10 }} />
                          <YAxis stroke="#888" fontSize={11} />
                          <Tooltip />
                          <Legend verticalAlign="top" height={36}/>
                          <Area type="monotone" dataKey="real" name="Obs. Real" stroke="#3b82f6" fillOpacity={1} fill="url(#colorReal)" strokeWidth={3} />
                          <Line type="stepAfter" dataKey="base" name="CBD Base" stroke="#9ca3af" strokeDasharray="5 5" dot={false} />
                        </AreaChart>
                      </ResponsiveContainer>
                    </div>
                  </div>

                  {/* Fila 3: Detalles Franjas y IFO Horario */}
                  <div className="chart-row">
                    <div className="chart-card glass">
                      <h4>📊 IFO por Hora (%) - Sistema AMA</h4>
                      <ResponsiveContainer width="100%" height={250}>
                        <BarChart data={data.buses_by_hour}>
                          <CartesianGrid strokeDasharray="3 3" opacity={0.1} />
                          <XAxis dataKey="hour" fontSize={10} stroke="#888" />
                          <YAxis domain={[0, 110]} fontSize={10} stroke="#888" />
                          <Tooltip />
                          <Bar dataKey="ifo" name="IFO Hourly" radius={[4, 4, 0, 0]}>
                            {data.buses_by_hour.map((entry, index) => (
                              <Cell key={`cell-h-${index}`} fill={entry.ifo >= 90 ? '#8b5cf6' : '#ec4899'} />
                            ))}
                          </Bar>
                          <ReferenceLine y={90} stroke="#ef4444" strokeDasharray="3 3" />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>

                    <div className="chart-card glass overflow-y">
                      <h4>🏢 Desglose Franjas: EOTs Destacadas</h4>
                      <div className="franjas-comparison">
                        {data.franjas_by_eot.map((item, idx) => (
                          <div key={idx} className="eot-detail-mini">
                            <h5>{item.eot}</h5>
                            <div className="franja-pills">
                              {item.franjas.map((f, fidx) => (
                                <div key={fidx} className={`franja-pill ${f.ifo >= 90 ? 'ok' : 'crit'}`}>
                                  <span className="fn">{f.denominacion}</span>
                                  <span className="fv">{f.ifo.toFixed(1)}%</span>
                                </div>
                              ))}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {activeTab === 'monthly' && monthlyData && (
                <div className="advanced-grid">
                  <div className="kpi-row">
                    <div className="kpi-card glass gold">
                      <h3>IFO Promedio Mes</h3>
                      <div className="kpi-value">{monthlyData.ifo_sistema.toFixed(2)}%</div>
                      <div className="kpi-sub">Resultado acumulado periodo</div>
                    </div>
                    <div className="kpi-card glass">
                      <h3>Siguiente Umbral</h3>
                      <div className="kpi-value">{monthlyData.umbral_obligatorio_mes_siguiente.toFixed(2)}%</div>
                      <div className="kpi-sub">Cierre estimado Res. 120/25</div>
                    </div>
                  </div>

                  <div className="chart-row stretch">
                    <div className="chart-card glass full-width">
                      <h4>📈 Tendencia Diaria del Mes (IFO Sistema %)</h4>
                      <ResponsiveContainer width="100%" height={350}>
                        <LineChart data={monthlyData.daily_averages}>
                          <CartesianGrid strokeDasharray="3 3" opacity={0.1} />
                          <XAxis 
                            dataKey="fecha" 
                            fontSize={10} 
                            tickFormatter={(val) => val.split('-')[2]} 
                            stroke="#888"
                          />
                          <YAxis domain={[0, 110]} fontSize={11} stroke="#888" />
                          <Tooltip 
                            contentStyle={{ backgroundColor: '#1f2937', color: '#fff', border: 'none', borderRadius: '8px' }}
                          />
                          <Legend />
                          <Line 
                            type="monotone" 
                            dataKey="promedio" 
                            name="Promedio Sistema" 
                            stroke="#10b981" 
                            strokeWidth={3} 
                            dot={{ r: 4 }} 
                            activeDot={{ r: 8 }} 
                          />
                          <Line type="monotone" dataKey="minimo" name="Mínimo" stroke="#ef4444" strokeDasharray="5 5" dot={false} />
                          <Line type="monotone" dataKey="maximo" name="Máximo" stroke="#3b82f6" strokeDasharray="5 5" dot={false} />
                          <ReferenceLine y={90} stroke="#ef4444" strokeDasharray="3 3" label={{ position: 'right', value: 'Base', fill: '#ef4444', fontSize: 10 }} />
                        </LineChart>
                      </ResponsiveContainer>
                    </div>
                  </div>

                  <div className="chart-row">
                    <div className="chart-card glass">
                      <h4>📊 Distribución de Empresas por Nivel</h4>
                      <ResponsiveContainer width="100%" height={300}>
                        <PieChart>
                          <Pie
                            data={[
                              { name: 'Nivel A (>95%)', value: monthlyData.eots.filter(e => e.ifo_mensual >= 95).length, color: '#10b981' },
                              { name: 'Nivel B (90-95%)', value: monthlyData.eots.filter(e => e.ifo_mensual >= 90 && e.ifo_mensual < 95).length, color: '#f59e0b' },
                              { name: 'Nivel C (<90%)', value: monthlyData.eots.filter(e => e.ifo_mensual < 90).length, color: '#ef4444' }
                            ]}
                            cx="50%"
                            cy="50%"
                            innerRadius={60}
                            outerRadius={80}
                            paddingAngle={5}
                            dataKey="value"
                            label
                          >
                            {[0, 1, 2].map((entry, index) => (
                              <Cell key={`cell-${index}`} fill={['#10b981', '#f59e0b', '#ef4444'][index]} />
                            ))}
                          </Pie>
                          <Tooltip />
                          <Legend verticalAlign="bottom" height={36}/>
                        </PieChart>
                      </ResponsiveContainer>
                    </div>
                    <div className="chart-card glass">
                      <h4>📅 Resumen de Exclusiones</h4>
                      <div className="exclusions-summary">
                        <div className="ex-item">
                          <span className="ex-label">Domingos</span>
                          <span className="ex-count">{monthlyData.dias_excluidos.domingos.length}</span>
                        </div>
                        <div className="ex-item">
                          <span className="ex-label">Feriados</span>
                          <span className="ex-count">{monthlyData.dias_excluidos.feriados.length}</span>
                        </div>
                        <div className="ex-item">
                          <span className="ex-label">Días Atípicos</span>
                          <span className="ex-count">{monthlyData.dias_excluidos.atipicos.length}</span>
                        </div>
                        <div className="ex-total">
                          Total Días Efectivos: {monthlyData.daily_averages.length}
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default AdvancedPerformanceModal;
