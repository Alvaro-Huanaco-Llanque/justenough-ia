import os
import sys

# Permite importar main.py, prediccion.py y caso_compartido.py desde los tests
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
