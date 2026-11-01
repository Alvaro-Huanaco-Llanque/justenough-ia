# justenough-ia
Servicio de predicción de demanda de JustEnough (FastAPI).

## Encender
```
python -m venv .venv
.venv\Scripts\Activate.ps1        (Mac / Linux: source .venv/bin/activate)
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```
Documentación de la API: http://localhost:8000/docs

## Qué hace
- `POST /api/predecir-semana`: recibe el historial de cada producto (producido, vendido, desperdiciado y tipo de día)
  y las fechas a predecir, y devuelve la cantidad sugerida para cada fecha y el nivel de confianza.
- El backend manda todos los productos en un solo pedido.
- El algoritmo está en `prediccion.py` y está explicado ahí mismo. Es el mismo que usa el backend como respaldo
  (`PronosticoLocal.java`): si se cambia uno, hay que cambiar el otro. El test compartido (`caso_compartido.py`) avisa si dejan de coincidir.

## Tests
```
pip install -r requirements-dev.txt
python -m pytest tests
```
