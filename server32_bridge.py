# src/server32_bridge.py
# Servidor 32-bit (corre bajo msl-loadlib) que carga la biblioteca C/ASM 32-bit
# y expone la función C a través de la red al cliente 64-bit.

import os
import ctypes
import sys
import platform

try:
    from msl.loadlib import Server32
except ImportError:
    print("ERROR: msl.loadlib no encontrado en el entorno Python de 32-bit.", file=sys.stderr)
    sys.exit(1)

# --- Logging ---
INFO_PREFIX = "INFO [Server32] "

ERROR_PREFIX = "ERROR [Server32] "

# --- Configuración ---
# Nombre de la biblioteca compartida (generada por build.sh)
LIB_FILENAME = 'libginiprocessor.so'
# Nombre de la función C a la que llamaremos desde Python
C_FUNCTION_NAME = 'process_gini_float'

# Determinar la ruta a la biblioteca .so
# __file__ es la ruta de este script (server32_bridge.py)
# La biblioteca estará en ../lib/ relativo a este script
SERVER_DIR = os.path.dirname(__file__)
LIB_DIR = os.path.abspath(os.path.join(SERVER_DIR, '..', 'lib')) # Sube un nivel y entra a lib/
LIBRARY_PATH = os.path.join(LIB_DIR, LIB_FILENAME)

class GiniProcessorServer(Server32):
    """
    Servidor msl-loadlib que carga libginiprocessor.so (32-bit)
    y expone la función 'process_gini_float'.
    """
    def __init__(self, host, port, **kwargs):
        """Inicializa el servidor y carga la biblioteca C."""
        print(f"{INFO_PREFIX}Inicializando GiniProcessorServer...", file=sys.stderr)
        print(f"{INFO_PREFIX}Arquitectura Python: {platform.architecture()[0]}", file=sys.stderr) # Debería ser 32bit
        print(f"{INFO_PREFIX}Buscando biblioteca en: {LIBRARY_PATH}", file=sys.stderr)

        if not os.path.exists(LIBRARY_PATH):
            error_msg = f"{INFO_PREFIX}FATAL ERROR: Biblioteca '{LIBRARY_PATH}' no encontrada."
            print(error_msg, file=sys.stderr)
            print(f"{INFO_PREFIX}Asegúrate de haber ejecutado './build.sh' primero.", file=sys.stderr)
            raise FileNotFoundError(error_msg) # Detiene el inicio del servidor

        try:
            # Carga la biblioteca usando Server32 (que usa ctypes.CDLL internamente)
            # 'cdll' asume la convención de llamada cdecl (estándar para gcc -m32)
            super().__init__(LIBRARY_PATH, 'cdll', host, port, **kwargs)
            print(f"{INFO_PREFIX}Biblioteca '{LIB_FILENAME}' cargada exitosamente.", file=sys.stderr)

            # --- Definir la firma de la función C ---
            # Accede a la función a través de self.lib (el objeto ctypes cargado)
            c_func = getattr(self.lib, C_FUNCTION_NAME)
            # Argumentos: un float (ctypes.c_float)
            c_func.argtypes = [ctypes.c_float]
            # Valor de retorno: un int (ctypes.c_int)
            c_func.restype = ctypes.c_int
            print(f"{INFO_PREFIX}Firma definida para la función C '{C_FUNCTION_NAME}'.", file=sys.stderr)

        except OSError as e:
            print(f"{ERROR_PREFIX}OSError al cargar la biblioteca '{LIBRARY_PATH}': {e}", file=sys.stderr)
            raise # Re-lanza para que msl-loadlib lo maneje
        except AttributeError as e:
             print(f"{ERROR_PREFIX}Función '{C_FUNCTION_NAME}' no encontrada en la biblioteca: {e}", file=sys.stderr)
             raise
        except Exception as e:
            print(f"{ERROR_PREFIX}Error inesperado durante la inicialización: {type(e).__name__}: {e}", file=sys.stderr)
            raise


    # --- Método expuesto al Client64 ---
    # El nombre de este método Python debe coincidir con el que llama el Client64
    def process_gini_float(self, gini_value_float):
        """
        Recibe el float del Client64, llama a la función C correspondiente
        en la biblioteca cargada y devuelve el resultado int.
        """
        print(f"{INFO_PREFIX}Recibida petición: process_gini_float({gini_value_float})", file=sys.stderr)
        try:
            # Llama a la función C usando el objeto self.lib de ctypes
            result = self.lib.process_gini_float(ctypes.c_float(gini_value_float))
            print(f"{INFO_PREFIX}Función C devolvió: {result} (tipo: {type(result).__name__})", file=sys.stderr)
            # Devuelve el resultado (int) al Client64
            return result
        except Exception as e:
            print(f"{ERROR_PREFIX}al llamar a la función C '{C_FUNCTION_NAME}': {type(e).__name__}: {e}", file=sys.stderr)
            # Re-lanza la excepción para que Client64 reciba un Server32Error
            raise

# No se necesita código adicional, Server32 maneja el bucle principal.
