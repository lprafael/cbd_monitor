"""
Script de validación unitaria de la lógica de exclusión Non Bis In Idem
para Artículos 15.2, 15.3, 15.4, 15.5 y 15.6.
"""

def evaluar_jornadas_simuladas(jornadas):
    """
    Simula la lógica de evaluación implementada en fines_report.py y enviar_informe_infraccion.py.
    """
    historial_faltas = []
    acum_b = {'PICO': 0, 'POS_PICO': 0}
    trigger_15_2 = False
    trigger_15_4 = False

    for dia in jornadas:
        fecha = dia['fecha']
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

            if cbd < 1.0:
                fail_15_6 = True

            if cat == 'PICO':
                if ifo < 80:
                    fail_15_3 = True
                elif ifo < 90:
                    b_pico_dia += 1
            elif cat == 'POS_PICO':
                if ifo < 80:
                    fail_15_5 = True
                elif ifo < 90:
                    b_pospico_dia += 1

        # 1. ICCBDM (15.6)
        if fail_15_6:
            historial_faltas.append({'fecha': fecha, 'base': 'Art. 15.6', 'jornales': 20})

        # 2. NIVEL C PICO (15.3)
        if fail_15_3:
            historial_faltas.append({'fecha': fecha, 'base': 'Art. 15.3', 'jornales': 20})

        # 3. NIVEL C POS PICO (15.5)
        if fail_15_5:
            historial_faltas.append({'fecha': fecha, 'base': 'Art. 15.5', 'jornales': 20})

        # REGLA NON BIS IN IDEM
        if not fail_15_3 and not trigger_15_2:
            acum_b['PICO'] += b_pico_dia

        if not fail_15_5 and not trigger_15_4:
            acum_b['POS_PICO'] += b_pospico_dia

        # 4. ACUMULACIÓN NIVEL B
        if not trigger_15_2 and acum_b['PICO'] >= 5:
            trigger_15_2 = True
            historial_faltas.append({'fecha': fecha, 'base': 'Art. 15.2', 'jornales': 10})

        if not trigger_15_4 and acum_b['POS_PICO'] >= 5:
            trigger_15_4 = True
            historial_faltas.append({'fecha': fecha, 'base': 'Art. 15.4', 'jornales': 10})

    return historial_faltas, acum_b

