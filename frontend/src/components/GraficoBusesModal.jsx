/**
 * GraficoBusesModal.jsx
 * Modal que muestra buses CBD observados por hora usando el endpoint
 * /api/cbd-data/buses-por-hora/{fecha}.
 * Muestra un gráfico de área apilada por empresa usando recharts
 * (que ya está instalado), sin necesitar chart.js ni el componente GraficoAvanzadoPromedioBuses.
 */

import React, { useState, useEffect } from 'react';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  Legend, ResponsiveContainer, ReferenceLine, ReferenceArea
} from 'recharts';
import { API_BASE_URL } from '../config';

// ── Paleta de colores para las empresas ─────────────────────────────────────
const COLORS = [
  '#2563eb', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6',
  '#06b6d4', '#ec4899', '#84cc16', '#f97316', '#6366f1',
  '#14b8a6', '#a855f7', '#fb923c', '#22d3ee', '#e879f9',
];

// ── Tooltip personalizado ────────────────────────────────────────────────────
const CustomTooltip = ({ active, payload, label, viewMode }) => {
  if (!active || !payload || !payload.length) return null;
  const total = payload.reduce((s, p) => s + (p.value || 0), 0);
  
  // Si estamos en modo sistema, el primer payload ya es el total
  const displayTotal = viewMode === 'sistema' ? payload[0].value : total;

  return (
    <div style={{
      background: '#1e293b', borderRadius: 10, padding: '12px 18px',
      boxShadow: '0 4px 20px #0006', color: '#f1f5f9', fontSize: 13,
      maxHeight: 340, overflowY: 'auto', minWidth: 200
    }}>
      <div style={{ fontWeight: 700, fontSize: 15, marginBottom: 8, color: '#60a5fa' }}>
        🕐 {label}:00 hs — Total: <span style={{ color: '#34d399' }}>{displayTotal}</span>
      </div>
      {viewMode === 'empresas' && payload.sort((a, b) => b.value - a.value).map((p, i) => (
        <div key={i} style={{ display: 'flex', justifyContent: 'space-between', gap: 16, marginBottom: 2 }}>
          <span style={{ color: p.fill }}>{p.name}</span>
          <span style={{ fontWeight: 600 }}>{p.value}</span>
        </div>
      ))}
      {viewMode === 'sistema' && (
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 16, marginBottom: 2 }}>
          <span style={{ color: '#3b82f6' }}>Total Sistema</span>
          <span style={{ fontWeight: 600 }}>{displayTotal}</span>
        </div>
      )}
    </div>
  );
};

