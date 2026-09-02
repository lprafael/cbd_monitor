"""
Script de validación unitaria de la lógica de exclusión Non Bis In Idem
para Artículos 15.1, 15.2, 15.3, 15.4, 15.5 y 15.6 (Resolución GVMT N° 120/2025 y 21/2026).
"""

def evaluar_mes_simulado(jornadas, umbral_pico=90.0, umbral_pos=90.0):
    """
    Simula la lógica de evaluación implementada en fines_report.py y enviar_informe_infraccion.py:
    1. Máximo 1 sanción de Nivel C por día (20 jornales), ya sea por Pico (15.3), Pos Pico (15.5) o ambas (15.3/15.5).
    2. Si en el mes hay al menos un día con Nivel C, NO se sanciona por Nivel B (ni 15.2 ni 15.4).
    3. Solo si en el mes NO hubo Nivel C, se evalúan las franjas Nivel B (>= 5 franjas) por separado para Picos (15.2) y Pos Picos (15.4).
    4. Art. 15.6 (ICCBDM) se evalúa diariamente de forma autónoma (20 jornales por día).
    5. Para Art. 15.1, los días ya sancionados (por Nivel C o Nivel B) quedan EXCLUIDOS de la medición mensual.
       Se evalúa Picos y Pos Picos por separado frente a sus respectivos umbrales.
    6. Franjas válidas: L-V picos y pospicos, sábados únicamente picos.
    """
    historial_faltas = []
    dias_sancionados_c = set()
    dias_con_b_pico = {}
    dias_con_b_pos = {}
    
    # 1. Evaluación diaria
    for dia in jornadas:
        fecha = dia['fecha']
        tipo_dia = dia.get('tipo_dia', 5) # 5: L-V, 6: Sáb, 7: Dom/Feriado
        if tipo_dia == 7 or dia.get('atipico', False):
            continue
            
        franjas = dia['franjas']
        fail_15_3 = False
        fail_15_5 = False
        fail_15_6 = False
        b_pico_dia = 0
        b_pospico_dia = 0

        for f in franjas:
            cat = f['cat']
            ifo = f.get('ifo')
            cbd = f.get('cbd', 1.0)

            # Regla 6: Excluir Pos Pico de Sábado
            if tipo_dia == 6 and cat == 'POS_PICO':
                continue

            if cbd is not None and cbd < 1.0:
                fail_15_6 = True

            if ifo is not None:
                if cat == 'PICO':
                    if ifo < 80.0:
                        fail_15_3 = True
                    elif ifo < 90.0:
                        b_pico_dia += 1
                elif cat == 'POS_PICO':
                    if ifo < 80.0:
                        fail_15_5 = True
                    elif ifo < 90.0:
                        b_pospico_dia += 1

        # Regla 4: ICCBDM (15.6) independiente diario
        if fail_15_6:
            historial_faltas.append({'fecha': fecha, 'base': 'Art. 15.6', 'desc': 'Incumplimiento ICCBDM', 'jornales': 20})

        # Regla 1: Nivel C diario (máximo 1 sanción de 20 jornales por día)
        if fail_15_3 and fail_15_5:
            dias_sancionados_c.add(fecha)
            historial_faltas.append({'fecha': fecha, 'base': 'Art. 15.3 / 15.5', 'desc': 'Nivel C en Franjas Pico y Pos Pico', 'jornales': 20})
        elif fail_15_3:
            dias_sancionados_c.add(fecha)
            historial_faltas.append({'fecha': fecha, 'base': 'Art. 15.3', 'desc': 'Nivel C en Franja Pico', 'jornales': 20})
        elif fail_15_5:
            dias_sancionados_c.add(fecha)
            historial_faltas.append({'fecha': fecha, 'base': 'Art. 15.5', 'desc': 'Nivel C en Franja Pos Pico', 'jornales': 20})
        else:
            # Si el día no tuvo Nivel C, las franjas Nivel B pueden sumar
            if b_pico_dia > 0:
                dias_con_b_pico[fecha] = b_pico_dia
            if b_pospico_dia > 0:
                dias_con_b_pos[fecha] = b_pospico_dia

    # Reglas 2 y 3: Exclusión mensual de Nivel B si hubo AL MENOS UN Nivel C en el mes
    hubo_c_en_mes = len(dias_sancionados_c) > 0
    dias_sancionados_b = set()

    if not hubo_c_en_mes:
        total_b_pico = sum(dias_con_b_pico.values())
        if total_b_pico >= 5:
            dias_sancionados_b.update(dias_con_b_pico.keys())
            historial_faltas.append({'fecha': 'FIN_MES', 'base': 'Art. 15.2', 'desc': f'Acumulación {total_b_pico} Franjas Pico Nivel B', 'jornales': 10})

        total_b_pos = sum(dias_con_b_pos.values())
        if total_b_pos >= 5:
            dias_sancionados_b.update(dias_con_b_pos.keys())
            historial_faltas.append({'fecha': 'FIN_MES', 'base': 'Art. 15.4', 'desc': f'Acumulación {total_b_pos} Franjas Pos Pico Nivel B', 'jornales': 10})

    # Regla 5: Art. 15.1 Mensual (Picos y Pos Picos por separado, excluyendo días ya sancionados)
    dias_excluidos_15_1 = dias_sancionados_c.union(dias_sancionados_b)

    daily_pico_clean = []
    daily_pos_clean = []

    for dia in jornadas:
        fecha = dia['fecha']
        tipo_dia = dia.get('tipo_dia', 5)
        if tipo_dia == 7 or dia.get('atipico', False):
            continue
        if fecha in dias_excluidos_15_1:
            continue # EXCLUIDO porque ya fue sancionado

        franjas = dia['franjas']
        p_vals = []
        pos_vals = []
        for f in franjas:
            cat = f['cat']
            ifo = f.get('ifo')
            if ifo is None:
                continue
            if tipo_dia == 6 and cat == 'POS_PICO':
                continue
            if cat == 'PICO':
                p_vals.append(ifo)
            elif cat == 'POS_PICO':
                pos_vals.append(ifo)

        if p_vals:
            daily_pico_clean.append(min(sum(p_vals) / len(p_vals), 110.0))
        if pos_vals:
            daily_pos_clean.append(min(sum(pos_vals) / len(pos_vals), 110.0))

    if daily_pico_clean:
        ifo_mensual_pico = sum(daily_pico_clean) / len(daily_pico_clean)
        if ifo_mensual_pico < umbral_pico:
            historial_faltas.append({
                'fecha': 'FIN_MES',
                'base': 'Art. 15.1 (Pico)',
                'desc': f'IFO Mensual Picos ({ifo_mensual_pico:.2f}%) < Umbral ({umbral_pico:.2f}%) en días no sancionados',
                'jornales': 173
            })

    if daily_pos_clean:
        ifo_mensual_pos = sum(daily_pos_clean) / len(daily_pos_clean)
        if ifo_mensual_pos < umbral_pos:
            historial_faltas.append({
                'fecha': 'FIN_MES',
                'base': 'Art. 15.1 (Pos Pico)',
                'desc': f'IFO Mensual Pos Picos ({ifo_mensual_pos:.2f}%) < Umbral ({umbral_pos:.2f}%) en días no sancionados',
                'jornales': 173
            })

    return historial_faltas, dias_sancionados_c, dias_sancionados_b


