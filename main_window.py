"""Interfaz Gráfica de Usuario (GUI) moderna construida con Tkinter y TTK."""

import tkinter as tk
from datetime import date
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText

from app.analysis.statistics import get_game_statistics
from app.database.connection import init_db
from app.database.repository import DrawRepository
from app.forecasting.timeseries import analyze_time_series, build_binary_time_series
from app.generation.generator import GenerationStrategy, PlayGenerator
from app.importers.batch_importer import BatchDirectoryImporter, ensure_historico_structure
from app.importers.yelu_importer import YeluImporter
from app.rules.game_rules import GameType
from app.scrapers.yelu_scraper import YeluWebScraper


class LeidsaAnalyzerGUI(tk.Tk):
    """Ventana principal de la aplicación LEIDSA Analyzer."""

    def __init__(self, db_path: str = "data/leidsa.db"):
        super().__init__()
        self.title("LEIDSA Analyzer - Sistema de Análisis Estadístico")
        self.geometry("950x750")
        self.minsize(850, 620)

        init_db(db_path)
        ensure_historico_structure("data/historico")
        self.repository = DrawRepository(db_path=db_path)
        self.importer = YeluImporter(repository=self.repository)
        self.batch_importer = BatchDirectoryImporter(yelu_importer=self.importer)
        self.web_scraper = YeluWebScraper(importer=self.importer)
        self.generator = PlayGenerator()

        self._configure_styles()
        self._build_ui()

    def _configure_styles(self):
        style = ttk.Style(self)
        available_themes = style.theme_names()
        if "clam" in available_themes:
            style.theme_use("clam")

        bg_main = "#f5f6f8"
        accent_color = "#1e3a8a"

        self.configure(bg=bg_main)

        style.configure("TFrame", background=bg_main)
        style.configure("TLabel", background=bg_main, font=("Segoe UI", 10))
        style.configure(
            "Header.TLabel", font=("Segoe UI", 14, "bold"), foreground=accent_color
        )
        style.configure(
            "SubHeader.TLabel", font=("Segoe UI", 11, "bold"), foreground="#334155"
        )
        style.configure("TButton", font=("Segoe UI", 10, "bold"), padding=6)
        style.configure("TNotebook", background=bg_main)
        style.configure("TNotebook.Tab", font=("Segoe UI", 10, "bold"), padding=[12, 6])

    def _build_ui(self):
        notebook = ttk.Notebook(self)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.tab_import = ttk.Frame(notebook)
        self.tab_history = ttk.Frame(notebook)
        self.tab_stats = ttk.Frame(notebook)
        self.tab_generator = ttk.Frame(notebook)

        notebook.add(self.tab_import, text=" Importación de Datos ")
        notebook.add(self.tab_history, text=" Histórico de Sorteos ")
        notebook.add(self.tab_stats, text=" Análisis y Series Temporales ")
        notebook.add(self.tab_generator, text=" Generador de Jugadas ")

        self._build_import_tab()
        self._build_history_tab()
        self._build_stats_tab()
        self._build_generator_tab()

    # -------------------------------------------------------------------------
    # Pestaña 1: Importación de Datos (Web Scraper / Carpeta / Texto / Mantenimiento)
    # -------------------------------------------------------------------------
    def _build_import_tab(self):
        frame = ttk.Frame(self.tab_import, padding=15)
        frame.pack(fill=tk.BOTH, expand=True)

        # Sección 1: Scraping Web Automático (Método Principal)
        web_panel = ttk.LabelFrame(
            frame, text=" Sincronización Web Automática (Yelu) ", padding=10
        )
        web_panel.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(
            web_panel,
            text="Descarga los últimos resultados publicados en la web y los sincroniza automáticamente con la base de datos:",
        ).pack(anchor=tk.W, pady=(0, 5))

        btn_web_sync = ttk.Button(
            web_panel,
            text=" Sincronizar Sorteos desde la Web (Yelu) ",
            command=self._handle_web_sync,
        )
        btn_web_sync.pack(anchor=tk.W)

        btn_recover_data = ttk.Button(
            web_panel,
            text=" Recuperar Datos de un Período ",
            command=self._handle_data_recovery,
        )
        btn_recover_data.pack(anchor=tk.W, pady=(8, 0))

        btn_latest_data = ttk.Button(
            web_panel,
            text=" Obtener Sorteos Recientes ",
            command=self._handle_latest_draws,
        )
        btn_latest_data.pack(anchor=tk.W, pady=(8, 0))

        # Sección 2: Importación por Carpeta (Fallback)
        folder_panel = ttk.LabelFrame(
            frame, text=" Fallback 1: Importación Masiva por Carpeta (.txt) ", padding=10
        )
        folder_panel.pack(fill=tk.X, pady=(0, 10))

        btn_select_folder = ttk.Button(
            folder_panel,
            text=" Seleccionar Carpeta de Histórico... ",
            command=self._handle_batch_folder_import,
        )
        btn_select_folder.pack(anchor=tk.W)

        # Sección 3: Pegar Texto Directo (Fallback)
        text_panel = ttk.LabelFrame(
            frame, text=" Fallback 2: Pegar Texto Directo ", padding=10
        )
        text_panel.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        self.txt_import = ScrolledText(text_panel, height=4, font=("Consolas", 10))
        self.txt_import.pack(fill=tk.BOTH, expand=True, pady=(0, 5))

        btn_import_text = ttk.Button(
            text_panel, text="Procesar Texto Pegado", command=self._handle_import_text
        )
        btn_import_text.pack(anchor=tk.E, pady=(0, 5))

        # Sección 4: Mantenimiento y Logs
        maint_panel = ttk.LabelFrame(
            frame, text=" Mantenimiento y Registros de Auditoría ", padding=10
        )
        maint_panel.pack(fill=tk.X, pady=(0, 10))

        btn_clear_db = ttk.Button(
            maint_panel,
            text=" Vaciar Toda la Base de Datos ",
            command=self._handle_clear_database,
        )
        btn_clear_db.pack(side=tk.LEFT, padx=(0, 10))

        btn_view_logs = ttk.Button(
            maint_panel,
            text=" Abrir Log de Errores (importer.log) ",
            command=self._handle_view_logs,
        )
        btn_view_logs.pack(side=tk.LEFT)

        # Resumen en pantalla
        self.lbl_import_summary = ttk.Label(
            frame, text="Esperando datos...", style="SubHeader.TLabel"
        )
        self.lbl_import_summary.pack(anchor=tk.W, pady=(5, 5))

        self.txt_import_details = ScrolledText(
            frame, height=4, font=("Consolas", 9), state=tk.DISABLED
        )
        self.txt_import_details.pack(fill=tk.BOTH, expand=True)

    def _handle_web_sync(self):
        summary = self.web_scraper.sync_all_history()

        summary_msg = (
            f"Encontrados en la web: {summary.total} | "
            f"Nuevos guardados: {summary.saved} | "
            f"Duplicados omitidos: {summary.duplicates} | "
            f"Errores: {summary.errors}"
        )
        self.lbl_import_summary.config(text=summary_msg)

        self.txt_import_details.config(state=tk.NORMAL)
        self.txt_import_details.delete("1.0", tk.END)
        self.txt_import_details.insert(
            tk.END, "--- RESULTADO DE SINCRONIZACIÓN WEB AUTOMÁTICA ---\n"
        )
        self.txt_import_details.insert(tk.END, f"{summary_msg}\n\n")

        for detail in summary.details:
            line = f"[{detail.status.upper()}] {detail.raw_header} -> {detail.message}\n"
            self.txt_import_details.insert(tk.END, line)

        self.txt_import_details.config(state=tk.DISABLED)

        self._refresh_history_table()
        self._refresh_stats_view()

        messagebox.showinfo("Sincronización Web Completada", summary_msg)


    def _handle_data_recovery(self):
        """Permite recuperar/reprocesar un período específico de Yelu."""

        recovery_window = tk.Toplevel(self)
        recovery_window.title("Recuperar Datos de Yelu")
        recovery_window.geometry("420x300")
        recovery_window.resizable(False, False)
        recovery_window.transient(self)
        recovery_window.grab_set()

        frame = ttk.Frame(recovery_window, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(
            frame,
            text="Recuperación de Datos",
            style="Header.TLabel",
        ).pack(anchor=tk.W, pady=(0, 5))

        ttk.Label(
            frame,
            text=(
                "Selecciona el período que deseas volver a procesar.\n"
                "La recuperación NO modifica el checkpoint histórico."
            ),
            wraplength=360,
        ).pack(anchor=tk.W, pady=(0, 20))

        # ------------------------------------------------------------
        # DESDE
        # ------------------------------------------------------------

        from_frame = ttk.Frame(frame)
        from_frame.pack(fill=tk.X, pady=5)

        ttk.Label(
            from_frame,
            text="Desde:",
            width=12,
        ).pack(side=tk.LEFT)

        start_month_var = tk.StringVar(value="04")
        start_year_var = tk.StringVar(value="2023")

        ttk.Label(from_frame, text="Mes").pack(side=tk.LEFT)

        start_month_entry = ttk.Entry(
            from_frame,
            textvariable=start_month_var,
            width=5,
        )
        start_month_entry.pack(side=tk.LEFT, padx=(5, 10))

        ttk.Label(from_frame, text="Año").pack(side=tk.LEFT)

        start_year_entry = ttk.Entry(
            from_frame,
            textvariable=start_year_var,
            width=7,
        )
        start_year_entry.pack(side=tk.LEFT, padx=5)

        # ------------------------------------------------------------
        # HASTA
        # ------------------------------------------------------------

        to_frame = ttk.Frame(frame)
        to_frame.pack(fill=tk.X, pady=5)

        ttk.Label(
            to_frame,
            text="Hasta:",
            width=12,
        ).pack(side=tk.LEFT)

        end_month_var = tk.StringVar(value="11")
        end_year_var = tk.StringVar(value="2025")

        ttk.Label(to_frame, text="Mes").pack(side=tk.LEFT)

        end_month_entry = ttk.Entry(
            to_frame,
            textvariable=end_month_var,
            width=5,
        )
        end_month_entry.pack(side=tk.LEFT, padx=(5, 10))

        ttk.Label(to_frame, text="Año").pack(side=tk.LEFT)

        end_year_entry = ttk.Entry(
            to_frame,
            textvariable=end_year_var,
            width=7,
        )
        end_year_entry.pack(side=tk.LEFT, padx=5)

        # ------------------------------------------------------------
        # BOTONES
        # ------------------------------------------------------------

        button_frame = ttk.Frame(frame)
        button_frame.pack(fill=tk.X, pady=(25, 0))

        def execute_recovery():
            try:
                start_month = int(start_month_var.get())
                start_year = int(start_year_var.get())

                end_month = int(end_month_var.get())
                end_year = int(end_year_var.get())

                if not 1 <= start_month <= 12:
                    raise ValueError(
                        "El mes inicial debe estar entre 1 y 12."
                    )

                if not 1 <= end_month <= 12:
                    raise ValueError(
                        "El mes final debe estar entre 1 y 12."
                    )

                start_value = start_year * 12 + start_month
                end_value = end_year * 12 + end_month

                if start_value > end_value:
                    raise ValueError(
                        "El período inicial no puede ser posterior "
                        "al período final."
                    )

            except ValueError as e:
                messagebox.showerror(
                    "Período inválido",
                    str(e),
                    parent=recovery_window,
                )
                return

            confirm = messagebox.askyesno(
                "Confirmar recuperación",
                (
                    f"¿Deseas recuperar los datos desde "
                    f"{start_year}-{start_month:02d} hasta "
                    f"{end_year}-{end_month:02d}?\n\n"
                    "Los datos existentes no serán duplicados. "
                    "Los registros faltantes serán guardados."
                ),
                parent=recovery_window,
            )

            if not confirm:
                return

            recovery_window.destroy()

            try:
                summary = self.web_scraper.sync_month_range(
                    start_year=start_year,
                    start_month=start_month,
                    end_year=end_year,
                    end_month=end_month,
                )

                summary_msg = (
                    f"Período recuperado: "
                    f"{start_year}-{start_month:02d} → "
                    f"{end_year}-{end_month:02d}\n\n"
                    f"Procesados: {summary.total}\n"
                    f"Nuevos guardados: {summary.saved}\n"
                    f"Duplicados omitidos: {summary.duplicates}\n"
                    f"Errores: {summary.errors}"
                )

                self.lbl_import_summary.config(
                    text=(
                        f"Recuperación: {summary.saved} nuevos | "
                        f"{summary.duplicates} duplicados | "
                        f"{summary.errors} errores"
                    )
                )

                self.txt_import_details.config(state=tk.NORMAL)
                self.txt_import_details.delete("1.0", tk.END)

                self.txt_import_details.insert(
                    tk.END,
                    "--- RESULTADO DE RECUPERACIÓN DE DATOS ---\n\n"
                )

                self.txt_import_details.insert(
                    tk.END,
                    f"{summary_msg}\n\n"
                )

                for detail in summary.details:
                    line = (
                        f"[{detail.status.upper()}] "
                        f"{detail.raw_header} -> "
                        f"{detail.message}\n"
                    )
                    self.txt_import_details.insert(
                        tk.END,
                        line,
                    )

                self.txt_import_details.config(state=tk.DISABLED)

                self._refresh_history_table()
                self._refresh_stats_view()

                messagebox.showinfo(
                    "Recuperación Completada",
                    summary_msg,
                )

            except Exception as e:
                messagebox.showerror(
                    "Error durante la recuperación",
                    f"Ocurrió un error durante la recuperación:\n\n{e}",
                )

        ttk.Button(
            button_frame,
            text="Cancelar",
            command=recovery_window.destroy,
        ).pack(side=tk.RIGHT, padx=(10, 0))

        ttk.Button(
            button_frame,
            text=" Recuperar Datos ",
            command=execute_recovery,
        ).pack(side=tk.RIGHT)

    def _handle_batch_folder_import(self):
        folder_selected = filedialog.askdirectory(
            title="Seleccionar Carpeta Raíz de Histórico",
            initialdir="data/historico",
        )
        if not folder_selected:
            return

        batch_summary = self.batch_importer.import_directory(folder_selected)

        summary_msg = (
            f"Archivos procesados: {batch_summary.files_processed} | "
            f"Sorteos encontrados: {batch_summary.total_draws_found} | "
            f"Guardados: {batch_summary.saved} | "
            f"Duplicados omitidos: {batch_summary.duplicates} | "
            f"Errores: {batch_summary.errors}"
        )
        self.lbl_import_summary.config(text=summary_msg)

        self.txt_import_details.config(state=tk.NORMAL)
        self.txt_import_details.delete("1.0", tk.END)
        self.txt_import_details.insert(
            tk.END, "--- RESULTADO DE IMPORTACIÓN MASIVA EN CARPETA ---\n"
        )
        self.txt_import_details.insert(tk.END, f"Ruta: {folder_selected}\n")
        self.txt_import_details.insert(tk.END, f"{summary_msg}\n\n")

        for file_path, summary in batch_summary.file_summaries:
            self.txt_import_details.insert(
                tk.END,
                f"Archivo: {file_path} -> Guardados: {summary.saved}, Duplicados: {summary.duplicates}, Errores: {summary.errors}\n",
            )

        self.txt_import_details.config(state=tk.DISABLED)

        self._refresh_history_table()
        self._refresh_stats_view()

        messagebox.showinfo("Importación Masiva Completada", summary_msg)

    def _handle_import_text(self):
        raw_text = self.txt_import.get("1.0", tk.END).strip()
        if not raw_text:
            messagebox.showwarning(
                "Texto vacío", "Por favor pega texto antes de procesar."
            )
            return

        summary = self.importer.import_text(raw_text)

        summary_msg = (
            f"Procesados: {summary.total} | Guardados: {summary.saved} | "
            f"Duplicados: {summary.duplicates} | Errores: {summary.errors}"
        )
        self.lbl_import_summary.config(text=summary_msg)

        self.txt_import_details.config(state=tk.NORMAL)
        self.txt_import_details.delete("1.0", tk.END)

        for detail in summary.details:
            line = f"[{detail.status.upper()}] {detail.raw_header} -> {detail.message}\n"
            self.txt_import_details.insert(tk.END, line)

        self.txt_import_details.config(state=tk.DISABLED)

        self._refresh_history_table()
        self._refresh_stats_view()

        messagebox.showinfo("Importación Finalizada", summary_msg)

    def _handle_clear_database(self):
        confirm = messagebox.askyesno(
            "Confirmar borrado total",
            "¿Estás seguro de que deseas eliminar TODOS los sorteos de la base de datos?\n\nEsta acción no se puede deshacer.",
            icon="warning",
        )
        if not confirm:
            return

        deleted_count = self.repository.clear_all_draws()
        msg = f"Se eliminaron correctamente {deleted_count} sorteos de la base de datos."

        self.lbl_import_summary.config(text=msg)

        self.txt_import_details.config(state=tk.NORMAL)
        self.txt_import_details.delete("1.0", tk.END)
        self.txt_import_details.insert(
            tk.END, f"{msg}\nBase de datos limpia y lista para datos reales."
        )
        self.txt_import_details.config(state=tk.DISABLED)

        self._refresh_history_table()
        self._refresh_stats_view()

        messagebox.showinfo("Base de Datos Limpia", msg)

    def _handle_view_logs(self):
        log_file = Path("logs/importer.log")
        if not log_file.exists():
            messagebox.showinfo(
                "Log no encontrado", "Aún no se ha generado el archivo 'logs/importer.log'."
            )
            return

        log_window = tk.Toplevel(self)
        log_window.title("Registro de Auditoría - logs/importer.log")
        log_window.geometry("800x500")

        txt_area = ScrolledText(log_window, font=("Consolas", 9))
        txt_area.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        try:
            content = log_file.read_text(encoding="utf-8")
            txt_area.insert(tk.END, content)
        except Exception as e:
            txt_area.insert(tk.END, f"Error al abrir el log: {e}")

        txt_area.config(state=tk.DISABLED)

    # -------------------------------------------------------------------------
    # Pestañas adicionales (Histórico, Stats, Generador)
    # -------------------------------------------------------------------------
    def _build_history_tab(self):
        frame = ttk.Frame(self.tab_history, padding=15)
        frame.pack(fill=tk.BOTH, expand=True)

        top_bar = ttk.Frame(frame)
        top_bar.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(top_bar, text="Filtrar por Juego:", style="SubHeader.TLabel").pack(
            side=tk.LEFT, padx=(0, 10)
        )

        self.var_game_history = tk.StringVar(value=GameType.KINO_TV.value)
        self.combo_game_history = ttk.Combobox(
            top_bar,
            textvariable=self.var_game_history,
            values=[g.value for g in GameType],
            state="readonly",
            width=20,
        )
        self.combo_game_history.pack(side=tk.LEFT, padx=(0, 10))
        self.var_game_history.trace_add(
            "write", lambda *args: self._refresh_history_table()
        )

        btn_refresh = ttk.Button(
            top_bar, text="Actualizar Tabla", command=self._refresh_history_table
        )
        btn_refresh.pack(side=tk.LEFT, padx=(0, 10))

        btn_delete_selected = ttk.Button(
            top_bar,
            text="Eliminar Sorteo Seleccionado",
            command=self._handle_delete_selected_draw,
        )
        btn_delete_selected.pack(side=tk.LEFT)

        columns = ("fecha", "juego", "numeros", "fuente")
        self.tree_history = ttk.Treeview(
            frame, columns=columns, show="headings", selectmode="browse"
        )

        self.tree_history.heading("fecha", text="Fecha Sorteo")
        self.tree_history.heading("juego", text="Juego")
        self.tree_history.heading("numeros", text="Números Ganadores")
        self.tree_history.heading("fuente", text="Fuente")

        self.tree_history.column("fecha", width=120, anchor=tk.CENTER)
        self.tree_history.column("juego", width=120, anchor=tk.CENTER)
        self.tree_history.column("numeros", width=480, anchor=tk.W)
        self.tree_history.column("fuente", width=100, anchor=tk.CENTER)

        scrollbar = ttk.Scrollbar(
            frame, orient=tk.VERTICAL, command=self.tree_history.yview
        )
        self.tree_history.configure(yscrollcommand=scrollbar.set)

        self.tree_history.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self._refresh_history_table()

    def _handle_delete_selected_draw(self):
        selected_item = self.tree_history.selection()
        if not selected_item:
            messagebox.showwarning(
                "Selección requerida",
                "Por favor, selecciona primero un sorteo en la tabla para eliminarlo.",
            )
            return

        values = self.tree_history.item(selected_item[0], "values")
        if not values:
            return

        raw_date, raw_game = values[0], values[1]
        try:
            draw_date = date.fromisoformat(raw_date)
            game_type = GameType(raw_game)
        except ValueError:
            messagebox.showerror(
                "Error", "No se pudieron interpretar los datos del sorteo seleccionado."
            )
            return

        confirm = messagebox.askyesno(
            "Confirmar Eliminación",
            f"¿Estás seguro de que deseas eliminar el sorteo de {raw_game} del {raw_date}?\n\nEsta acción no se puede deshacer.",
            icon="warning",
        )
        if not confirm:
            return

        deleted = self.repository.delete_draw(game_type, draw_date)
        if deleted:
            messagebox.showinfo(
                "Sorteo Eliminado",
                f"El sorteo de {raw_game} del {raw_date} ha sido eliminado.",
            )
            self._refresh_history_table()
            self._refresh_stats_view()
        else:
            messagebox.showerror("Error", "No se pudo eliminar el sorteo especificado.")

    def _refresh_history_table(self):
        for row in self.tree_history.get_children():
            self.tree_history.delete(row)

        game_name = self.var_game_history.get()
        try:
            game_type = GameType(game_name)
        except ValueError:
            return

        draws = self.repository.get_draws_by_game(game_type)
        for d in draws:
            nums_formatted = d.formatted_numbers_str()
            self.tree_history.insert(
                "",
                tk.END,
                values=(
                    d.draw_date.isoformat(),
                    d.game.value,
                    nums_formatted,
                    d.source,
                ),
            )

    def _build_stats_tab(self):
        frame = ttk.Frame(self.tab_stats, padding=15)
        frame.pack(fill=tk.BOTH, expand=True)

        top_bar = ttk.Frame(frame)
        top_bar.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(
            top_bar, text="Seleccionar Juego:", style="SubHeader.TLabel"
        ).pack(side=tk.LEFT, padx=(0, 10))

        self.var_game_stats = tk.StringVar(value=GameType.LOTO_POOL.value)
        self.combo_game_stats = ttk.Combobox(
            top_bar,
            textvariable=self.var_game_stats,
            values=[g.value for g in GameType],
            state="readonly",
            width=20,
        )
        self.combo_game_stats.pack(side=tk.LEFT, padx=(0, 10))
        self.var_game_stats.trace_add(
            "write", lambda *args: self._refresh_stats_view()
        )

        btn_calc = ttk.Button(
            top_bar, text="Calcular Estadísticas", command=self._refresh_stats_view
        )
        btn_calc.pack(side=tk.LEFT)

        self.txt_stats_report = ScrolledText(frame, font=("Consolas", 10))
        self.txt_stats_report.pack(fill=tk.BOTH, expand=True, pady=(10, 0))

        self._refresh_stats_view()

    def _refresh_stats_view(self):
        self.txt_stats_report.config(state=tk.NORMAL)
        self.txt_stats_report.delete("1.0", tk.END)

        game_name = self.var_game_stats.get()
        try:
            game_type = GameType(game_name)
        except ValueError:
            self.txt_stats_report.config(state=tk.DISABLED)
            return

        draws = self.repository.get_draws_by_game(game_type)

        if not draws:
            self.txt_stats_report.insert(
                tk.END,
                f"No hay registros de sorteos almacenados para {game_type.value}.\n",
            )
            self.txt_stats_report.config(state=tk.DISABLED)
            return

        report = []
        report.append("=" * 70)
        report.append(
            f"   REPORTE ESTADÍSTICO Y SERIES TEMPORALES: {game_type.value.upper()}"
        )
        report.append("=" * 70)
        report.append(f"Total de sorteos en base de datos: {len(draws)}\n")

        stats = get_game_statistics(draws, game_type)
        top_hot = sorted(stats, key=lambda s: s.absolute_frequency, reverse=True)[:5]
        top_cold = sorted(
            [s for s in stats if s.draws_since_last is not None],
            key=lambda s: s.draws_since_last,
            reverse=True,
        )[:5]

        report.append(" Top 5 Números Más Frecuentes (Histórico):")
        for s in top_hot:
            report.append(
                f"   - Número {s.number:02d}: {s.absolute_frequency} apariciones "
                f"(Atraso actual: {s.draws_since_last} sorteos)"
            )

        report.append("\n Top 5 Números Más Atrasados:")
        for s in top_cold:
            report.append(
                f"   - Número {s.number:02d}: {s.draws_since_last} sorteos sin salir "
                f"(Frecuencia absoluta: {s.absolute_frequency})"
            )

        if top_hot:
            target_num = top_hot[0].number
            series = build_binary_time_series(draws, target_number=target_num)
            ts_res = analyze_time_series(series, target_number=target_num, max_lag=5)

            report.append("\n" + "-" * 70)
            report.append(
                f" Evaluación de Series Temporales (fpp3) - Número {target_num:02d}:"
            )
            report.append(f"   - Observaciones analizadas: {ts_res.total_observations}")
            report.append(f"   - p-valor (Test Ljung-Box): {ts_res.ljung_box_p_value:.4f}")
            eval_str = (
                "SÍ (Proceso totalmente aleatorio)"
                if ts_res.is_white_noise
                else "NO (Presenta estructura temporal)"
            )
            report.append(f"   - ¿Es consistente con Ruido Blanco?: {eval_str}")
            report.append("-" * 70)

        self.txt_stats_report.insert(tk.END, "\n".join(report))
        self.txt_stats_report.config(state=tk.DISABLED)

    def _build_generator_tab(self):
        frame = ttk.Frame(self.tab_generator, padding=15)
        frame.pack(fill=tk.BOTH, expand=True)

        control_panel = ttk.LabelFrame(
            frame, text=" Configuración de Generación ", padding=15
        )
        control_panel.pack(fill=tk.X, pady=(0, 15))

        ttk.Label(control_panel, text="Juego:").grid(
            row=0, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.var_gen_game = tk.StringVar(value=GameType.LOTO.value)
        self.combo_gen_game = ttk.Combobox(
            control_panel,
            textvariable=self.var_gen_game,
            values=[g.value for g in GameType],
            state="readonly",
            width=20,
        )
        self.combo_gen_game.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)

        ttk.Label(control_panel, text="Estrategia Estadísticas:").grid(
            row=1, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.var_gen_strat = tk.StringVar(value=GenerationStrategy.BALANCED.value)
        self.combo_gen_strat = ttk.Combobox(
            control_panel,
            textvariable=self.var_gen_strat,
            values=[s.value for s in GenerationStrategy],
            state="readonly",
            width=25,
        )
        self.combo_gen_strat.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)

        btn_generate = ttk.Button(
            control_panel,
            text=" Generar Combinación Candidata ",
            command=self._handle_generate_play,
        )
        btn_generate.grid(row=2, column=0, columnspan=2, pady=(10, 0))

        res_frame = ttk.LabelFrame(frame, text=" Resultado Generado ", padding=15)
        res_frame.pack(fill=tk.BOTH, expand=True)

        self.var_gen_numbers = tk.StringVar(
            value="[ Haz clic en 'Generar Combinación Candidata' ]"
        )

        self.entry_gen_numbers = ttk.Entry(
            res_frame,
            textvariable=self.var_gen_numbers,
            font=("Consolas", 14, "bold"),
            justify=tk.CENTER,
        )
        self.entry_gen_numbers.pack(
            fill=tk.X,
            padx=10,
            pady=15,
        )

        self.txt_gen_disclaimer = tk.Text(
            res_frame,
            height=5,
            font=("Segoe UI", 9, "italic"),
            bg="#f8fafc",
            relief=tk.FLAT,
            wrap=tk.WORD,
        )
        self.txt_gen_disclaimer.pack(fill=tk.X, expand=False, pady=(10, 0))

    def _handle_generate_play(self):
        game_type = GameType(self.var_gen_game.get())
        strategy = GenerationStrategy(self.var_gen_strat.get())

        draws = self.repository.get_draws_by_game(game_type)
        play = self.generator.generate_play(
            game_type=game_type, strategy=strategy, historical_draws=draws
        )

        d = play.draw_data
        nums_str = d.formatted_numbers_str()
        self.var_gen_numbers.set(f"{d.game.value}: {nums_str}")

        # Selecciona automáticamente el resultado para facilitar Ctrl+C.
        self.entry_gen_numbers.focus_set()
        self.entry_gen_numbers.selection_range(0, tk.END)

        self.txt_gen_disclaimer.config(state=tk.NORMAL)
        self.txt_gen_disclaimer.delete("1.0", tk.END)
        self.txt_gen_disclaimer.insert(
            tk.END, f"Estrategia utilizada: {play.strategy.value}\n\n"
        )
        self.txt_gen_disclaimer.insert(tk.END, play.disclaimer)
        self.txt_gen_disclaimer.config(state=tk.DISABLED)

    def _handle_latest_draws(self):
        """Descarga y procesa los resultados más recientes disponibles en Yelu."""

        try:
            summary = self.web_scraper.sync_latest_draws()

            summary_msg = (
                f"Encontrados: {summary.total} | "
                f"Nuevos guardados: {summary.saved} | "
                f"Duplicados omitidos: {summary.duplicates} | "
                f"Errores: {summary.errors}"
            )

            self.lbl_import_summary.config(
                text=f"Resultados recientes: {summary.saved} nuevos | "
                     f"{summary.duplicates} duplicados | "
                     f"{summary.errors} errores"
            )

            self.txt_import_details.config(state=tk.NORMAL)
            self.txt_import_details.delete("1.0", tk.END)

            self.txt_import_details.insert(
                tk.END,
                "--- RESULTADO DE OBTENCIÓN DE SORTEOS RECIENTES ---\n\n"
            )
            self.txt_import_details.insert(
                tk.END,
                f"{summary_msg}\n\n"
            )

            for detail in summary.details:
                line = (
                    f"[{detail.status.upper()}] "
                    f"{detail.raw_header} -> "
                    f"{detail.message}\n"
                )
                self.txt_import_details.insert(tk.END, line)

            self.txt_import_details.config(state=tk.DISABLED)

            self._refresh_history_table()
            self._refresh_stats_view()

            messagebox.showinfo(
                "Sorteos Recientes",
                summary_msg,
            )

        except Exception as e:
            messagebox.showerror(
                "Error al obtener sorteos recientes",
                f"Ocurrió un error al obtener los resultados recientes:\n\n{e}",
            )


def launch_gui():
    app = LeidsaAnalyzerGUI()
    app.mainloop()