from datetime import date
from typing import List, Literal

from fastapi import FastAPI
from pydantic import BaseModel, Field

import prediccion

app = FastAPI(
    title="JustEnough - Servicio Predictivo",
    description="Microservicio de predicción de demanda para optimizar la producción y el stock.",
    version="2.0.0",
)

TipoDia = Literal["NORMAL", "FERIADO", "MAS_DEMANDA", "MENOS_DEMANDA"]


# ===== Lo que envía el backend (Spring Boot) =====
class DiaHistoricoDto(BaseModel):
    fecha: date
    cantidad_producida: float = Field(ge=0)
    cantidad_vendida: float = Field(ge=0)
    cantidad_desperdiciada: float = Field(default=0.0, ge=0)
    tipo_dia: TipoDia = "NORMAL"


class DiaObjetivoDto(BaseModel):
    fecha: date
    tipo_dia: TipoDia = "NORMAL"


class ProductoDto(BaseModel):
    producto_id: int
    nombre_producto: str
    priorizado: bool = False
    stock_minimo: float = 0.0
    redondear_a_entero: bool = True
    dias_historicos: int = 0          # días con datos en todo el historial (define la confianza)
    historial: List[DiaHistoricoDto] = []
    fechas_objetivo: List[DiaObjetivoDto]


class PedidoSemana(BaseModel):
    productos: List[ProductoDto]


# ===== Lo que responde =====
class PrediccionDia(BaseModel):
    fecha: date
    cantidad: float


class ResultadoProducto(BaseModel):
    producto_id: int
    nombre_producto: str
    nivel_confianza: str              # "BAJA", "MEDIA" o "ALTA" (según los días de datos)
    dias_historicos: int
    mensaje_explicativo: str
    predicciones: List[PrediccionDia]


class RespuestaSemana(BaseModel):
    resultados: List[ResultadoProducto]


@app.get("/")
def read_root():
    return {"status": "Servicio predictivo de JustEnough funcionando correctamente"}


# Predicción de varios productos en un solo pedido (el backend manda todos los de la semana juntos)
@app.post("/api/predecir-semana", response_model=RespuestaSemana)
def predecir_semana(pedido: PedidoSemana) -> RespuestaSemana:
    resultados = []
    for p in pedido.productos:
        historial = [prediccion.DiaHistorico(h.fecha, h.cantidad_producida, h.cantidad_vendida,
                                             h.cantidad_desperdiciada, h.tipo_dia) for h in p.historial]
        objetivos = [prediccion.DiaObjetivo(o.fecha, o.tipo_dia) for o in p.fechas_objetivo]
        r = prediccion.calcular(historial, objetivos, priorizado=p.priorizado, stock_minimo=p.stock_minimo,
                                redondear_a_entero=p.redondear_a_entero, dias_historicos=p.dias_historicos)
        resultados.append(ResultadoProducto(
            producto_id=p.producto_id,
            nombre_producto=p.nombre_producto,
            nivel_confianza=r.nivel_confianza,
            dias_historicos=r.dias_historicos,
            mensaje_explicativo=r.mensaje,
            predicciones=[PrediccionDia(fecha=f, cantidad=c) for f, c in r.cantidades.items()],
        ))
    return RespuestaSemana(resultados=resultados)
