from datetime import date, timedelta

import caso_compartido
import prediccion
from prediccion import DiaHistorico, DiaObjetivo

HOY = date(2026, 11, 2)  # lunes


def historial(dias, datos, tipo=lambda f: "NORMAL"):
    lista = []
    for i in range(dias, 0, -1):
        f = HOY - timedelta(days=i)
        producido, vendido, desperdiciado = datos(f)
        lista.append(DiaHistorico(f, producido, vendido, desperdiciado, tipo(f)))
    return lista


def semana(tipo=lambda f: "NORMAL"):
    return [DiaObjetivo(HOY + timedelta(days=i), tipo(HOY + timedelta(days=i))) for i in range(7)]


def test_sin_historial_usa_stock_minimo():
    r = prediccion.calcular([], semana(), stock_minimo=7)
    assert r.nivel_confianza == "BAJA"
    assert set(r.cantidades.values()) == {7.0}


def test_demanda_estable():
    r = prediccion.calcular(historial(70, lambda f: (12, 10, 2)), semana())
    assert set(r.cantidades.values()) == {10.0}
    assert r.nivel_confianza == "ALTA"
    assert r.dias_historicos == 70


def test_aprende_el_dia_de_la_semana():
    r = prediccion.calcular(historial(56, lambda f: (25, 20, 5) if f.weekday() == 5 else (12, 10, 2)), semana())
    assert 17 <= r.cantidades[HOY + timedelta(days=5)] <= 20   # sábado
    assert 9 <= r.cantidades[HOY + timedelta(days=1)] <= 11    # martes


def test_si_se_agoto_la_demanda_es_mayor():
    r = prediccion.calcular(historial(40, lambda f: (10, 10, 0)), semana())
    assert set(r.cantidades.values()) == {11.0}


def test_eventos_con_valor_inicial():
    tipos = {HOY + timedelta(days=2): "MAS_DEMANDA", HOY + timedelta(days=3): "MENOS_DEMANDA", HOY + timedelta(days=4): "FERIADO"}
    r = prediccion.calcular(historial(40, lambda f: (12, 10, 2)), semana(lambda f: tipos.get(f, "NORMAL")),
                            redondear_a_entero=False)
    assert r.cantidades[HOY + timedelta(days=2)] == 12.5
    assert r.cantidades[HOY + timedelta(days=3)] == 7.5
    assert r.cantidades[HOY + timedelta(days=4)] == 11.0
    assert r.cantidades[HOY] == 10.0


def test_aprende_el_efecto_de_los_feriados():
    feriados = {HOY - timedelta(days=d) for d in (10, 20, 30, 40)}
    r = prediccion.calcular(
        historial(50, lambda f: (12, 5, 7) if f in feriados else (12, 10, 2), lambda f: "FERIADO" if f in feriados else "NORMAL"),
        semana(lambda f: "FERIADO" if f == HOY + timedelta(days=2) else "NORMAL"), redondear_a_entero=False)
    assert r.cantidades[HOY + timedelta(days=2)] == 7.0


def test_priorizado_y_decimales():
    r = prediccion.calcular(historial(40, lambda f: (3, 2.5, 0.5)), semana(), priorizado=True, redondear_a_entero=False)
    assert set(r.cantidades.values()) == {2.8}


def test_niveles_de_confianza():
    assert prediccion.nivel_confianza(29) == "BAJA"
    assert prediccion.nivel_confianza(30) == "MEDIA"
    assert prediccion.nivel_confianza(60) == "ALTA"
    assert prediccion.mensaje_confianza(12) == "Faltan 18 días para alcanzar confianza Media."


def test_caso_compartido_con_java():
    # Mismo resultado que CasoCompartido.java en el backend
    r = prediccion.calcular(caso_compartido.historial(), caso_compartido.objetivos())
    assert list(r.cantidades.values()) == [24.0, 26.0, 23.0, 32.0, 34.0, 48.0, 29.0]
    assert r.nivel_confianza == "ALTA"
