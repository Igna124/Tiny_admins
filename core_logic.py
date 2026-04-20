# src/core_logic.py
# Contiene la lógica central: obtención de datos de la API del Banco Mundial,
# procesamiento de datos y la comunicación con el servidor 32-bit usando Client64.

import requests
import sys
import ctypes # Aún necesario para c_float si no se usa __getattr__ o para claridad
import os
from typing import Optional, List, Dict, Any
import platform

# --- Importar Client64 de msl-loadlib ---
try:
    from msl.loadlib import Client64
    from msl.loadlib.exceptions import Server32Error # Para capturar errores del server
except ImportError:
    print("ERROR: 'msl-loadlib' no está instalado. Ejecuta './setup.sh' o 'pip install msl-loadlib'", file=sys.stderr)
    sys.exit(1)

# --- Constantes API ---
BASE_URL = "https://api.worldbank.org/v2/en/country"
INDICATOR = "SI.POV.GINI"
DATE_RANGE = "2011:2020" # Rango de años para buscar datos
PER_PAGE = "100"        # Registros por página (para evitar paginación simple)

# --- Configuración del Cliente 64-bit ---
# Nombre del módulo Python que contiene la clase Server32 (sin .py)
SERVER_MODULE_NAME = 'server32_bridge' # Apunta al nuevo nombre de archivo

# Variable global para la instancia del cliente (se inicializa una sola vez)
_gini_client_instance = None

class GiniClient64(Client64):
    """Cliente 64-bit para comunicarse con GiniProcessorServer (32-bit)."""
    def __init__(self):
        print(f"[Client64] Inicializando GiniClient64...", file=sys.stderr)
        print(f"[Client64] Arquitectura Python: {platform.architecture()[0]}", file=sys.stderr) # Debería ser 64bit
        try:
            # Inicializa Client64, apuntando al módulo del servidor 32-bit
            # msl-loadlib buscará src/server32_bridge.py y lo ejecutará en un Python 32-bit
            super().__init__(module32=SERVER_MODULE_NAME)
            print(f"[Client64] Conectado al servidor 32-bit '{SERVER_MODULE_NAME}'.", file=sys.stderr)
        except Exception as e:
            print(f"[Client64] FATAL ERROR durante la inicialización: {type(e).__name__}: {e}", file=sys.stderr)
            print("[Client64] Posibles causas: Python 32-bit no encontrado, error en server32_bridge.py.", file=sys.stderr)
            import traceback
            traceback.print_exc(file=sys.stderr)
            raise # Re-lanza para indicar fallo

    # --- Método explícito para llamar a la función del servidor ---
    # Es más claro que usar __getattr__ para un solo método.
    def process_gini_float_on_server(self, gini_value: float) -> int:
        """
        Envía una petición al método 'process_gini_float' en el GiniProcessorServer.
        """
        print(f"[Client64] Enviando petición 'process_gini_float' con valor: {gini_value}", file=sys.stderr)
        # Llama al método 'process_gini_float' en la instancia del Server32 remoto.
        # Los argumentos se pasan directamente.
        return self.request32('process_gini_float', gini_value)

def _get_client() -> Optional[GiniClient64]:
    """Obtiene o crea la instancia singleton del cliente GiniClient64."""
    global _gini_client_instance
    if _gini_client_instance is None:
        print("[CoreLogic] Creando instancia de GiniClient64...", file=sys.stderr)
        try:
            _gini_client_instance = GiniClient64()
        except Exception as e:
            # Fallo al crear el cliente (ya se imprimió el error en __init__)
            print(f"[CoreLogic] No se pudo crear la instancia de GiniClient64: {e}", file=sys.stderr)
            _gini_client_instance = None # Asegura que siga siendo None
    return _gini_client_instance

# --- Función Principal de Procesamiento con C/ASM ---
def process_gini_with_c_asm(gini_value: float) -> Optional[int]:
    """
    Orquesta la llamada a la función C/ASM a través del puente msl-loadlib.

    Args:
        gini_value: El valor GINI float a procesar.

    Returns:
        El resultado entero del procesamiento C/ASM, o None si ocurre un error.
    """
    client = _get_client()
    if client is None:
        print("[CoreLogic] No se puede procesar con C/ASM: El cliente 64-bit no está disponible.", file=sys.stderr)
        return None

    try:
        # Llama al método definido en GiniClient64
        result = client.process_gini_float_on_server(gini_value)
        print(f"[CoreLogic] Resultado recibido del servidor 32-bit: {result}", file=sys.stderr)
        return result
    except Server32Error as e:
        # Error específico del proceso del servidor 32-bit
        print(f"[CoreLogic] Error recibido del servidor 32-bit: {e}", file=sys.stderr)
        return None
    except Exception as e:
        # Otros errores (conexión, etc.)
        print(f"[CoreLogic] Error durante la comunicación con el servidor 32-bit: {type(e).__name__}: {e}", file=sys.stderr)
        return None

