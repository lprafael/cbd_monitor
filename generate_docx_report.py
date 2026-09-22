import docx
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import parse_xml, OxmlElement
from docx.oxml.ns import nsdecls, qn

def create_report():
    doc = Document()

    # Configure Margins (Normal: 1 inch = 2.54 cm)
    for section in doc.sections:
        section.top_margin = Inches(0.8)
        section.bottom_margin = Inches(0.8)
        section.left_margin = Inches(0.9)
        section.right_margin = Inches(0.9)

    # Helper colors
    c_navy = RGBColor(15, 43, 92)
    c_dark = RGBColor(15, 23, 42)
    c_gray = RGBColor(100, 116, 139)
    c_black = RGBColor(30, 41, 59)

    # ------------------ ENCABEZADO INSTITUCIONAL ------------------
    header_p1 = doc.add_paragraph()
    header_p1.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r1 = header_p1.add_run("GOBIERNO DEL PARAGUAY\nMINISTERIO DE OBRAS PÚBLICAS Y COMUNICACIONES\nVICEMINISTERIO DE TRANSPORTE")
    r1.font.name = "Arial"
    r1.font.size = Pt(11)
    r1.font.bold = True
    r1.font.color.rgb = c_navy

    header_p2 = doc.add_paragraph()
    header_p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r2 = header_p2.add_run("DIRECCIÓN METROPOLITANA DE TRANSPORTE\nCOORDINACIÓN DE INNOVACIÓN Y DESARROLLO (CID)")
    r2.font.name = "Arial"
    r2.font.size = Pt(10)
    r2.font.bold = True
    r2.font.color.rgb = c_dark

    p_line = doc.add_paragraph()
    p_line.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_line = p_line.add_run("―" * 45)
    r_line.font.color.rgb = RGBColor(194, 65, 12)
    r_line.font.bold = True

    # Metadatos del Documento
    p_meta = doc.add_paragraph()
    p_meta.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r_meta = p_meta.add_run("DICTAMEN TÉCNICO N°: CID-DMT-IT-024/2026\nFecha de Emisión: 22 de septiembre de 2026")
    r_meta.font.name = "Arial"
    r_meta.font.size = Pt(9.5)
    r_meta.font.bold = True
    r_meta.font.color.rgb = c_gray

    # Título Principal
    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_title.paragraph_format.space_before = Pt(10)
    p_title.paragraph_format.space_after = Pt(4)
    r_title = p_title.add_run("INFORME TÉCNICO DE IMPLEMENTACIÓN Y VALIDACIÓN DE SOFTWARE")
    r_title.font.name = "Arial"
    r_title.font.size = Pt(15)
    r_title.font.bold = True
    r_title.font.color.rgb = c_navy

    p_sub = doc.add_paragraph()
    p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_sub.paragraph_format.space_after = Pt(16)
    r_sub = p_sub.add_run("ADECUACIÓN DEL MOTOR DE REGLAS SANCIONATORIAS DEL SICOM CONFORME A LA RESOLUCIÓN GVMT N° 104/2026")
    r_sub.font.name = "Arial"
    r_sub.font.size = Pt(11)
    r_sub.font.bold = True
    r_sub.font.color.rgb = RGBColor(194, 65, 12)

    # ------------------ TABLA SUMARIO EJECUTIVO ------------------
    sum_table = doc.add_table(rows=6, cols=2)
    sum_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    sum_table.autofit = False

    data_sum = [
        ("Norma de Referencia:", "Resolución GVMT N° 104/2026 (Extensión de Etapa 2 y Lineamientos Técnicos)."),
        ("Marco Jurídico Garantista:", "Ley N° 6715/2021 (Art. 74 - Proporcionalidad y Non Bis In Idem). Dictámenes C.J. N° 357 y 415/2026."),
        ("Módulo de Software Intervenido:", "Motor de Sanciones SICOM: backend/routes/fines_report.py (Endpoint /api/fines-report)."),
        ("Suite de Validación y Pruebas:", "test_exclusion_logic.py (8 escenarios unitarios automatizados)."),
        ("Alcance Temporal de Aplicación:", "Operativa de JULIO/2026 en adelante y Actas de Comprobación pendientes."),
        ("Resultado de la Certificación:", "HOMOLOGADO (100% de asertividad - 8/8 pruebas unitarias superadas con éxito).")
    ]

    for i, (label, val) in enumerate(data_sum):
        row = sum_table.rows[i]
        c0, c1 = row.cells[0], row.cells[1]
        c0.width = Inches(2.2)
        c1.width = Inches(4.5)
        
        # Shading
        shd0 = parse_xml(f'<w:shd {nsdecls("w")} w:fill="F1F5F9"/>')
        shd1 = parse_xml(f'<w:shd {nsdecls("w")} w:fill="FFFFFF"/>')
        c0._tc.get_or_add_tcPr().append(shd0)
        c1._tc.get_or_add_tcPr().append(shd1)
        
        p0 = c0.paragraphs[0]
        p0.paragraph_format.space_before = Pt(3)
        p0.paragraph_format.space_after = Pt(3)
        r0 = p0.add_run(label)
        r0.font.name = "Arial"
        r0.font.size = Pt(9.5)
        r0.font.bold = True
        r0.font.color.rgb = c_navy

        p1 = c1.paragraphs[0]
        p1.paragraph_format.space_before = Pt(3)
        p1.paragraph_format.space_after = Pt(3)
        r1 = p1.add_run(val)
        r1.font.name = "Arial"
        r1.font.size = Pt(9.5)
        if i == 5:
            r1.font.bold = True
            r1.font.color.rgb = RGBColor(5, 150, 105)
        else:
            r1.font.color.rgb = c_black

    doc.add_paragraph().paragraph_format.space_before = Pt(10)

    # ------------------ SECCIONES DE CONTENIDO ------------------
    def add_sec_title(title_text):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(14)
        p.paragraph_format.space_after = Pt(4)
        r = p.add_run(title_text)
        r.font.name = "Arial"
        r.font.size = Pt(12)
        r.font.bold = True
        r.font.color.rgb = c_navy

    # 1. ANTECEDENTES Y MANDATO
    add_sec_title("1. ANTECEDENTES Y MANDATO DE LA RESOLUCIÓN GVMT N° 104/2026")
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(6)
    p.paragraph_format.line_spacing = 1.15
    r = p.add_run(
        "El régimen de control operativo implementado por el Viceministerio de Transporte (GVMT) mediante la Resolución "
        "GVMT N° 120/2025 y sus modificatorias (Res. N° 21/2026 y N° 26/2026) estableció la evaluación del desempeño mediante "
        "el Índice de Flota Operativa (IFO) y la Cantidad Mínima de Buses Diferentes (CBDmín). Cumplidos los tres meses de la "
        "Etapa 2 de implementación parcial iniciada el 19 de mayo de 2026, la Dirección Metropolitana de Transporte (DMT) y la "
        "Coordinación de Innovación y Desarrollo (CID) diagnosticaron la existencia de superposiciones conceptuales entre faltas "
        "diarias e infracciones acumuladas mensuales, comprometiendo el principio constitucional y administrativo de Non Bis In Idem "
        "(Art. 74, Ley N° 6715/2021).\n\n"
        "Ante este informe técnico y el dictamen concordante de la Coordinación Jurídica (C.J. N° 357/2026 y N° 415/2026), la máxima "
        "autoridad dictó la Resolución GVMT N° 104/2026, extendiendo la Etapa 2 y aprobando formalmente cuatro reglas de consolidación "
        "automatizada. Sus Artículos 4° y 7° instruyen expresamente a la CID a parametrizar, reprogramar y validar el motor de reglas "
        "del SICOM, disponiendo la elevación del presente dictamen formal previo a la emisión de las Actas de Comprobación correspondientes "
        "a la operativa de JULIO/2026 en adelante."
    )
    r.font.name = "Arial"
    r.font.size = Pt(10)
    r.font.color.rgb = c_black

    # 2. DIAGNÓSTICO DEL SISTEMA PREVIO
    add_sec_title("2. DIAGNÓSTICO TÉCNICO Y HALLAZGOS EN EL MOTOR PREVIO DE REGLAS")
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(6)
    p.paragraph_format.line_spacing = 1.15
    r = p.add_run(
        "La revisión técnica exhaustiva del módulo backend/routes/fines_report.py reveló dos inconsistencias algorítmicas fundamentales:\n\n"
        "a) Superposición Sancionatoria en Nivel C y Nivel B: Previamente, una empresa que registraba IFO < 80% en franja pico y pos pico "
        "de un mismo día recibía dos multas independientes (20 + 20 = 40 jornales). Asimismo, eventos con IFO deficitario eran imputados "
        "tanto como falta grave en el día como componente de la acumulación mensual de 5 franjas (Nivel B).\n\n"
        "b) Desvío Algorítmico en el Cálculo de IFO Mensual (Regla 4): En el código preexistente de la rama non_bis_in_idem, el sistema excluía "
        "indebidamente los días que ya habían recibido sanción por Nivel B o Nivel C:\n"
        "    dias_excluidos_15_1 = dias_sancionados_c.union(dias_sancionados_b)\n"
        "    if fecha_eval in dias_excluidos_15_1: continue\n\n"
        "Impacto Crítico: Al omitir los días sancionados (que eran precisamente aquellos con peor desempeño operativo), el promedio mensual "
        "del IFO se calculaba únicamente sobre las jornadas normales, inflando artificialmente el porcentaje mensual de cumplimiento y "
        "exonerando erróneamente a empresas infractoras de la sanción gravísima de 173 jornales (Art. 15.1). Esto contradecía flagrantemente "
        "la Regla N° 4 de la Res. 104/2026, la cual exige expresamente computar la totalidad de jornadas evaluables del mes."
    )
    r.font.name = "Arial"
    r.font.size = Pt(10)
    r.font.color.rgb = c_black

    # 3. DETALLE DE LAS MODIFICACIONES INTRODUCIDAS
    add_sec_title("3. DETALLE DE LAS MODIFICACIONES ALGORÍTMICAS INTRODUCIDAS")
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(6)
    p.paragraph_format.line_spacing = 1.15
    r = p.add_run(
        "Se procedió a la refactorización integral del backend de cálculo de infracciones conforme a las cuatro reglas aprobadas:\n\n"
        "• REGLA N° 1 (Sanción Única Diaria por Nivel C - Arts. 15.3 y 15.5): Si en una misma fecha calendario una empresa incumple Nivel C "
        "en Pico y en Pos Pico, el motor genera una única sanción diaria unificada de 20 jornales mínimos (Gs. 2.230.040) bajo la causal "
        "'Art. 15.3 / 15.5'.\n\n"
        "• REGLA N° 2 (Absorción Mensual de Nivel B ante Nivel C - Arts. 15.2 y 15.4): Cuando en el mes se verifique al menos una (1) sanción "
        "diaria por Nivel C, queda bloqueada y extinguida toda sanción por acumulación mensual de Nivel B, absorbiéndose las faltas menores en la más grave.\n\n"
        "• REGLA N° 3 (Acumulación Separada y Multa Unificada Nivel B): En meses con cero (0) Nivel C, las acumulaciones de 5 franjas se evalúan de forma "
        "estrictamente independiente para picos y pos picos. Si ambos acumulan >= 5 franjas, se emite una sola multa unificada de 10 jornales "
        "(Gs. 1.115.020) bajo 'Art. 15.2 / 15.4'.\n\n"
        "• REGLA N° 4 (Cómputo Integral de IFO Mensual - Art. 15.1): Se eliminó completamente la exclusión de jornadas con sanciones previas. El IFO Mensual "
        "promedia todas las jornadas hábiles evaluables del mes (con tope de consistencia de 110%). Se mantienen taxativamente solo las exclusiones legales: "
        "domingos, feriados oficiales y días atípicos por precipitación > 5 mm informados por DINAC.\n\n"
        "• Autonomía del Art. 15.6 (ICCBDM Buses Mínimos): Se verifica de forma diaria y autónoma, sin absorberse ni absorber el IFO."
    )
    r.font.name = "Arial"
    r.font.size = Pt(10)
    r.font.color.rgb = c_black

    # 4. PRUEBAS UNITARIAS
    add_sec_title("4. MATRIZ DE CERTIFICACIÓN Y PRUEBAS UNITARIAS (test_exclusion_logic.py)")
    
    t_tests = doc.add_table(rows=9, cols=5)
    t_tests.alignment = WD_TABLE_ALIGNMENT.CENTER
    t_tests.autofit = False

    headers_test = ["Escenario", "Regla / Artículo", "Comportamiento Evaluado", "Resultado de Sanción", "Estado"]
    widths_test = [Inches(1.0), Inches(1.3), Inches(2.2), Inches(1.5), Inches(0.8)]

    for j, h in enumerate(headers_test):
        cell = t_tests.rows[0].cells[j]
        cell.width = widths_test[j]
        shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="0F172A"/>')
        cell._tc.get_or_add_tcPr().append(shd)
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(h)
        r.font.name = "Arial"
        r.font.size = Pt(8.5)
        r.font.bold = True
        r.font.color.rgb = RGBColor(255, 255, 255)

    test_rows = [
        ("Escenario 1", "Regla 1 (15.3/15.5)", "IFO < 80% en Pico y Pos Pico mismo día.", "1 sola sanción de 20 jornales", "APROBADO"),
        ("Escenario 2", "Regla 2 (Absorción B)", "Día 1 con Nivel C + 5 franjas B en el mes.", "15.3 (20j). Nivel B anulado (0j)", "APROBADO"),
        ("Escenario 3a", "Regla 3 (Tolerancia)", "Mes sin C: 4 franjas B Pico y 4 B Pos Pico.", "Cero multas (Tolerancia cumplida)", "APROBADO"),
        ("Escenario 3b", "Regla 3 (Unificación B)", "Mes sin C: 5 franjas B Pico y 5 B Pos Pico.", "1 multa unificada de 10 jornales", "APROBADO"),
        ("Escenario 4", "Art. 15.6 (ICCBDM)", "IFO cumple (95%), Buses Mínimos deficitario.", "Multa de 20j autónoma por 15.6", "APROBADO"),
        ("Escenario 5", "Regla 4 (IFO Mensual)", "Día con Nivel C computado en el IFO mensual.", "Aplica 15.3 (20j) Y 15.1 (173j)", "APROBADO"),
        ("Escenario 6", "Desdoblamiento 15.1", "Pico mensual cumple (95%), Pos Pico bajo (82%).", "Aplica 173j solo en Pos Pico", "APROBADO"),
        ("Escenario 7", "Exclusiones Etapa 2", "Pos Pico sábado y Domingo evaluados.", "Descarte automático (0 multas)", "APROBADO"),
    ]

    for i, row_data in enumerate(test_rows):
        row = t_tests.rows[i+1]
        for j, val in enumerate(row_data):
            cell = row.cells[j]
            cell.width = widths_test[j]
            bg_col = "F8FAFC" if i % 2 == 1 else "FFFFFF"
            shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{bg_col}"/>')
            cell._tc.get_or_add_tcPr().append(shd)
            p = cell.paragraphs[0]
            p.paragraph_format.space_before = Pt(2)
            p.paragraph_format.space_after = Pt(2)
            if j == 4 or j == 0:
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            r = p.add_run(val)
            r.font.name = "Arial"
            r.font.size = Pt(8.5)
            if j == 4:
                r.font.bold = True
                r.font.color.rgb = RGBColor(5, 150, 105)
            elif j == 0:
                r.font.bold = True
                r.font.color.rgb = c_navy
            else:
                r.font.color.rgb = c_black

    # 5. TABLA SANCIONES CONCORDADAS
    add_sec_title("5. RÉGIMEN SANCIONATORIO CONCORDADO (Jornal Legal: Gs. 111.502)")
    t_sanc = doc.add_table(rows=8, cols=5)
    t_sanc.alignment = WD_TABLE_ALIGNMENT.CENTER
    t_sanc.autofit = False

    headers_sanc = ["Infracción", "Tipo / Gravedad", "Jornales", "Monto Liquidable (Gs.)", "Criterio Algorítmico Aplicado"]
    widths_sanc = [Inches(1.0), Inches(1.3), Inches(0.8), Inches(1.6), Inches(2.1)]

    for j, h in enumerate(headers_sanc):
        cell = t_sanc.rows[0].cells[j]
        cell.width = widths_sanc[j]
        shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="0F172A"/>')
        cell._tc.get_or_add_tcPr().append(shd)
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(h)
        r.font.name = "Arial"
        r.font.size = Pt(8.5)
        r.font.bold = True
        r.font.color.rgb = RGBColor(255, 255, 255)

    sanc_rows = [
        ("Art. 15.1", "Gravísima (IFO Mensual)", "173", "Gs. 19.289.846", "Regla 4: Muestra mensual íntegra."),
        ("Art. 15.2", "Leve (Acumulación B Pico)", "10", "Gs. 1.115.020", "Regla 2: Absorbido si hay C. Unificado con 15.4."),
        ("Art. 15.3", "Intermedia (Nivel C Pico)", "20", "Gs. 2.230.040", "Regla 1: Sanción única 20j si coincide con 15.5."),
        ("Art. 15.4", "Leve (Acumulación B Pos)", "10", "Gs. 1.115.020", "Regla 2: Absorbido si hay C. Unificado con 15.2."),
        ("Art. 15.5", "Intermedia (Nivel C Pos)", "20", "Gs. 2.230.040", "Regla 1: Sanción única 20j si coincide con 15.3."),
        ("Art. 15.6", "Intermedia (Buses Mín.)", "20", "Gs. 2.230.040", "Evaluación diaria autónoma e independiente."),
        ("Art. 16.1", "Reincidencia IFO Mensual", "224.9", "Gs. 25.076.800", "Recargo legal automático del 30% s/ 173 jornales.")
    ]

    for i, row_data in enumerate(sanc_rows):
        row = t_sanc.rows[i+1]
        for j, val in enumerate(row_data):
            cell = row.cells[j]
            cell.width = widths_sanc[j]
            bg_col = "F8FAFC" if i % 2 == 1 else "FFFFFF"
            shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{bg_col}"/>')
            cell._tc.get_or_add_tcPr().append(shd)
            p = cell.paragraphs[0]
            p.paragraph_format.space_before = Pt(2)
            p.paragraph_format.space_after = Pt(2)
            if j in [0, 2]:
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            elif j == 3:
                p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            r = p.add_run(val)
            r.font.name = "Arial"
            r.font.size = Pt(8.5)
            if j == 0:
                r.font.bold = True
                r.font.color.rgb = c_navy
            elif j == 3:
                r.font.bold = True
                r.font.color.rgb = c_black
            else:
                r.font.color.rgb = c_black

    # 6. CONCLUSIÓN Y DICTAMEN
    add_sec_title("6. CONCLUSIÓN TÉCNICA Y RECOMENDACIÓN FINAL")
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(24)
    p.paragraph_format.line_spacing = 1.15
    r = p.add_run(
        "1. Conforme a las verificaciones realizadas, la adecuación algorítmica del backend del SICOM cumple plenamente con los "
        "lineamientos de la Resolución GVMT N° 104/2026, blindando las sanciones de objeciones por doble juzgamiento (Non Bis In Idem).\n"
        "2. La corrección de la Regla 4 restablece la integridad del cálculo del IFO Mensual, asegurando que las deficiencias graves de flota "
        "computen en el promedio mensual sin distorsiones artificiales.\n"
        "3. Se certifica la aptitud operativa del sistema con el 100% de pruebas unitarias superadas.\n"
        "4. En virtud de los Arts. 4° y 7° de la Res. 104/2026, la Coordinación de Innovación y Desarrollo eleva el presente informe recomendando "
        "a la Dirección Metropolitana de Transporte autorizar el reprocesamiento informático de JULIO/2026 en adelante y dar curso a la emisión "
        "formal de las Actas de Comprobación."
    )
    r.font.name = "Arial"
    r.font.size = Pt(10)
    r.font.color.rgb = c_black

    # FIRMAS
    sig_table = doc.add_table(rows=1, cols=2)
    sig_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    sig_table.autofit = False
    sig_table.rows[0].cells[0].width = Inches(3.3)
    sig_table.rows[0].cells[1].width = Inches(3.3)

    p_sig1 = sig_table.rows[0].cells[0].paragraphs[0]
    p_sig1.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p_sig1.add_run("_________________________________________\nCOORDINACIÓN DE INNOVACIÓN Y DESARROLLO\nViceministerio de Transporte - MOPC")
    r.font.name = "Arial"
    r.font.size = Pt(9.5)
    r.font.bold = True
    r.font.color.rgb = c_navy

    p_sig2 = sig_table.rows[0].cells[1].paragraphs[0]
    p_sig2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p_sig2.add_run("_________________________________________\nDIRECCIÓN METROPOLITANA DE TRANSPORTE\nViceministerio de Transporte - MOPC")
    r.font.name = "Arial"
    r.font.size = Pt(9.5)
    r.font.bold = True
    r.font.color.rgb = c_navy

    output_path = r"c:\Users\rafael\Documents\Desarrollos\CID\ifo\ifo\cbd_monitor\INFORME_TECNICO_MODIFICACIONES_RES_104_2026.docx"
    doc.save(output_path)
    print(f"Documento DOCX generado exitosamente en: {output_path}")

if __name__ == "__main__":
    create_report()
