import {
  Document,
  Packer,
  Paragraph,
  TextRun,
  Table,
  TableRow,
  TableCell,
  BorderStyle,
  WidthType,
  ImageRun,
  AlignmentType,
  Header,
  Footer,
  ShadingType
} from "docx";

const urlToBlob = async (url) => {
  const resp = await fetch(url);
  return await resp.blob();
};

const getMonthName = (monthNumber) => {
  const months = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
  ];
  return months[monthNumber - 1] || "";
};

export const generateCROWord = async ({
  eot,
  year,
  month,
  numeroCRO,
  fechaEmision,
  isFechaBlanco,
  numeroMemorandum
}) => {
  // 1. Cargar Logo MOPC VMT
  const logoUrl = process.env.PUBLIC_URL + "/imagenes/Logo_MOPC_VMT_CRO.png";
  let logoBuffer = null;
  try {
    const logoBlob = await urlToBlob(logoUrl);
    logoBuffer = await logoBlob.arrayBuffer();
  } catch (e) {
    console.warn("No se pudo cargar la imagen del logo para el Word CRO", e);
  }

  // 2. Encabezado institucional
  const docHeader = new Header({
    children: [
      new Paragraph({
        alignment: AlignmentType.CENTER,
        children: logoBuffer
          ? [
            new ImageRun({
              data: logoBuffer,
              transformation: {
                width: 480,
                height: 55
              }
            })
          ]
          : [
            new TextRun({
              text: "GOBIERNO DEL PARAGUAY | MINISTERIO DE OBRAS PÚBLICAS Y COMUNICACIONES",
              bold: true,
              font: "Tahoma",
              size: 18
            })
          ]
      }),
      new Paragraph({
        border: {
          bottom: { color: "000000", space: 2, value: BorderStyle.SINGLE, size: 8 }
        },
        children: []
      })
    ]
  });

  // 3. Pie de página institucional con raya horizontal encima
  const docFooter = new Footer({
    children: [
      new Paragraph({
        border: {
          top: { color: "000000", space: 6, value: BorderStyle.SINGLE, size: 12 }
        },
        alignment: AlignmentType.JUSTIFY,
        spacing: { before: 100, after: 40 },
        children: [
          new TextRun({
            text: "Misión: ",
            bold: true,
            font: "Tahoma",
            size: 16
          }),
          new TextRun({
            text: '"Somos un organismo que elabora, propone y ejecuta políticas en materia de infraestructura pública, transporte, minería, energía, para la integración y desarrollo económico de la población".',
            italics: true,
            font: "Tahoma",
            size: 16
          })
        ]
      }),
      new Paragraph({
        alignment: AlignmentType.JUSTIFY,
        children: [
          new TextRun({
            text: "Visión: ",
            bold: true,
            font: "Tahoma",
            size: 16
          }),
          new TextRun({
            text: '"Ser reconocidos por nuestra idoneidad en planificación y ejecución de políticas y proyectos, garantizando la conectividad a través de infraestructuras públicas innovadoras, gestionadas de forma eficiente, transparente y enfocadas al ciudadano".',
            italics: true,
            font: "Tahoma",
            size: 16
          })
        ]
      })
    ]
  });

  // 4. Formatear Número de CRO (incluir /2026 siempre después del número)
  const numCroClean = numeroCRO ? numeroCRO.trim() : "";
  const yearSuffix = year || 2026;
  let nroCROFinal = "";
  if (!numCroClean) {
    nroCROFinal = `___ / ${yearSuffix}`;
  } else if (numCroClean.includes("/")) {
    nroCROFinal = numCroClean;
  } else {
    nroCROFinal = `${numCroClean} / ${yearSuffix}`;
  }

  const mesOperativoStr = getMonthName(month);
  const iccbdmVal = typeof eot.iccbdm_mensual === "number" ? eot.iccbdm_mensual : parseFloat(eot.iccbdm_mensual || 0);
  const cumple = eot.cumple_subsidio !== undefined ? eot.cumple_subsidio : (eot.estado_color !== "red" && iccbdmVal >= 95.0);
  const resultadoEvaluacion = cumple ? "CUMPLE" : "NO CUMPLE";

  // Formato de Fecha de Emisión
  let textoExpedicion = "";
  if (isFechaBlanco) {
    textoExpedicion = `Se emite la presente constancia a los ___ días del mes de ____________ de ${year || 2026}, para los fines a que hubiere lugar.-`;
  } else {
    let dateObj = new Date();
    if (fechaEmision) {
      const [fYear, fMonth, fDay] = fechaEmision.split("-");
      if (fYear && fMonth && fDay) {
        dateObj = new Date(parseInt(fYear), parseInt(fMonth) - 1, parseInt(fDay));
      }
    }
    const diaEmision = dateObj.getDate();
    const mesEmisionNombre = getMonthName(dateObj.getMonth() + 1);
    const anioEmision = dateObj.getFullYear();
    textoExpedicion = `Se emite la presente constancia a los ${diaEmision} días del mes de ${mesEmisionNombre.toLowerCase()} de ${anioEmision}, para los fines a que hubiere lugar.-`;
  }

  // Estilos Base
  const fontObj = { font: "Tahoma", size: 22 };
  const fontBold = { font: "Tahoma", size: 22, bold: true };

  // 5. Tabla I (Evaluación)
  const cellBorder = {
    top: { style: BorderStyle.SINGLE, size: 6, color: "000000" },
    bottom: { style: BorderStyle.SINGLE, size: 6, color: "000000" },
    left: { style: BorderStyle.SINGLE, size: 6, color: "000000" },
    right: { style: BorderStyle.SINGLE, size: 6, color: "000000" }
  };

  const tablaEvaluacion = new Table({
    width: { size: 100, type: WidthType.PERCENTAGE },
    rows: [
      new TableRow({
        children: [
          new TableCell({
            width: { size: 40, type: WidthType.PERCENTAGE },
            shading: { fill: "F1F5F9", type: ShadingType.CLEAR },
            borders: cellBorder,
            children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "INDICADOR EVALUADO", font: "Tahoma", size: 20, bold: true })] })]
          }),
          new TableCell({
            width: { size: 20, type: WidthType.PERCENTAGE },
            shading: { fill: "F1F5F9", type: ShadingType.CLEAR },
            borders: cellBorder,
            children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "UMBRAL MÍNIMO EXIGIDO", font: "Tahoma", size: 20, bold: true })] })]
          }),
          new TableCell({
            width: { size: 20, type: WidthType.PERCENTAGE },
            shading: { fill: "F1F5F9", type: ShadingType.CLEAR },
            borders: cellBorder,
            children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "RESULTADO OBTENIDO (EOT)", font: "Tahoma", size: 20, bold: true })] })]
          }),
          new TableCell({
            width: { size: 20, type: WidthType.PERCENTAGE },
            shading: { fill: "F1F5F9", type: ShadingType.CLEAR },
            borders: cellBorder,
            children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "EVALUACIÓN FINAL", font: "Tahoma", size: 20, bold: true })] })]
          })
        ]
      }),
      new TableRow({
        children: [
          new TableCell({
            borders: cellBorder,
            children: [
              new Paragraph({
                alignment: AlignmentType.JUSTIFY,
                children: [
                  new TextRun({ text: "Índice de Cumplimiento de Cantidad de Buses Distintos Mínimo Mensual (ICCBDM Mensual)", font: "Tahoma", size: 20 })
                ]
              })
            ]
          }),
          new TableCell({
            borders: cellBorder,
            children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "95.00%", font: "Tahoma", size: 20 })] })]
          }),
          new TableCell({
            borders: cellBorder,
            children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: `${iccbdmVal.toFixed(2)}%`, font: "Tahoma", size: 20 })] })]
          }),
          new TableCell({
            borders: cellBorder,
            children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: resultadoEvaluacion, font: "Tahoma", size: 20, bold: true })] })]
          })
        ]
      })
    ]
  });

  // 7. Tabla de Firmas
  const noBorder = {
    top: { style: BorderStyle.NONE, size: 0, color: "auto" },
    bottom: { style: BorderStyle.NONE, size: 0, color: "auto" },
    left: { style: BorderStyle.NONE, size: 0, color: "auto" },
    right: { style: BorderStyle.NONE, size: 0, color: "auto" }
  };

  const tablaFirmas = new Table({
    width: { size: 100, type: WidthType.PERCENTAGE },
    rows: [
      new TableRow({
        children: [
          new TableCell({
            width: { size: 50, type: WidthType.PERCENTAGE },
            borders: noBorder,
            children: [
              new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "________________________________________", font: "Tahoma", size: 20 })] }),
              new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "Coordinación de Innovación y Desarrollo", font: "Tahoma", size: 20, bold: true })] }),
              new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "Viceministerio de Transporte - MOPC", font: "Tahoma", size: 18 })] })
            ]
          }),
          new TableCell({
            width: { size: 50, type: WidthType.PERCENTAGE },
            borders: noBorder,
            children: [
              new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "________________________________________", font: "Tahoma", size: 20 })] }),
              new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "Dirección Metropolitana de Transporte", font: "Tahoma", size: 20, bold: true })] }),
              new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "Viceministerio de Transporte - MOPC", font: "Tahoma", size: 18 })] })
            ]
          })
        ]
      })
    ]
  });

  // 8. Armar el contenido del Documento
  const doc = new Document({
    sections: [
      {
        headers: { default: docHeader },
        footers: { default: docFooter },
        properties: {
          page: {
            margin: {
              top: 1000,
              bottom: 1000,
              left: 1200,
              right: 1200
            }
          }
        },
        children: [
          // Título Principal
          new Paragraph({
            alignment: AlignmentType.CENTER,
            spacing: { before: 200, after: 0 },
            children: [
              new TextRun({
                text: `CONSTANCIA DE RENDIMIENTO OPERATIVO N° ${nroCROFinal}`,
                font: "Tahoma",
                size: 24,
                bold: true
              })
            ]
          }),
          new Paragraph({
            alignment: AlignmentType.CENTER,
            spacing: { before: 0, after: 400 },
            children: [
              new TextRun({
                text: `Coordinación de Innovación y Desarrollo – DMT – VMT`,
                font: "Tahoma",
                size: 20
              })
            ]
          }),

          // CONSTE QUE
          new Paragraph({
            alignment: AlignmentType.JUSTIFY,
            spacing: { after: 200 },
            children: [
              new TextRun({ text: `CONSTE QUE LA EMPRESA OPERADORA DE TRANSPORTE `, font: "Tahoma", size: 22 }),
              new TextRun({ text: `${eot.eot_nombre.toUpperCase()}`, font: "Tahoma", size: 22, bold: true }),
              new TextRun({ text: `, DURANTE EL MES OPERATIVO DE `, font: "Tahoma", size: 22 }),
              new TextRun({ text: `${mesOperativoStr.toUpperCase()} DE ${year}`, font: "Tahoma", size: 22, bold: true }),
              new TextRun({ text: ` HA OPERADO CON LOS SIGUIENTES INDICADORES CONSOLIDADOS DE DESEMPEÑO OPERATIVO A NIVEL EMPRESA:`, font: "Tahoma", size: 22 })
            ]
          }),

          // Tabla I
          tablaEvaluacion,

          // Espaciador
          new Paragraph({ spacing: { after: 250 }, children: [] }),

          new Paragraph({
            alignment: AlignmentType.JUSTIFY,
            indent: { firstLine: 720 },
            spacing: { after: 150 },
            children: [
              new TextRun({
                text: `Visto los indicadores operativos que obran en el informe técnico y en base a los parámetros de cumplimiento vigentes, se concluye que la EOT `,
                font: "Tahoma",
                size: 22
              }),
              new TextRun({
                text: `${eot.eot_nombre.toUpperCase()}`,
                font: "Tahoma",
                size: 22,
                bold: true
              }),
              new TextRun({
                text: ` en la operativa consolidada del mes de ${mesOperativoStr.toLowerCase()} de ${year}, `,
                font: "Tahoma",
                size: 22
              }),
              new TextRun({
                text: `${resultadoEvaluacion}`,
                font: "Tahoma",
                size: 22,
                bold: true
              }),
              new TextRun({
                text: ` con el Nivel de Servicio Mínimo establecido para la habilitación al cobro de subsidios.`,
                font: "Tahoma",
                size: 22
              })
            ]
          }),

          new Paragraph({
            alignment: AlignmentType.JUSTIFY,
            indent: { firstLine: 720 },
            spacing: { after: 150 },
            children: [
              new TextRun({
                text: `Los índices operativos que obran en el informe adjunto fueron calculados con base en la información transaccional y de monitoreo contenida en la base de datos de la Central de Control y Monitoreo del Billetaje Electrónico, aplicando la metodología y parámetros del Índice de Cumplimiento de Cantidad de Buses Distintos Mínimo Mensual (ICCBDM Mensual) previstos en la Resolución GVMT N° 120/2025 "POR LA CUAL SE ESTABLECEN NUEVOS INDICADORES DE DESEMPEÑO, NIVELES DE SERVICIO Y PARÁMETROS DE EVALUACIÓN DE RENDIMIENTO PARA EL SERVICIO DE TRANSPORTE PÚBLICO METROPOLITANO DE PASAJEROS Y SE IMPLEMENTA UN SISTEMA INTEGRAL DE CONTROL Y MONITOREO".`,
                font: "Tahoma",
                size: 22
              })
            ]
          }),

          new Paragraph({
            alignment: AlignmentType.JUSTIFY,
            indent: { firstLine: 720 },
            spacing: { after: 150 },
            children: [
              new TextRun({
                text: `En atención a lo fijado en el Artículo 23 de la Resolución GVMT N° 120/2025 sobre el régimen de transición y entrada en vigor a partir del 1 de julio de 2026, esta medición global a nivel empresa sustituye al esquema de evaluación por troncales que disponía la abrogada Resolución GVMT N° 290/2021.-`,
                font: "Tahoma",
                size: 22
              })
            ]
          }),

          new Paragraph({
            alignment: AlignmentType.JUSTIFY,
            indent: { firstLine: 720 },
            spacing: { after: 150 },
            children: [
              new TextRun({
                text: `El análisis técnico correspondiente a la operativa de la empresa en el mes de ${mesOperativoStr.toLowerCase()} de ${year} se informa a la Dirección Metropolitana de Transporte adjunto al presente Memorándum, recomendándose su consideración para el procesamiento de solicitudes en el marco del régimen de subsidios establecido en el Art. 9°, inciso i) del Decreto N° 710/2023 y la Resolución MOPC N° 1901/2023.`,
                font: "Tahoma",
                size: 22
              })
            ]
          }),

          new Paragraph({
            alignment: AlignmentType.JUSTIFY,
            indent: { firstLine: 720 },
            spacing: { after: 250 },
            children: [
              new TextRun({
                text: `Asimismo, en concordancia con la Resolución GVMT N° 166/2023, se remite en el Memorándum CID N° ${numeroMemorandum ? numeroMemorandum.trim() : `___/${year || 2026}`} el resultado del análisis de los usos considerados como "llamativos" durante el mes de ${mesOperativoStr.toLowerCase()} del año ${year || 2026}, para los fines administrativos que correspondan.`,
                font: "Tahoma",
                size: 22
              })
            ]
          }),

          // Párrafo Expedición
          new Paragraph({
            alignment: AlignmentType.JUSTIFY,
            indent: { firstLine: 720 },
            spacing: { before: 200, after: 400 },
            children: [
              new TextRun({
                text: textoExpedicion,
                font: "Tahoma",
                size: 22
              })
            ]
          }),

          // Firmas
          tablaFirmas
        ]
      }
    ]
  });

  // 9. Generar y descargar el archivo .docx de forma directa nativa
  const rawBlob = await Packer.toBlob(doc);
  const blob = new Blob([rawBlob], {
    type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
  });
  const cleanName = eot.eot_nombre.replace(/[^a-zA-Z0-9]/g, "_");
  const fileName = `CRO_${cleanName}_${mesOperativoStr}_${year}.docx`;

  const link = document.createElement("a");
  link.style.display = "none";
  link.href = URL.createObjectURL(blob);
  link.download = fileName;
  document.body.appendChild(link);
  link.click();

  setTimeout(() => {
    document.body.removeChild(link);
    URL.revokeObjectURL(link.href);
  }, 300);
};
