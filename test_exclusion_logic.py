"""
Script de validación unitaria de la lógica de exclusión Non Bis In Idem
para Artículos 15.1, 15.2, 15.3, 15.4, 15.5 y 15.6 (Resolución GVMT N° 120/2025 y 21/2026).
"""

def evaluar_mes_simulado(jornadas, umbral_general=90.0, aplicar_non_bis_in_idem=True, **kwargs):
    """
    Simula la lógica de evaluación implementada en fines_report.py y enviar_informe_infraccion.py:
    Permite alternar entre la metodología estándar y el criterio 'Non bis in quo' (aplicar_non_bis_in_idem).
    """
    if 'umbral_pico' in kwargs:
        umbral_general = kwargs['umbral_pico']

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

        if not aplicar_non_bis_in_idem:
            # Metodología Estándar
            if fail_15_6:
                historial_faltas.append({'fecha': fecha, 'base': 'Art. 15.6', 'desc': 'Incumplimiento ICCBDM', 'jornales': 20})
            if fail_15_3:
                historial_faltas.append({'fecha': fecha, 'base': 'Art. 15.3', 'desc': 'Nivel C en Franja Pico', 'jornales': 20})
            if fail_15_5:
                historial_faltas.append({'fecha': fecha, 'base': 'Art. 15.5', 'desc': 'Nivel C en Franja Pos Pico', 'jornales': 20})
            if not fail_15_3 and b_pico_dia > 0:
                dias_con_b_pico[fecha] = dias_con_b_pico.get(fecha, 0) + b_pico_dia
            if not fail_15_5 and b_pospico_dia > 0:
                dias_con_b_pos[fecha] = dias_con_b_pos.get(fecha, 0) + b_pospico_dia
        else:
            # Metodología Non bis in quo (Res. 120/2025)
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
                if b_pico_dia > 0:
                    dias_con_b_pico[fecha] = b_pico_dia
                if b_pospico_dia > 0:
                    dias_con_b_pos[fecha] = b_pospico_dia

    dias_sancionados_b = set()

    if not aplicar_non_bis_in_idem:
        # Metodología Estándar de Nivel B
        total_b_pico = sum(dias_con_b_pico.values())
        total_b_pos = sum(dias_con_b_pos.values())
        if total_b_pico >= 5:
            historial_faltas.append({'fecha': 'FIN_MES', 'base': 'Art. 15.2', 'desc': f'Acumulación {total_b_pico} Franjas Pico Nivel B', 'jornales': 10})
        if total_b_pos >= 5:
            historial_faltas.append({'fecha': 'FIN_MES', 'base': 'Art. 15.4', 'desc': f'Acumulación {total_b_pos} Franjas Pos Pico Nivel B', 'jornales': 10})
    else:
        # Reglas 2 y 3: Exclusión mensual de Nivel B si hubo AL MENOS UN Nivel C en el mes
        # Y si en el mes no hubo C pero incumple 15.2 y 15.4, se aplica UNA SOLA multa mensual (no 2)
        hubo_c_en_mes = len(dias_sancionados_c) > 0
        if not hubo_c_en_mes:
            total_b_pico = sum(dias_con_b_pico.values())
            total_b_pos = sum(dias_con_b_pos.values())
            fail_b_pico = total_b_pico >= 5
            fail_b_pos = total_b_pos >= 5

            if fail_b_pico and fail_b_pos:
                dias_sancionados_b.update(dias_con_b_pico.keys())
                dias_sancionados_b.update(dias_con_b_pos.keys())
                historial_faltas.append({'fecha': 'FIN_MES', 'base': 'Art. 15.2 / 15.4', 'desc': f'Acumulación Nivel B en Franjas Pico ({total_b_pico}) y Pos Pico ({total_b_pos})', 'jornales': 10})
            elif fail_b_pico:
                dias_sancionados_b.update(dias_con_b_pico.keys())
                historial_faltas.append({'fecha': 'FIN_MES', 'base': 'Art. 15.2', 'desc': f'Acumulación {total_b_pico} Franjas Pico Nivel B', 'jornales': 10})
            elif fail_b_pos:
                dias_sancionados_b.update(dias_con_b_pos.keys())
                historial_faltas.append({'fecha': 'FIN_MES', 'base': 'Art. 15.4', 'desc': f'Acumulación {total_b_pos} Franjas Pos Pico Nivel B', 'jornales': 10})

    # Regla 4 (Res. GVMT N° 104/2026 y 120/2025): Art. 15.1 Mensual General
    # Se calcula como el promedio de los IFO diarios del mes (con tope 110%).
    # Si aplicar_non_bis_in_idem es True: se excluyen los días con sanción directa de Nivel C.
    daily_ifo_clean = []

    for dia in jornadas:
        fecha = dia['fecha']
        tipo_dia = dia.get('tipo_dia', 5)
        if tipo_dia == 7 or dia.get('atipico', False):
            continue
        if aplicar_non_bis_in_idem and fecha in dias_sancionados_c:
            continue

        franjas = dia['franjas']
        vals = []
        for f in franjas:
            cat = f['cat']
            ifo = f.get('ifo')
            if ifo is None:
                continue
            if tipo_dia == 6 and cat == 'POS_PICO':
                continue
            if cat in ['PICO', 'POS_PICO']:
                vals.append(ifo)

        if vals:
            daily_ifo_clean.append(min(sum(vals) / len(vals), 110.0))

    if daily_ifo_clean:
        ifo_mensual = sum(daily_ifo_clean) / len(daily_ifo_clean)
        if ifo_mensual < umbral_general:
            historial_faltas.append({
                'fecha': 'FIN_MES',
                'base': 'Art. 15.1',
                'desc': f'IFO Mensual ({ifo_mensual:.2f}%) < Umbral ({umbral_general:.2f}%)',
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

    # Escenario 3a: Mes SIN Nivel C con 4 franjas B en Pico y 4 en Pos Pico -> NO corresponde multa por Nivel B
    jornadas_3a = [
        {'fecha': '2026-06-01', 'tipo_dia': 5, 'franjas': [{'cat': 'PICO', 'ifo': 85.0}, {'cat': 'POS_PICO', 'ifo': 85.0}]},
        {'fecha': '2026-06-02', 'tipo_dia': 5, 'franjas': [{'cat': 'PICO', 'ifo': 85.0}, {'cat': 'POS_PICO', 'ifo': 85.0}]},
        {'fecha': '2026-06-03', 'tipo_dia': 5, 'franjas': [{'cat': 'PICO', 'ifo': 85.0}, {'cat': 'POS_PICO', 'ifo': 85.0}]},
        {'fecha': '2026-06-04', 'tipo_dia': 5, 'franjas': [{'cat': 'PICO', 'ifo': 85.0}, {'cat': 'POS_PICO', 'ifo': 85.0}]}
    ]
    faltas_3a, _, _ = evaluar_mes_simulado(jornadas_3a)
    assert not any('15.2' in f['base'] or '15.4' in f['base'] for f in faltas_3a), "Falla: 4 franjas B en Pico y 4 en Pos Pico NO deben generar multa de Nivel B"
    print("  [OK] Escenario 3a: 4 Nivel B en Pico y 4 en Pos Pico no suman entre sí y NO generan multa por Nivel B.")

    # Escenario 3b: Mes SIN Nivel C con 5 franjas B en Pico y 5 en Pos Pico -> Aplica UNA SOLA multa al mes (Art. 15.2 / 15.4 de 10 jornales)
    jornadas_3b = [
        {'fecha': '2026-06-01', 'tipo_dia': 5, 'franjas': [{'cat': 'PICO', 'ifo': 85.0}, {'cat': 'POS_PICO', 'ifo': 85.0}]},
        {'fecha': '2026-06-02', 'tipo_dia': 5, 'franjas': [{'cat': 'PICO', 'ifo': 85.0}, {'cat': 'POS_PICO', 'ifo': 85.0}]},
        {'fecha': '2026-06-03', 'tipo_dia': 5, 'franjas': [{'cat': 'PICO', 'ifo': 85.0}, {'cat': 'POS_PICO', 'ifo': 85.0}]},
        {'fecha': '2026-06-04', 'tipo_dia': 5, 'franjas': [{'cat': 'PICO', 'ifo': 85.0}, {'cat': 'POS_PICO', 'ifo': 85.0}]},
        {'fecha': '2026-06-05', 'tipo_dia': 5, 'franjas': [{'cat': 'PICO', 'ifo': 85.0}, {'cat': 'POS_PICO', 'ifo': 85.0}]}
    ]
    faltas_3b, _, _ = evaluar_mes_simulado(jornadas_3b)
    sanciones_b = [f for f in faltas_3b if '15.2' in f['base'] or '15.4' in f['base']]
    assert len(sanciones_b) == 1, f"Falla: Debe aplicar exactamente 1 sola multa al mes por Nivel B, pero aplicó {len(sanciones_b)}"
    assert sanciones_b[0]['base'] == 'Art. 15.2 / 15.4'
    assert sanciones_b[0]['jornales'] == 10
    print("  [OK] Escenario 3b: Al incumplir 15.2 y 15.4 a la vez, se aplica una sola multa de 10 jornales (Art. 15.2 / 15.4).")

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

    # Escenario 5: Exclusión de días con Nivel C en Art. 15.1 bajo Non Bis In Idem
    # Día 1: Nivel C en Pico (70%) -> sancionado con 15.3.
    # Días 2 al 10 (9 días): Días con IFO 92%.
    # Con Non Bis In Idem: El día 1 se excluye de la muestra mensual, quedando el promedio en 92% (>= 90%).
    # No genera sanción de 15.1, evitando el doble castigo por el mismo déficit de flota.
    # Con Metodología Estándar: Computa los 10 días -> promedio 89.8% (< 90%), generando 15.1.
    jornadas_5 = [
        {'fecha': '2026-06-01', 'tipo_dia': 5, 'franjas': [{'cat': 'PICO', 'ifo': 70.0}]}, # Sancionado con 15.3
    ]
    for d in range(2, 11):
        jornadas_5.append({
            'fecha': f'2026-06-{d:02d}',
            'tipo_dia': 5,
            'franjas': [{'cat': 'PICO', 'ifo': 92.0}]
        })
    faltas_5_non_bis, _, _ = evaluar_mes_simulado(jornadas_5, umbral_general=90.0, aplicar_non_bis_in_idem=True)
    assert any(f['base'] == 'Art. 15.3' for f in faltas_5_non_bis), "Falla: Día 1 debe tener 15.3"
    assert not any('15.1' in f['base'] for f in faltas_5_non_bis), "Falla: Non Bis In Idem excluye el día con Nivel C de la muestra de 15.1"
    
    faltas_5_std, _, _ = evaluar_mes_simulado(jornadas_5, umbral_general=90.0, aplicar_non_bis_in_idem=False)
    assert any('15.1' in f['base'] for f in faltas_5_std), "Falla: Metodología estándar debe gatillar 15.1 (89.8% < 90%)"
    print("  [OK] Escenario 5: Exclusión de días con Nivel C en IFO Mensual bajo Non Bis In Idem (evita doble sanción).")

    # Escenario 6: IFO Mensual General (una única sanción consolidada, no desdoblada por franja)
    # Día con Pico (95%) y Pos Pico (82%). Promedio diario general = (95 + 82) / 2 = 88.5% (< 90%).
    # Aplica EXACTAMENTE 1 sola sanción de 173 jornales por Art. 15.1, NUNCA dos sanciones desdobladas.
    jornadas_6 = [
        {
            'fecha': '2026-06-01',
            'tipo_dia': 5,
            'franjas': [
                {'cat': 'PICO', 'ifo': 95.0},     # Pico 95%
                {'cat': 'POS_PICO', 'ifo': 82.0}  # Pos Pico 82%
            ]
        }
    ]
    faltas_6, _, _ = evaluar_mes_simulado(jornadas_6, umbral_general=90.0)
    sanciones_15_1 = [f for f in faltas_6 if '15.1' in f['base']]
    assert len(sanciones_15_1) == 1, f"Falla: Debe emitir exactamente 1 sanción general por Art. 15.1, emitió {len(sanciones_15_1)}"
    assert sanciones_15_1[0]['base'] == 'Art. 15.1'
    assert sanciones_15_1[0]['jornales'] == 173
    print("  [OK] Escenario 6: IFO Mensual se calcula de forma general (1 sola sanción unificada de 173 jornales).")

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

    # Escenario 8: Verificación del flag opcional aplicar_non_bis_in_idem (False vs True)
    # Jornada con Nivel C en Pico y Pos Pico el mismo día + 5 franjas B en Pico en otros días
    jornadas_8 = [
        {'fecha': '2026-06-01', 'tipo_dia': 5, 'franjas': [{'cat': 'PICO', 'ifo': 70.0}, {'cat': 'POS_PICO', 'ifo': 65.0}]},
        {'fecha': '2026-06-02', 'tipo_dia': 5, 'franjas': [{'cat': 'PICO', 'ifo': 85.0}]},
        {'fecha': '2026-06-03', 'tipo_dia': 5, 'franjas': [{'cat': 'PICO', 'ifo': 85.0}]},
        {'fecha': '2026-06-04', 'tipo_dia': 5, 'franjas': [{'cat': 'PICO', 'ifo': 85.0}]},
        {'fecha': '2026-06-05', 'tipo_dia': 5, 'franjas': [{'cat': 'PICO', 'ifo': 85.0}]},
        {'fecha': '2026-06-06', 'tipo_dia': 6, 'franjas': [{'cat': 'PICO', 'ifo': 85.0}]},
    ]
    # Con aplicar_non_bis_in_idem=False (Metodología estándar previa):
    # - Día 1 genera 2 sanciones de Nivel C: 15.3 (20 j) y 15.5 (20 j) -> 40 j
    # - Además genera sanción de Nivel B 15.2 (10 j) porque en la estándar no se cancela Nivel B mensual
    faltas_std, _, _ = evaluar_mes_simulado(jornadas_8, umbral_pico=50.0, umbral_pos=50.0, aplicar_non_bis_in_idem=False)
    assert any(f['base'] == 'Art. 15.3' for f in faltas_std), "Std: debe tener 15.3"
    assert any(f['base'] == 'Art. 15.5' for f in faltas_std), "Std: debe tener 15.5"
    assert any(f['base'] == 'Art. 15.2' for f in faltas_std), "Std: debe tener 15.2"
    jornales_std = sum(f['jornales'] for f in faltas_std)
    assert jornales_std == 50, f"Std: debe sumar 50 jornales (20 + 20 + 10), sumó {jornales_std}"

    # Con aplicar_non_bis_in_idem=True (Nueva metodología Non bis in quo):
    # - Día 1 genera 1 sola sanción de Nivel C: 15.3 / 15.5 (20 j)
    # - Nivel B queda anulado por haber Nivel C en el mes -> 0 j
    # Total = 20 jornales
    faltas_non_bis, _, _ = evaluar_mes_simulado(jornadas_8, umbral_pico=50.0, umbral_pos=50.0, aplicar_non_bis_in_idem=True)
    assert len(faltas_non_bis) == 1, f"Non bis: debe tener 1 sola falta, tuvo {len(faltas_non_bis)}"
    assert faltas_non_bis[0]['base'] == 'Art. 15.3 / 15.5'
    assert faltas_non_bis[0]['jornales'] == 20
    print("  [OK] Escenario 8: Flag opcional aplicar_non_bis_in_idem distingue correctamente entre Metodología Estándar (50 jornales) y Non bis in quo (20 jornales).")

    print("\n>>> TODOS LOS TESTS UNITARIOS PASARON CON ÉXITO (8/8).")

if __name__ == "__main__":
    test_escenarios()
