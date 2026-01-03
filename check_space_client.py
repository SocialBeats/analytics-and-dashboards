"""
Script de diagnóstico para verificar el estado del cliente SPACE
Ejecutar con: python check_space_client.py
"""

import asyncio
import sys
from pathlib import Path

# Añadir el directorio raíz al path para importar módulos
sys.path.insert(0, str(Path(__file__).parent))

from app.core.config import settings
from app.utils.space_connection import SpaceClient, get_space_client, is_pricing_enabled


def print_section(title: str):
    """Imprime un título de sección formateado"""
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print("=" * 70)


def print_check(label: str, value: any, is_ok: bool = None):
    """Imprime una línea de verificación con formato"""
    if is_ok is None:
        print(f"   {label}: {value}")
    else:
        symbol = "✓" if is_ok else "✗"
        print(f"   {symbol} {label}: {value}")


def check_configuration():
    """Verifica la configuración de SPACE desde las variables de entorno"""
    print_section("1. CONFIGURACIÓN DE VARIABLES DE ENTORNO")

    # ENABLE_PRICING
    pricing_enabled = settings.ENABLE_PRICING
    print_check("ENABLE_PRICING", pricing_enabled, is_ok=pricing_enabled)

    # SPACE_URL
    space_url = settings.SPACE_URL
    print_check("SPACE_URL", space_url)

    # SPACE_API_KEY
    has_api_key = bool(settings.SPACE_API_KEY)
    if has_api_key:
        masked_key = (
            f"***{settings.SPACE_API_KEY[-4:]}" if len(settings.SPACE_API_KEY) > 4 else "***"
        )
        print_check("SPACE_API_KEY", masked_key, is_ok=True)
    else:
        print_check("SPACE_API_KEY", "NO CONFIGURADA", is_ok=False)

    return pricing_enabled, has_api_key


def check_pricing_status():
    """Verifica el estado del sistema de pricing"""
    print_section("2. ESTADO DEL SISTEMA DE PRICING")

    pricing_enabled = is_pricing_enabled()
    print_check("is_pricing_enabled()", f"{pricing_enabled}", is_ok=pricing_enabled)

    if not pricing_enabled:
        print("\n   ⚠️  ADVERTENCIA: El pricing está deshabilitado.")
        print("      Para habilitarlo, configura ENABLE_PRICING=True en .env")

    return pricing_enabled


def check_client_instance():
    """Verifica la instancia del cliente SPACE"""
    print_section("3. INSTANCIA DEL CLIENTE SPACE")

    client = get_space_client()

    if client is None:
        print_check("get_space_client()", "None", is_ok=False)
        print("\n   ❌ El cliente SPACE NO está disponible")
        print("   Posibles razones:")
        print("      - ENABLE_PRICING está en False")
        print("      - SPACE_API_KEY no está configurada")
        return None

    elif isinstance(client, SpaceClient):
        print_check("get_space_client()", "SpaceClient instance", is_ok=True)
        print_check("URL del cliente", client.url)
        print_check("API Key presente", bool(client.api_key), is_ok=True)
        print("\n   ✅ El cliente SPACE está correctamente configurado")
        return client

    else:
        print_check("get_space_client()", f"Tipo inesperado: {type(client)}", is_ok=False)
        return None


async def test_connection(client: SpaceClient):
    """Prueba la conexión con el servidor SPACE"""
    print_section("4. PRUEBA DE CONEXIÓN CON SPACE")

    if client is None:
        print("   ⏭️  Omitiendo prueba (cliente no disponible)")
        return False

    try:
        print(f"   Intentando conectar a: {client.url}")
        async with client:
            print("   ✅ Cliente HTTP inicializado correctamente")

            # Verificar que el servidor SPACE está activo
            print("\n   Verificando que el servidor SPACE está activo...")
            health_endpoint = "/api/v1/healthcheck"
            full_url = f"{client.url}{health_endpoint}"
            print(f"   Intentando acceder a: {full_url}")

            try:
                response = await client._client.get(health_endpoint)
                response.raise_for_status()
                print(f"   ✅ Servidor SPACE activo (Status: {response.status_code})")

                # Mostrar la respuesta del health check
                try:
                    health_data = response.json()
                    print(f"   Respuesta: {health_data}")
                except:
                    print(f"   Respuesta: {response.text}")

                return True

            except Exception as health_error:
                print(f"   ❌ Error al verificar health: {str(health_error)}")
                print(f"   Tipo de error: {type(health_error).__name__}")

                if "ConnectError" in str(type(health_error).__name__):
                    print("   💡 No se pudo conectar - el servidor SPACE no está ejecutándose")
                elif "TimeoutException" in str(type(health_error).__name__):
                    print("   💡 Timeout - el servidor SPACE no responde")
                elif "404" in str(health_error):
                    print("   ⚠️  Endpoint /api/v1/healthcheck no encontrado")
                    print("   💡 Intenta verificar la URL correcta del health check de SPACE")
                else:
                    print(f"   💡 El servidor SPACE podría no estar ejecutándose en: {client.url}")
                    print(f"   💡 O puede haber un problema con la configuración de la URL")
                return False

    except Exception as e:
        print(f"   ❌ Error de conexión: {str(e)}")
        print(f"\n   Detalles del error: {type(e).__name__}")
        print("   💡 El servidor SPACE podría no estar ejecutándose")
        print(f"      Verifica que SPACE esté corriendo en: {client.url}")
        return False


