from fastapi.testclient import TestClient

from main import app

cliente = TestClient(app)


def test_salud():
    respuesta = cliente.get("/")
    assert respuesta.status_code == 200
    assert "funcionando" in respuesta.json()["status"]


def test_predecir_semana_varios_productos():
    historial = [{"fecha": f"2026-10-{d:02d}", "cantidad_producida": 12, "cantidad_vendida": 10,
                  "cantidad_desperdiciada": 2, "tipo_dia": "NORMAL"} for d in range(1, 32)]
    pedido = {"productos": [
        {"producto_id": 1, "nombre_producto": "Medialuna", "dias_historicos": 31, "historial": historial,
         "fechas_objetivo": [{"fecha": "2026-11-02"}, {"fecha": "2026-11-03", "tipo_dia": "MAS_DEMANDA"}]},
        {"producto_id": 2, "nombre_producto": "Scon", "stock_minimo": 6, "historial": [],
         "fechas_objetivo": [{"fecha": "2026-11-02"}]},
    ]}
    respuesta = cliente.post("/api/predecir-semana", json=pedido)
    assert respuesta.status_code == 200
    resultados = respuesta.json()["resultados"]
    assert [r["producto_id"] for r in resultados] == [1, 2]

    medialuna = resultados[0]
    assert medialuna["nivel_confianza"] == "MEDIA"
    assert medialuna["predicciones"] == [{"fecha": "2026-11-02", "cantidad": 10.0}, {"fecha": "2026-11-03", "cantidad": 13.0}]

    scon = resultados[1]
    assert scon["nivel_confianza"] == "BAJA"
    assert scon["predicciones"][0]["cantidad"] == 6.0


def test_rechaza_datos_invalidos():
    pedido = {"productos": [{"producto_id": 1, "nombre_producto": "X",
                             "historial": [{"fecha": "2026-10-01", "cantidad_producida": -1, "cantidad_vendida": 1}],
                             "fechas_objetivo": [{"fecha": "2026-11-02", "tipo_dia": "INVENTADO"}]}]}
    assert cliente.post("/api/predecir-semana", json=pedido).status_code == 422
