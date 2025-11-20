"""
API de Biometría Facial - Seguros Bolívar
Flask application para generar URLs de biometría facial y convertir audio a base64
"""

import os
import json
import time
import random
import string
import requests
from flask import Flask, request, jsonify
from datetime import datetime
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)


# Configuración de la API de Seguros Bolívar
class SegurosBolivarAPI:
    def __init__(self):
        self.client_id = os.getenv('SEGUROS_CLIENT_ID', '7p2djtisjjsng91q8laktkmp36')
        self.client_secret = os.getenv('SEGUROS_CLIENT_SECRET', '1ocv4ohfjqu69r7cukebhccbk51panhqdgfl31fu2og49d3hmk1s')
        self.token_url = 'https://api-conecta.segurosbolivar.com/prod/oauth2/token'
        self.biometric_url = 'https://api-conecta.segurosbolivar.com/prod/identidadDigital/biometria/facial/url'
        self.access_token = None
        self.token_expiry = None

    def generar_id_transaccion(self):
        """Genera un ID único para la transacción"""
        timestamp = str(int(time.time()))
        random_str = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
        return f"{timestamp}{random_str}"

    def obtener_token(self):
        """Obtiene el token de acceso OAuth2"""
        try:
            payload = {
                'grant_type': 'client_credentials',
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'scope': 'aws.cognito.signin.user.admin SrcServerCognitoConecta/ConectaApiScope'
            }

            headers = {
                'Content-Type': 'application/x-www-form-urlencoded'
            }

            logger.info("Solicitando token OAuth2...")
            response = requests.post(self.token_url, data=payload, headers=headers, timeout=30)

            if response.status_code != 200:
                logger.error(f"Error al obtener token: {response.status_code} - {response.text}")
                return None

            data = response.json()
            self.access_token = data.get('access_token')
            # Calcular expiración (por defecto 1 hora)
            expires_in = data.get('expires_in', 3600)
            self.token_expiry = time.time() + expires_in - 60  # 1 minuto de margen

            logger.info("Token obtenido exitosamente")
            return self.access_token

        except Exception as e:
            logger.error(f"Error en obtener_token: {str(e)}")
            return None

    def token_valido(self):
        """Verifica si el token actual es válido"""
        return (self.access_token is not None and
                self.token_expiry is not None and
                time.time() < self.token_expiry)

    def consultar_biometria_facial(self, numero_documento, tipo_documento='CC', id_transaccion=None):
        """Consulta la URL de biometría facial"""
        try:
            # Verificar/obtener token
            if not self.token_valido():
                if not self.obtener_token():
                    return {
                        'error': True,
                        'message': 'No se pudo obtener el token de acceso'
                    }

            # Usar ID de transacción proporcionado o generar uno nuevo
            transaction_id = id_transaccion or self.generar_id_transaccion()

            # Preparar headers (valores fijos como en Apps Script)
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'X-Channel': 'SEGUROS_BOLIVAR',
                'X-IPAddr': '186.82.101.105',
                'X-Id_transaction': transaction_id,
                'process': 'indem_patri',
                'Content-Type': 'application/json'
            }

            # Preparar body
            body_data = {
                'userData': {
                    'userId': str(numero_documento),
                    'userType': tipo_documento
                }
            }

            logger.info(f"Consultando biometría para documento: {numero_documento}")
            logger.info(f"Headers: {headers}")
            logger.info(f"Body: {json.dumps(body_data)}")

            response = requests.post(
                self.biometric_url,
                json=body_data,
                headers=headers,
                timeout=30
            )

            logger.info(f"Status code: {response.status_code}")
            logger.info(f"Response: {response.text}")

            if response.status_code != 200:
                return {
                    'error': True,
                    'message': f'API Error {response.status_code}: {response.text}',
                    'status_code': response.status_code
                }

            return response.json()

        except requests.exceptions.RequestException as e:
            logger.error(f"Error de conexión: {str(e)}")
            return {
                'error': True,
                'message': f'Error de conexión: {str(e)}'
            }
        except Exception as e:
            logger.error(f"Error en consultar_biometria_facial: {str(e)}")
            return {
                'error': True,
                'message': f'Error interno: {str(e)}'
            }


# Instancia global de la API
seguros_api = SegurosBolivarAPI()


@app.route('/', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'Seguros Bolívar Biometric API',
        'timestamp': datetime.now().isoformat()
    })


