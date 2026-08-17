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
    textoExpedicion = `Se expide la presente Constancia de Rendimiento Operativo en la ciudad de Asunción, a los ___ días del mes de ____________ de 2026, para su remisión a la Dirección Metropolitana de Transporte y fines administrativos pertinentes.`;
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
    textoExpedicion = `Se expide la presente Constancia de Rendimiento Operativo en la ciudad de Asunción, a los ${diaEmision} días del mes de ${mesEmisionNombre} de ${anioEmision}, para su remisión a la Dirección Metropolitana de Transporte y fines administrativos pertinentes.`;
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
      // Fila Encabezado
      new TableRow({
        children: [
          new TableCell({
            width: { size: 45, type: WidthType.PERCENTAGE },
            shading: { fill: "F1F5F9", type: ShadingType.CLEAR },
            borders: cellBorder,
            children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "INDICADOR EVALUADO", font: "Tahoma", size: 20, bold: true })] })]
          }),
          new TableCell({
            width: { size: 18, type: WidthType.PERCENTAGE },
            shading: { fill: "F1F5F9", type: ShadingType.CLEAR },
            borders: cellBorder,
            children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "UMBRAL MÍNIMO EXIGIDO", font: "Tahoma", size: 20, bold: true })] })]
          }),
          new TableCell({
            width: { size: 18, type: WidthType.PERCENTAGE },
            shading: { fill: "F1F5F9", type: ShadingType.CLEAR },
            borders: cellBorder,
            children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "RESULTADO OBTENIDO", font: "Tahoma", size: 20, bold: true })] })]
          }),
          new TableCell({
            width: { size: 19, type: WidthType.PERCENTAGE },
            shading: { fill: "F1F5F9", type: ShadingType.CLEAR },
            borders: cellBorder,
            children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "EVALUACIÓN FINAL", font: "Tahoma", size: 20, bold: true })] })]
          })
        ]
      }),
      // Fila Datos
      new TableRow({
        children: [
          new TableCell({
            borders: cellBorder,
            children: [
              new Paragraph({
                alignment: AlignmentType.JUSTIFY,
                children: [
                  new TextRun({ text: "Índice de Cumplimiento de Cantidad de Buses Distintos Mínimo Mensual (ICCBDM Mensual)\n", font: "Tahoma", size: 20, bold: true }),
                  new TextRun({ text: "(Medición consolidada de flota operativa a nivel empresa)", font: "Tahoma", size: 18, italics: true })
                ]
              })
            ]
          }),
          new TableCell({
            borders: cellBorder,
            children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "95.00 %", font: "Tahoma", size: 20, bold: true })] })]
          }),
          new TableCell({
            borders: cellBorder,
            children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: `${iccbdmVal.toFixed(2)} %`, font: "Tahoma", size: 20, bold: true })] })]
          }),
          new TableCell({
            borders: cellBorder,
            children: [
              new Paragraph({
                alignment: AlignmentType.CENTER,
                children: [
                  new TextRun({
                    text: resultadoEvaluacion,
                    font: "Tahoma",
                    size: 20,
                    bold: true
                  })
                ]
              })
            ]
          })
        ]
      })
    ]
  });

  // 6. Tabla de Franjas Operativas Computables (Alineada en tabla limpia)
  const noBorder = {
    top: { style: BorderStyle.NONE, size: 0, color: "auto" },
    bottom: { style: BorderStyle.NONE, size: 0, color: "auto" },
    left: { style: BorderStyle.NONE, size: 0, color: "auto" },
    right: { style: BorderStyle.NONE, size: 0, color: "auto" }
  };

  const tablaFranjas = new Table({
    width: { size: 100, type: WidthType.PERCENTAGE },
    rows: [
      // Header 1
      new TableRow({
        children: [
          new TableCell({
            width: { size: 100, type: WidthType.PERCENTAGE },
            columnSpan: 3,
            borders: noBorder,
            children: [
              new Paragraph({
                spacing: { before: 80, after: 40 },
                children: [
                  new TextRun({ text: "1. Lunes a Viernes:", font: "Tahoma", size: 22, bold: true })
                ]
              })
            ]
          })
        ]
      }),
      // Item 1.1
      new TableRow({
        children: [
          new TableCell({ width: { size: 4, type: WidthType.PERCENTAGE }, borders: noBorder, children: [new Paragraph({ children: [] })] }),
          new TableCell({ width: { size: 26, type: WidthType.PERCENTAGE }, borders: noBorder, children: [new Paragraph({ children: [new TextRun({ text: "• Pico Mañana:", font: "Tahoma", size: 20, bold: true })] })] }),
          new TableCell({ width: { size: 70, type: WidthType.PERCENTAGE }, borders: noBorder, children: [new Paragraph({ children: [new TextRun({ text: "05:00 a 07:59 h   -> COMPUTABLE (Alcanzada por exigibilidad y sanción)", font: "Tahoma", size: 20 })] })] })
        ]
      }),
      // Item 1.2
      new TableRow({
        children: [
          new TableCell({ width: { size: 4, type: WidthType.PERCENTAGE }, borders: noBorder, children: [new Paragraph({ children: [] })] }),
          new TableCell({ width: { size: 26, type: WidthType.PERCENTAGE }, borders: noBorder, children: [new Paragraph({ children: [new TextRun({ text: "• Pos Pico (Entre):", font: "Tahoma", size: 20, bold: true })] })] }),
          new TableCell({ width: { size: 70, type: WidthType.PERCENTAGE }, borders: noBorder, children: [new Paragraph({ children: [new TextRun({ text: "08:00 a 15:59 h   -> COMPUTABLE (Alcanzada por exigibilidad y sanción)", font: "Tahoma", size: 20 })] })] })
        ]
      }),
      // Item 1.3
      new TableRow({
        children: [
          new TableCell({ width: { size: 4, type: WidthType.PERCENTAGE }, borders: noBorder, children: [new Paragraph({ children: [] })] }),
          new TableCell({ width: { size: 26, type: WidthType.PERCENTAGE }, borders: noBorder, children: [new Paragraph({ children: [new TextRun({ text: "• Pico Tarde:", font: "Tahoma", size: 20, bold: true })] })] }),
          new TableCell({ width: { size: 70, type: WidthType.PERCENTAGE }, borders: noBorder, children: [new Paragraph({ children: [new TextRun({ text: "16:00 a 18:59 h   -> COMPUTABLE (Alcanzada por exigibilidad y sanción)", font: "Tahoma", size: 20 })] })] })
        ]
      }),
      // Item 1.4
      new TableRow({
        children: [
          new TableCell({ width: { size: 4, type: WidthType.PERCENTAGE }, borders: noBorder, children: [new Paragraph({ children: [] })] }),
          new TableCell({ width: { size: 26, type: WidthType.PERCENTAGE }, borders: noBorder, children: [new Paragraph({ children: [new TextRun({ text: "• Pos Pico Tarde:", font: "Tahoma", size: 20, bold: true })] })] }),
          new TableCell({ width: { size: 70, type: WidthType.PERCENTAGE }, borders: noBorder, children: [new Paragraph({ children: [new TextRun({ text: "19:00 a 20:59 h   -> COMPUTABLE (Alcanzada por exigibilidad y sanción)", font: "Tahoma", size: 20 })] })] })
        ]
      }),
      // Header 2
      new TableRow({
        children: [
          new TableCell({
            width: { size: 100, type: WidthType.PERCENTAGE },
            columnSpan: 3,
            borders: noBorder,
            children: [
              new Paragraph({
                spacing: { before: 120, after: 40 },
                children: [
                  new TextRun({ text: "2. Sábados:", font: "Tahoma", size: 22, bold: true })
                ]
              })
            ]
          })
        ]
      }),
      // Item 2.1
      new TableRow({
        children: [
          new TableCell({ width: { size: 4, type: WidthType.PERCENTAGE }, borders: noBorder, children: [new Paragraph({ children: [] })] }),
          new TableCell({ width: { size: 26, type: WidthType.PERCENTAGE }, borders: noBorder, children: [new Paragraph({ children: [new TextRun({ text: "• Pico Sábados:", font: "Tahoma", size: 20, bold: true })] })] }),
          new TableCell({ width: { size: 70, type: WidthType.PERCENTAGE }, borders: noBorder, children: [new Paragraph({ children: [new TextRun({ text: "06:00 a 15:59 h   -> COMPUTABLE (Alcanzada por exigibilidad y sanción)", font: "Tahoma", size: 20 })] })] })
        ]
      })
    ]
  });

  // 7. Tabla de Firmas
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
            spacing: { before: 200, after: 300 },
            children: [
              new TextRun({
                text: `CONSTANCIA DE RENDIMIENTO OPERATIVO N° ${nroCROFinal}`,
                font: "Tahoma",
                size: 24,
                bold: true
              })
            ]
          }),

          // CONSTE QUE
          new Paragraph({
            alignment: AlignmentType.JUSTIFY,
            spacing: { after: 150 },
            children: [new TextRun({ text: "CONSTE QUE:", font: "Tahoma", size: 22, bold: true })]
          }),

          // Párrafo Inicial
          new Paragraph({
            alignment: AlignmentType.JUSTIFY,
            indent: { firstLine: 720 },
            spacing: { after: 200 },
            children: [
              new TextRun({ text: "La Empresa Operadora de Transporte (EOT) ", font: "Tahoma", size: 22 }),
              new TextRun({ text: `${eot.eot_nombre.toUpperCase()}`, font: "Tahoma", size: 22, bold: true }),
              new TextRun({ text: ", prestadora del servicio metropolitano de transporte público en las líneas e itinerarios autorizados bajo su concesión, durante el mes operativo correspondiente a ", font: "Tahoma", size: 22 }),
              new TextRun({ text: `${mesOperativoStr.toUpperCase()} DE ${year}`, font: "Tahoma", size: 22, bold: true }),
              new TextRun({ text: ", ha registrado en la base de datos de la Central de Control y Monitoreo(CCM) del Sistema Nacional de Billetaje Electrónico(SNBE) los siguientes indicadores consolidados de rendimiento a nivel empresa:", font: "Tahoma", size: 22 })
            ]
          }),

          // Sección I - Encabezado
          new Paragraph({
            alignment: AlignmentType.JUSTIFY,
            spacing: { before: 200, after: 150 },
            children: [
              new TextRun({
                text: "I. EVALUACIÓN DE RENDIMIENTO OPERATIVO GLOBAL (A NIVEL EMPRESA)",
                font: "Tahoma",
                size: 22,
                bold: true
              })
            ]
          }),

          // Tabla I
          tablaEvaluacion,

          // Espaciador
          new Paragraph({ spacing: { after: 250 }, children: [] }),

          // Sección II
          new Paragraph({
            alignment: AlignmentType.JUSTIFY,
            spacing: { before: 150, after: 150 },
            children: [
              new TextRun({
                text: "II. DELIMITACIÓN DE FRANJAS OPERATIVAS COMPUTABLES (DICTAMEN C.J. N° 357/2026)",
                font: "Tahoma",
                size: 22,
                bold: true
              })
            ]
          }),
          new Paragraph({
            alignment: AlignmentType.JUSTIFY,
            indent: { firstLine: 720 },
            spacing: { after: 150 },
            children: [
              new TextRun({ text: "En estricta concordancia con el Dictamen ", font: "Tahoma", size: 22 }),
              new TextRun({ text: "C.J. N° 357/2026", font: "Tahoma", size: 22, bold: true }),
              new TextRun({ text: " emitido por la Coordinación Jurídica del VMT (en armonización con los Arts. 4° y 21 de la Res. GVMT N° 120/2025 y la Res. GVMT N° 21/2026), la evaluación de exigibilidad técnica para la presente etapa de implementación se circunscribe exclusivamente a las siguientes franjas operativas:", font: "Tahoma", size: 22 })
            ]
          }),

          // Tabla ordenada de Franjas
          tablaFranjas,

          // Nota de Franjas Exceptuadas
          new Paragraph({
            alignment: AlignmentType.JUSTIFY,
            spacing: { before: 120, after: 250 },
            children: [
              new TextRun({
                text: "* Franjas Exceptuadas en la presente etapa (Solo monitoreo informativo): Madrugada (L-V), Nocturna (L-V), Pos Pico Sábados, Nocturna Sábados, Domingos y Feriados.",
                font: "Tahoma",
                size: 18,
                italics: true
              })
            ]
          }),

          // Sección III
          new Paragraph({
            alignment: AlignmentType.JUSTIFY,
            spacing: { before: 150, after: 150 },
            children: [
              new TextRun({
                text: "III. FUNDAMENTACIÓN TÉCNICA, LEGAL Y MARCO NORMATIVO DE RESPALDO",
                font: "Tahoma",
                size: 22,
                bold: true
              })
            ]
          }),
          new Paragraph({
            alignment: AlignmentType.JUSTIFY,
            indent: { firstLine: 720 },
            spacing: { after: 120 },
            children: [
              new TextRun({ text: "1. PARÁMETRO VIGENTE Y METODOLOGÍA: ", font: "Tahoma", size: 22, bold: true }),
              new TextRun({
                text: "Los índices operativos consignados fueron calculados en base a los registros transaccionales y GPS(según Resolución GVMT N° 65/2024) de la Central de Control y Monitoreo del Billetaje Electrónico (Ley N° 5230/2014), aplicando el Índice de Cumplimiento de Cantidad de Buses Distintos Mínimo Mensual (ICCBDM Mensual) reglamentado en el Artículo 11 de la Resolución GVMT N° 120/2025 (\"Por la cual se establecen nuevos indicadores de desempeño, niveles de servicio y parámetros de evaluación de rendimiento para el servicio de transporte público metropolitano de pasajeros y se implementa un sistema integral de control y monitoreo\"), modificada por las Resoluciones GVMT N° 21/2026 y N° 26/2026.",
                font: "Tahoma",
                size: 22
              })
            ]
          }),
          new Paragraph({
            alignment: AlignmentType.JUSTIFY,
            indent: { firstLine: 720 },
            spacing: { after: 120 },
            children: [
              new TextRun({ text: "2. ABROGACIÓN DEL RÉGIMEN ANTERIOR: ", font: "Tahoma", size: 22, bold: true }),
              new TextRun({
                text: "De acuerdo con el régimen transitorio establecido en el Art. 23 de la Res. GVMT N° 120/2025 y refrendado por el Dictamen C.J. N° 357/2026, la anterior Resolución GVMT N° 290/2021 (y sus modificatorias 223/2021, 244/2021 y 11/2024) quedó abrogada de pleno derecho al 30 de junio de 2026. Por consiguiente, la antigua evaluación fraccionada por troncales ha sido sustituida de manera exclusiva por la evaluación global de flota a nivel empresa (ICCBDM Mensual) a partir de la operativa de julio de 2026.",
                font: "Tahoma",
                size: 22
              })
            ]
          }),
          new Paragraph({
            alignment: AlignmentType.JUSTIFY,
            indent: { firstLine: 720 },
            spacing: { after: 120 },
            children: [
              new TextRun({ text: "3. EXCLUSIONES NORMATIVAS EXPRESAS: ", font: "Tahoma", size: 22, bold: true }),
              new TextRun({
                text: 'En cumplimiento de los Arts. 9° y 10 de la Resolución GVMT N° 120/2025 y el Dictamen C.J. N° 357/2026, se hallan excluidas del cálculo del CBDmín y del IFO las líneas nocturnas especiales "Búho" (B1 a B4) y las operadas con buses 100% eléctricos (E1 a E3), rigiéndose por sus respectivos pliegos contractuales.',
                font: "Tahoma",
                size: 22
              })
            ]
          }),
          new Paragraph({
            alignment: AlignmentType.JUSTIFY,
            indent: { firstLine: 720 },
            spacing: { after: 120 },
            children: [
              new TextRun({ text: "4. RESPALDO PARA EL RÉGIMEN DE SUBSIDIOS: ", font: "Tahoma", size: 22, bold: true }),
              new TextRun({
                text: 'La presente Constancia certifica el cumplimiento del requisito sustancial exigido por el Artículo 9°, inciso i) del Decreto N° 710/2023 ("Cumplir con los niveles de servicio establecidos por el Gabinete del Viceministro de Transporte, comprobada por la Constancia de Rendimiento Operativo del mes solicitado") en concordancia con su Artículo 16 (decaimiento del derecho), y el procedimiento previsto en el Artículo 2°, numeral II, inciso C.a) de la Resolución MOPC N° 1901/2023, poseyendo plena validez y eficacia jurídica para la tramitación de las solicitudes de pago de subsidio.',
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
              new TextRun({ text: "5. CONTROL DE USOS LLAMATIVOS: ", font: "Tahoma", size: 22, bold: true }),
              new TextRun({
                text: `En concordancia con lo dispuesto en la Resolución GVMT N° 166/2023, esta Coordinación eleva de forma paralela a la Dirección Metropolitana de Transporte el Memorándum CID N° ${numeroMemorandum ? numeroMemorandum.trim() : `___/${year || 2026}`}, contentivo del informe de validaciones y transacciones consideradas como "usos llamativos" durante el mes evaluado.`,
                font: "Tahoma",
                size: 22
              })
            ]
          }),

          // Sección IV
          new Paragraph({
            alignment: AlignmentType.JUSTIFY,
            spacing: { before: 150, after: 150 },
            children: [
              new TextRun({
                text: "IV. CONCLUSIÓN Y HABILITACIÓN AL SUBSIDIO",
                font: "Tahoma",
                size: 22,
                bold: true
              })
            ]
          }),
          new Paragraph({
            alignment: AlignmentType.JUSTIFY,
            indent: { firstLine: 720 },
            spacing: { after: 250 },
            children: [
              new TextRun({
                text: `Visto el informe técnico emitido por la CCCM del SNBE y habiéndose evaluado el desempeño bajo el umbral legal mínimo del 95.00% del ICCBDM Mensual en las franjas computables fijadas en el Dictamen C.J. N° 357/2026, se concluye que la Empresa Operadora de Transporte `,
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
                text: ` en la operativa del mes de `,
                font: "Tahoma",
                size: 22
              }),
              new TextRun({
                text: `${mesOperativoStr.toUpperCase()} DE ${year}`,
                font: "Tahoma",
                size: 22,
                bold: true
              }),
              new TextRun({
                text: `, `,
                font: "Tahoma",
                size: 22
              }),
              new TextRun({
                text: `${resultadoEvaluacion}`,
                font: "Tahoma",
                size: 22,
                bold: true,
                color: cumple ? "15803D" : "B91C1C"
              }),
              new TextRun({
                text: ` con los Niveles de Servicio Mínimos exigidos para la habilitación al cobro del subsidio estatal al transporte.`,
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
