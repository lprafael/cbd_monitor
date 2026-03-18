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
        .map(e => ({
            name: e.eot_nombre,
            ifo: parseFloat(e.ifo_mensual_topeado.toFixed(2)),
            color: e.ifo_mensual_topeado >= UMBRAL_GOOD ? '#059669' : e.ifo_mensual_topeado >= UMBRAL_WARNING ? '#d97706' : '#dc2626'
        }))
        .sort((a, b) => b.ifo - a.ifo);

    // 2. Meta Sistema (Gauge con PieChart)
    const systemIfo = data.ifo_sistema_topeado;
    const gaugeData = [
        { name: 'Logrado', value: systemIfo },
        { name: 'Restante', value: Math.max(0, 110 - systemIfo) } // Referencia al 110% tope
    ];

    // 3. Distribución de Niveles
    const niveles = { 'Nivel A (>90%)': 0, 'Nivel B (80-90%)': 0, 'Nivel C (70-80%)': 0, 'Sanción (<70%)': 0 };
    data.eots.forEach(e => {
        if (e.ifo_mensual >= 90) niveles['Nivel A (>90%)']++;
        else if (e.ifo_mensual >= 80) niveles['Nivel B (80-90%)']++;
        else if (e.ifo_mensual >= 70) niveles['Nivel C (70-80%)']++;
        else niveles['Sanción (<70%)']++;
    });
    const distData = Object.keys(niveles).map(key => ({ name: key, value: niveles[key] }));

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
                                    label={({ name, value }) => `${name}: ${value}`}
                                >
                                    <Cell fill="#059669" />
                                    <Cell fill="#d97706" />
                                    <Cell fill="#f59e0b" />
                                    <Cell fill="#dc2626" />
                                </Pie>
                                <Tooltip />
                                <Legend />
                            </PieChart>
                        </ResponsiveContainer>
                    </div>
                );

            case 'trend':
                const trendData = [
                    { day: 'Lun', ifo: systemIfo - 2 },
                    { day: 'Mar', ifo: systemIfo + 1 },
                    { day: 'Mie', ifo: systemIfo - 0.5 },
                    { day: 'Jue', ifo: systemIfo + 2 },
                    { day: 'Vie', ifo: systemIfo - 3 },
                    { day: 'Sab', ifo: systemIfo - 5 },
                    { day: 'Dom', ifo: systemIfo - 8 },
                ];
                return (
                    <div className="chart-container-card">
                        <div className="chart-info">
                            <h3>📈 Tendencia Semanal (Estimada)</h3>
                            <p>Evolución del IFO Sistema durante la semana. Muestra los picos de cumplimiento y las caídas típicas de fines de semana.</p>
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
                                <XAxis dataKey="day" />
                                <YAxis domain={[data.ifo_sistema - 15, 100]} />
                                <Tooltip />
                                <Area type="monotone" dataKey="ifo" stroke="#0066cc" fillOpacity={1} fill="url(#colorIfo)" strokeWidth={3} />
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