const GraficoBusesModal = ({ isOpen, onClose, fecha, selectedEots }) => {
  const [chartData, setChartData] = useState([]);
  const [empresas, setEmpresas] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [viewMode, setViewMode] = useState('empresas'); // 'empresas' | 'sistema'

  useEffect(() => {
    if (!isOpen || !fecha) return;

    const fetchData = async () => {
      setLoading(true);
      setError(null);
      setChartData([]);
      setEmpresas([]);
      try {
        let url = `${API_BASE_URL}/cbd-data/buses-por-hora/${fecha}`;
        // Solo filtramos por EOTs si estamos en modo "Por empresa"
        if (viewMode === 'empresas' && selectedEots && selectedEots.length > 0) {
          const eotQuery = selectedEots.map(id => `eot_ids=${id}`).join('&');
          url += `?${eotQuery}`;
        }

        const resp = await fetch(url);
        if (!resp.ok) throw new Error(`Error ${resp.status}: ${resp.statusText}`);
        const rows = await resp.json(); // [{hora, eot_id, eot_nombre, cantidad}]

        // Extraer lista de empresas únicas
        const empresasSet = [...new Set(rows.map(r => r.eot_nombre))].sort();
        setEmpresas(empresasSet);

        // Pivotar: agrupar por hora → { hora: N, "EmpresaA": x, "EmpresaB": y, ... }
        const byHora = {};
        rows.forEach(({ hora, eot_nombre, cantidad }) => {
          if (!byHora[hora]) byHora[hora] = { hora };
          byHora[hora][eot_nombre] = cantidad;
        });

        // Rellenar horas faltantes (0-23) con 0 para cada empresa
        const data = [];
        for (let h = 0; h <= 23; h++) {
          const entry = byHora[h] || { hora: h };
          empresasSet.forEach(e => { if (!(e in entry)) entry[e] = 0; });
          // Total sistémico
          entry._total = empresasSet.reduce((s, e) => s + (entry[e] || 0), 0);
          data.push(entry);
        }
        setChartData(data);
      } catch (err) {
        console.error('Error al cargar buses por hora:', err);
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [isOpen, fecha, selectedEots, viewMode]);

  if (!isOpen) return null;

  // ── Overlay ──────────────────────────────────────────────────────────────
  return (
    <div style={{
      position: 'fixed', top: 0, left: 0, width: '100vw', height: '100vh',
      background: 'rgba(2,10,30,0.72)', zIndex: 5000,
      display: 'flex', alignItems: 'center', justifyContent: 'center'
    }}>
      <div style={{
        background: 'linear-gradient(135deg,#0f172a 0%,#1e293b 100%)',
        borderRadius: 16, width: '96vw', height: '92vh',
        boxShadow: '0 8px 48px #000a', display: 'flex', flexDirection: 'column',
        overflow: 'hidden', position: 'relative'
      }}>
        {/* Header del modal */}
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '20px 28px 14px', borderBottom: '1px solid #334155', flexShrink: 0
        }}>
          <div>
            <h2 style={{ margin: 0, color: '#f1f5f9', fontSize: 22, fontWeight: 700 }}>
              📊 Buses CBD por Hora — Sistema AMA
            </h2>
            <div style={{ display: 'flex', alignItems: 'center', gap: 15, marginTop: 4 }}>
              <span style={{ color: '#64748b', fontSize: 13 }}>
                Fecha: <b style={{ color: '#94a3b8' }}>{fecha}</b>
                {!loading && chartData.length > 0 && (
                  <> · {empresas.length} empresas</>
                )}
              </span>
              
              {/* Selector de modo de vista */}
              {!loading && chartData.length > 0 && (
                <div style={{ 
                  display: 'flex', 
                  background: '#0f172a', 
                  borderRadius: 8, 
                  padding: 3,
                  border: '1px solid #334155'
                }}>
                  <button
                    onClick={() => setViewMode('sistema')}
                    style={{
                      background: viewMode === 'sistema' ? '#1e40af' : 'transparent',
                      color: viewMode === 'sistema' ? '#fff' : '#94a3b8',
                      border: 'none',
                      borderRadius: 6,
                      padding: '4px 12px',
                      fontSize: 12,
                      fontWeight: 600,
                      cursor: 'pointer',
                      transition: 'all 0.2s'
                    }}
                  >
                    Todo el sistema
                  </button>
                  <button
                    onClick={() => setViewMode('empresas')}
                    style={{
                      background: viewMode === 'empresas' ? '#1e40af' : 'transparent',
                      color: viewMode === 'empresas' ? '#fff' : '#94a3b8',
                      border: 'none',
                      borderRadius: 6,
                      padding: '4px 12px',
                      fontSize: 12,
                      fontWeight: 600,
                      cursor: 'pointer',
                      transition: 'all 0.2s'
                    }}
                  >
                    Por empresa
                  </button>
                </div>
              )}
            </div>
          </div>
          <button
            onClick={onClose}
            style={{
              background: '#1e40af', color: '#fff', border: 'none',
              borderRadius: 10, padding: '8px 22px', fontSize: 15,
              fontWeight: 600, cursor: 'pointer', transition: 'background 0.2s'
            }}
            onMouseEnter={e => e.target.style.background = '#2563eb'}
            onMouseLeave={e => e.target.style.background = '#1e40af'}
          >
            ✖ Cerrar
          </button>
        </div>

        {/* Cuerpo */}
        <div style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column', padding: '16px 24px 20px' }}>
          {loading && (
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 16 }}>
              <div style={{
                width: 52, height: 52, borderRadius: '50%',
                border: '5px solid #334155', borderTopColor: '#3b82f6',
                animation: 'gbs-spin 0.85s linear infinite'
              }} />
              <p style={{ color: '#94a3b8', fontSize: 16 }}>Cargando datos de buses...</p>
              <style>{`@keyframes gbs-spin { to { transform: rotate(360deg); } }`}</style>
            </div>
          )}

          {!loading && error && (
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 12 }}>
              <div style={{ fontSize: 48 }}>⚠️</div>
              <p style={{ color: '#f87171', fontSize: 17, fontWeight: 600 }}>{error}</p>
            </div>
          )}

          {!loading && !error && chartData.length === 0 && (
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 12 }}>
              <div style={{ fontSize: 48 }}>📭</div>
              <p style={{ color: '#94a3b8', fontSize: 17 }}>No hay datos de buses para esta fecha.</p>
            </div>
          )}

          {!loading && !error && chartData.length > 0 && (
            <>
              {/* KPI rápido */}
              <div style={{ display: 'flex', gap: 12, marginBottom: 14, flexWrap: 'wrap' }}>
                {(() => {
                  const pico = chartData.reduce((max, d) => d._total > max._total ? d : max, chartData[0]);
                  return (
                    <div style={{ background: '#1e3a5f', borderRadius: 10, padding: '10px 20px', color: '#f1f5f9' }}>
                      <div style={{ fontSize: 11, color: '#64748b', textTransform: 'uppercase', letterSpacing: 1 }}>Hora Pico</div>
                      <div style={{ fontSize: 22, fontWeight: 700, color: '#60a5fa' }}>{pico.hora}:00 hs</div>
                      <div style={{ fontSize: 13, color: '#94a3b8' }}>{pico._total} buses</div>
                    </div>
                  );
                })()}
              </div>

              {/* Gráfico */}
              <div style={{ flex: 1, minHeight: 0 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={chartData} margin={{ top: 10, right: 20, left: 0, bottom: 24 }}>
                    <defs>
                      <linearGradient id="grad-total" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.7} />
                        <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.05} />
                      </linearGradient>
                      {empresas.map((emp, i) => (
                        <linearGradient key={emp} id={`grad-${i}`} x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor={COLORS[i % COLORS.length]} stopOpacity={0.7} />
                          <stop offset="95%" stopColor={COLORS[i % COLORS.length]} stopOpacity={0.05} />
                        </linearGradient>
                      ))}
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                    <XAxis
                      dataKey="hora"
                      tickFormatter={h => `${h}:00`}
                      tick={{ fill: '#94a3b8', fontSize: 12 }}
                      axisLine={{ stroke: '#334155' }}
                      tickLine={false}
                      label={{ value: 'Hora del día', position: 'insideBottom', offset: -16, fill: '#64748b', fontSize: 12 }}
                    />
                    <YAxis
                      tick={{ fill: '#94a3b8', fontSize: 12 }}
                      axisLine={false}
                      tickLine={false}
                      label={{ value: 'Buses', angle: -90, position: 'insideLeft', offset: 10, fill: '#64748b', fontSize: 12 }}
                    />
                    <Tooltip content={<CustomTooltip viewMode={viewMode} />} />
                    <Legend
                      wrapperStyle={{ color: '#94a3b8', fontSize: 12, paddingTop: 8, paddingBottom: 4 }}
                      iconType="circle"
                    />

                    {/* Áreas de Franja Pico */}
                    <ReferenceArea x1={5} x2={9} fill="#3b82f6" fillOpacity={0.06} label={{ value: 'PICO MAÑANA', position: 'insideTopLeft', fill: '#3b82f6', fontSize: 10, fontWeight: 600, offset: 10 }} />
                    <ReferenceArea x1={16} x2={19} fill="#3b82f6" fillOpacity={0.06} label={{ value: 'PICO TARDE', position: 'insideTopLeft', fill: '#3b82f6', fontSize: 10, fontWeight: 600, offset: 10 }} />

                    {viewMode === 'empresas' ? (
                      empresas.map((emp, i) => (
                        <Area
                          key={emp}
                          type="monotone"
                          dataKey={emp}
                          stackId="1"
                          stroke={COLORS[i % COLORS.length]}
                          fill={`url(#grad-${i})`}
                          strokeWidth={2}
                          dot={false}
                          activeDot={{ r: 5 }}
                        />
                      ))
                    ) : (
                      <Area
                        type="monotone"
                        dataKey="_total"
                        name="Total Sistema"
                        stroke="#3b82f6"
                        fill="url(#grad-total)"
                        strokeWidth={3}
                        dot={false}
                        activeDot={{ r: 6 }}
                      />
                    )}
                    
                    <ReferenceLine
                      x={chartData.reduce((max, d) => d._total > (chartData.find(c => c.hora === max)?._total || 0) ? d.hora : max,
                        chartData[0]?.hora)}
                      stroke="#f59e0b"
                      strokeDasharray="4 4"
                      label={{ value: 'Hora pico real', position: 'top', fill: '#f59e0b', fontSize: 11 }}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default GraficoBusesModal;
