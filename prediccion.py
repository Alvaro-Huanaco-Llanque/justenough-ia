"""
Algoritmo de predicción de demanda de JustEnough.

Es el mismo cálculo que hace el backend (PronosticoLocal.java) cuando este servicio no está
encendido. Si se cambia algo acá, hay que cambiarlo también allá (y el test compartido avisa).

Idea general:
  1. Nivel base: promedio de lo vendido en días normales, dando más peso a lo reciente
     (lo de hace 4 semanas pesa la mitad que lo de ayer).
  2. Si un día se vendió todo lo producido, la demanda real fue probablemente mayor: se suma un 10%.
  3. Factor por día de la semana: cuánto se vende ese día comparado con el promedio (ej: sábado x1,3).
  4. Factor por evento (feriado, evento propio con más o menos demanda): se aprende del historial;
     si todavía no hubo suficientes, se usa un valor inicial razonable.
  5. Productos priorizados (los que no pueden faltar) llevan un 10% extra de margen.
  Con pocos datos, los factores se acercan a "sin efecto" para no exagerar por casualidad.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date

VIDA_MEDIA_DIAS = 28.0
AJUSTE_AGOTADO = 1.10
MARGEN_PRIORIZADO = 1.10
SUAVIZADO = 2.0
DIAS_CONFIANZA_MEDIA = 30
DIAS_CONFIANZA_ALTA = 60

FACTOR_EVENTO_INICIAL = {
    "FERIADO": 1.10,
    "MAS_DEMANDA": 1.25,
    "MENOS_DEMANDA": 0.75,
}


@dataclass
class DiaHistorico:
    fecha: date
    producido: float
    vendido: float
    desperdiciado: float = 0.0
    tipo_dia: str = "NORMAL"


@dataclass
class DiaObjetivo:
    fecha: date
    tipo_dia: str = "NORMAL"


@dataclass
class Resultado:
    nivel_confianza: str
    dias_historicos: int
    mensaje: str
    cantidades: dict[date, float]


def nivel_confianza(dias: int) -> str:
    if dias < DIAS_CONFIANZA_MEDIA:
        return "BAJA"
    if dias < DIAS_CONFIANZA_ALTA:
        return "MEDIA"
    return "ALTA"


def mensaje_confianza(dias: int) -> str:
    if dias < DIAS_CONFIANZA_MEDIA:
        return f"Faltan {DIAS_CONFIANZA_MEDIA - dias} días para alcanzar confianza Media."
    if dias < DIAS_CONFIANZA_ALTA:
        return f"Faltan {DIAS_CONFIANZA_ALTA - dias} días para alcanzar confianza Alta."
    return "Nivel máximo de madurez alcanzado."


def redondear(valor: float, a_entero: bool) -> float:
    # Primero se limpia el ruido de las cuentas con decimales (12.4999999 -> 12.5) y después se
    # redondea "hacia arriba desde ,5" igual que Java (el round() de Python redondea al par)
    valor = round(valor, 6)
    if a_entero:
        return float(math.floor(valor + 0.5))
    return math.floor(valor * 10 + 0.5) / 10.0


def demanda(dia: DiaHistorico) -> float:
    """Lo vendido, o un poco más si ese día se agotó."""
    agotado = dia.producido > 0 and dia.vendido >= dia.producido
    return dia.vendido * AJUSTE_AGOTADO if agotado else dia.vendido


def _promedio_ponderado(dias: list[DiaHistorico], referencia: date) -> float:
    suma = pesos = 0.0
    for d in dias:
        edad = (referencia - d.fecha).days
        peso = math.pow(0.5, edad / VIDA_MEDIA_DIAS)
        suma += peso * demanda(d)
        pesos += peso
    return suma / pesos if pesos else 0.0


def _suavizar(crudo: float, n: int, valor_seguro: float) -> float:
    return (n * crudo + SUAVIZADO * valor_seguro) / (n + SUAVIZADO)


def calcular(historial: list[DiaHistorico], objetivos: list[DiaObjetivo], *, priorizado: bool = False,
             stock_minimo: float = 0.0, redondear_a_entero: bool = True, dias_historicos: int = 0) -> Resultado:
    dias = dias_historicos if dias_historicos > 0 else len({h.fecha for h in historial})
    nivel = nivel_confianza(dias)

    if not historial:
        valor = redondear(max(0.0, stock_minimo), redondear_a_entero)
        return Resultado("BAJA", 0, "Todavía no hay ventas cargadas: se usa el stock mínimo como referencia.",
                         {o.fecha: valor for o in objetivos})

    referencia = max(h.fecha for h in historial)
    normales = [h for h in historial if (h.tipo_dia or "NORMAL") == "NORMAL"] or historial

    base = _promedio_ponderado(normales, referencia)
    if base <= 0:
        return Resultado(nivel, dias, "No hay ventas registradas en el historial reciente.",
                         {o.fecha: 0.0 for o in objetivos})

    factor_dia = {}
    for dia_semana in range(7):
        del_dia = [h for h in normales if h.fecha.weekday() == dia_semana]
        crudo = _promedio_ponderado(del_dia, referencia) / base if del_dia else 1.0
        factor_dia[dia_semana] = _suavizar(crudo, len(del_dia), 1.0)

    factor_evento = {"NORMAL": 1.0}
    for tipo, inicial in FACTOR_EVENTO_INICIAL.items():
        suma, n = 0.0, 0
        for h in historial:
            if h.tipo_dia != tipo:
                continue
            esperado = base * factor_dia[h.fecha.weekday()]
            if esperado > 0:
                suma += demanda(h) / esperado
                n += 1
        crudo = suma / n if n else inicial
        factor_evento[tipo] = _suavizar(crudo, n, inicial)

    margen = MARGEN_PRIORIZADO if priorizado else 1.0
    cantidades = {}
    for o in objetivos:
        tipo = o.tipo_dia if o.tipo_dia in factor_evento else "NORMAL"
        valor = base * factor_dia[o.fecha.weekday()] * factor_evento[tipo] * margen
        cantidades[o.fecha] = redondear(max(0.0, valor), redondear_a_entero)
    return Resultado(nivel, dias, mensaje_confianza(dias), cantidades)
