import React, { useState, useEffect } from 'react';
import { Line } from 'react-chartjs-2';
import annotationPlugin from 'chartjs-plugin-annotation';
import ChartDataLabels from 'chartjs-plugin-datalabels';
import { Chart } from 'chart.js';
import { API_BASE_URL } from '../config';

function unique(arr) {
  return Array.from(new Set(arr));
}

// Utilidad para normalizar nombres (sin tildes, minúsculas)
function normalizar(str) {
  return str
    ? str.normalize('NFD').replace(/\p{Diacritic}/gu, '').toLowerCase()
    : '';
}

// Mínimos por Resolución 290
const MINIMOS_290 = {
  'Lunes a Viernes': {
    'Pico Mañana': 4,
    'Pico Tarde': 4,
    'Postpico Mañana': 2,
    'Postpico Tarde': 2,
    'Nocturno': 1
  },
  'Sábados': {
    'Pico': 2,
    'Postpico': 1, // Actualizado: mínimo 1 bus en cada hora en postpico
    'Nocturno': 1
  },
  'Domingos y Feriados': {
    'Horario Normal': 1
  }
};

function getPicoAnnotations(tipoDiaSel, franjasSel, nombreFranjaMap, horas) {
  // Definir los rangos de horas de pico según el tipo de día
  let rangos = [];
  if (tipoDiaSel === 'Lunes a Viernes') {
    franjasSel.forEach(f => {
      const label = nombreFranjaMap[f] || f;
      if (label === 'Pico Mañana' || label === 'Pico Tarde') {
        const [inicio, fin] = f.split('-').map(Number);
        rangos.push({ inicio, fin });
      }
    });
  } else if (tipoDiaSel === 'Sábados') {
    franjasSel.forEach(f => {
      const label = nombreFranjaMap[f] || f;
      if (label === 'Pico') {
        const [inicio, fin] = f.split('-').map(Number);
        rangos.push({ inicio, fin });
      }
    });
  }
  // Mapear a índices del eje X (horas)
  const annotations = {};
  rangos.forEach((rango, idx) => {
    // Buscar el índice de inicio y fin en el array de horas
    const xMin = horas.indexOf(rango.inicio);
    const xMax = horas.indexOf(rango.fin);
    if (xMin !== -1 && xMax !== -1) {
      annotations[`pico${idx}`] = {
        type: 'box',
        xMin,
        xMax: xMax + 1, // para incluir la última hora
        backgroundColor: 'rgba(30,30,60,0.18)',
        borderWidth: 0,
        yScaleID: 'y',
      };
    }
  });
  return annotations;
}