# --- Obtención de Datos de la API (sin cambios respecto al original) ---
def get_gini_data(country_code: str) -> tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
    """
    Obtiene datos del índice GINI desde la API del Banco Mundial.
    Devuelve (lista_de_registros, None) en éxito, o (None, mensaje_de_error) en fallo.
    Una lista vacía [] significa que no hay datos para el país/periodo.
    """
    url = f"{BASE_URL}/{country_code}/indicator/{INDICATOR}"
    params = {"format": "json", "date": DATE_RANGE, "per_page": PER_PAGE}
    print(f"[CoreLogic] Solicitando URL: {url} con params: {params}", file=sys.stderr)
    error_message = None
    try:
        response = requests.get(url, params=params, timeout=15) # Timeout de 15s
        print(f"[CoreLogic] Código de estado HTTP: {response.status_code}", file=sys.stderr)

        # Verifica si la respuesta es JSON antes de decodificar
        content_type = response.headers.get('Content-Type', '')
        if 'application/json' not in content_type:
            error_detail = f"La API no devolvió JSON. Content-Type: {content_type}. Respuesta: {response.text[:200]}..."
            print(f"Error: {error_detail}", file=sys.stderr)
            # Intenta dar un mensaje más útil basado en errores comunes de la API
            if response.text and 'Invalid format' in response.text: error_message = "Error API Banco Mundial: Formato inválido o recurso no encontrado."
            elif response.text and 'Invalid value' in response.text: error_message = f"Error API Banco Mundial: ¿Código de país inválido '{country_code}'?"
            else: error_message = "Respuesta no JSON recibida del servidor."
            return None, error_message

        response.raise_for_status() # Lanza HTTPError para códigos 4xx/5xx

        data = response.json()

        # --- Análisis de la respuesta JSON ---
        # Formato esperado: [[{paginación}], [{datos}]] o a veces [{mensaje de error}]
        if not isinstance(data, list) or len(data) < 1:
            error_message = "Formato de respuesta inesperado (no es lista o está vacía)."
            print(f"Error: {error_message} Respuesta: {data}", file=sys.stderr)
            return None, error_message

        # Chequeo de mensaje de error explícito de la API
        if isinstance(data[0], dict) and "message" in data[0]:
            error_messages = [msg.get("value", "Error desconocido") for msg in data[0]["message"]]
            error_text = "\n".join(error_messages)
            print(f"Error de la API del Banco Mundial: {error_text}", file=sys.stderr)
            # Si el error es "sin datos", devolvemos lista vacía (no es un error fatal)
            if any("No data available" in msg for msg in error_messages) or \
               any("No matches" in msg for msg in error_messages):
                return [], None # No hay datos, pero la consulta fue válida
            else:
                error_message = f"Error API Banco Mundial:\n{error_text}"
                return None, error_message # Otro tipo de error

        # Formato esperado: data[1] contiene la lista de registros
        if len(data) == 2:
            if data[1] is None: # A veces devuelve [pagination, null] si no hay datos
                return [], None # No hay datos
            if not isinstance(data[1], list):
                error_message = f"Formato de datos inesperado (data[1] no es lista). Tipo: {type(data[1])}"
                print(f"Error: {error_message}", file=sys.stderr)
                return None, "Estructura de datos inesperada del servidor."
            # Éxito: devuelve la lista de registros
            return data[1], None
        # Caso raro: a veces devuelve solo [{paginación}] si total=0
        elif len(data) == 1 and isinstance(data[0], dict) and "total" in data[0] and data[0]["total"] == 0:
            return [], None # No hay datos
        else:
            # Estructura no reconocida
            print(f"Advertencia: Estructura de respuesta no manejada (longitud {len(data)}). Asumiendo sin datos.", file=sys.stderr)
            return [], None

    # --- Manejo de Excepciones de `requests` ---
    except requests.exceptions.HTTPError as e:
        error_message = f"Error HTTP: {e.response.status_code} {e.response.reason}"
        print(f"Error: {error_message} para URL {e.request.url}", file=sys.stderr)
        return None, error_message
    except requests.exceptions.ConnectionError as e:
        error_message = "Error de conexión con la API del Banco Mundial.\nVerifica tu conexión a internet."
        print(f"Error: {e}", file=sys.stderr)
        return None, error_message
    except requests.exceptions.Timeout:
        error_message = "Timeout: La solicitud a la API del Banco Mundial tardó demasiado."
        print("Error: Timeout", file=sys.stderr)
        return None, error_message
    except requests.exceptions.RequestException as e:
        error_message = f"Error en la solicitud: {e}"
        print(f"Error: {error_message}", file=sys.stderr)
        return None, error_message
    except requests.exceptions.JSONDecodeError:
        error_message = "Error al decodificar la respuesta del servidor (JSON inválido)."
        print(f"Error: {error_message}", file=sys.stderr)
        try: print(f"Texto recibido: {response.text[:500]}...", file=sys.stderr)
        except NameError: pass # response puede no estar definida si falló antes
        return None, error_message
    except Exception as e: # Captura genérica para errores inesperados
        error_message = f"Error inesperado en get_gini_data: {type(e).__name__}"
        print(f"Error: {error_message}: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        return None, error_message

# --- Procesamiento de Datos (sin cambios respecto al original) ---
def find_latest_valid_gini(records: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Encuentra el registro con el año más reciente que tenga un valor GINI válido.
    """
    latest_valid_record = None
    latest_year = -1

    if not records:
        return None

    for record in records:
        # Asegura que es un diccionario y tiene las claves esperadas
        if not isinstance(record, dict):
            continue
        value = record.get('value')
        date_str = record.get('date')

        # Verifica que 'value' no sea None y 'date' exista
        if value is not None and date_str:
            try:
                # Intenta convertir a float y año a int para validar y comparar
                _ = float(value) # Verifica si es numérico
                current_year = int(date_str)

                if current_year > latest_year:
                    latest_year = current_year
                    # Añade el nombre del país al registro para facilidad de uso
                    record['country_name'] = record.get('country', {}).get('value', 'N/A')
                    latest_valid_record = record
            except (ValueError, TypeError):
                # Ignora registros con valor o fecha no válidos
                # print(f"[CoreLogic] Advertencia: Saltando registro con formato inválido: {record}", file=sys.stderr)
                continue

    return latest_valid_record

# --- Limpieza al salir (opcional pero buena práctica) ---
# No usamos atexit aquí porque la GUI puede cerrarse de formas que no lo activan bien.
# El Client64 se cierra automáticamente al terminar el script principal.