def print_usage_examples():
    """Muestra ejemplos de uso del cliente"""
    print_section("5. EJEMPLOS DE USO")

    print("""
   Ejemplo 1 - Verificar si el cliente está disponible:
   ─────────────────────────────────────────────────────
   from app.utils.space_connection import get_space_client

   client = get_space_client()
   if client:
       print("✓ Pricing disponible")
   else:
       print("✗ Pricing NO disponible")


   Ejemplo 2 - Usar el cliente con context manager:
   ─────────────────────────────────────────────────────
   from app.utils.space_connection import get_space_client

   client = get_space_client()
   if client:
       async with client:
           result = await client.evaluate_feature(
               user_id="user123",
               feature_name="analytics-maxDashboards",
               consumption={"maxDashboards": 1}
           )
           if result["eval"]:
               print("✓ Usuario puede crear dashboard")
           else:
               print("✗ Usuario ha alcanzado el límite")


   Ejemplo 3 - Usar el cliente global:
   ─────────────────────────────────────────────────────
   from app.utils.space_connection import space_client

   if space_client:
       async with space_client:
           features = await space_client.get_all_features_for_user("user123")
           print(f"Features del usuario: {features}")
    """)


def print_summary(
    pricing_enabled: bool, has_api_key: bool, client_available: bool, connection_ok: bool
):
    """Imprime un resumen del diagnóstico"""
    print_section("6. RESUMEN DEL DIAGNÓSTICO")

    issues = []

    # Verificar cada componente
    if not pricing_enabled:
        issues.append("ENABLE_PRICING está deshabilitado")

    if not has_api_key:
        issues.append("SPACE_API_KEY no está configurada")

    if not client_available:
        issues.append("El cliente SPACE no pudo ser inicializado")

    if client_available and not connection_ok:
        issues.append("No se pudo conectar al servidor SPACE")

    # Mostrar resultado
    if not issues:
        print("\n   🎉 ¡TODO ESTÁ CORRECTO!")
        print("   El sistema de pricing está completamente funcional.")
        print(f"\n   Estado final:")
        print(f"      • Pricing habilitado: ✅")
        print(f"      • API Key configurada: ✅")
        print(f"      • Cliente disponible: ✅")
        print(f"      • Conexión exitosa: ✅")
    else:
        print("\n   ⚠️  SE ENCONTRARON PROBLEMAS:")
        for i, issue in enumerate(issues, 1):
            print(f"      {i}. {issue}")

        print(f"\n   Estado final:")
        print(f"      • Pricing habilitado: {'✅' if pricing_enabled else '❌'}")
        print(f"      • API Key configurada: {'✅' if has_api_key else '❌'}")
        print(f"      • Cliente disponible: {'✅' if client_available else '❌'}")
        print(f"      • Conexión exitosa: {'✅' if connection_ok else '❌'}")

        print("\n   💡 SOLUCIONES SUGERIDAS:")
        if not pricing_enabled:
            print("      → Añade ENABLE_PRICING=True a tu archivo .env")
        if not has_api_key:
            print("      → Añade SPACE_API_KEY=tu_api_key a tu archivo .env")
        if client_available and not connection_ok:
            print(
                f"      → Verifica que el servidor SPACE esté ejecutándose en {settings.SPACE_URL}"
            )
            print("      → Comprueba que la API key sea correcta")


async def main():
    """Función principal que ejecuta todos los diagnósticos"""
    print("\n")
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 15 + "DIAGNÓSTICO DEL CLIENTE SPACE" + " " * 24 + "║")
    print("╚" + "═" * 68 + "╝")

    # 1. Verificar configuración
    pricing_enabled, has_api_key = check_configuration()

    # 2. Verificar estado del pricing
    pricing_enabled = check_pricing_status()

    # 3. Verificar instancia del cliente
    client = check_client_instance()
    client_available = client is not None

    # 4. Probar conexión
    connection_ok = False
    if client:
        connection_ok = await test_connection(client)
    else:
        print_section("4. PRUEBA DE CONEXIÓN CON SPACE")
        print("   ⏭️  Omitiendo prueba (cliente no disponible)")

    # 5. Mostrar ejemplos de uso
    print_usage_examples()

    # 6. Mostrar resumen
    print_summary(pricing_enabled, has_api_key, client_available, connection_ok)

    print("\n" + "═" * 70 + "\n")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Diagnóstico interrumpido por el usuario")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n❌ Error fatal durante el diagnóstico: {str(e)}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
