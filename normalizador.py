from postal.expand import expand_address
from unidecode import unidecode
import re

def normalizar_direccion(direccion_original):
    direccion = unidecode(direccion_original).lower()
    variantes = expand_address(direccion)
    direccion_expandida = variantes[0] if variantes else direccion
    direccion_final = re.sub(r'\s+', ' ', direccion_expandida).strip()
    return direccion_final