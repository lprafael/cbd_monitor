import { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, BorderStyle, WidthType, ImageRun, AlignmentType, PageBreak, Header, Footer } from "docx";
import { saveAs } from "file-saver";

const urlToBlob = async (url) => {
  const resp = await fetch(url);
  return await resp.blob();
};

export const generateNotificacionesWord = async (reporte, fechaReporte) => {
  const logoUrl = process.env.PUBLIC_URL + '/imagenes/Logo MOPC VMT.png';
  let logoBlob;
  let logoBuffer;
  try {
    logoBlob = await urlToBlob(logoUrl);
    logoBuffer = await logoBlob.arrayBuffer();
  } catch (e) {
    console.warn("Could not load logo for Word document", e);
  }

  const docHeader = new Header({
    children: [
      new Paragraph({
        alignment: AlignmentType.CENTER,
        children: logoBuffer ? [
          new ImageRun({
            data: logoBuffer,
            transformation: {
              width: 500,
              height: 52
            }
          })
        ] : [new TextRun({ text: "GOBIERNO DEL PARAGUAY | MOPC | VMT", bold: true })]
      }),
      new Paragraph({
        border: {
          bottom: { color: "000000", space: 1, value: BorderStyle.SINGLE, size: 6 }
        },
        children: []
      })
    ]
  });

  const docFooter = new Footer({
    children: [
      new Paragraph({
        border: {
          top: { color: "000000", space: 1, value: BorderStyle.SINGLE, size: 6 }
        },
        children: []
      }),
      new Paragraph({
        children: [
          new TextRun({ text: "Misión: ", bold: true, size: 16 }),
          new TextRun({ text: '"Somos un organismo que elabora, propone y ejecuta políticas en materia de infraestructura pública, transporte, minería y energía, para la integración y desarrollo económico de la población".', italics: true, size: 16 })
        ]
      }),
      new Paragraph({
        children: [
          new TextRun({ text: "Visión: ", bold: true, size: 16 }),
          new TextRun({ text: '"Ser reconocidos por nuestra idoneidad en planificación y ejecución de políticas y proyectos, garantizando la conectividad a través de infraestructuras públicas innovadoras, gestionadas de forma eficiente, transparente y enfocadas al ciudadano".', italics: true, size: 16 })
        ]
      })
    ]
  });

  const today = new Date();
  const day = today.getDate();
  const monthName = today.toLocaleDateString('es-ES', { month: 'long' });
  const yearStr = today.getFullYear();

  const [rYear, rMonth] = fechaReporte.split('-');
  const dateExtraccion = new Date(parseInt(rYear), parseInt(rMonth), 1);
  const actMonthName = dateExtraccion.toLocaleDateString('es-ES', { month: 'long' });
  const actYear = dateExtraccion.getFullYear();
  const actaDateStr = `01 de ${actMonthName} de ${actYear}`;

  const allChildren = [];

  for (let i = 0; i < reporte.length; i++) {
    const empresa = reporte[i];
    if (!empresa.infracciones || empresa.infracciones.length === 0) continue;

    const articulosSet = new Set();
    empresa.infracciones.forEach(inf => articulosSet.add(inf.base || 'Art. 15.6'));
    const articulosStr = Array.from(articulosSet).join(', ');

    const summaryMap = {};
    empresa.infracciones.forEach(inf => {
      const base = inf.base || 'Art. 15.6';
      if (!summaryMap[base]) summaryMap[base] = 0;
      summaryMap[base]++;
    });

    const children = [
      new Paragraph({
        text: `Asunción, ${day} de ${monthName} de ${yearStr}.`,
        alignment: AlignmentType.RIGHT,
        spacing: { after: 200 }
      }),
      new Paragraph({
        children: [new TextRun({ text: "NOTIFICACIÓN DMT N° ___/2026", bold: true })],
        alignment: AlignmentType.CENTER,
        spacing: { after: 400 }
      }),
      new Paragraph({ children: [new TextRun({ text: "SEÑORES", bold: true })] }),
      new Paragraph({
        children: [new TextRun({ text: `EMPRESA OPERADORA DE TRANSPORTE ${empresa.eot_nombre}`, bold: true })]
      }),
      new Paragraph({ children: [new TextRun({ text: "PRESENTE", bold: true })], spacing: { after: 400 } }),
      new Paragraph({
        children: [new TextRun({ text: "El Gabinete del Viceministro de Transporte, por intermedio de la Dirección Metropolitana de Transporte, realiza la notificación de infracción en cumplimiento a lo establecido en la Resolución GVMT N° 120/2025 y su modificatoria N° 21/2026." })],
        spacing: { after: 400 },
        alignment: AlignmentType.JUSTIFIED
      }),
      new Paragraph({
        children: [
          new TextRun({ text: "ACTA CID N°: ", bold: true }),
          new TextRun({ text: "___/2026" })
        ]
      }),
      new Paragraph({
        children: [
          new TextRun({ text: "FECHA DEL ACTA: ", bold: true }),
          new TextRun({ text: actaDateStr })
        ]
      }),
      new Paragraph({
        children: [
          new TextRun({ text: "EMPRESA: ", bold: true }),
          new TextRun({ text: `EMPRESA OPERADORA DE TRANSPORTE ${empresa.eot_nombre}` })
        ]
      }),
      new Paragraph({
        children: [
          new TextRun({ text: "ARTÍCULOS INFRACCIONADOS: ", bold: true }),
          new TextRun({ text: articulosStr })
        ],
        spacing: { after: 400 }
      }),

      new Paragraph({ children: [new TextRun({ text: "INFRACCIONES DETECTADAS", bold: true })], alignment: AlignmentType.CENTER, spacing: { after: 200 } }),
      
      new Table({
        width: { size: 100, type: WidthType.PERCENTAGE },
        rows: [
          new TableRow({
            children: [
              new TableCell({ children: [new Paragraph({ children: [new TextRun({ text: "FECHA", bold: true })] })] }),
              new TableCell({ children: [new Paragraph({ children: [new TextRun({ text: "INFRACCIÓN", bold: true })] })] }),
              new TableCell({ children: [new Paragraph({ children: [new TextRun({ text: "DESCRIPCIÓN", bold: true })] })] }),
            ],
            tableHeader: true
          }),
          ...empresa.infracciones.map(inf => new TableRow({
            children: [
              new TableCell({ children: [new Paragraph({ text: inf.fecha })] }),
              new TableCell({ children: [new Paragraph({ text: inf.base || 'Art. 15.6' })] }),
              new TableCell({ children: [new Paragraph({ text: inf.desc })] }),
            ]
          }))
        ]
      }),

      new Paragraph({ text: "", spacing: { after: 400 } }),
      new Paragraph({ children: [new TextRun({ text: "RESUMEN DE INFRACCIONES", bold: true })], alignment: AlignmentType.CENTER, spacing: { after: 200 } }),

      new Table({
        width: { size: 100, type: WidthType.PERCENTAGE },
        rows: [
          new TableRow({
            children: [
              new TableCell({ children: [new Paragraph({ children: [new TextRun({ text: "ARTÍCULO", bold: true })] })] }),
              new TableCell({ children: [new Paragraph({ children: [new TextRun({ text: "CANTIDAD", bold: true })] })] }),
              new TableCell({ children: [new Paragraph({ children: [new TextRun({ text: "ESCALA", bold: true })] })] }),
            ],
            tableHeader: true
          }),
          ...Object.keys(summaryMap).map(key => new TableRow({
            children: [
              new TableCell({ children: [new Paragraph({ text: key })] }),
              new TableCell({ children: [new Paragraph({ text: summaryMap[key].toString() })] }),
              new TableCell({ children: [new Paragraph({ text: "Intermedia" })] }),
            ]
          }))
        ]
      }),
      
      new Paragraph({ text: "", spacing: { after: 400 } }),
      new Paragraph({
        children: [new TextRun({ text: "Que, en la fecha registrada se ha constatado la infracción descrita, de conformidad con la Resolución GVMT N° 120/2025 y su modificatoria N° 21/2026. De acuerdo al Artículo 9° de la Resolución GVMT N° 07/2024, la empresa operadora de transporte deberá abonar al Viceministerio de Transporte dentro de los cinco (5) días hábiles, a partir de la presente notificación." })],
        alignment: AlignmentType.JUSTIFIED,
        spacing: { after: 200 }
      }),
      new Paragraph({ children: [new TextRun({ text: "Queda usted debidamente notificado." })], spacing: { after: 1500 } }),

      new Paragraph({ text: "____________________________________", alignment: AlignmentType.CENTER }),
      new Paragraph({ children: [new TextRun({ text: "ING. ROLANDO GONZÁLEZ", bold: true })], alignment: AlignmentType.CENTER }),
      new Paragraph({ children: [new TextRun({ text: "DIRECTOR METROPOLITANO DE TRANSPORTE", bold: true })], alignment: AlignmentType.CENTER }),
      new Paragraph({ children: [new TextRun({ text: "VICEMINISTERIO DE TRANSPORTE - MOPC", bold: true })], alignment: AlignmentType.CENTER })
    ];

    allChildren.push(...children);
    if (i < reporte.length - 1) {
      allChildren.push(new Paragraph({ children: [new PageBreak()] }));
    }
  }

  if (allChildren.length === 0) {
    alert("No hay empresas con infracciones para generar notificaciones.");
    return;
  }

  const doc = new Document({
    sections: [{
      properties: {
        page: {
          margin: { top: 1500, bottom: 1500, right: 1000, left: 1000 }
        }
      },
      headers: { default: docHeader },
      footers: { default: docFooter },
      children: allChildren
    }]
  });

  const blob = await Packer.toBlob(doc);
  saveAs(blob, `Notificaciones_DMT_${fechaReporte}.docx`);
};