function GraficoAvanzadoPromedioBuses({ data, nombreFranjaMap, onClose, modoSimple = false }) {
  // Extraer valores únicos para los selectores
  const gremios = unique(data.map(d => d.gre_nombre).filter(Boolean)).sort((a, b) => a.localeCompare(b, 'es', { sensitivity: 'base' }));
  const meses = unique(data.map(d => `${String(d.mes).padStart(2, '0')}/${d.anio}`));
  const tipoDias = unique(data.map(d => d.tipo_dia));
  const franjas = unique(data.map(d => d.franja));

  // Estado local para filtros
  const [gremiosSel, setGremiosSel] = useState(gremios);
  // Calcular empresas según gremios seleccionados
  const empresas = unique(data.filter(d => gremiosSel.includes(d.gre_nombre)).map(d => d.empresa_nombre)).sort((a, b) => a.localeCompare(b, 'es', { sensitivity: 'base' }));
  const [empresasSel, setEmpresasSel] = useState(empresas);
  const [mesesSel, setMesesSel] = useState(meses);
  // Tipo de día: selección única
  const [tipoDiaSel, setTipoDiaSel] = useState(tipoDias[0] || '');
  const [franjasSel, setFranjasSel] = useState(franjas);
  const [verificar290, setVerificar290] = useState(false);
  // Estado para comparar
  const [mostrarComparar, setMostrarComparar] = useState(false);
  const [fechaComparar, setFechaComparar] = useState('');
  const [datosComparar, setDatosComparar] = useState(null);
  const [cargandoComparar, setCargandoComparar] = useState(false);
  const [errorComparar, setErrorComparar] = useState(null);
  // Estado para esencialidad
  const [verificarEsencialidad, setVerificarEsencialidad] = useState(false);
  const [porcentajeEsencialidad, setPorcentajeEsencialidad] = useState(90);
  // Estado para fuente de línea azul
  const [fuentePromedio, setFuentePromedio] = useState('meses'); // 'meses' o 'semanas'
  const [numSemanas, setNumSemanas] = useState(4);
  const [promedioSemanas, setPromedioSemanas] = useState(null);
  const [cargandoSemanas, setCargandoSemanas] = useState(false);

  // Filtrar datos según selección
  const datosFiltrados = data.filter(d =>
    gremiosSel.includes(d.gre_nombre) &&
    empresasSel.includes(d.empresa_nombre) &&
    mesesSel.includes(`${String(d.mes).padStart(2, '0')}/${d.anio}`) &&
    d.tipo_dia === tipoDiaSel &&
    franjasSel.includes(d.franja)
  );

  // Determinar el eje X (horas)
  const horas = unique(datosFiltrados.map(d => d.hora)).sort((a, b) => a - b);

  // Calcular la suma de promedios mensuales por empresa para cada hora (default)
  const sumaPromediosPorHora = horas.map(hora => {
    const empresasData = empresasSel.map(empresa => {
      const valores = datosFiltrados.filter(d => d.empresa_nombre === empresa && d.hora === hora)
        .map(d => d.promedio_buses);
      if (valores.length === 0) return 0;
      return valores.reduce((acc, v) => acc + v, 0) / valores.length;
    });
    return empresasData.reduce((acc, v) => acc + v, 0);
  });
  // Si la fuente es semanas y hay datos, usar ese promedio
  let lineaAzulPorHora = sumaPromediosPorHora;
  if (fuentePromedio === 'semanas' && promedioSemanas && Array.isArray(promedioSemanas)) {
    lineaAzulPorHora = horas.map(hora => {
      const found = promedioSemanas.find(d => d.hora === hora);
      return found ? found.promedio : null;
    });
  }

  // Línea de referencia Resolución 290
  let referencia290 = null;
  if (verificar290 && tipoDiaSel) {
    // Para cada hora, buscar la franja seleccionada que la contiene y asignar el mínimo correspondiente
    referencia290 = horas.map(hora => {
      let franjaLabel = null;
      for (let f of franjasSel) {
        // El key de franja es del tipo '06-15'
        const partes = f.split('-');
        if (partes.length === 2) {
          const inicio = Number(partes[0]);
          const fin = Number(partes[1]);
          if (hora >= inicio && hora <= fin) {
            franjaLabel = nombreFranjaMap[f] || f;
            break;
          }
        }
      }
      // Buscar el mínimo según la resolución para el tipo de día y franja
      // Normalizar para evitar problemas de tildes/capitalización
      const minimosTipoDia = MINIMOS_290[tipoDiaSel] || {};
      let min = undefined;
      for (const key in minimosTipoDia) {
        if (normalizar(key) === normalizar(franjaLabel)) {
          min = minimosTipoDia[key];
          break;
        }
      }
      return (min !== undefined) ? min : null;
    });
  }

  // Línea de esencialidad
  let esencialidadPorHora = null;
  if (verificarEsencialidad && porcentajeEsencialidad > 0) {
    esencialidadPorHora = lineaAzulPorHora.map(v => v !== null && v !== undefined ? v * (porcentajeEsencialidad / 100) : null);
  }

  // Handler para comparar (trae la fecha seleccionada y el día anterior)
  async function handleComparar() {
    if (!fechaComparar) return;
    setCargandoComparar(true);
    setErrorComparar(null);
    setDatosComparar(null);
    try {
      const fechaSel = fechaComparar;
      // Calcular día anterior en formato YYYY-MM-DD
      const fechaPrev = (() => {
        const d = new Date(fechaSel);
        d.setDate(d.getDate() - 1);
        return d.toISOString().slice(0, 10);
      })();
      // Hacer ambas peticiones en paralelo
      const [respSel, respPrev] = await Promise.all([
        fetch(`${API_BASE_URL}/servicios_por_hora`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            empresas: empresasSel,
            fecha: fechaSel,
            tipo_dia: tipoDiaSel
          })
        }),
        fetch(`${API_BASE_URL}/servicios_por_hora`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            empresas: empresasSel,
            fecha: fechaPrev,
            tipo_dia: tipoDiaSel
          })
        })
      ]);

      if (!respSel.ok || !respPrev.ok) throw new Error('Error en el backend');
      const dataSel = await respSel.json();
      const dataPrev = await respPrev.json();
      // Guardar como objeto por fecha para soportar múltiples series
      setDatosComparar({ [fechaSel]: dataSel, [fechaPrev]: dataPrev });
    } catch (e) {
      setErrorComparar('Error al obtener datos de comparación: ' + e.message);
    } finally {
      setCargandoComparar(false);
    }
  }

  // Preparar datasets
  const colors = ['#1976d2'];
  const datasets = [
    {
      label: 'Promedio de selección',
      data: lineaAzulPorHora,
      borderColor: colors[0],
      backgroundColor: colors[0],
      borderWidth: 5,
      fill: false,
      tension: 0.2
    }
  ];
  if (verificar290 && referencia290 && referencia290.some(v => v !== null)) {
    datasets.push({
      label: 'Mínimo Res. GVMT N° 290',
      data: referencia290,
      borderColor: 'red',
      backgroundColor: 'red',
      borderWidth: 3,
      borderDash: [8, 4],
      fill: false,
      pointRadius: 0,
      tension: 0,
      stepped: true
    });
  }
  if (esencialidadPorHora) {
    datasets.push({
      label: `Esencialidad (${porcentajeEsencialidad}%)`,
      data: esencialidadPorHora,
      borderColor: 'orange',
      backgroundColor: 'orange',
      borderWidth: 3,
      borderDash: [4, 4],
      fill: false,
      pointRadius: 0,
      tension: 0.2,
      datalabels: { display: false },
    });
  }
  // Línea de comparación: soporta fecha seleccionada y el día anterior
  if (datosComparar && typeof datosComparar === 'object') {
    // colores para las series de comparación (seleccionada, anterior)
    const compColors = ['#1b5e20', '#2e7d32']; // fecha seleccionada, fecha anterior
    let idxColor = 0;
    // Object.keys conserva el orden de inserción (seleccionada primero, luego anterior)
    for (const fechaKey of Object.keys(datosComparar)) {
      const series = datosComparar[fechaKey];
      const dataComp = horas.map(hora => {
        const found = Array.isArray(series) ? series.find(d => d.hora === hora) : null;
        return found ? found.servicios : null;
      });
      datasets.push({
        label: `Servicios en ${fechaKey}`,
        data: dataComp,
        borderColor: compColors[idxColor % compColors.length],
        backgroundColor: compColors[idxColor % compColors.length],
        borderWidth: 4,
        fill: false,
        tension: 0.2,
        pointStyle: idxColor === 0 ? 'rectRot' : 'triangle'
      });
      idxColor++;
    }
  }

  const chartData = {
    labels: horas,
    datasets
  };

  const noData = !data || data.length === 0 || horas.length === 0 || lineaAzulPorHora.every(v => v === null);

  // Handlers para selección múltiple
  function handleMultiSelect(setter) {
    return e => {
      const options = Array.from(e.target.options);
      setter(options.filter(o => o.selected).map(o => o.value));
    };
  }
  // Handler para gremios: al cambiar, actualizar empresas seleccionadas
  function handleGremiosChange(e) {
    const options = Array.from(e.target.options);
    const nuevosGremios = options.filter(o => o.selected).map(o => o.value);
    setGremiosSel(nuevosGremios);
    // Actualizar empresas seleccionadas para reflejar solo las del gremio seleccionado
    const nuevasEmpresas = unique(data.filter(d => nuevosGremios.includes(d.gre_nombre)).map(d => d.empresa_nombre));
    setEmpresasSel(nuevasEmpresas);
  }

  // Al cerrar comparar, limpiar datosComparar y fechaComparar
  function handleToggleComparar() {
    setMostrarComparar(v => {
      if (v) {
        setDatosComparar(null);
        setFechaComparar('');
        setErrorComparar(null);
      }
      return !v;
    });
  }

  // Actualizar automáticamente la línea verde al cambiar empresas si hay fecha de comparación
  useEffect(() => {
    if (fechaComparar && mostrarComparar) {
      handleComparar();
    }
    // eslint-disable-next-line
  }, [empresasSel]);

  // useEffect para consultar promedio de semanas si corresponde
  useEffect(() => {
    async function fetchPromedioSemanas() {
      if (fuentePromedio === 'semanas' && fechaComparar && empresasSel.length > 0) {
        setCargandoSemanas(true);
        try {
          const resp = await fetch(`${API_BASE_URL}/promedio_semanas_por_hora`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              empresas: empresasSel,
              fecha: fechaComparar,
              semanas: numSemanas
            })
          });
          if (!resp.ok) throw new Error('Error en el backend');
          const data = await resp.json();
          setPromedioSemanas(data); // [{hora, promedio}]
        } catch (e) {
          setPromedioSemanas(null);
        } finally {
          setCargandoSemanas(false);
        }
      } else {
        setPromedioSemanas(null);
      }
    }
    fetchPromedioSemanas();
    // eslint-disable-next-line
  }, [fuentePromedio, numSemanas, fechaComparar, empresasSel]);

  Chart.register(annotationPlugin);
  Chart.register(ChartDataLabels);

  return (
    <div style={{ position: 'fixed', top: 0, left: 0, width: '100vw', height: '100vh', background: 'rgba(0,0,0,0.45)', zIndex: 5000, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <div style={{ background: '#fff', borderRadius: 12, padding: 0, minWidth: 'unset', maxWidth: 'unset', boxShadow: '0 4px 24px #0003', position: 'relative', width: '98vw', height: '98vh', overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
        <button onClick={onClose} style={{ position: 'absolute', top: 18, right: 18, fontSize: 22, background: '#e3f2fd', color: '#1976d2', border: '2px solid #90caf9', borderRadius: 20, width: 'auto', height: 48, padding: '0 24px', cursor: 'pointer', zIndex: 3001, fontWeight: 'bold', display: 'flex', alignItems: 'center', gap: 8 }}>
          Cerrar
        </button>

        {/* Encabezado */}
        <div style={{ padding: modoSimple ? '20px 32px 12px 32px' : '32px 32px 0 32px' }}>
          <h2 style={{ marginTop: 0 }}>
            {modoSimple ? '📊 Cantidad de Buses por Hora' : 'Gráfico Avanzado de Promedio de Buses'}
          </h2>

          {/* Filtros: solo en modo completo */}
          {!modoSimple && (
            <div style={{ display: 'flex', gap: 16, marginBottom: 18, flexWrap: 'wrap', alignItems: 'end' }}>
              <div>
                <label><b>Gremios:</b></label><br />
                <select multiple value={gremiosSel} onChange={handleGremiosChange} style={{ minWidth: 120, height: 80 }}>
                  {gremios.map(g => <option key={g} value={g}>{g}</option>)}
                </select>
              </div>
              <div>
                <label>Empresas:</label><br />
                <select multiple value={empresasSel} onChange={handleMultiSelect(setEmpresasSel)} style={{ minWidth: 120, height: 80 }}>
                  {empresas.map(e => <option key={e} value={e}>{e}</option>)}
                </select>
              </div>
              <div>
                <label>Meses:</label><br />
                <select multiple value={mesesSel} onChange={handleMultiSelect(setMesesSel)} style={{ minWidth: 100, height: 80 }}>
                  {meses.map(m => <option key={m} value={m}>{m}</option>)}
                </select>
              </div>
              <div>
                <label>Tipo de Día:</label><br />
                <select value={tipoDiaSel} onChange={e => setTipoDiaSel(e.target.value)} style={{ minWidth: 120, height: 36 }}>
                  {tipoDias.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
              <div>
                <label>Franjas:</label><br />
                <select multiple value={franjasSel} onChange={handleMultiSelect(setFranjasSel)} style={{ minWidth: 120, height: 80 }}>
                  {franjas.map(f => <option key={f} value={f}>{nombreFranjaMap[f] || f}</option>)}
                </select>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center', marginLeft: 16, gap: 2 }}>
                <div style={{ display: 'flex', alignItems: 'center', height: 32 }}>
                  <input type="checkbox" id="verif290" checked={verificar290} onChange={e => setVerificar290(e.target.checked)} style={{ marginRight: 6 }} />
                  <label htmlFor="verif290">Verificar Res. GVMT N° 290</label>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', height: 32 }}>
                  <input type="checkbox" id="verifEsencialidad" checked={verificarEsencialidad} onChange={e => setVerificarEsencialidad(e.target.checked)} style={{ marginRight: 6 }} />
                  <label htmlFor="verifEsencialidad">Verificar Esencialidad</label>
                  {verificarEsencialidad && (
                    <input type="number" min={1} max={100} value={porcentajeEsencialidad} onChange={e => setPorcentajeEsencialidad(Number(e.target.value))} style={{ width: 90, marginLeft: 8 }} />
                  )}
                  {verificarEsencialidad && <span style={{ marginLeft: 4 }}>%</span>}
                </div>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center', marginLeft: 16, gap: 2 }}>
                <div style={{ fontWeight: 'bold', marginBottom: 2 }}>Fuente Promedio:</div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                  <label><input type="radio" name="fuentePromedio" value="meses" checked={fuentePromedio === 'meses'} onChange={() => setFuentePromedio('meses')} /> Meses seleccionados</label>
                  <label><input type="radio" name="fuentePromedio" value="semanas" checked={fuentePromedio === 'semanas'} onChange={() => setFuentePromedio('semanas')} /> X semanas anteriores</label>
                  {fuentePromedio === 'semanas' && (
                    <div style={{ display: 'flex', alignItems: 'center', gap: 4, marginTop: 2 }}>
                      <input type="number" min={1} max={12} value={numSemanas} onChange={e => setNumSemanas(Number(e.target.value))} style={{ width: 50 }} />
                      <span>semanas</span>
                      {cargandoSemanas && <span style={{ marginLeft: 8, color: '#1976d2' }}>Cargando...</span>}
                    </div>
                  )}
                </div>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'start', gap: 4 }}>
                <button onClick={handleToggleComparar} style={{ background: '#388e3c', color: '#fff', fontWeight: 'bold', padding: '6px 18px', borderRadius: 8, border: 'none', fontSize: 15, cursor: 'pointer', marginBottom: 2 }}>
                  {mostrarComparar ? 'Ocultar Comparar' : 'Comparar'}
                </button>
                {mostrarComparar && (
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <input type="date" value={fechaComparar} onChange={e => setFechaComparar(e.target.value)} style={{ fontSize: 15 }} />
                    <button onClick={handleComparar} disabled={!fechaComparar || cargandoComparar} style={{ background: '#1976d2', color: '#fff', fontWeight: 'bold', padding: '4px 12px', borderRadius: 6, border: 'none', fontSize: 14, cursor: (!fechaComparar || cargandoComparar) ? 'not-allowed' : 'pointer' }}>
                      {cargandoComparar ? 'Cargando...' : 'Graficar'}
                    </button>
                  </div>
                )}
                {errorComparar && <div style={{ color: '#d84315', fontSize: 13 }}>{errorComparar}</div>}
              </div>
            </div>
          )}
        </div>

        {/* Área del gráfico */}
        <div style={{ flex: 1, width: '100%', minHeight: 0, padding: modoSimple ? '0 32px 32px 32px' : '0 32px 32px 32px', boxSizing: 'border-box', display: 'flex', flexDirection: 'column' }}>
          {noData ? (
            <div style={{ color: '#d84315', fontWeight: 'bold', fontSize: 18, padding: 32, textAlign: 'center' }}>
              No hay datos para graficar con los filtros seleccionados.
            </div>
          ) : (
            <div style={{ flex: 1, minHeight: 0, height: '100%' }}>
              <Line
                data={chartData}
                options={{
                  responsive: true,
                  maintainAspectRatio: false,
                  elements: {
                    line: { borderWidth: 5 },
                    point: { radius: 6, hoverRadius: 8 }
                  },
                  plugins: {
                    legend: { display: true, position: 'top', labels: { font: { size: 16 } } },
                    annotation: {
                      annotations: getPicoAnnotations(tipoDiaSel, franjasSel, nombreFranjaMap, horas)
                    },
                    datalabels: {
                      display: function (context) {
                        // No mostrar etiquetas para la línea de la Resolución 290 ni para esencialidad
                        return !((context.dataset.label && context.dataset.label.startsWith('Mínimo Res.')) || (context.dataset.label && context.dataset.label.startsWith('Esencialidad')));
                      },
                      color: '#222',
                      font: { weight: 'bold', size: 13 },
                      align: 'top',
                      formatter: function (value, context) {
                        // Solo mostrar hasta dos decimales
                        return value !== null && value !== undefined ? Number(value).toFixed(2) : '';
                      }
                    },
                    tooltip: {
                      callbacks: {
                        title: function (context) {
                          if (context && context.length > 0) {
                            return `Hora: ${context[0].label}`;
                          }
                          return '';
                        },
                        // Etiqueta por cada punto (mantener simple)
                        label: function (context) {
                          const label = context.dataset.label || '';
                          // No mostrar tooltip individual para la línea de referencia (Res. 290)
                          if (label && label.startsWith('Mínimo Res.')) return null;
                          const value = context.parsed && context.parsed.y !== undefined && context.parsed.y !== null ? Number(context.parsed.y).toFixed(2) : 'n/a';
                          return `${label}: ${value} buses`;
                        },
                        // Footer: mostrar resumen con Promedio, Día seleccionado, Día anterior y Esencialidad
                        footer: function (context) {
                          if (!context || context.length === 0) return '';
                          const idx = context[0].dataIndex;
                          const datasets = context[0].chart.data.datasets;

                          let promedio = null;
                          let esencialidad = null;
                          const comparaciones = []; // {label, value}

                          datasets.forEach(ds => {
                            const lbl = ds.label || '';
                            const val = (ds.data && ds.data[idx] !== undefined && ds.data[idx] !== null) ? ds.data[idx] : null;
                            if (lbl === 'Promedio de selección') promedio = val;
                            else if (lbl && lbl.startsWith('Esencialidad')) esencialidad = val;
                            else if (lbl && lbl.startsWith('Servicios en')) {
                              comparaciones.push({ label: lbl.replace('Servicios en ', ''), value: val });
                            }
                          });

                          const lines = [];
                          if (promedio !== null && promedio !== undefined) {
                            lines.push(`Promedio: ${Number(promedio).toFixed(2)} buses`);
                          }

                          // Ordenar comparaciones para mostrar seleccionado primero (si existe)
                          if (comparaciones.length > 0) {
                            // Si fechaComparar existe, intentar ordenar para que esa fecha aparezca primero
                            try {
                              const sel = fechaComparar;
                              comparaciones.sort((a, b) => (a.label === sel ? -1 : b.label === sel ? 1 : 0));
                            } catch (e) { }
                            comparaciones.forEach(c => {
                              if (c.value !== null && c.value !== undefined) {
                                const vari = (promedio !== null && promedio !== undefined && promedio !== 0) ? ((c.value - promedio) / promedio) * 100 : null;
                                let s = `Servicios (${c.label}): ${Number(c.value).toFixed(2)} buses`;
                                if (vari !== null) s += ` (Δ ${vari.toFixed(2)}%)`;
                                lines.push(s);
                              }
                            });
                          }

                          if (esencialidad !== null && esencialidad !== undefined) {
                            lines.push(`Esencialidad: ${Number(esencialidad).toFixed(2)} buses`);
                          }

                          return lines;
                        }
                      }
                    }
                  }
                }}
                style={{ width: '100%', height: '100%', background: '#fff' }} // fondo claro
                plugins={[ChartDataLabels]}
              />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default GraficoAvanzadoPromedioBuses;