@app.route('/biometria', methods=['POST'])
def generar_url_biometria():
    """Endpoint principal para generar URL de biometría facial"""
    try:
        # Log request para debugging
        logger.info(f"Request method: {request.method}")
        logger.info(f"Request headers: {dict(request.headers)}")
        logger.info(f"Request content type: {request.content_type}")
        logger.info(f"Request data: {request.data}")

        # Intentar obtener datos del request de múltiples formas
        data = None

        # Método 1: JSON estándar
        try:
            data = request.get_json(force=True)
            logger.info(f"JSON data (method 1): {data}")
        except Exception as e:
            logger.warning(f"Failed to parse JSON with method 1: {e}")

        # Método 2: Si falla, intentar parsear manualmente
        if not data:
            try:
                raw_data = request.get_data(as_text=True)
                logger.info(f"Raw data: {raw_data}")
                if raw_data:
                    data = json.loads(raw_data)
                    logger.info(f"JSON data (method 2): {data}")
            except Exception as e:
                logger.warning(f"Failed to parse JSON with method 2: {e}")

        # Método 3: Intentar desde form data
        if not data and request.form:
            try:
                data = request.form.to_dict()
                logger.info(f"Form data (method 3): {data}")
            except Exception as e:
                logger.warning(f"Failed to parse form data: {e}")

        if not data:
            logger.error("No se pudo obtener datos del request")
            return jsonify({
                'error': True,
                'message': 'Body JSON requerido',
                'debug': {
                    'content_type': request.content_type,
                    'method': request.method,
                    'headers': dict(request.headers),
                    'raw_data': request.get_data(as_text=True)[:500]  # Primeros 500 chars
                }
            }), 400

        # Solo estos 3 campos son requeridos del JSON
        numero_documento = data.get('numeroDocumento')
        tipo_documento = data.get('tipoDocumento', 'CC')
        id_transaccion = data.get('idTransaccion')

        if not numero_documento:
            return jsonify({
                'error': True,
                'message': 'numeroDocumento es requerido'
            }), 400

        # Consultar API (IP fija, otros valores quemados)
        resultado = seguros_api.consultar_biometria_facial(
            numero_documento=numero_documento,
            tipo_documento=tipo_documento,
            id_transaccion=id_transaccion
        )

        if resultado.get('error'):
            status_code = resultado.get('status_code', 500)
            return jsonify(resultado), status_code

        # Procesar la respuesta para modificar la URL
        if resultado.get('data') and resultado['data'].get('url'):
            # Remover https:// de la URL
            original_url = resultado['data']['url']
            if original_url.startswith('https://'):
                resultado['data']['url'] = original_url.replace('https://', '')
                logger.info(f"URL procesada: {original_url} -> {resultado['data']['url']}")

        # Respuesta exitosa
        return jsonify({
            'success': True,
            'data': resultado,
            'input': {
                'numeroDocumento': numero_documento,
                'tipoDocumento': tipo_documento,
                'idTransaccion': id_transaccion
            },
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"Error en generar_url_biometria: {str(e)}")
        return jsonify({
            'error': True,
            'message': f'Error interno del servidor: {str(e)}'
        }), 500


@app.route('/test', methods=['GET'])
def test_endpoint():
    """Endpoint de prueba con datos predeterminados"""
    numero_documento = request.args.get('documento', '1007409364')
    tipo_documento = request.args.get('tipo', 'CC')
    id_transaccion = request.args.get('idTransaccion', '983223933nn111')

    resultado = seguros_api.consultar_biometria_facial(
        numero_documento=numero_documento,
        tipo_documento=tipo_documento,
        id_transaccion=id_transaccion
    )

    return jsonify({
        'test': True,
        'input': {
            'numeroDocumento': numero_documento,
            'tipoDocumento': tipo_documento,
            'idTransaccion': id_transaccion
        },
        'resultado': resultado,
        'timestamp': datetime.now().isoformat()
    })


@app.route('/token/refresh', methods=['POST'])
def refresh_token():
    """Endpoint para forzar refresh del token"""
    resultado = seguros_api.obtener_token()

    if resultado:
        return jsonify({
            'success': True,
            'message': 'Token renovado exitosamente',
            'timestamp': datetime.now().isoformat()
        })
    else:
        return jsonify({
            'error': True,
            'message': 'Error al renovar token'
        }), 500


@app.route('/audio_base64', methods=['POST'])
def convertir_audio_base64():
    """Endpoint para convertir audio URL a base64 usando Google Apps Script"""
    try:
        # Log request para debugging
        logger.info(f"Request method: {request.method}")
        logger.info(f"Request headers: {dict(request.headers)}")
        logger.info(f"Request content type: {request.content_type}")
        logger.info(f"Request data: {request.data}")

        # Obtener datos del request (usando la misma lógica robusta del endpoint biometria)
        data = None

        # Método 1: JSON estándar
        try:
            data = request.get_json(force=True)
            logger.info(f"JSON data (method 1): {data}")
        except Exception as e:
            logger.warning(f"Failed to parse JSON with method 1: {e}")

        # Método 2: Si falla, intentar parsear manualmente
        if not data:
            try:
                raw_data = request.get_data(as_text=True)
                logger.info(f"Raw data: {raw_data}")
                if raw_data:
                    data = json.loads(raw_data)
                    logger.info(f"JSON data (method 2): {data}")
            except Exception as e:
                logger.warning(f"Failed to parse JSON with method 2: {e}")

        # Método 3: Intentar desde form data
        if not data and request.form:
            try:
                data = request.form.to_dict()
                logger.info(f"Form data (method 3): {data}")
            except Exception as e:
                logger.warning(f"Failed to parse form data: {e}")

        if not data:
            logger.error("No se pudo obtener datos del request")
            return jsonify({
                'error': True,
                'message': 'Body JSON requerido',
                'debug': {
                    'content_type': request.content_type,
                    'method': request.method,
                    'headers': dict(request.headers),
                    'raw_data': request.get_data(as_text=True)[:500]
                }
            }), 400

        # Validar campos requeridos (solo audio_url e id_session)
        audio_url = data.get('audio_url')
        id_session = data.get('id_session')

        if not audio_url:
            return jsonify({
                'error': True,
                'message': 'audio_url es requerido'
            }), 400

        if not id_session:
            return jsonify({
                'error': True,
                'message': 'id_session es requerido'
            }), 400

        # Auth token fijo (configurado internamente)
        auth_token = "4ea2df623fed2f34af5b27c258f47581-e418b99d-1476-4103-a128-a5a7b8e28778"

        # URL del Google Apps Script
        apps_script_url = 'https://script.google.com/macros/s/AKfycbx4Vho2TiRvTDdCZoKeLVzxXjGfigyf74YqwbLnHkQdXpn-4JHqhqu8lIpZIgzXoA3svQ/exec'

        # Preparar payload para Apps Script (incluyendo auth_token fijo)
        payload = {
            'audio_url': audio_url,
            'id_session': id_session,
            'auth_token': auth_token
        }

        # Headers para la petición
        headers = {
            'Content-Type': 'application/json'
        }

        logger.info(f"Enviando petición a Apps Script: {apps_script_url}")
        logger.info(f"Payload: {json.dumps(payload)}")

        # Hacer petición al Google Apps Script
        response = requests.post(
            apps_script_url,
            json=payload,
            headers=headers,
            timeout=60  # Timeout más largo para procesamiento de audio
        )

        logger.info(f"Apps Script response status: {response.status_code}")
        logger.info(f"Apps Script response: {response.text}")

        if response.status_code != 200:
            return jsonify({
                'error': True,
                'message': f'Error en Google Apps Script: {response.status_code}',
                'details': response.text,
                'input': {
                    'audio_url': audio_url,
                    'id_session': id_session
                }
            }), 500

        # Parsear respuesta del Apps Script
        try:
            apps_script_response = response.json()
        except Exception as e:
            logger.error(f"Error parsing Apps Script response: {e}")
            return jsonify({
                'error': True,
                'message': 'Error parsing response from Google Apps Script',
                'raw_response': response.text,
                'input': {
                    'audio_url': audio_url,
                    'id_session': id_session
                }
            }), 500

        # Retornar la respuesta del Apps Script tal como viene
        return jsonify(apps_script_response)

    except requests.exceptions.RequestException as e:
        logger.error(f"Error de conexión con Google Apps Script: {str(e)}")
        return jsonify({
            'error': True,
            'message': f'Error de conexión con Google Apps Script: {str(e)}'
        }), 500
    except Exception as e:
        logger.error(f"Error en convertir_audio_base64: {str(e)}")
        return jsonify({
            'error': True,
            'message': f'Error interno del servidor: {str(e)}'
        }), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)