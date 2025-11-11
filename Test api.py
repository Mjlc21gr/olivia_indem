"""
Script de prueba para la API de Biometría Facial
Permite probar la API tanto localmente como en producción
"""

import requests
import json
import sys


def test_health_check(base_url):
    """Probar el health check endpoint"""
    print(f"\n🔍 Probando Health Check: {base_url}/")
    try:
        response = requests.get(f"{base_url}/", timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_biometria_endpoint(base_url, numero_documento="1007409364", tipo_documento="CC",
                            id_transaccion="983223933nn111"):
    """Probar el endpoint de biometría"""
    print(f"\n🔍 Probando Biometría: {base_url}/biometria")

    payload = {
        "tipoDocumento": tipo_documento,
        "numeroDocumento": numero_documento,
        "idTransaccion": id_transaccion
    }

    print(f"Payload: {json.dumps(payload, indent=2)}")

    try:
        response = requests.post(
            f"{base_url}/biometria",
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )

        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")

        # Verificar si la respuesta contiene una URL válida
        if response.status_code == 200:
            data = response.json()
            if data.get('success') and 'url' in data.get('data', {}):
                url = data['data']['url']
                print(f"✅ URL generada: {url}")

                # Verificar si es URL de biometría o onboarding
                if 'onboarding.davivienda.com' in url:
                    print("⚠️  ADVERTENCIA: Se recibió URL de onboarding, no de biometría")
                    return False
                else:
                    print("✅ URL de biometría correcta")
                    return True
            else:
                print("❌ Respuesta sin URL válida")
                return False
        else:
            print("❌ Error en la respuesta")
            return False

    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_endpoint_prueba(base_url, numero_documento="1007409364", tipo_documento="CC", id_transaccion="983223933nn111"):
    """Probar el endpoint de prueba"""
    print(f"\n🔍 Probando Endpoint de Prueba: {base_url}/test")

    try:
        response = requests.get(
            f"{base_url}/test?documento={numero_documento}&tipo={tipo_documento}&idTransaccion={id_transaccion}",
            timeout=30
        )

        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200

    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def main():
    """Función principal"""
    print("🚀 Iniciando pruebas de la API de Biometría Facial\n")

    # URLs a probar
    urls = [
        "http://localhost:8080",  # Local
    ]

    # Si se pasa una URL como argumento, usarla
    if len(sys.argv) > 1:
        urls = [sys.argv[1]]

    # Datos de prueba
    numero_documento = input("Número de documento (default: 1007409364): ").strip() or "1007409364"
    tipo_documento = input("Tipo de documento (default: CC): ").strip() or "CC"
    id_transaccion = input("ID Transacción (default: 983223933nn111): ").strip() or "983223933nn111"

    for base_url in urls:
        print(f"\n{'=' * 60}")
        print(f"🌐 Probando: {base_url}")
        print(f"{'=' * 60}")

        # Probar endpoints
        health_ok = test_health_check(base_url)
        biometria_ok = test_biometria_endpoint(base_url, numero_documento, tipo_documento, id_transaccion)
        test_ok = test_endpoint_prueba(base_url, numero_documento, tipo_documento, id_transaccion)

        # Resumen
        print(f"\n📊 Resumen para {base_url}:")
        print(f"   Health Check: {'✅' if health_ok else '❌'}")
        print(f"   Biometría:    {'✅' if biometria_ok else '❌'}")
        print(f"   Test:         {'✅' if test_ok else '❌'}")

        if health_ok and biometria_ok and test_ok:
            print(f"🎉 Todos los tests pasaron para {base_url}")
        else:
            print(f"⚠️  Algunos tests fallaron para {base_url}")


if __name__ == "__main__":
    main()