def test_escenarios():
    print("Iniciando pruebas unitarias de las 6 Reglas de Amonestación y Sanción...")

    # Escenario 1: Nivel C en Pico y Pos Pico el mismo día -> Se aplica UNA SOLA SANCIÓN de 20 jornales
    jornadas_1 = [
        {
            'fecha': '2026-06-01',
            'tipo_dia': 5,
            'franjas': [
                {'cat': 'PICO', 'ifo': 70.0},     # Nivel C Pico
                {'cat': 'POS_PICO', 'ifo': 65.0}  # Nivel C Pos Pico
            ]
        }
    ]
    faltas, c_days, b_days = evaluar_mes_simulado(jornadas_1)
    sanciones_c = [f for f in faltas if '15.3' in f['base'] or '15.5' in f['base']]
    assert len(sanciones_c) == 1, f"Falla: Debe aplicar exactamente 1 sanción diaria de Nivel C, pero aplicó {len(sanciones_c)}"
    assert sanciones_c[0]['jornales'] == 20, f"Falla: Debe ser 20 jornales, fue {sanciones_c[0]['jornales']}"
    assert sanciones_c[0]['base'] == 'Art. 15.3 / 15.5'
    print("  [OK] Escenario 1: Nivel C en Pico y Pos Pico aplica UNA sola sanción de 20 jornales (Art. 15.3 / 15.5).")

    # Escenario 2: Nivel C en un día + 5 franjas Nivel B en otros días del mes -> NO aplica Nivel B en el mes
    jornadas_2 = [
        # Día 1: Nivel C en Pico (sanción 15.3)
        {'fecha': '2026-06-01', 'tipo_dia': 5, 'franjas': [{'cat': 'PICO', 'ifo': 70.0}]},
        # Días 2 al 6: Franjas Nivel B limpias (5 franjas)
        {'fecha': '2026-06-02', 'tipo_dia': 5, 'franjas': [{'cat': 'PICO', 'ifo': 85.0}]},
        {'fecha': '2026-06-03', 'tipo_dia': 5, 'franjas': [{'cat': 'PICO', 'ifo': 85.0}]},
        {'fecha': '2026-06-04', 'tipo_dia': 5, 'franjas': [{'cat': 'PICO', 'ifo': 85.0}]},
        {'fecha': '2026-06-05', 'tipo_dia': 5, 'franjas': [{'cat': 'PICO', 'ifo': 85.0}]},
        {'fecha': '2026-06-06', 'tipo_dia': 6, 'franjas': [{'cat': 'PICO', 'ifo': 85.0}]}
    ]
    faltas, c_days, b_days = evaluar_mes_simulado(jornadas_2)
    assert any(f['base'] == 'Art. 15.3' for f in faltas), "Falla: Debe aplicar 15.3"
    assert not any(f['base'] == 'Art. 15.2' for f in faltas), "Falla: NO debe aplicar 15.2 porque hubo Nivel C en el mes"
    print("  [OK] Escenario 2: Al haber Nivel C en el mes, ya no se sanciona Nivel B en todo el mes.")

    # Escenario 3: Mes SIN ningún Nivel C con 5 franjas Nivel B en Pico y 5 en Pos Pico -> Aplica 15.2 y 15.4
    jornadas_3 = [
        {'fecha': '2026-06-01', 'tipo_dia': 5, 'franjas': [{'cat': 'PICO', 'ifo': 85.0}, {'cat': 'POS_PICO', 'ifo': 85.0}]},
        {'fecha': '2026-06-02', 'tipo_dia': 5, 'franjas': [{'cat': 'PICO', 'ifo': 85.0}, {'cat': 'POS_PICO', 'ifo': 85.0}]},
        {'fecha': '2026-06-03', 'tipo_dia': 5, 'franjas': [{'cat': 'PICO', 'ifo': 85.0}, {'cat': 'POS_PICO', 'ifo': 85.0}]},
        {'fecha': '2026-06-04', 'tipo_dia': 5, 'franjas': [{'cat': 'PICO', 'ifo': 85.0}, {'cat': 'POS_PICO', 'ifo': 85.0}]},
        {'fecha': '2026-06-05', 'tipo_dia': 5, 'franjas': [{'cat': 'PICO', 'ifo': 85.0}, {'cat': 'POS_PICO', 'ifo': 85.0}]}
    ]
    faltas, c_days, b_days = evaluar_mes_simulado(jornadas_3)
    assert any(f['base'] == 'Art. 15.2' for f in faltas), "Falla: Debe aplicar 15.2"
    assert any(f['base'] == 'Art. 15.4' for f in faltas), "Falla: Debe aplicar 15.4"
    print("  [OK] Escenario 3: Sin Nivel C en el mes, se computan separadamente 15.2 y 15.4.")

    # Escenario 4: Art. 15.6 es autónomo e independiente
    jornadas_4 = [
        {
            'fecha': '2026-06-01',
            'tipo_dia': 5,
            'franjas': [
                {'cat': 'PICO', 'ifo': 95.0, 'cbd': 0.8} # IFO cumple (95%), CBD incumple (0.8)
            ]
        }
    ]
    faltas, c_days, b_days = evaluar_mes_simulado(jornadas_4)
    assert any(f['base'] == 'Art. 15.6' for f in faltas), "Falla: Debe aplicar 15.6"
    assert not any(f['base'] in ['Art. 15.2', 'Art. 15.3', 'Art. 15.4', 'Art. 15.5'] for f in faltas)
    print("  [OK] Escenario 4: Art. 15.6 se computa de forma independiente.")

    # Escenario 5: Exclusión de días ya sancionados para medición de Art. 15.1
    # Día 1: Nivel C en Pico (70%) -> sancionado con 15.3.
    # Días 2 al 10: Días limpios con IFO 92% (por encima del umbral de 90%).
    # Si el día 1 entrara al promedio, el promedio bajaría. Al excluirse el día 1, el promedio de los días limpios es 92% y NO debe gatillar 15.1.
    jornadas_5 = [
        {'fecha': '2026-06-01', 'tipo_dia': 5, 'franjas': [{'cat': 'PICO', 'ifo': 70.0}]}, # Sancionado con 15.3
    ]
    for d in range(2, 11):
        jornadas_5.append({
            'fecha': f'2026-06-{d:02d}',
            'tipo_dia': 5,
            'franjas': [{'cat': 'PICO', 'ifo': 92.0}] # Días limpios
        })
    faltas, c_days, b_days = evaluar_mes_simulado(jornadas_5, umbral_pico=90.0)
    assert any(f['base'] == 'Art. 15.3' for f in faltas), "Falla: Día 1 debe tener 15.3"
    assert not any(f['base'] == 'Art. 15.1 (Pico)' for f in faltas), "Falla: Días no sancionados promedian 92% >= 90%, NO debe gatillar 15.1"
    print("  [OK] Escenario 5: Días ya sancionados con Nivel C quedan excluidos del cálculo para 15.1.")

    # Escenario 6: Desdoblamiento de 15.1 (Pico cumple pero Pos Pico incumple)
    jornadas_6 = [
        {
            'fecha': '2026-06-01',
            'tipo_dia': 5,
            'franjas': [
                {'cat': 'PICO', 'ifo': 95.0},     # Pico cumple (95% >= 90%)
                {'cat': 'POS_PICO', 'ifo': 82.0}  # Pos Pico no sancionado (82% Nivel B pero no llega a 5), pero mensual < umbral 90%
            ]
        }
    ]
    faltas, c_days, b_days = evaluar_mes_simulado(jornadas_6, umbral_pico=90.0, umbral_pos=90.0)
    assert not any(f['base'] == 'Art. 15.1 (Pico)' for f in faltas), "Falla: Pico no debe gatillar 15.1"
    assert any(f['base'] == 'Art. 15.1 (Pos Pico)' for f in faltas), "Falla: Pos Pico debe gatillar 15.1 (Pos Pico)"
    print("  [OK] Escenario 6: Art. 15.1 evalúa Picos y Pos Picos de forma independiente.")

    # Escenario 7: Franjas válidas (Sábado Pos Pico no entra, Domingo no entra)
    jornadas_7 = [
        # Sábado con Pos Pico en Nivel C (debe ser ignorada por Regla 6)
        {'fecha': '2026-06-06', 'tipo_dia': 6, 'franjas': [{'cat': 'POS_PICO', 'ifo': 60.0}]},
        # Domingo con Nivel C (debe ser ignorado)
        {'fecha': '2026-06-07', 'tipo_dia': 7, 'franjas': [{'cat': 'PICO', 'ifo': 50.0}]}
    ]
    faltas, c_days, b_days = evaluar_mes_simulado(jornadas_7)
    assert len(faltas) == 0, f"Falla: Pos Pico de sábado y domingos deben ser descartados, pero generó {faltas}"
    print("  [OK] Escenario 7: Pos Pico de sábado y domingos/feriados correctamente excluidos.")

    print("\n>>> TODOS LOS TESTS UNITARIOS PASARON CON ÉXITO (7/7).")

if __name__ == "__main__":
    test_escenarios()
