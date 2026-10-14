from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import pandas as pd
from typing import List, Optional

app = FastAPI(
    title="JustEnough - Servicio Predictivo",
    description="Microservicio de IA/Predicción de demanda para optimización de stock y producción.",
    version="1.0.0"
)

# 1. Definir la estructura de los datos de entrada (lo que enviará Spring Boot)
class RegistroHistoricoDto(BaseModel):
    fecha: str
    cantidad_producida: float
    cantidad_vendida: float
    cantidad_desperdiciada: Optional[float] = 0.0
    es_feriado_o_evento: bool = False

class PrediccionRequest(BaseModel):
    producto_id: int  # Cambiado de Long a int
    nombre_producto: str
    dias_historicos_disponibles: int  # Sirve para calcular la "Madurez" del modelo
    historial: List[RegistroHistoricoDto]

# 2. Definir la estructura de la respuesta (lo que consumirá el backend o frontend)
class SugerenciaResponse(BaseModel):
    producto_id: int
    nombre_producto: str
    cantidad_sugerida: float
    nivel_confianza: str  # "BAJA", "MEDIA", "ALTA" (Basado en los días de datos)
    mensaje_explicativo: str


@app.get("/")
def read_root():
    return {"status": "Servicio predictivo de JustEnough funcionando correctamente 🚀"}


@app.post("/api/predecir", response_model=SugerenciaResponse)
def predecir_demanda(request: PrediccionRequest):
    try:
        if not request.historial:
            raise HTTPException(status_code=400, detail="El historial de datos está vacío.")

        # Convertir la lista de registros a un DataFrame de Pandas para análisis estadístico
        df = pd.DataFrame([item.dict() for item in request.historial])

        # --- LÓGICA PREDICTIVA DEL MVP ---
        # 1. Promedio base de ventas históricas
        promedio_ventas = df['cantidad_vendida'].mean()

        # 2. Factor de desperdicio (si se tira mucho, penalizamos o ajustamos la producción)
        desperdicio_total = df['cantidad_desperdiciada'].sum()
        
        # 3. Ajuste por eventos/feriados (si hay días marcados con evento, aumentamos un 15% de holgura)
        factor_evento = 1.15 if df['es_feriado_o_evento'].any() else 1.0

        # Cálculo matemático simple pero efectivo para el MVP:
        # Sugerencia = (Promedio de ventas) * Factor de evento
        cantidad_sugerida = round(promedio_ventas * factor_evento, 2)

        # 4. Determinar el Nivel de Confianza basado en la "Madurez" (días de datos disponibles)
        # Regla coherente con su diseño de Figma: < 30 días = BAJA, 30-59 días = MEDIA, 60+ días = ALTA
        dias = request.dias_historicos_disponibles
        if dias < 30:
            nivel_confianza = "BAJA"
            explicacion = f"Faltan {30 - dias} días para alcanzar confianza Media."
        elif dias < 60:
            nivel_confianza = "MEDIA"
            explicacion = f"Faltan {60 - dias} días para alcanzar confianza Alta."
        else:
            nivel_confianza = "ALTA"
            explicacion = "Nivel máximo de madurez alcanzado."

        return SugerenciaResponse(
            producto_id=request.producto_id,
            nombre_producto=request.nombre_producto,
            cantidad_sugerida=cantidad_sugerida,
            nivel_confianza=nivel_confianza,
            mensaje_explicativo=explicacion
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al procesar la predicción: {str(e)}")