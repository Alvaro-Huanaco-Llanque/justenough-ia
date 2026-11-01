"""
Caso de prueba compartido con el backend (CasoCompartido.java): mismo historial y mismas fechas.
Los dos algoritmos (Python y Java) tienen que dar exactamente las mismas cantidades.
"""
from datetime import date, timedelta

from prediccion import DiaHistorico, DiaObjetivo

HOY = date(2026, 11, 2)  # lunes


def historial() -> list[DiaHistorico]:
    dias = []
    for i in range(63, 0, -1):
        fecha = HOY - timedelta(days=i)
        vendido = 20 + fecha.weekday() * 3 + (i % 5)
        tipo = "NORMAL"
        if i % 17 == 0:
            tipo = "FERIADO"
            vendido = round(vendido * 0.6)
        elif i % 23 == 0:
            tipo = "MAS_DEMANDA"
            vendido = round(vendido * 1.4)
        producido = vendido if i % 9 == 0 else vendido + 4
        dias.append(DiaHistorico(fecha, producido, vendido, producido - vendido, tipo))
    return dias


def objetivos() -> list[DiaObjetivo]:
    tipos = {2: "FERIADO", 5: "MAS_DEMANDA", 6: "MENOS_DEMANDA"}
    return [DiaObjetivo(HOY + timedelta(days=i), tipos.get(i, "NORMAL")) for i in range(7)]
