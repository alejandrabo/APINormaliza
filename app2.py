#Normalización - conexión con google maps - coordenadas exactas
##clave google maps: AIzaSyCGZa-B855BN32OIaI1fdRQTvem_ibLsgY
from flask import Flask, request, jsonify
from postal.parser import parse_address
import re
import unicodedata
from flask_cors import CORS
import requests
import pyodbc
 
# Configuración de la conexión a SQL Server
conn_str = "DRIVER={ODBC Driver 17 for SQL Server};SERVER=172.16.1.160;DATABASE=TransporteQA;UID=DevTransporte;PWD=Sol.2022"
conexion = pyodbc.connect(conn_str)
app = Flask(__name__)
CORS(app)

# clave de API:
GOOGLE_API_KEY = 'AIzaSyCGZa-B855BN32OIaI1fdRQTvem_ibLsgY'

REEMPLAZOS = {
    "cra": "carrera",
    "cr": "carrera",
    "carrera": "carrera",
    "carr": "carrera",
    "cll": "calle",
    "calle": "calle",
    "cal": "calle",
    "clle": "calle",
    "call": "calle",
    "dg": "diagonal",
    "diag": "diagonal",
    "av": "avenida",
    "av.": "avenida",
    "ak": "autopista",
    "aut": "autopista",
    "tv": "transversal",
    "transv": "transversal",
    "bta": "bogota",
    "pte": "puente",
    "pto": "puerto",
    "mz": "manzana",
    "lt": "lote",
    "et": "etapa",
    "urb": "urbanizacion",
    "int": "interior",
    "ed": "edificio",
    "bod": "bodega",
    "pqi": "parque industrial",
    "nro": "",
    "no": "",
    "n°": "",
    "n": ""
}

TRADUCCION_COMPONENTES = {
    'house_number': 'numero',
    'road': 'via',
    'unit': 'unidad',
    'suburb': 'barrio',
    'city': 'ciudad',
    'state': 'departamento',
    'postcode': 'codigo_postal',
    'country': 'pais',
    'level': 'nivel',
    'staircase': 'escalera',
    'entrance': 'entrada',
    'apto': 'apartamento',
    'int': 'interior',
    'edificio': 'edificio',
    'bodega': 'bodega',
    'conjunto': 'conjunto',
    'urbanizacion': 'urbanizacion',
    'parque industrial': 'parque_industrial'
}

PALABRAS_UNIDAD = [
    'bodega', 'interior', 'apto', 'apartamento', 'manzana', 'lote',
    'torre', 'bloque', 'etapa', 'edificio', 'conjunto', 'urbanizacion', 'parque industrial'
]

def quitar_tildes(texto):
    return ''.join(
        c for c in unicodedata.normalize('NFD', texto)
        if unicodedata.category(c) != 'Mn'
    )

def aplicar_reemplazos(texto):
    texto = texto.lower()
    texto = quitar_tildes(texto)
    texto = re.sub(r"[#\-.·•…:,;|!\"\'\[\]\(\)\{\}<>@°+=*?^%$]", " ", texto)
    texto = re.sub(r"\b(nro|no|n°|n)\b", "", texto)
    for abreviado, completo in REEMPLAZOS.items():
        texto = re.sub(rf"\b{abreviado}\b", completo, texto)
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto

def crear_texto_para_parsear(texto):
    for palabra in PALABRAS_UNIDAD:
        texto = re.sub(rf'\b{palabra} (\d+)\b', rf'unidad_{palabra}_\1', texto)
    return texto

#para verificar que existe en la base de datos

def buscar_coordenadas_en_bd(direccion_normalizada):
    cursor = conexion.cursor()
    query = "SELECT LisDesCY, LisDes FROM DireccionesGeoreferenciadas WHERE LisDesDirTra = ?"
    cursor.execute(query, (direccion_normalizada,))
    fila = cursor.fetchone()
    return {'latitud': fila[0], 'longitud': fila[1]} if fila else None

def obtener_coordenadas(direccion, api_key):
    url = 'https://maps.googleapis.com/maps/api/geocode/json'
    params = {'address': direccion, 'key': api_key}
    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json()
        if data['results']:
            location = data['results'][0]['geometry']['location']
        return {
        'latitud': round(location['lat'], 11),
        'longitud': round(location['lng'], 11)
        } 
    return None

@app.route('/')
def home():
    return '¡Hola! Esta es la API de normalización de direcciones con geolocalización.'

@app.route('/normalizar', methods=['POST'])
def normalizar():
    try:
        data = request.get_json(force=True)
        direccion_original = data.get('DireccionIn', '').strip()

        if not direccion_original:
            return jsonify({'error': 'No se proporcionó ninguna dirección'}), 400

        direccion_limpia = aplicar_reemplazos(direccion_original)
        direccion_para_parsear = crear_texto_para_parsear(direccion_limpia)
        parsed = parse_address(direccion_para_parsear)

        componentes_agrupados = {}
        for value, label in parsed:
            if value.startswith('unidad_'):
                partes = value.split('_')
                tipo = 'unidad'
                valor = f"{partes[1]} {partes[2]}"
            else:
                tipo = TRADUCCION_COMPONENTES.get(label, label)
                valor = value

            if tipo not in componentes_agrupados:
                componentes_agrupados[tipo] = []
            componentes_agrupados[tipo].append(valor)

        direccion_normalizada = " ".join([
            f"{k}:{' '.join(v)}" for k, v in componentes_agrupados.items()
        ])

        # 🔍 Buscar en la base de datos
        coords = buscar_coordenadas_en_bd(direccion_normalizada)
        if coords:
            return jsonify({
                'direccion_original': direccion_original,
                'direccion_limpia': direccion_limpia,
                'direccion_normalizada': direccion_normalizada,
                'coordenadas': coords,
                'mensaje': '✅ Coordenadas ya existen en la base de datos'
            })

        # 🧭 Llamar a la API de Google si no existe
        coords = obtener_coordenadas(direccion_limpia, api_key)
        if coords:
            guardar_en_bd(direccion_limpia, direccion_normalizada, coords['latitud'], coords['longitud'])
            return jsonify({
                'direccion_original': direccion_original,
                'direccion_limpia': direccion_limpia,
                'direccion_normalizada': direccion_normalizada,
                'coordenadas': coords,
                'mensaje': '✅ Coordenadas obtenidas de Google Maps'
            })

        return jsonify({
            'direccion_original': direccion_original,
            'direccion_limpia': direccion_limpia,
            'direccion_normalizada': direccion_normalizada,
            'mensaje': '❌ No se pudieron obtener coordenadas'
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
