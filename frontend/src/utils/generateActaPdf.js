import jsPDF from 'jspdf';
import autoTable from 'jspdf-autotable';

export const generateActaPdf = async (empresa, fechaReporte) => {
  const doc = new jsPDF('p', 'pt', 'a4');

  // Intentar cargar el logo del MOPC / VMT
  const logoUrl = process.env.PUBLIC_URL + '/imagenes/Logo MOPC VMT.png';
  let logoBase64 = null;
  try {
    const response = await fetch(logoUrl);
    if (response.ok) {
      const blob = await response.blob();
      logoBase64 = await new Promise((resolve) => {
        const reader = new FileReader();
        reader.onloadend = () => resolve(reader.result);
        reader.readAsDataURL(blob);
      });
    }
  } catch (e) {
    console.warn("Could not load logo image", e);
  }

  if (logoBase64) {
    // Dimensiones aproximadas de la imagen del MOPC
    doc.addImage(logoBase64, 'PNG', 60, 30, 475, 50);
  } else {
    doc.setFontSize(14);
    doc.setFont("helvetica", "bold");
    doc.text("GOBIERNO DEL PARAGUAY | MOPC | VMT", 60, 60);
  }

  // Línea separadora
  doc.setLineWidth(1);
  doc.line(60, 95, 535, 95);

  // Título
  doc.setFontSize(11);
  doc.setFont("helvetica", "bold");
  doc.text("ACTA DE COMPROBACIÓN CID N° ___/2026", doc.internal.pageSize.getWidth() / 2, 130, { align: 'center' });

  // Subtítulo
  doc.text("COMPROBACION DE INFRACCIONES A TRAVES DEL CENTRO DE CONTROL Y MONITOREO", doc.internal.pageSize.getWidth() / 2, 150, { align: 'center' });
  doc.text("DEL SISTEMA NACIONAL DE BILLETAJE ELECTRÓNICO", doc.internal.pageSize.getWidth() / 2, 165, { align: 'center' });

  doc.setFontSize(10);
  doc.setFont("helvetica", "normal");

  const today = new Date();
  const day = today.getDate();
  const monthName = today.toLocaleDateString('es-ES', { month: 'long' });
  const yearStr = today.getFullYear();

  // Fecha del reporte (ej: "2026-05")
  const [rYear, rMonth] = fechaReporte.split('-');
  const dateReporte = new Date(rYear, parseInt(rMonth) - 1, 1);
  const reporteMonthName = dateReporte.toLocaleDateString('es-ES', { month: 'long' });

  // Fecha de extracción de datos (1er día del mes siguiente al analizado)
  const dateExtraccion = new Date(parseInt(rYear), parseInt(rMonth), 1);
  const actMonthName = dateExtraccion.toLocaleDateString('es-ES', { month: 'long' });
  const actYear = dateExtraccion.getFullYear();

  const p1 = `En la ciudad de Asunción, a los ${day} día/s del mes de ${monthName} del ${yearStr}, se procede a labrar la presente acta, en atención a los datos extraídos y analizados del Centro de Control y Monitoreo del SNBE, en fecha 01 de ${actMonthName} del año ${actYear}, correspondientes al periodo operativo de ${reporteMonthName}, conforme a las siguientes normativas:`;

  const splitP1 = doc.splitTextToSize(p1, 475);
  doc.text(splitP1, 60, 190);

  let currentY = 190 + (splitP1.length * 12) + 5;

  const normativas = [
    "* artículos 5° y 7° de la Ley 5230/2014;",
    "* el Decreto Reglamentario N° 6912/2017;",
    "* los Manuales vinculantes al SNBE;",
    "* el Artículo 6° de la Resolución GVMT N° 07/2024 que faculta a ésta dependencia a consignar las",
    "  infracciones detectadas a través de los datos obrantes en la CCM, y;",
    "* la Resolución GVMT N° 120/2025 y su modificatoria N° 21/2026,",
    "* así como en concordancia con la información contenida en el Parque Automotor vigente,"
  ];

  normativas.forEach(n => {
    doc.text(n, 90, currentY);
    currentY += 12;
  });

  currentY += 5;
  const p2 = `se comprueba que la Empresa Operadora de Transporte ${empresa.eot_nombre}, ha incurrido en la siguiente infracción:`;
  const splitP2 = doc.splitTextToSize(p2, 475);
  doc.text(splitP2, 60, currentY);

  currentY += (splitP2.length * 12) + 10;

  doc.setFont("helvetica", "bold");
  doc.text("INFRACCION DEL ARTICULO 15.6, Resolución GVMT N° 21/2026", doc.internal.pageSize.getWidth() / 2, currentY, { align: 'center' });
  currentY += 15;

  // Tabla 1: Detalle Infracciones
  const table1Data = empresa.infracciones.map(inf => [inf.fecha, inf.base || 'Art. 15.6', inf.desc]);

  autoTable(doc, {
    startY: currentY,
    margin: { left: 60, right: 60 },
    head: [['Fecha', 'Infracción', 'Descripción']],
    body: table1Data,
    theme: 'grid',
    headStyles: { fillColor: [210, 210, 210], textColor: [0, 0, 0], halign: 'center', lineWidth: 0.1, lineColor: [0, 0, 0] },
    bodyStyles: { textColor: [0, 0, 0], lineWidth: 0.1, lineColor: [0, 0, 0] },
    styles: { fontSize: 9, cellPadding: 3, font: 'helvetica' },
    columnStyles: {
      0: { halign: 'center', cellWidth: 70 },
      1: { halign: 'center', cellWidth: 70 },
      2: { halign: 'left' }
    }
  });

  currentY = doc.lastAutoTable.finalY + 25;

  // Tabla 2: Resumen
  const summaryMap = {};
  empresa.infracciones.forEach(inf => {
    const base = inf.base || 'Art. 15.6';
    if (!summaryMap[base]) summaryMap[base] = 0;
    summaryMap[base]++;
  });

  const table2Data = Object.keys(summaryMap).map(key => [
    key,
    summaryMap[key],
    'Intermedia'
  ]);

  autoTable(doc, {
    startY: currentY,
    margin: { left: 60, right: 60 },
    head: [['Infracción', 'Cantidad de infracción', 'Escala de Infracción']],
    body: table2Data,
    theme: 'grid',
    headStyles: { fillColor: [210, 210, 210], textColor: [0, 0, 0], halign: 'center', lineWidth: 0.1, lineColor: [0, 0, 0] },
    bodyStyles: { textColor: [0, 0, 0], lineWidth: 0.1, lineColor: [0, 0, 0], halign: 'center' },
    styles: { fontSize: 9, cellPadding: 3, font: 'helvetica' }
  });

  currentY = doc.lastAutoTable.finalY + 25;

  doc.setFont("helvetica", "normal");
  const p3 = "Las infracciones y sanciones serán notificadas a la EOT, a los propietarios de las unidades de transporte, quienes deberán abonar en el Viceministerio de Transporte dentro de los 5 (cinco) días de la notificación de la misma (Resolución GVMT 07/24 - Articulo 9).";
  const splitP3 = doc.splitTextToSize(p3, 475);
  doc.text(splitP3, 60, currentY);
  currentY += (splitP3.length * 12) + 5;

  currentY += 40;

  // Firmas
  doc.setFontSize(10);
  doc.text("ELABORADO POR:", 60, currentY);
  doc.text("________________________________________________", 160, currentY);

  currentY += 40;
  doc.text("VERIFICADO POR:", 60, currentY);
  doc.text("________________________________________________", 160, currentY);

  // Pie de página (Misión y Visión)
  const footerY = 750;
  doc.setLineWidth(1);
  doc.line(60, footerY, 535, footerY);

  doc.setFontSize(9);

  // Misión
  doc.setFont("helvetica", "bold");
  doc.text("Misión:", 60, footerY + 15);
  doc.setFont("helvetica", "italic");
  doc.text(' "Somos un organismo que elabora, propone y ejecuta políticas en materia de infraestructura pública, transporte,', 95, footerY + 15);
  doc.text('minería y energía, para la integración y desarrollo económico de la población".', 60, footerY + 27);

  // Visión
  doc.setFont("helvetica", "bold");
  doc.text("Visión:", 60, footerY + 45);
  doc.setFont("helvetica", "italic");
  doc.text(' "Ser reconocidos por nuestra idoneidad en planificación y ejecución de políticas y proyectos, garantizando la', 95, footerY + 45);
  doc.text('conectividad a través de infraestructuras públicas innovadoras, gestionadas de forma eficiente, transparente y enfocadas', 60, footerY + 57);
  doc.text('al ciudadano".', 60, footerY + 69);

  // Guardar PDF
  doc.save(`Acta_Infraccion_${empresa.eot_nombre.replace(/\s+/g, '_')}_${fechaReporte}.pdf`);
};
