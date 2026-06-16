# src/gui.py
# Define la clase de la aplicación GUI con Tkinter.
# Importa y utiliza funciones de core_logic.py.

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import sys
import core_logic # <--- Importar el módulo renombrado
from typing import Optional, List, Dict, Any

class GiniApp:
    def __init__(self, master: tk.Tk):
        self.master = master
        master.title("GINI Index Fetcher (TP2)")
        master.geometry("550x500") # Un poco más de alto para el botón C
        master.config(bg="#f0f0f0")

        # --- Inyectar funciones de core_logic ---
        self.get_gini_data = core_logic.get_gini_data
        self.find_latest_valid_gini = core_logic.find_latest_valid_gini
        # Usar la función de core_logic que maneja Client64 -> Server32 -> C/ASM
        self.process_with_c_asm = core_logic.process_gini_with_c_asm

        self._setup_styles()
        self._create_widgets()
        self._layout_widgets()

        # Guarda el último GINI float válido para pasarlo a C/ASM
        self.latest_gini_value_for_processing: Optional[float] = None
        self.entry_code.focus_set()

    def _setup_styles(self):
        """Configura estilos ttk."""
        self.style = ttk.Style()
        # Intenta usar temas modernos si están disponibles
        available_themes = self.style.theme_names()
        if 'clam' in available_themes: self.style.theme_use('clam')
        elif 'alt' in available_themes: self.style.theme_use('alt')
        # Define estilos para diferentes widgets
        self.style.configure("TLabel", background="#f0f0f0", font=("Segoe UI", 10))
        self.style.configure("TButton", font=("Segoe UI", 10), padding=5)
        self.style.configure("TEntry", font=("Segoe UI", 10), padding=5)
        self.style.configure("TFrame", background="#f0f0f0")
        self.style.configure("Header.TLabel", font=("Segoe UI", 12, "bold"))
        self.style.configure("Summary.TLabel", font=("Segoe UI", 11))
        self.style.configure("Status.TLabel", font=("Segoe UI", 9), foreground="gray")
        self.style.configure("Processing.TButton", font=("Segoe UI", 10, "bold"), padding=6) # Estilo para el botón C/ASM

    def _create_widgets(self):
        """Crea todos los widgets de la GUI."""
        # Variables Tkinter para vincular a widgets
        self.country_code_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Introduce código de país (3 letras) y pulsa 'Obtener Datos'.")
        self.summary_country_var = tk.StringVar(value="-")
        self.summary_year_var = tk.StringVar(value="-")
        self.summary_gini_var = tk.StringVar(value="-")

        # Frames para organizar la interfaz
        self.input_frame = ttk.Frame(self.master, padding="15 10 15 5")
        self.summary_frame = ttk.Frame(self.master, padding="15 5 15 10", borderwidth=1, relief="solid")
        # Frame para el botón de procesamiento C/ASM
        self.processing_frame = ttk.Frame(self.master, padding="15 0 15 5")
        self.history_frame = ttk.Frame(self.master, padding="15 0 15 5")
        self.status_frame = ttk.Frame(self.master, padding="15 5 15 10")

        # Widgets de entrada
        self.label_code = ttk.Label(self.input_frame, text="Código País (ISO 3):")
        self.entry_code = ttk.Entry(self.input_frame, textvariable=self.country_code_var, width=8)
        self.fetch_button = ttk.Button(self.input_frame, text="Obtener Datos", command=self.fetch_and_display_handler)

        # Widgets de resumen
        self.label_summary_country_title = ttk.Label(self.summary_frame, text="País:", style="Summary.TLabel")
        self.label_summary_country_value = ttk.Label(self.summary_frame, textvariable=self.summary_country_var, style="Summary.TLabel", anchor="w")
        self.label_summary_year_title = ttk.Label(self.summary_frame, text="Últ. Año:", style="Summary.TLabel")
        self.label_summary_year_value = ttk.Label(self.summary_frame, textvariable=self.summary_year_var, style="Summary.TLabel")
        self.label_summary_gini_title = ttk.Label(self.summary_frame, text="Últ. GINI:", style="Summary.TLabel")
        self.label_summary_gini_value = ttk.Label(self.summary_frame, textvariable=self.summary_gini_var, style="Summary.TLabel")

        # Botón para C/ASM
        self.process_button = ttk.Button(self.processing_frame, text="Procesar GINI con C/ASM",
                                          command=self._trigger_c_asm_processing, style="Processing.TButton",
                                          state=tk.DISABLED) # Deshabilitado inicialmente

        # Widgets de historial
        self.label_history_header = ttk.Label(self.history_frame, text="Historial Datos (Válidos, por año)", style="Header.TLabel")
        self.result_text = scrolledtext.ScrolledText(self.history_frame, wrap=tk.WORD, state='disabled', height=8, width=60, font=("Consolas", 9), relief=tk.SUNKEN, borderwidth=1)

        # Barra de estado
        self.status_label = ttk.Label(self.status_frame, textvariable=self.status_var, style="Status.TLabel")

        # Binding para tecla Enter en el campo de código
        self.entry_code.bind("<Return>", self.fetch_and_display_handler)

    def _layout_widgets(self):
        """Organiza los widgets usando grid."""
        # Configuración de filas/columnas principales
        self.master.grid_columnconfigure(0, weight=1)
        self.master.grid_rowconfigure(0, weight=0) # Input
        self.master.grid_rowconfigure(1, weight=0) # Summary
        self.master.grid_rowconfigure(2, weight=0) # Process Button
        self.master.grid_rowconfigure(3, weight=1) # History Text
        self.master.grid_rowconfigure(4, weight=0) # Status Bar

        # Input Frame
        self.input_frame.grid(row=0, column=0, sticky="ew")
        self.input_frame.grid_columnconfigure(1, weight=1) # Entry se expande
        self.label_code.grid(row=0, column=0, padx=(0, 5), pady=5, sticky="w")
        self.entry_code.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.fetch_button.grid(row=0, column=2, padx=(5, 0), pady=5, sticky="e")

        # Summary Frame
        self.summary_frame.grid(row=1, column=0, sticky="ew", pady=(5, 10))
        self.summary_frame.grid_columnconfigure(1, weight=1) # Valor del país se expande
        self.label_summary_country_title.grid(row=0, column=0, sticky="w", padx=5, pady=2)
        self.label_summary_country_value.grid(row=0, column=1, columnspan=3, sticky="ew", padx=5, pady=2)
        self.label_summary_year_title.grid(row=1, column=0, sticky="w", padx=5, pady=2)
        self.label_summary_year_value.grid(row=1, column=1, sticky="w", padx=5, pady=2)
        self.label_summary_gini_title.grid(row=1, column=2, sticky="e", padx=(10, 5), pady=2)
        self.label_summary_gini_value.grid(row=1, column=3, sticky="w", padx=5, pady=2)

        # Processing Frame (para el botón C/ASM)
        self.processing_frame.grid(row=2, column=0, sticky="ew", pady=(0, 5))
        self.process_button.pack(pady=5) # Centrado simple con pack

        # History Frame
        self.history_frame.grid(row=3, column=0, sticky="nsew")
        self.history_frame.grid_rowconfigure(1, weight=1)
        self.history_frame.grid_columnconfigure(0, weight=1)
        self.label_history_header.grid(row=0, column=0, sticky="w", pady=(0, 5))
        self.result_text.grid(row=1, column=0, sticky="nsew")

        # Status Frame
        self.status_frame.grid(row=4, column=0, sticky="ew")
        self.status_label.pack(fill=tk.X) # Ocupa todo el ancho

    # --- Métodos de Ayuda para la UI ---
    def update_status(self, message: str, is_error=False):
        """Actualiza el texto y color de la barra de estado."""
        self.status_var.set(message)
        self.status_label.config(foreground="red" if is_error else "gray")
        self.master.update_idletasks() # Asegura actualización inmediata

    def clear_output_fields(self):
        """Limpia los campos de resumen e historial."""
        self.summary_country_var.set("-")
        self.summary_year_var.set("-")
        self.summary_gini_var.set("-")
        self.latest_gini_value_for_processing = None # Resetea valor guardado
        self.process_button.config(state=tk.DISABLED) # Deshabilita botón C/ASM
        try:
            self.result_text.config(state='normal')
            self.result_text.delete('1.0', tk.END)
            self.result_text.config(state='disabled')
        except tk.TclError as e:
            print(f"Error limpiando el widget de texto: {e}", file=sys.stderr)

    def display_history_in_textbox(self, records: Optional[List[Dict[str, Any]]]):
        """Muestra el historial de datos GINI en el ScrolledText."""
        text_to_display = ""
        if records: # Si records es una lista (puede estar vacía)
            # Filtra y ordena solo registros válidos
            valid_records = sorted(
                [r for r in records if r and r.get('value') is not None and r.get('date')],
                key=lambda x: x.get('date', '')
            )
            if valid_records:
                lines = []
                for entry in valid_records:
                    try:
                        # Intenta formatear como float con 2 decimales
                        value_float = float(entry['value'])
                        lines.append(f"  Año: {entry['date']}, Índice GINI: {value_float:>6.2f}")
                    except (ValueError, TypeError):
                        # Si no se puede convertir, muestra el valor original
                        lines.append(f"  Año: {entry.get('date','?')}, Índice GINI: {entry.get('value','?')} (inválido?)")
                text_to_display = "\n".join(lines)
            else:
                text_to_display = "(No se encontraron puntos de datos históricos válidos)"
        elif records == []: # Si la API devolvió explícitamente "sin datos"
            text_to_display = "(No hay datos GINI disponibles para este país/periodo)"
        else: # Si hubo un error al obtener los datos (records es None)
            text_to_display = "(No se pudo cargar el historial de datos)"

        try:
            self.result_text.config(state='normal')
            self.result_text.delete('1.0', tk.END)
            self.result_text.insert(tk.END, text_to_display)
            self.result_text.config(state='disabled')
        except tk.TclError as e:
            print(f"Error actualizando el widget de texto: {e}", file=sys.stderr)

    # --- Manejador de Eventos Principal ---
    def fetch_and_display_handler(self, event=None):
        """Maneja el clic del botón 'Obtener Datos' o la tecla Enter."""
        country_code = self.country_code_var.get().strip().upper()
        # Validación simple del código de país
        if len(country_code) != 3 or not country_code.isalpha():
            messagebox.showerror("Error de Entrada", "Introduce un código de país ISO válido de 3 letras (ej: ARG, USA, BRA).")
            return

        # Deshabilitar controles durante la carga
        self.fetch_button.config(state='disabled')
        self.entry_code.config(state='disabled')
        self.clear_output_fields() # Limpia resultados anteriores
        self.update_status(f"Obteniendo datos para {country_code}...")

        # --- Llamada a la capa de lógica ---
        gini_records, error_msg = self.get_gini_data(country_code)
        # -----------------------------------

        # Rehabilitar controles
        self.fetch_button.config(state='normal')
        self.entry_code.config(state='normal')
        self.entry_code.select_range(0, tk.END) # Selecciona texto para fácil reemplazo
        # self.entry_code.focus_set() # Devuelve foco

        # --- Procesar resultado de la lógica ---
        if error_msg:
            # Hubo un error en la API o conexión
            messagebox.showerror("Error de API/Red", error_msg)
            self.update_status(f"Fallo al obtener datos para {country_code}.", is_error=True)
            self.display_history_in_textbox(None) # Muestra mensaje de error en historial
        elif gini_records is not None:
            # La llamada fue exitosa, buscar el último GINI válido
            latest_record = self.find_latest_valid_gini(gini_records)

            if latest_record:
                # Mostrar datos del último registro válido
                country_name = latest_record.get('country_name', country_code)
                year = latest_record.get('date', 'N/A')
                self.summary_country_var.set(country_name)
                self.summary_year_var.set(year)
                try:
                    # Intenta convertir GINI a float y mostrarlo
                    gini_float = float(latest_record['value'])
                    self.summary_gini_var.set(f"{gini_float:.2f}")
                    # Guarda el float para usarlo con el botón C/ASM
                    self.latest_gini_value_for_processing = gini_float
                    # Habilita el botón de procesamiento C/ASM
                    self.process_button.config(state=tk.NORMAL)
                    self.update_status(f"Datos obtenidos para {country_name}. Listo para procesar.")
                except (ValueError, TypeError):
                    # El último valor GINI no es un número válido
                    self.summary_gini_var.set("Inválido")
                    self.update_status(f"Advertencia: Último valor GINI para {country_name} no es numérico.", is_error=True)
                    self.latest_gini_value_for_processing = None
                    self.process_button.config(state=tk.DISABLED) # Mantiene botón deshabilitado
            elif not gini_records:
                # La API respondió ok, pero sin datos para ese país/periodo
                self.update_status(f"No se encontraron datos GINI para {country_code} en {core_logic.DATE_RANGE}.", is_error=False)
            else:
                # Había registros, pero ninguno con valor GINI válido
                self.update_status(f"Se encontraron registros para {country_code}, pero ninguno tenía un valor GINI válido.", is_error=True)

            # Muestra el historial (incluso si está vacío o tiene errores parciales)
            self.display_history_in_textbox(gini_records)
        else:
             # Caso inesperado: gini_records es None sin error_msg (no debería ocurrir)
             self.update_status(f"Error desconocido al procesar datos para {country_code}.", is_error=True)
             self.display_history_in_textbox(None)


    # --- Manejador para el botón de procesamiento C/ASM ---
    def _trigger_c_asm_processing(self):
        """
        Llamado al hacer clic en el botón 'Procesar GINI con C/ASM'.
        Utiliza el último valor GINI float válido guardado.
        """
        if self.latest_gini_value_for_processing is None:
            messagebox.showwarning("No Procesable", "No hay un valor GINI numérico válido para procesar.")
            return

        gini_input_float = self.latest_gini_value_for_processing
        self.update_status(f"Procesando {gini_input_float:.2f} con C/ASM...")
        self.process_button.config(state=tk.DISABLED) # Deshabilita mientras procesa

        print(f"[GUI] Iniciando procesamiento C/ASM con valor: {gini_input_float}", file=sys.stderr)
        try:
            # --- Llamada a la capa de lógica que maneja C/ASM ---
            c_asm_result = self.process_with_c_asm(gini_input_float)
            # -----------------------------------------------------

            if c_asm_result is not None:
                # Éxito: Muestra el resultado
                result_msg = f"Entrada GINI (float): {gini_input_float:.2f}\n" \
                             f"Resultado de C/ASM (int redondeado): {c_asm_result}"
                messagebox.showinfo("Resultado del Procesamiento C/ASM", result_msg)
                self.update_status(f"Procesamiento C/ASM completado. Resultado: {c_asm_result}")
            else:
                # Error durante el procesamiento (ya se logueó en core_logic o server32)
                error_msg = "Falló la ejecución de la función C/ASM.\n" \
                            "Revisa la consola/terminal para ver los errores detallados.\n" \
                            "(Posibles causas: biblioteca .so no encontrada, error en C o ASM, fallo del servidor 32-bit)."
                messagebox.showerror("Error de Procesamiento C/ASM", error_msg)
                self.update_status("Error durante el procesamiento C/ASM.", is_error=True)

        except Exception as e:
            # Error inesperado en la propia GUI al intentar llamar a la lógica
            print(f"[GUI] Error inesperado al llamar a process_with_c_asm: {e}", file=sys.stderr)
            messagebox.showerror("Error Inesperado", f"Error inesperado en la GUI al iniciar el procesamiento:\n{e}")
            self.update_status("Error inesperado en la GUI.", is_error=True)
        finally:
            # Rehabilita el botón si aún hay un valor válido para procesar
            if self.latest_gini_value_for_processing is not None:
                 self.process_button.config(state=tk.NORMAL)
