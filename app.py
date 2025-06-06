#app para normalizar direcciones
from flask import Flask, request, jsonify
from postal.parser import parse_address
import re
import unicodedata
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

REEMPLAZOS = {
    "cra": "carrera",
    "cr": "carrera",
    "car": "carrera",
    "cll": "calle",
    "cl": "calle",
    "cal": "calle",
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

    # Extras
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
    texto = re.sub(r"[#\-·•…:,;|!\"\'\[\]\(\)\{\}<>@°+=*?^%$]", " ", texto)
    texto = re.sub(r"\b(nro|no|n°|n)\b", "", texto)
    for abreviado, completo in REEMPLAZOS.items():
        texto = re.sub(rf"\b{abreviado}\b", completo, texto)
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto

def crear_texto_para_parsear(texto):
    for palabra in PALABRAS_UNIDAD:
        texto = re.sub(rf'\b{palabra} (\d+)\b', rf'unidad_{palabra}_\1', texto)
    return texto

@app.route('/')
def home():
    return '¡Hola! Esta es la API de normalización de direcciones.'

@app.route('/normalizar', methods=['POST'])
def normalizar():
    try:
        data = request.get_json(force=True)
        direccion_original = data.get('DireccionIn', '')

        print(f"\n📥 Dirección original: {direccion_original}")

        if not direccion_original.strip():
            return jsonify({'error': 'No se proporcionó ninguna dirección'}), 400

        direccion_limpia = aplicar_reemplazos(direccion_original)
        print(f"🧼 Dirección limpia: {direccion_limpia}")

        direccion_para_parsear = crear_texto_para_parsear(direccion_limpia)
        print(f"🔍 Dirección para parsear: {direccion_para_parsear}")

        parsed = parse_address(direccion_para_parsear)
        print(f"📊 Resultado libpostal (bruto): {parsed}")

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

        print(f"✅ Componentes agrupados: {componentes_agrupados}")

        respuesta = {
            'direccion_original': direccion_original,
            'direccion_limpia': direccion_limpia,
            'direccion_normalizada': componentes_agrupados
        }

        return jsonify(respuesta)

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