def test_escenarios():
    print("Iniciando pruebas unitarias de la Regla Non Bis In Idem...")

    # Escenario 1: Mismo día con Nivel B (85%) y Nivel C (70%) en Pico
    jornadas_1 = [
        {
            'fecha': '2026-06-01',
            'franjas': [
                {'cat': 'PICO', 'ifo': 85.0}, # Nivel B
                {'cat': 'PICO', 'ifo': 70.0}  # Nivel C -> Bloquea Pico Nivel B del día
            ]
        }
    ]
    faltas, acum = evaluar_jornadas_simuladas(jornadas_1)
    assert any(f['base'] == 'Art. 15.3' for f in faltas), "Falla: Debe aplicar 15.3"
    assert acum['PICO'] == 0, f"Falla: acum_b['PICO'] debe ser 0 pero es {acum['PICO']}"
    print("  [OK] Escenario 1: Nivel C Pico bloquea Nivel B Pico del mismo día.")

    # Escenario 2: Mismo día con Nivel C (70%) en Pico y Nivel B (85%) en Pos Pico
    jornadas_2 = [
        {
            'fecha': '2026-06-01',
            'franjas': [
                {'cat': 'PICO', 'ifo': 70.0},     # Nivel C Pico
                {'cat': 'POS_PICO', 'ifo': 85.0}  # Nivel B Pos Pico -> SÍ debe sumar a Pos Pico
            ]
        }
    ]
    faltas, acum = evaluar_jornadas_simuladas(jornadas_2)
    assert any(f['base'] == 'Art. 15.3' for f in faltas), "Falla: Debe aplicar 15.3"
    assert acum['PICO'] == 0, f"Falla: acum_b['PICO'] debe ser 0"
    assert acum['POS_PICO'] == 1, f"Falla: acum_b['POS_PICO'] debe ser 1 pero es {acum['POS_PICO']}"
    print("  [OK] Escenario 2: Nivel C Pico NO bloquea Nivel B Pos Pico.")

    # Escenario 3: Mismo día con Nivel C (70%) en Pos Pico y Nivel B (85%) en Pico
    jornadas_3 = [
        {
            'fecha': '2026-06-01',
            'franjas': [
                {'cat': 'PICO', 'ifo': 85.0},     # Nivel B Pico -> SÍ debe sumar a Pico
                {'cat': 'POS_PICO', 'ifo': 70.0}  # Nivel C Pos Pico
            ]
        }
    ]
    faltas, acum = evaluar_jornadas_simuladas(jornadas_3)
    assert any(f['base'] == 'Art. 15.5' for f in faltas), "Falla: Debe aplicar 15.5"
    assert acum['PICO'] == 1, f"Falla: acum_b['PICO'] debe ser 1 pero es {acum['PICO']}"
    assert acum['POS_PICO'] == 0, f"Falla: acum_b['POS_PICO'] debe ser 0"
    print("  [OK] Escenario 3: Nivel C Pos Pico NO bloquea Nivel B Pico.")

    # Escenario 4: Mismo día con Nivel C en Pico y Pos Pico
    jornadas_4 = [
        {
            'fecha': '2026-06-01',
            'franjas': [
                {'cat': 'PICO', 'ifo': 70.0},
                {'cat': 'PICO', 'ifo': 85.0},
                {'cat': 'POS_PICO', 'ifo': 75.0},
                {'cat': 'POS_PICO', 'ifo': 88.0}
            ]
        }
    ]
    faltas, acum = evaluar_jornadas_simuladas(jornadas_4)
    assert sum(1 for f in faltas if f['base'] in ['Art. 15.3', 'Art. 15.5']) == 2
    assert acum['PICO'] == 0 and acum['POS_PICO'] == 0
    print("  [OK] Escenario 4: Nivel C en ambas franjas bloquea ambos acumuladores de Nivel B.")

    # Escenario 5: 4 franjas limpias de Nivel B + 1 franja en día con Nivel C
    jornadas_5 = [
        {'fecha': '2026-06-01', 'franjas': [{'cat': 'PICO', 'ifo': 85.0}]},
        {'fecha': '2026-06-02', 'franjas': [{'cat': 'PICO', 'ifo': 85.0}]},
        {'fecha': '2026-06-03', 'franjas': [{'cat': 'PICO', 'ifo': 85.0}]},
        {'fecha': '2026-06-04', 'franjas': [{'cat': 'PICO', 'ifo': 85.0}]},
        # Día 5: Nivel B pero también Nivel C en otra franja pico
        {'fecha': '2026-06-05', 'franjas': [{'cat': 'PICO', 'ifo': 85.0}, {'cat': 'PICO', 'ifo': 70.0}]}
    ]
    faltas, acum = evaluar_jornadas_simuladas(jornadas_5)
    assert not any(f['base'] == 'Art. 15.2' for f in faltas), "Falla: NO debe gatillar 15.2 porque acumuló 4 franjas limpias"
    assert any(f['base'] == 'Art. 15.3' for f in faltas), "Falla: Debe aplicar 15.3 del día 5"
    assert acum['PICO'] == 4, f"Falla: acum_b['PICO'] debe ser 4 y es {acum['PICO']}"
    print("  [OK] Escenario 5: 4 franjas limpias + 1 franja en día sancionado con Nivel C no alcanza el umbral de 5.")

    # Escenario 6: 5 franjas limpias de Nivel B gatillan Art. 15.2
    jornadas_6 = [
        {'fecha': '2026-06-01', 'franjas': [{'cat': 'PICO', 'ifo': 85.0}]},
        {'fecha': '2026-06-02', 'franjas': [{'cat': 'PICO', 'ifo': 85.0}]},
        {'fecha': '2026-06-03', 'franjas': [{'cat': 'PICO', 'ifo': 85.0}]},
        {'fecha': '2026-06-04', 'franjas': [{'cat': 'PICO', 'ifo': 85.0}]},
        {'fecha': '2026-06-05', 'franjas': [{'cat': 'PICO', 'ifo': 85.0}]}
    ]
    faltas, acum = evaluar_jornadas_simuladas(jornadas_6)
    assert any(f['base'] == 'Art. 15.2' for f in faltas), "Falla: Debe gatillar 15.2"
    assert acum['PICO'] == 5
    print("  [OK] Escenario 6: 5 franjas limpias gatillan Art. 15.2 correctamente.")

    print("\n>>> TODOS LOS TESTS PASARON EXITOSAMENTE (6/6).")

if __name__ == "__main__":
    test_escenarios()
