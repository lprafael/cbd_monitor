/**
 * generateGeneralReportExcel.js
 * Genera un reporte Excel (.xls) con el listado de todas las EOTs,
 * días analizados, ICCBDM mensual y estado de subsidio.
 * Usa SpreadsheetML (XML nativo de Excel) sin dependencias adicionales.
 */

const getMonthName = (monthNumber) => {
  const months = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
  ];
  return months[monthNumber - 1] || "";
};

/**
 * Escapa caracteres especiales XML
 */
const escXml = (val) =>
  String(val ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");

/**
 * Genera una celda de encabezado (negrita, fondo azul oscuro, texto blanco)
 */
const headerCell = (value, colSpan = 1) => {
  const merge = colSpan > 1 ? ` ss:MergeAcross="${colSpan - 1}"` : "";
  return `<Cell${merge} ss:StyleID="sHeader"><Data ss:Type="String">${escXml(value)}</Data></Cell>`;
};

/**
 * Celda de título principal (fusionada, centrada, negrita grande)
 */
const titleCell = (value, colSpan = 1) => {
  const merge = colSpan > 1 ? ` ss:MergeAcross="${colSpan - 1}"` : "";
  return `<Cell${merge} ss:StyleID="sTitle"><Data ss:Type="String">${escXml(value)}</Data></Cell>`;
};

/**
 * Celda de subtítulo (fusionada, centrada, itálica)
 */
const subtitleCell = (value, colSpan = 1) => {
  const merge = colSpan > 1 ? ` ss:MergeAcross="${colSpan - 1}"` : "";
  return `<Cell${merge} ss:StyleID="sSubtitle"><Data ss:Type="String">${escXml(value)}</Data></Cell>`;
};

/**
 * Celda de dato normal (centrada)
 */
const dataCell = (value, type = "String", styleId = "sData") =>
  `<Cell ss:StyleID="${styleId}"><Data ss:Type="${type}">${escXml(value)}</Data></Cell>`;

/**
 * Celda de dato numérico
 */
const numCell = (value) =>
  `<Cell ss:StyleID="sDataNum"><Data ss:Type="Number">${escXml(value)}</Data></Cell>`;

/**
 * Celda de estado CUMPLE / NO CUMPLE con color
 */
const statusCell = (cumple) => {
  const style = cumple ? "sCumple" : "sNoCumple";
  const text = cumple ? "CUMPLE" : "NO CUMPLE";
  return `<Cell ss:StyleID="${style}"><Data ss:Type="String">${text}</Data></Cell>`;
};

/**
 * Celda de nombre de empresa (alineación izquierda)
 */
const nameCell = (value) =>
  `<Cell ss:StyleID="sName"><Data ss:Type="String">${escXml(value)}</Data></Cell>`;

/**
 * Fila vacía
 */
const emptyRow = (colCount = 5) => {
  const cells = Array(colCount).fill(`<Cell ss:StyleID="sData"><Data ss:Type="String"></Data></Cell>`).join("");
  return `<Row ss:Height="6">${cells}</Row>`;
};

export const generateGeneralReportExcel = ({ data, year, month }) => {
  const mesNombre = getMonthName(month);
  const periodo = `${mesNombre.toUpperCase()} ${year}`;
  const totalCols = 5; // #, Empresa, Días Analizados, ICCBDM Mensual, Estado

  // Ordenar EOTs: primero las que cumplen, luego las que no, y dentro de cada grupo por ICCBDM desc
  const eotsOrdenadas = [...data.eots].sort((a, b) => {
    const aCumple = a.cumple_subsidio !== undefined ? a.cumple_subsidio : a.iccbdm_mensual >= 95;
    const bCumple = b.cumple_subsidio !== undefined ? b.cumple_subsidio : b.iccbdm_mensual >= 95;
    if (aCumple !== bCumple) return bCumple ? 1 : -1;
    return b.iccbdm_mensual - a.iccbdm_mensual;
  });

  // Construir filas de datos
  const dataRows = eotsOrdenadas.map((eot, idx) => {
    const cumple = eot.cumple_subsidio !== undefined
      ? eot.cumple_subsidio
      : (eot.estado_color !== "red" && eot.iccbdm_mensual >= 95.0);
    const iccbdm = typeof eot.iccbdm_mensual === "number"
      ? eot.iccbdm_mensual
      : parseFloat(eot.iccbdm_mensual || 0);

    return `<Row ss:Height="18">
      ${dataCell(idx + 1, "Number", "sDataNumCenter")}
      ${nameCell(eot.eot_nombre)}
      ${dataCell(eot.dias_validos ?? "-", "String", "sDataCenter")}
      ${dataCell(iccbdm.toFixed(2) + " %", "String", "sDataCenter")}
      ${statusCell(cumple)}
    </Row>`;
  }).join("\n");

  // Resumen
  const promedioSistema = typeof data.promedio_sistema === "number"
    ? data.promedio_sistema.toFixed(2)
    : parseFloat(data.promedio_sistema || 0).toFixed(2);

  const xml = `<?xml version="1.0" encoding="UTF-8"?>
<?mso-application progid="Excel.Sheet"?>
<Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet"
  xmlns:o="urn:schemas-microsoft-com:office:office"
  xmlns:x="urn:schemas-microsoft-com:office:excel"
  xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet"
  xmlns:html="http://www.w3.org/TR/REC-html40">
  <DocumentProperties xmlns="urn:schemas-microsoft-com:office:office">
    <Title>Reporte General ICCBDM - ${escXml(periodo)}</Title>
    <Author>Coordinación de Innovación y Desarrollo - VMT MOPC</Author>
  </DocumentProperties>
  <Styles>
    <!-- Título principal -->
    <Style ss:ID="sTitle">
      <Alignment ss:Horizontal="Center" ss:Vertical="Center" ss:WrapText="1"/>
      <Font ss:FontName="Tahoma" ss:Size="14" ss:Bold="1" ss:Color="#1E3A5F"/>
      <Interior ss:Color="#FFFFFF" ss:Pattern="Solid"/>
      <Borders>
        <Border ss:Position="Bottom" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#1E3A5F"/>
      </Borders>
    </Style>
    <!-- Subtítulo -->
    <Style ss:ID="sSubtitle">
      <Alignment ss:Horizontal="Center" ss:Vertical="Center"/>
      <Font ss:FontName="Tahoma" ss:Size="10" ss:Italic="1" ss:Color="#555555"/>
      <Interior ss:Color="#FFFFFF" ss:Pattern="Solid"/>
    </Style>
    <!-- Encabezado de columna -->
    <Style ss:ID="sHeader">
      <Alignment ss:Horizontal="Center" ss:Vertical="Center" ss:WrapText="1"/>
      <Font ss:FontName="Tahoma" ss:Size="10" ss:Bold="1" ss:Color="#FFFFFF"/>
      <Interior ss:Color="#1E3A5F" ss:Pattern="Solid"/>
      <Borders>
        <Border ss:Position="Top" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#FFFFFF"/>
        <Border ss:Position="Bottom" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#FFFFFF"/>
        <Border ss:Position="Left" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#FFFFFF"/>
        <Border ss:Position="Right" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#FFFFFF"/>
      </Borders>
    </Style>
    <!-- Dato genérico centrado -->
    <Style ss:ID="sData">
      <Alignment ss:Horizontal="Center" ss:Vertical="Center"/>
      <Font ss:FontName="Tahoma" ss:Size="10"/>
      <Borders>
        <Border ss:Position="Top" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#000000"/>
        <Border ss:Position="Bottom" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#000000"/>
        <Border ss:Position="Left" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#000000"/>
        <Border ss:Position="Right" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#000000"/>
      </Borders>
    </Style>
    <!-- Dato centrado (alias) -->
    <Style ss:ID="sDataCenter">
      <Alignment ss:Horizontal="Center" ss:Vertical="Center"/>
      <Font ss:FontName="Tahoma" ss:Size="10"/>
      <Borders>
        <Border ss:Position="Top" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#000000"/>
        <Border ss:Position="Bottom" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#000000"/>
        <Border ss:Position="Left" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#000000"/>
        <Border ss:Position="Right" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#000000"/>
      </Borders>
    </Style>
    <!-- Número centrado -->
    <Style ss:ID="sDataNum">
      <Alignment ss:Horizontal="Center" ss:Vertical="Center"/>
      <Font ss:FontName="Tahoma" ss:Size="10"/>
      <NumberFormat ss:Format="General"/>
      <Borders>
        <Border ss:Position="Top" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#000000"/>
        <Border ss:Position="Bottom" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#000000"/>
        <Border ss:Position="Left" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#000000"/>
        <Border ss:Position="Right" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#000000"/>
      </Borders>
    </Style>
    <!-- Número centrado (alias) -->
    <Style ss:ID="sDataNumCenter">
      <Alignment ss:Horizontal="Center" ss:Vertical="Center"/>
      <Font ss:FontName="Tahoma" ss:Size="10"/>
      <Borders>
        <Border ss:Position="Top" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#000000"/>
        <Border ss:Position="Bottom" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#000000"/>
        <Border ss:Position="Left" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#000000"/>
        <Border ss:Position="Right" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#000000"/>
      </Borders>
    </Style>
    <!-- Nombre de empresa (izquierda) -->
    <Style ss:ID="sName">
      <Alignment ss:Horizontal="Left" ss:Vertical="Center" ss:Indent="1"/>
      <Font ss:FontName="Tahoma" ss:Size="10"/>
      <Borders>
        <Border ss:Position="Top" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#000000"/>
        <Border ss:Position="Bottom" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#000000"/>
        <Border ss:Position="Left" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#000000"/>
        <Border ss:Position="Right" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#000000"/>
      </Borders>
    </Style>
    <!-- CUMPLE -->
    <Style ss:ID="sCumple">
      <Alignment ss:Horizontal="Center" ss:Vertical="Center"/>
      <Font ss:FontName="Tahoma" ss:Size="10" ss:Bold="1" ss:Color="#155724"/>
      <Interior ss:Color="#D4EDDA" ss:Pattern="Solid"/>
      <Borders>
        <Border ss:Position="Top" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#000000"/>
        <Border ss:Position="Bottom" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#000000"/>
        <Border ss:Position="Left" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#000000"/>
        <Border ss:Position="Right" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#000000"/>
      </Borders>
    </Style>
    <!-- NO CUMPLE -->
    <Style ss:ID="sNoCumple">
      <Alignment ss:Horizontal="Center" ss:Vertical="Center"/>
      <Font ss:FontName="Tahoma" ss:Size="10" ss:Bold="1" ss:Color="#721C24"/>
      <Interior ss:Color="#F8D7DA" ss:Pattern="Solid"/>
      <Borders>
        <Border ss:Position="Top" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#000000"/>
        <Border ss:Position="Bottom" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#000000"/>
        <Border ss:Position="Left" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#000000"/>
        <Border ss:Position="Right" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#000000"/>
      </Borders>
    </Style>
    <!-- Resumen -->
    <Style ss:ID="sResumen">
      <Alignment ss:Horizontal="Left" ss:Vertical="Center" ss:Indent="1"/>
      <Font ss:FontName="Tahoma" ss:Size="10" ss:Bold="1"/>
      <Interior ss:Color="#EEF2F7" ss:Pattern="Solid"/>
      <Borders>
        <Border ss:Position="Top" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#1E3A5F"/>
        <Border ss:Position="Bottom" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#1E3A5F"/>
        <Border ss:Position="Left" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#1E3A5F"/>
        <Border ss:Position="Right" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#1E3A5F"/>
      </Borders>
    </Style>
    <!-- Nota al pie -->
    <Style ss:ID="sFootnote">
      <Alignment ss:Horizontal="Left" ss:Vertical="Center" ss:Indent="1"/>
      <Font ss:FontName="Tahoma" ss:Size="9" ss:Italic="1" ss:Color="#666666"/>
      <Interior ss:Color="#FFFFFF" ss:Pattern="Solid"/>
    </Style>
  </Styles>
  <Worksheet ss:Name="Reporte ICCBDM">
    <Table ss:DefaultColumnWidth="80">
      <!-- Anchos de columna -->
      <Column ss:Width="35"/>
      <Column ss:Width="230"/>
      <Column ss:Width="100"/>
      <Column ss:Width="110"/>
      <Column ss:Width="100"/>

      <!-- Fila 1: Encabezado institucional (título) -->
      <Row ss:Height="40">
        ${titleCell("MINISTERIO DE OBRAS PÚBLICAS Y COMUNICACIONES | VICEMINISTERIO DE TRANSPORTE", totalCols)}
      </Row>
      <!-- Fila 2: Coordinación -->
      <Row ss:Height="20">
        ${subtitleCell("Coordinación de Innovación y Desarrollo (CID) — Sistema de Monitoreo CBD", totalCols)}
      </Row>
      <!-- Fila 3: Vacía separadora -->
      ${emptyRow(totalCols)}
      <!-- Fila 4: Título del reporte -->
      <Row ss:Height="30">
        ${titleCell(`REPORTE GENERAL DE HABILITACIÓN AL SUBSIDIO — ${periodo}`, totalCols)}
      </Row>
      <!-- Fila 5: Umbral -->
      <Row ss:Height="18">
        ${subtitleCell("Umbral mínimo de habilitación: ICCBDM Mensual ≥ 95,00 %   |   Res. GVMT N° 120/2025", totalCols)}
      </Row>
      <!-- Fila 6: Vacía separadora -->
      ${emptyRow(totalCols)}
      <!-- Fila 7: Encabezados de columna -->
      <Row ss:Height="30">
        ${headerCell("#")}
        ${headerCell("EMPRESA OPERADORA DE TRANSPORTE (EOT)")}
        ${headerCell("DÍAS ANALIZADOS")}
        ${headerCell("ICCBDM MENSUAL")}
        ${headerCell("ESTADO SUBSIDIO")}
      </Row>

      <!-- Filas de datos -->
      ${dataRows}

      <!-- Fila vacía separadora -->
      ${emptyRow(totalCols)}

      <!-- Fila de resumen -->
      <Row ss:Height="20">
        <Cell ss:MergeAcross="1" ss:StyleID="sResumen"><Data ss:Type="String">RESUMEN DEL SISTEMA</Data></Cell>
        <Cell ss:StyleID="sResumen"><Data ss:Type="String">Total EOTs: ${data.total_eots ?? eotsOrdenadas.length}</Data></Cell>
        <Cell ss:StyleID="sResumen"><Data ss:Type="String">Promedio: ${promedioSistema} %</Data></Cell>
        <Cell ss:StyleID="sResumen"><Data ss:Type="String">Cumplen: ${data.eots_cumplen_100 + data.eots_cumplen_95} / ${data.total_eots ?? eotsOrdenadas.length}</Data></Cell>
      </Row>
      <!-- Fila detalle resumen -->
      <Row ss:Height="18">
        <Cell ss:MergeAcross="${totalCols - 1}" ss:StyleID="sFootnote">
          <Data ss:Type="String">  100%: ${data.eots_cumplen_100} empresas   |   95%-99.9%: ${data.eots_cumplen_95} empresas   |   &lt; 95% (No habilitan): ${data.eots_bajo_95} empresas</Data>
        </Cell>
      </Row>
      <!-- Fila vacía -->
      ${emptyRow(totalCols)}
      <!-- Nota al pie -->
      <Row ss:Height="15">
        <Cell ss:MergeAcross="${totalCols - 1}" ss:StyleID="sFootnote">
          <Data ss:Type="String">  Generado por: CID — Sistema CBD Monitor | Fecha de generación: ${new Date().toLocaleDateString("es-PY", { day: "2-digit", month: "long", year: "numeric" })}</Data>
        </Cell>
      </Row>
      <Row ss:Height="15">
        <Cell ss:MergeAcross="${totalCols - 1}" ss:StyleID="sFootnote">
          <Data ss:Type="String">  Fuente: Central de Control y Monitoreo del Billetaje Electrónico (CCM) — Ley N° 5230/2014</Data>
        </Cell>
      </Row>
    </Table>
    <WorksheetOptions xmlns="urn:schemas-microsoft-com:office:excel">
      <PageSetup>
        <Layout x:Orientation="Landscape"/>
        <PageMargins x:Bottom="0.75" x:Left="0.75" x:Right="0.75" x:Top="0.75"/>
      </PageSetup>
      <FitToPage/>
      <Print>
        <FitWidth>1</FitWidth>
        <FitHeight>0</FitHeight>
      </Print>
      <FreezePanes/>
      <SplitHorizontal>7</SplitHorizontal>
      <TopRowBottomPane>7</TopRowBottomPane>
      <ActivePane>2</ActivePane>
    </WorksheetOptions>
  </Worksheet>
</Workbook>`;

  // Descargar el archivo
  const blob = new Blob([xml], {
    type: "application/vnd.ms-excel;charset=utf-8"
  });

  const cleanPeriod = `${mesNombre}_${year}`;
  const fileName = `Reporte_ICCBDM_${cleanPeriod}.xls`;

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
