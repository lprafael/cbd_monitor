import React, { useState, useEffect, useCallback } from 'react';
import {
    BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
    PieChart, Pie, Cell,
    AreaChart, Area,
    LineChart, Line,
    ComposedChart,
    ReferenceLine, Label
} from 'recharts';
import './SystemChartsDashboard.css';
import { API_BASE_URL } from '../config';

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884d8', '#82ca9d'];
const UMBRAL_GOOD = 90;
const UMBRAL_WARNING = 80;

const SystemChartsDashboard = ({ year, month }) => {
    const [data, setData] = useState(null);
    const [baseline, setBaseline] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [activeChart, setActiveChart] = useState('ranking');
    const [selectedLevel, setSelectedLevel] = useState(null);

    const fetchChartData = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            const formattedMonth = month.toString().padStart(2, '0');
            const [dataRes, baselineRes] = await Promise.all([
                fetch(`${API_BASE_URL}/reports/res120/system-ifo-breakdown/${year}/${month}`),
                fetch(`${API_BASE_URL}/reports/res120/system-ifo-baseline/${year}-${formattedMonth}-01`)
            ]);

            if (!dataRes.ok) throw new Error('Error al obtener datos');
            const dataResult = await dataRes.json();
            setData(dataResult);

            if (baselineRes.ok) {
                const baselineResult = await baselineRes.json();
                setBaseline(baselineResult);
            }
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    }, [year, month]);

    useEffect(() => {
        if (year && month) {
            fetchChartData();
        }
    }, [year, month, fetchChartData]);

    if (loading) return <div className="loading-message"><div className="spinner"></div><p>Cargando visualizaciones...</p></div>;
    if (error) return <div className="error-message"><h3>❌ Error</h3><p>{error}</p></div>;
    if (!data) return null;

    // --- PROCESAMIENTO DE DATOS PARA RECHARTS ---

    // 1. Ranking de Empresas
    const rankingData = data.eots
        .map(e => {
            const ifo = parseFloat(e.ifo_mensual_topeado.toFixed(2));
            // Se compara exclusivamente con el IFO Base (Objetivo sistema)
            // Si no hay baseline cargado, se usa 80% como referencia técnica por defecto
            const threshold = baseline ? baseline.ifo_objetivo : UMBRAL_WARNING;
            
            return {
                name: e.eot_nombre,
                ifo: ifo,
                color: ifo >= threshold ? '#059669' : '#dc2626'
            };
        })
        .sort((a, b) => b.ifo - a.ifo);

    // 2. Meta Sistema (Gauge con PieChart)
    const systemIfo = data.ifo_sistema_topeado;
    const gaugeData = [
        { name: 'Logrado', value: systemIfo },
        { name: 'Restante', value: Math.max(0, 110 - systemIfo) } // Referencia al 110% tope
    ];

    // 3. Distribución de Niveles (Guardamos empresas por nivel para desglose)
    const niveles = { 
        'Nivel A (≥90%)': [], 
        'Nivel B (80-90%)': [], 
        'Nivel C (<80%)': [] 
    };
    data.eots.forEach(e => {
        const item = { name: e.eot_nombre, ifo: e.ifo_mensual_topeado };
        if (e.ifo_mensual >= 90) niveles['Nivel A (≥90%)'].push(item);
        else if (e.ifo_mensual >= 80) niveles['Nivel B (80-90%)'].push(item);
        else niveles['Nivel C (<80%)'].push(item);
    });
    
    const distData = Object.keys(niveles).map(key => ({ 
        name: key, 
        value: niveles[key].length,
        companies: niveles[key]
    }));

    // 4. Mapa de Calor (Simulado con los promedios de EOTs por posición)
    // Para un heatmap real necesitaríamos datos por día del sistema completo

    const renderChart = () => {
        switch (activeChart) {
            case 'ranking':
                return (
                    <div className="chart-container-card">
                        <div className="chart-info">
                            <h3>🏆 Ranking de Cumplimiento por EOT</h3>
                            <p>Comparativa del IFO Mensual entre todas las empresas operadoras del sistema. Los colores indican el nivel de cumplimiento (Verde: Óptimo, Naranja: Alerta, Rojo: Crítico).</p>
                        </div>
                        <ResponsiveContainer width="100%" height={1000}>
                            <BarChart data={rankingData} layout="vertical" margin={{ left: 10, right: 60, top: 20, bottom: 20 }}>
                                <CartesianGrid strokeDasharray="3 3" horizontal={true} vertical={false} stroke="#f1f5f9" />
                                <XAxis type="number" domain={[0, 115]} unit="%" />
                                <YAxis
                                    dataKey="name"
                                    type="category"
                                    width={280}
                                    tick={{ fontSize: 10, fontWeight: 600 }}
                                />
                                <Tooltip
                                    formatter={(value) => [`${value}%`, 'IFO Topeado']}
                                    contentStyle={{ borderRadius: '10px', border: 'none', boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }}
                                />
                                <Bar dataKey="ifo" radius={[0, 4, 4, 0]} barSize={20}>
                                    {rankingData.map((entry, index) => (
                                        <Cell key={`cell-${index}`} fill={entry.color} />
                                    ))}
                                </Bar>
                                {baseline && (
                                    <ReferenceLine
                                        x={baseline.ifo_objetivo}
                                        stroke="#dc2626"
                                        strokeDasharray="5 5"
                                        strokeWidth={4}
                                    >
                                        <Label
                                            value={`IFO BASE (${baseline.mes}/${baseline.anio}): ${baseline.ifo_objetivo.toFixed(2)}%`}
                                            position="insideBottomRight"
                                            fill="#dc2626"
                                            fontSize={12}
                                            fontWeight={900}
                                            offset={20}
                                        />
                                    </ReferenceLine>
                                )}
                                {baseline && (
                                    <ReferenceLine
                                        x={baseline.ifo_objetivo}
                                        stroke="#1e293b"
                                        strokeDasharray="3 3"
                                        strokeWidth={2}
                                        strokeOpacity={0.8}
                                    />
                                )}
                                <ReferenceLine
                                    x={110}
                                    stroke="#10b981"
                                    strokeDasharray="3 3"
                                    strokeWidth={2}
                                >
                                    <Label
                                        value="TOPE: 110%"
                                        position="insideTopRight"
                                        fill="#10b981"
                                        fontSize={11}
                                        fontWeight={700}
                                        offset={30}
                                    />
                                </ReferenceLine>
                            </BarChart>
                        </ResponsiveContainer>
                    </div>
                );

            case 'gauge':
                return (
                    <div className="chart-container-card">
                        <div className="chart-info">
                            <h3>🎯 Cumplimiento Meta Sistema</h3>
                            <p>Representación del IFO Global del sistema frente al 100%. La aguja marca el desempeño consolidado del mes.</p>
                        </div>
                        <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
                            <ResponsiveContainer width="100%" height={400}>
                                <PieChart>
                                    <Pie
                                        data={gaugeData}
                                        cx="50%"
                                        cy="80%"
                                        startAngle={180}
                                        endAngle={0}
                                        innerRadius={120}
                                        outerRadius={180}
                                        paddingAngle={0}
                                        dataKey="value"
                                    >
                                        <Cell fill="#0066cc" />
                                        <Cell fill="#f1f5f9" />
                                    </Pie>
                                    <text x="50%" y="70%" textAnchor="middle" dominantBaseline="middle" style={{ fontSize: '3rem', fontWeight: 800, fill: '#1e293b' }}>
                                        {systemIfo.toFixed(2)}%
                                    </text>
                                    <text x="50%" y="85%" textAnchor="middle" dominantBaseline="middle" style={{ fontSize: '1rem', fontWeight: 600, fill: '#64748b' }}>
                                        IFO SISTEMA (TOPEADO)
                                    </text>
                                </PieChart>
                            </ResponsiveContainer>
                        </div>
                        <div className="chart-legend-custom">
                            <div className="legend-item-custom"><div className="legend-color" style={{ backgroundColor: '#0066cc' }}></div> IFO Logrado</div>
                            <div className="legend-item-custom"><div className="legend-color" style={{ backgroundColor: '#f1f5f9' }}></div> Brecha al 110%</div>
                        </div>
                    </div>
                );

            case 'distribution':
                return (
                    <div className="chart-container-card">
                        <div className="chart-info">
                            <h3>📊 Concentración de Empresas por Nivel</h3>
                            <p>Distribución de las operadoras según su rango de cumplimiento. Permite visualizar cuántas empresas están en zona de riesgo o excelencia.</p>
                        </div>
                        <ResponsiveContainer width="100%" height={400}>
                            <PieChart>
                                <Pie
                                    data={distData}
                                    cx="50%"
                                    cy="50%"
                                    innerRadius={80}
                                    outerRadius={140}
                                    paddingAngle={5}
                                    dataKey="value"
                                    label={({ name, value }) => `${name.split(' ')[1]}: ${value}`}
                                    onClick={(event) => setSelectedLevel(event.name)}
                                    style={{ cursor: 'pointer' }}
                                >
                                    <Cell fill="#059669" /> {/* Nivel A - Verde */}
                                    <Cell fill="#d97706" /> {/* Nivel B - Naranja */}
                                    <Cell fill="#dc2626" /> {/* Nivel C - Rojo */}
                                </Pie>
                                <Tooltip />
                                <Legend />
                            </PieChart>
                        </ResponsiveContainer>

                        {selectedLevel && (
                            <div className="level-detail-box">
                                <h4>📋 Empresas en {selectedLevel}</h4>
                                <div className="company-grid">
                                    {distData.find(d => d.name === selectedLevel)?.companies.map((c, i) => (
                                        <div key={i} className="company-chip">
                                            <span className="name">{c.name}</span>
                                            <span className="value">{c.ifo.toFixed(2)}%</span>
                                        </div>
                                    ))}
                                </div>
                                <button className="clear-selection" onClick={() => setSelectedLevel(null)}>Cerrar detalle</button>
                            </div>
                        )}
                    </div>
                );

            case 'trend':
                const weekdaysLabels = ['Lun', 'Mar', 'Mie', 'Jue', 'Vie', 'Sab', 'Dom'];
                const statsByDay = [0, 1, 2, 3, 4, 5, 6].map(i => ({
                    day: weekdaysLabels[i],
                    ifoSum: 0,
                    minSum: 0,
                    maxSum: 0,
                    count: 0
                }));

                (data.daily_averages || []).forEach(d => {
                    const date = new Date(d.fecha + 'T00:00:00');
                    let dayIdx = date.getDay() - 1; // 0 index for Monday
                    if (dayIdx === -1) dayIdx = 6; // Sunday
                    
                    statsByDay[dayIdx].ifoSum += d.promedio;
                    statsByDay[dayIdx].minSum += d.minimo;
                    statsByDay[dayIdx].maxSum += d.maximo;
                    statsByDay[dayIdx].count++;
                });

                const trendData = statsByDay
                    .filter(s => s.count > 0)
                    .map(s => ({
                        day: s.day,
                        ifo: parseFloat((s.ifoSum / s.count).toFixed(2)),
                        min: parseFloat((s.minSum / s.count).toFixed(2)),
                        max: parseFloat((s.maxSum / s.count).toFixed(2))
                    }));

                return (
                    <div className="chart-container-card">
                        <div className="chart-info">
                            <h3>📈 Perfil de Desempeño por Día de la Semana</h3>
                            <p>Análisis agregado del comportamiento del sistema según el día de la semana. Muestra el promedio consolidado del periodo y sus rangos de variación típicos.</p>
                        </div>
                        <ResponsiveContainer width="100%" height={400}>
                            <AreaChart data={trendData}>
                                <defs>
                                    <linearGradient id="colorIfo" x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="5%" stopColor="#0066cc" stopOpacity={0.3} />
                                        <stop offset="95%" stopColor="#0066cc" stopOpacity={0} />
                                    </linearGradient>
                                </defs>
                                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                                <XAxis dataKey="day" label={{ value: 'Día de la Semana', position: 'insideBottom', offset: -10 }} />
                                <YAxis domain={[Math.max(0, Math.min(...trendData.map(d => d.min)) - 5), 115]} unit="%" />
                                <Tooltip formatter={(value) => [`${value}%`]} />
                                <Legend verticalAlign="top" height={36}/>
                                <Area 
                                    type="monotone" 
                                    dataKey="ifo" 
                                    name="Promedio Diario" 
                                    stroke="#0066cc" 
                                    fillOpacity={1} 
                                    fill="url(#colorIfo)" 
                                    strokeWidth={3} 
                                />
                                <Line 
                                    type="monotone" 
                                    dataKey="min" 
                                    name="Mínimo Típico" 
                                    stroke="#dc2626" 
                                    strokeDasharray="5 5" 
                                    dot={false} 
                                    strokeWidth={2} 
                                />
                                <Line 
                                    type="monotone" 
                                    dataKey="max" 
                                    name="Máximo Típico" 
                                    stroke="#059669" 
                                    strokeDasharray="5 5" 
                                    dot={false} 
                                    strokeWidth={2} 
                                />
                            </AreaChart>
                        </ResponsiveContainer>
                    </div>
                );

            case 'deficit':
                const targetValue = baseline?.ifo_objetivo || 100;
                const deficitData = data.eots.map(e => ({
                    name: e.eot_nombre.split(' ')[0], // Mantenemos recorte por espacio en eje X
                    real: e.ifo_mensual_topeado,
                    gap: Math.max(0, targetValue - e.ifo_mensual_topeado)
                })).sort((a, b) => b.gap - a.gap).slice(0, 10);

                return (
                    <div className="chart-container-card">
                        <div className="chart-info">
                            <h3>🚩 Top 10 - Brecha de Incumplimiento</h3>
                            <p>Visualización del Gap necesario para alcanzar el <b>IFO BASE ({targetValue.toFixed(2)}%)</b>. Las empresas con mayor brecha (amarillo) requieren mayor intervención.</p>
                        </div>
                        <ResponsiveContainer width="100%" height={450}>
                            <BarChart data={deficitData}>
                                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                                <XAxis dataKey="name" />
                                <YAxis domain={[0, Math.max(110, targetValue + 5)]} />
                                <Tooltip formatter={(value) => [`${value.toFixed(2)}%`]} />
                                <Legend />
                                <Bar dataKey="real" name="IFO Logrado (Topeado) %" stackId="a" fill="#0066cc" />
                                <Bar dataKey="gap" name="Brecha al Objetivo %" stackId="a" fill="#ffd700" />
                            </BarChart>
                        </ResponsiveContainer>
                    </div>
                );

            default:
                return null;
        }
    };

    return (
        <div className="system-charts-dashboard">
            <div className="charts-header">
                <h2>Visualizaciones de Desempeño</h2>
                <p>Panorama visual del sistema - {month}/{year}</p>
            </div>

            <div className="charts-selector">
                <button
                    className={`chart-tab ${activeChart === 'ranking' ? 'active' : ''}`}
                    onClick={() => setActiveChart('ranking')}
                >
                    🏆 Ranking EOTs
                </button>
                <button
                    className={`chart-tab ${activeChart === 'gauge' ? 'active' : ''}`}
                    onClick={() => setActiveChart('gauge')}
                >
                    🎯 Meta Sistema
                </button>
                <button
                    className={`chart-tab ${activeChart === 'distribution' ? 'active' : ''}`}
                    onClick={() => setActiveChart('distribution')}
                >
                    📊 Distribución
                </button>
                <button
                    className={`chart-tab ${activeChart === 'trend' ? 'active' : ''}`}
                    onClick={() => setActiveChart('trend')}
                >
                    📈 Tendencia
                </button>
                <button
                    className={`chart-tab ${activeChart === 'deficit' ? 'active' : ''}`}
                    onClick={() => setActiveChart('deficit')}
                >
                    🚩 Brecha
                </button>
            </div>

            <div className="chart-display-area">
                {renderChart()}
            </div>
        </div>
    );
};

export default SystemChartsDashboard;
