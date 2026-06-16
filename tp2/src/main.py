# src/main.py
# Punto de entrada principal de la aplicación GINI Fetcher.
# Simplemente instancia y ejecuta la clase GiniApp desde gui.py.

import tkinter as tk
import gui # Importa el módulo de la interfaz gráfica
import sys
import os

if __name__ == "__main__":
    print("Lanzando Aplicación GINI Fetcher...")
    # Añadir el directorio src al sys.path temporalmente si es necesario
    # (generalmente no se requiere si se ejecuta desde el directorio raíz con `python src/main.py`)
    # src_dir = os.path.dirname(__file__)
    # if src_dir not in sys.path:
    #     sys.path.insert(0, src_dir)

    try:
        root = tk.Tk()
        app = gui.GiniApp(root) # Instancia la aplicación desde gui.py
        root.mainloop()
        print("Aplicación cerrada.")
    except tk.TclError as e:
         # Error común si falta tkinter o hay problemas de tema
         print(f"\nError de Tkinter: {e}", file=sys.stderr)
         print("No se pudo inicializar la GUI de Tkinter.", file=sys.stderr)
         print("Asegúrate de tener instalado 'python3-tk' (o equivalente para tu SO).", file=sys.stderr)
         print("Ejecuta './setup.sh' para intentar instalarlo.", file=sys.stderr)
         sys.exit(1)
    except ImportError as e:
        # Error si no encuentra gui.py o core_logic.py
        print(f"\nError de Importación: {e}", file=sys.stderr)
        print("No se pudo encontrar un módulo necesario (gui.py, core_logic.py?).", file=sys.stderr)
        print(f"Asegúrate de estar ejecutando desde el directorio raíz del proyecto y que la estructura de 'src/' sea correcta.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        # Captura cualquier otro error inesperado al inicio
        print(f"\nError Inesperado al Iniciar: {type(e).__name__}: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
