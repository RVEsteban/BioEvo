"""
BioEvo | LabStats Formatter (v1.0.0-rc.1)
Copyright (c) 2026 Esteban Rosero / BioEvo Core. Todos los derechos reservados.
Estación de trabajo bioestadística local-first para maquetación LaTeX y diagnóstico analítico.
"""

import os
import re
import sys
import csv
import json
import threading
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Dict, Callable, Optional, Tuple, Any

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import customtkinter as ctk
import pandas as pd
import numpy as np
from scipy import stats

import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt

# =============================================================================
# 0. CONFIGURACIÓN VISUAL Y PALETAS BIOEVO
# =============================================================================

PALETTES = {
    "BioEvo Classic (Cyan/Blue)": {
        "primary": "#1f6feb",
        "accent": "#38bdf8",
        "secondary": "#58a6ff",
        "highlight": "#39d353"
    },
    "Emerald Forest": {
        "primary": "#238636",
        "accent": "#3fb950",
        "secondary": "#56d364",
        "highlight": "#e3b341"
    },
    "Nordic Dark": {
        "primary": "#5e81ac",
        "accent": "#88c0d0",
        "secondary": "#81a1c1",
        "highlight": "#a3be8c"
    }
}

THEME_BASE = {
    "bg": "#0d1117",
    "surface": "#161b22",
    "card": "#21262d",
    "border": "#30363d",
    "text": "#e6edf3",
    "text_muted": "#8b949e",
    "warning": "#d29922",
    "danger": "#f85149",
    "success": "#3fb950"
}

matplotlib.rcParams["text.color"] = THEME_BASE["text"]
matplotlib.rcParams["axes.labelcolor"] = THEME_BASE["text"]
matplotlib.rcParams["xtick.color"] = THEME_BASE["text_muted"]
matplotlib.rcParams["ytick.color"] = THEME_BASE["text_muted"]
matplotlib.rcParams["mathtext.fontset"] = "cm"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

try:
    import pyperclip
    HAS_PYPERCLIP = True
except ImportError:
    HAS_PYPERCLIP = False

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


# =============================================================================
# 1. BLINDAJE DE DATOS 100% (LECTOR DETERMINISTA Y SANEAMIENTO)
# =============================================================================

def sanitize_latex(text: str) -> str:
    """Escapa caracteres reservados de LaTeX preservando coherencia matemática."""
    mapping = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
    }
    for char, rep in mapping.items():
        text = text.replace(char, rep)
    return text


def validate_latex_syntax(code: str) -> Tuple[bool, str]:
    """Valida balance de entornos y detecta desalineaciones de columnas."""
    begins = re.findall(r"\\begin\{([^}]+)\}", code)
    ends = re.findall(r"\\end\{([^}]+)\}", code)
    if sorted(begins) != sorted(ends):
        return False, f"Desbalance de entornos: \\begin={begins} vs \\end={ends}"
    
    # Comprobar consistencia de ampersands por fila tabular
    tabular_match = re.search(r"\\begin\{tabular\}\{([^}]+)\}(.*?)\\end\{tabular\}", code, re.DOTALL)
    if tabular_match:
        cols_spec = tabular_match.group(1).strip()
        expected_cols = len([c for c in cols_spec if c in "lcrpmsS"])
        table_body = tabular_match.group(2)
        rows = [r.strip() for r in table_body.split(r"\\") if r.strip() and not r.strip().startswith(r"\toprule") and not r.strip().startswith(r"\midrule") and not r.strip().startswith(r"\bottomrule")]
        for i, r in enumerate(rows):
            if r.startswith(r"\addlinespace"):
                continue
            amp_count = r.count("&")
            if amp_count != expected_cols - 1:
                return False, f"Fila {i+1} tabular posee {amp_count+1} columnas; la especificación {{{cols_spec}}} espera {expected_cols}."
                
    return True, "Sintaxis verificada exitosamente"


def read_delimited_robust(path: str) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Lector determinista con detección de delimitador (csv.Sniffer), normalización 
    de comas decimales y fallback múltiple de codificación.
    """
    metadata = {
        "encoding": "utf-8",
        "delimiter": ",",
        "coerced_columns": 0,
        "coerced_names": [],
        "total_rows": 0,
        "total_cols": 0
    }

    if path.endswith((".xlsx", ".xls")):
        df = pd.read_excel(path)
        metadata["encoding"] = "binary/excel"
        metadata["delimiter"] = "N/A"
    else:
        encodings = ["utf-8", "latin-1", "cp1252", "iso-8859-1"]
        raw_bytes = open(path, "rb").read(32768)
        
        detected_enc = None
        for enc in encodings:
            try:
                raw_text = raw_bytes.decode(enc)
                detected_enc = enc
                break
            except UnicodeDecodeError:
                continue

        if not detected_enc:
            detected_enc = "latin-1"
        metadata["encoding"] = detected_enc

        # Detección de delimitador con csv.Sniffer
        sample_str = raw_bytes.decode(detected_enc, errors="ignore")
        try:
            sniffer = csv.Sniffer()
            dialect = sniffer.sniff(sample_str[:4096], delimiters=[",", ";", "\t", "|"])
            detected_sep = dialect.delimiter
        except Exception:
            # Conteo de frecuencia de delimitadores como fallback
            line1 = sample_str.split("\n")[0]
            counts = {sep: line1.count(sep) for sep in [";", ",", "\t", "|"]}
            detected_sep = max(counts, key=counts.get)
            if counts[detected_sep] == 0:
                detected_sep = None

        metadata["delimiter"] = detected_sep if detected_sep else "auto"

        try:
            df = pd.read_csv(path, sep=detected_sep, encoding=detected_enc, engine="python")
        except Exception:
            df = pd.read_csv(path, sep=None, engine="python", encoding="latin-1")

    # Normalización de comas decimales a nivel DataFrame completo
    for col in df.columns:
        if pd.api.types.is_string_dtype(df[col]) or df[col].dtype == object:
            series_clean = df[col].dropna().astype(str).str.strip()
            # Detecta si todas las entradas son números formateados con coma (ej: "12,45" o "-0,87")
            if len(series_clean) > 0 and series_clean.str.match(r"^-?\d+([,.]\d+)?$").all():
                try:
                    df[col] = pd.to_numeric(series_clean.str.replace(",", "."), errors="coerce")
                    metadata["coerced_columns"] += 1
                    metadata["coerced_names"].append(col)
                except Exception:
                    pass

    metadata["total_rows"] = len(df)
    metadata["total_cols"] = len(df.columns)
    return df, metadata


# =============================================================================
# 2. PATRÓN STRATEGY COMPLETO Y FORMATEO POR MÉTRICA
# =============================================================================

class StatMetric(ABC):
    @property
    @abstractmethod
    def id_key(self) -> str: pass

    @property
    @abstractmethod
    def display_name(self) -> str: pass

    @property
    @abstractmethod
    def latex_header(self) -> str: pass

    @property
    @abstractmethod
    def is_parametric(self) -> bool: pass

    @property
    @abstractmethod
    def default_active(self) -> bool: pass

    @abstractmethod
    def compute(self, series: pd.Series, fmt: Callable[[float, int], str]) -> str: pass


class MeanStdMetric(StatMetric):
    @property
    def id_key(self) -> str: return "mean_sd"
    @property
    def display_name(self) -> str: return "Media ± DE"
    @property
    def latex_header(self) -> str: return r"Media $\pm$ DE"
    @property
    def is_parametric(self) -> bool: return True
    @property
    def default_active(self) -> bool: return True

    def compute(self, series: pd.Series, fmt: Callable[[float, int], str]) -> str:
        if len(series) == 0: return "---"
        m = series.mean()
        s = series.std(ddof=1) if len(series) > 1 else 0.0
        return f"{fmt(m, 2)} $\\pm$ {fmt(s, 2)}"


class SEMMetric(StatMetric):
    @property
    def id_key(self) -> str: return "sem"
    @property
    def display_name(self) -> str: return "Error Estándar (SEM)"
    @property
    def latex_header(self) -> str: return r"$\mathrm{SEM}$"
    @property
    def is_parametric(self) -> bool: return True
    @property
    def default_active(self) -> bool: return False

    def compute(self, series: pd.Series, fmt: Callable[[float, int], str]) -> str:
        n = len(series)
        if n <= 1: return "---"
        sem_val = series.std(ddof=1) / np.sqrt(n)
        return fmt(sem_val, 3)


class CI95Metric(StatMetric):
    @property
    def id_key(self) -> str: return "ci95"
    @property
    def display_name(self) -> str: return "IC 95%"
    @property
    def latex_header(self) -> str: return r"IC 95\%"
    @property
    def is_parametric(self) -> bool: return True
    @property
    def default_active(self) -> bool: return False

    def compute(self, series: pd.Series, fmt: Callable[[float, int], str]) -> str:
        n = len(series)
        if n < 2: return "---"
        m = series.mean()
        sem_val = series.std(ddof=1) / np.sqrt(n)
        ci = stats.t.interval(0.95, df=n - 1, loc=m, scale=sem_val)
        return f"[{fmt(ci[0], 2)} -- {fmt(ci[1], 2)}]"


class VarianceMetric(StatMetric):
    @property
    def id_key(self) -> str: return "variance"
    @property
    def display_name(self) -> str: return "Varianza (s²)"
    @property
    def latex_header(self) -> str: return r"$s^2$"
    @property
    def is_parametric(self) -> bool: return True
    @property
    def default_active(self) -> bool: return False

    def compute(self, series: pd.Series, fmt: Callable[[float, int], str]) -> str:
        if len(series) <= 1: return "---"
        return fmt(series.var(ddof=1), 2)


class MedianIQRMetric(StatMetric):
    @property
    def id_key(self) -> str: return "median_iqr"
    @property
    def display_name(self) -> str: return "Mediana [IQR]"
    @property
    def latex_header(self) -> str: return "Mediana [IQR]"
    @property
    def is_parametric(self) -> bool: return False
    @property
    def default_active(self) -> bool: return True

    def compute(self, series: pd.Series, fmt: Callable[[float, int], str]) -> str:
        if len(series) == 0: return "---"
        med = series.median()
        q1 = series.quantile(0.25)
        q3 = series.quantile(0.75)
        return f"{fmt(med, 2)} [{fmt(q1, 2)} -- {fmt(q3, 2)}]"


class P10P90Metric(StatMetric):
    @property
    def id_key(self) -> str: return "p10_p90"
    @property
    def display_name(self) -> str: return "Rango P10–P90"
    @property
    def latex_header(self) -> str: return r"$P_{10}$ -- $P_{90}$"
    @property
    def is_parametric(self) -> bool: return False
    @property
    def default_active(self) -> bool: return False

    def compute(self, series: pd.Series, fmt: Callable[[float, int], str]) -> str:
        if len(series) == 0: return "---"
        return f"[{fmt(series.quantile(0.10), 2)} -- {fmt(series.quantile(0.90), 2)}]"


class MinMaxMetric(StatMetric):
    @property
    def id_key(self) -> str: return "min_max"
    @property
    def display_name(self) -> str: return "Mín – Máx"
    @property
    def latex_header(self) -> str: return r"M\'{\i}n -- M\'ax"
    @property
    def is_parametric(self) -> bool: return False
    @property
    def default_active(self) -> bool: return False

    def compute(self, series: pd.Series, fmt: Callable[[float, int], str]) -> str:
        if len(series) == 0: return "---"
        return f"{fmt(series.min(), 2)} -- {fmt(series.max(), 2)}"


class SkewKurtMetric(StatMetric):
    @property
    def id_key(self) -> str: return "skew_kurt"
    @property
    def display_name(self) -> str: return "Asimetría / Curtosis"
    @property
    def latex_header(self) -> str: return r"Asim. / Curt."
    @property
    def is_parametric(self) -> bool: return False
    @property
    def default_active(self) -> bool: return False

    def compute(self, series: pd.Series, fmt: Callable[[float, int], str]) -> str:
        if len(series) < 3: return "---"
        return f"{fmt(series.skew(), 2)} / {fmt(series.kurtosis(), 2)}"


class SampleSizeMetric(StatMetric):
    @property
    def id_key(self) -> str: return "sample_size"
    @property
    def display_name(self) -> str: return "Tamaño muestral (n)"
    @property
    def latex_header(self) -> str: return "$n$"
    @property
    def is_parametric(self) -> bool: return False
    @property
    def default_active(self) -> bool: return True

    def compute(self, series: pd.Series, fmt: Callable[[float, int], str]) -> str:
        return str(len(series))


# =============================================================================
# 3. VENTANA PRINCIPAL LABSTATS WORKSTATION
# =============================================================================

class LabStatsApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("BioEvo | LabStats Formatter v1.0.0-rc.1")
        self.geometry("1440x920")
        self.minsize(1160, 740)

        self.df: Optional[pd.DataFrame] = None
        self.current_filepath: str = ""
        self.current_meta: Dict[str, Any] = {}
        self.var_checkboxes: Dict[str, ctk.CTkCheckBox] = {}
        self.stat_switches: Dict[StatMetric, ctk.CTkSwitch] = {}

        self.metrics: List[StatMetric] = [
            MeanStdMetric(),
            SEMMetric(),
            CI95Metric(),
            VarianceMetric(),
            MedianIQRMetric(),
            P10P90Metric(),
            MinMaxMetric(),
            SkewKurtMetric(),
            SampleSizeMetric()
        ]

        # Bindings globales
        self.bind("<Control-o>", lambda _: self.load_file_threaded())
        self.bind("<Control-s>", lambda _: self.save_tex_file())

        self._build_layout()

    def _build_layout(self):
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Barra lateral izquierda
        self.sidebar = ctk.CTkFrame(self, width=340, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")

        # Pestañas operativas
        self.tabview = ctk.CTkTabview(self, corner_radius=8)
        self.tabview.grid(row=0, column=1, sticky="nsew", padx=12, pady=12)

        self.tabview.add("Tabla & LaTeX")
        self.tabview.add("Normalidad & Rangos")
        self.tabview.add("Gráficas Analíticas")
        self.tabview.add("Fundamento Matemático")

        self._setup_sidebar()
        self._setup_tab_latex()
        self._setup_tab_stats()
        self._setup_tab_plots()
        self._setup_tab_math()

    # -------------------------------------------------------------------------
    # SIDEBAR
    # -------------------------------------------------------------------------
    def _setup_sidebar(self):
        header_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        header_frame.pack(fill="x", padx=16, pady=(16, 6))

        ctk.CTkLabel(header_frame, text="LabStats", font=ctk.CTkFont(size=20, weight="bold")).pack(side="left")
        badge = ctk.CTkLabel(
            header_frame, text="v1.0.0-rc.1", font=ctk.CTkFont(family="Consolas", size=10),
            fg_color=THEME_BASE["card"], text_color=THEME_BASE["text_muted"], corner_radius=4
        )
        badge.pack(side="right", pady=4)

        # Acciones de Archivo y Proyecto
        btn_grid = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        btn_grid.pack(fill="x", padx=16, pady=4)

        self.btn_load = ctk.CTkButton(btn_grid, text="📂 Cargar (Ctrl+O)", command=self.load_file_threaded)
        self.btn_load.pack(fill="x", pady=2)

        self.btn_save_proj = ctk.CTkButton(
            btn_grid, text="💾 Proyecto .bioevo", fg_color=THEME_BASE["card"], hover_color=THEME_BASE["border"],
            command=self.save_project_json
        )
        self.btn_save_proj.pack(fill="x", pady=2)

        self.btn_save_tex = ctk.CTkButton(
            btn_grid, text="📄 Guardar .tex", fg_color=THEME_BASE["primary"], hover_color="#388bfd",
            state="disabled", command=self.save_tex_file
        )
        self.btn_save_tex.pack(fill="x", pady=2)

        self.btn_copy = ctk.CTkButton(
            btn_grid, text="📋 Copiar LaTeX", fg_color="#238636", hover_color="#2ea043",
            state="disabled", command=self.copy_latex
        )
        self.btn_copy.pack(fill="x", pady=2)

        # Barra de progreso y log de saneamiento
        self.progress_bar = ctk.CTkProgressBar(self.sidebar, height=4, mode="determinate")
        self.progress_bar.pack(fill="x", padx=16, pady=(8, 2))
        self.progress_bar.set(0)

        self.lbl_progress = ctk.CTkLabel(self.sidebar, text="Esperando datos", font=ctk.CTkFont(size=11), text_color=THEME_BASE["text_muted"])
        self.lbl_progress.pack(pady=(0, 4))

        # Contenedor con scroll para configuraciones
        self.scroll_sidebar = ctk.CTkScrollableFrame(self.sidebar, height=480)
        self.scroll_sidebar.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # Variables y buscador
        ctk.CTkLabel(self.scroll_sidebar, text="Variables a analizar", font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", padx=6, pady=(6, 2))
        self.entry_filter_var = ctk.CTkEntry(self.scroll_sidebar, placeholder_text="🔍 Filtrar nombre...")
        self.entry_filter_var.pack(fill="x", padx=6, pady=2)
        self.entry_filter_var.bind("<KeyRelease>", lambda _: self._filter_variable_checkboxes())

        btn_row = ctk.CTkFrame(self.scroll_sidebar, fg_color="transparent")
        btn_row.pack(fill="x", padx=6, pady=2)
        ctk.CTkButton(btn_row, text="Todas", width=75, height=24, command=self.select_all_vars).pack(side="left", padx=(0, 4))
        ctk.CTkButton(btn_row, text="Ninguna", width=75, height=24, command=self.deselect_all_vars).pack(side="left")

        self.var_container = ctk.CTkFrame(self.scroll_sidebar, fg_color=THEME_BASE["bg"], corner_radius=6)
        self.var_container.pack(fill="x", padx=6, pady=4)

        # Agrupación por factores
        ctk.CTkLabel(self.scroll_sidebar, text="Agrupar por", font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", padx=6, pady=(8, 2))
        self.combo_group = ctk.CTkComboBox(self.scroll_sidebar, values=["(sin agrupar)"], command=lambda _: self.trigger_analysis_thread())
        self.combo_group.pack(fill="x", padx=6, pady=2)

        # Catálogo Estadístico y Toggles
        ctk.CTkLabel(self.scroll_sidebar, text="Catálogo Estadístico", font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", padx=6, pady=(10, 2))
        self.sw_strict_norm = ctk.CTkSwitch(
            self.scroll_sidebar, text="Auto según normalidad",
            command=self.trigger_analysis_thread
        )
        self.sw_strict_norm.pack(anchor="w", padx=6, pady=3)

        for metric in self.metrics:
            # Vinculación contextual con pestaña matemática al hacer click
            sw = ctk.CTkSwitch(
                self.scroll_sidebar, text=metric.display_name,
                command=lambda m=metric: self._on_metric_switch_toggled(m)
            )
            if metric.default_active:
                sw.select()
            sw.pack(anchor="w", padx=6, pady=2)
            self.stat_switches[metric] = sw

        # Maquetación LaTeX
        ctk.CTkLabel(self.scroll_sidebar, text="Maquetación LaTeX", font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", padx=6, pady=(12, 2))
        self.sw_resize = ctk.CTkSwitch(self.scroll_sidebar, text="Autoajuste (\\resizebox)", command=self.trigger_analysis_thread)
        self.sw_resize.select()
        self.sw_resize.pack(anchor="w", padx=6, pady=2)

        self.sw_linespace = ctk.CTkSwitch(self.scroll_sidebar, text="Separar con \\addlinespace", command=self.trigger_analysis_thread)
        self.sw_linespace.pack(anchor="w", padx=6, pady=2)

        self.sw_comma = ctk.CTkSwitch(self.scroll_sidebar, text="Coma decimal (,)", command=self.trigger_analysis_thread)
        self.sw_comma.select()
        self.sw_comma.pack(anchor="w", padx=6, pady=2)

        self.sw_apa = ctk.CTkSwitch(self.scroll_sidebar, text="Nota al pie (APA 7)", command=self.trigger_analysis_thread)
        self.sw_apa.select()
        self.sw_apa.pack(anchor="w", padx=6, pady=2)

        ctk.CTkLabel(self.scroll_sidebar, text="Tipografía / Tamaño:").pack(anchor="w", padx=6, pady=(4, 1))
        self.combo_font = ctk.CTkComboBox(
            self.scroll_sidebar, values=["\\small", "\\footnotesize", "\\scriptsize", "\\normalsize"],
            command=lambda _: self.trigger_analysis_thread()
        )
        self.combo_font.set("\\small")
        self.combo_font.pack(fill="x", padx=6, pady=2)

        # Micro-espaciado y dimensiones de celda
        self.lbl_tabcol = ctk.CTkLabel(self.scroll_sidebar, text="Espaciado (\\tabcolsep): 6 pt")
        self.lbl_tabcol.pack(anchor="w", padx=6, pady=(6, 1))
        self.slider_tabcol = ctk.CTkSlider(self.scroll_sidebar, from_=2, to=16, number_of_steps=14, command=self._on_slider_tabcol)
        self.slider_tabcol.set(6)
        self.slider_tabcol.pack(fill="x", padx=6, pady=2)

        self.lbl_stretch = ctk.CTkLabel(self.scroll_sidebar, text="Interlineado (\\arraystretch): 1.15")
        self.lbl_stretch.pack(anchor="w", padx=6, pady=(6, 1))
        self.slider_stretch = ctk.CTkSlider(self.scroll_sidebar, from_=1.0, to=2.0, number_of_steps=10, command=self._on_slider_stretch)
        self.slider_stretch.set(1.15)
        self.slider_stretch.pack(fill="x", padx=6, pady=2)

    def _on_slider_tabcol(self, val: float):
        self.lbl_tabcol.configure(text=f"Espaciado (\\tabcolsep): {int(val)} pt")
        self.trigger_analysis_thread()

    def _on_slider_stretch(self, val: float):
        self.lbl_stretch.configure(text=f"Interlineado (\\arraystretch): {val:.2f}")
        self.trigger_analysis_thread()

    def _on_metric_switch_toggled(self, metric: StatMetric):
        # Al alternar un switch, el fundamento matemático se actualiza a la ecuación respectiva
        metric_to_math_map = {
            "mean_sd": "Media y Desviación Estándar (Paramétrico)",
            "sem": "Error Estándar (SEM) e Intervalo de Confianza 95%",
            "ci95": "Error Estándar (SEM) e Intervalo de Confianza 95%",
            "variance": "Media y Desviación Estándar (Paramétrico)",
            "median_iqr": "Mediana y Rango Intercuartílico (No Paramétrico)",
            "p10_p90": "Mediana y Rango Intercuartílico (No Paramétrico)",
            "skew_kurt": "Asimetría y Curtosis Muestral"
        }
        if metric.id_key in metric_to_math_map:
            self.combo_math_metric.set(metric_to_math_map[metric.id_key])
            self._render_math_formula()
        self.trigger_analysis_thread()

    # -------------------------------------------------------------------------
    # TAB 1: PREVIEWS Y EDITOR LATEX
    # -------------------------------------------------------------------------
    def _setup_tab_latex(self):
        tab = self.tabview.tab("Tabla & LaTeX")
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_columnconfigure(1, weight=1)
        tab.grid_rowconfigure(1, weight=1)
        tab.grid_rowconfigure(3, weight=2)

        ctk.CTkLabel(tab, text="Dataset Cargado", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, sticky="w", padx=10, pady=(4, 2))
        tree_frame = ctk.CTkFrame(tab)
        tree_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 6))

        scroll_y = ttk.Scrollbar(tree_frame, orient="vertical")
        scroll_x = ttk.Scrollbar(tree_frame, orient="horizontal")
        self.tree = ttk.Treeview(tree_frame, show="headings", yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)
        scroll_y.config(command=self.tree.yview)
        scroll_x.config(command=self.tree.xview)
        scroll_y.pack(side="right", fill="y")
        scroll_x.pack(side="bottom", fill="x")
        self.tree.pack(side="left", fill="both", expand=True)

        render_header = ctk.CTkFrame(tab, fg_color="transparent")
        render_header.grid(row=0, column=1, sticky="ew", padx=10, pady=(4, 2))
        ctk.CTkLabel(render_header, text="Previsualización Renderizada", font=ctk.CTkFont(weight="bold")).pack(side="left")

        self.sw_multiline = ctk.CTkSwitch(render_header, text="Encabezados 2 Líneas", command=self.trigger_analysis_thread)
        self.sw_multiline.select()
        self.sw_multiline.pack(side="right", padx=6)

        self.preview_frame = ctk.CTkFrame(tab, fg_color=THEME_BASE["surface"], corner_radius=6)
        self.preview_frame.grid(row=1, column=1, sticky="nsew", padx=10, pady=(0, 6))

        self.fig_preview = Figure(figsize=(5, 3), dpi=105, facecolor=THEME_BASE["surface"])
        self.ax_preview = self.fig_preview.add_subplot(111)
        self.ax_preview.axis("off")
        self.canvas_preview = FigureCanvasTkAgg(self.fig_preview, master=self.preview_frame)
        self.canvas_preview.get_tk_widget().pack(fill="both", expand=True)

        # Editor de Código e Indicador de Validación
        editor_bar = ctk.CTkFrame(tab, fg_color="transparent")
        editor_bar.grid(row=2, column=0, columnspan=2, sticky="ew", padx=10, pady=(6, 2))
        ctk.CTkLabel(editor_bar, text="Código Fuente LaTeX (booktabs / APA 7)", font=ctk.CTkFont(weight="bold")).pack(side="left")
        self.lbl_latex_validation = ctk.CTkLabel(editor_bar, text="Sintaxis: Pendiente", font=ctk.CTkFont(size=11), text_color=THEME_BASE["text_muted"])
        self.lbl_latex_validation.pack(side="right")

        self.tex_editor = ctk.CTkTextbox(tab, font=("Consolas", 12), wrap="none")
        self.tex_editor.grid(row=3, column=0, columnspan=2, sticky="nsew", padx=10, pady=(0, 10))

    # -------------------------------------------------------------------------
    # TAB 2: NORMALIDAD Y DIAGNÓSTICO
    # -------------------------------------------------------------------------
    def _setup_tab_stats(self):
        tab = self.tabview.tab("Normalidad & Rangos")
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(1, weight=1)

        lbl = ctk.CTkLabel(tab, text="Diagnóstico de Distribución y Rangos Biológicos", font=ctk.CTkFont(size=14, weight="bold"))
        lbl.grid(row=0, column=0, sticky="w", padx=14, pady=10)

        self.txt_norm = ctk.CTkTextbox(tab, font=("Consolas", 12), wrap="none")
        self.txt_norm.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        self.txt_norm.insert("1.0", "% Carga un archivo para evaluar el ajuste a la distribución normal.")

    # -------------------------------------------------------------------------
    # TAB 3: VISUALIZACIONES ANALÍTICAS
    # -------------------------------------------------------------------------
    def _setup_tab_plots(self):
        tab = self.tabview.tab("Gráficas Analíticas")
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(1, weight=1)

        top_bar = ctk.CTkFrame(tab, fg_color="transparent")
        top_bar.grid(row=0, column=0, sticky="ew", padx=10, pady=8)

        ctk.CTkLabel(top_bar, text="Var X:").pack(side="left", padx=(0, 4))
        self.combo_plot_var = ctk.CTkComboBox(top_bar, values=["(ninguna)"], width=130, command=lambda _: self.render_selected_plot())
        self.combo_plot_var.pack(side="left", padx=4)

        ctk.CTkLabel(top_bar, text="Var Y:").pack(side="left", padx=(6, 4))
        self.combo_plot_var_y = ctk.CTkComboBox(top_bar, values=["(ninguna)"], width=130, command=lambda _: self.render_selected_plot())
        self.combo_plot_var_y.pack(side="left", padx=4)

        ctk.CTkLabel(top_bar, text="Tipo:").pack(side="left", padx=(6, 4))
        self.combo_plot_type = ctk.CTkComboBox(
            top_bar,
            values=[
                "Sugerido por IA (Auto)",
                "Boxplot + Jitter",
                "Violin Plot",
                "Dot Plot + SEM",
                "Histograma + KDE",
                "Q-Q Plot Normal",
                "Forest Plot (IC 95%)",
                "Dispersión + Regresión",
                "Heatmap Correlación"
            ],
            width=170,
            command=lambda _: self.render_selected_plot()
        )
        self.combo_plot_type.pack(side="left", padx=4)

        ctk.CTkLabel(top_bar, text="Paleta:").pack(side="left", padx=(6, 4))
        self.combo_palette = ctk.CTkComboBox(
            top_bar,
            values=list(PALETTES.keys()),
            width=180,
            command=lambda _: self.render_selected_plot()
        )
        self.combo_palette.set("BioEvo Classic (Cyan/Blue)")
        self.combo_palette.pack(side="left", padx=4)

        self.sw_log_scale = ctk.CTkSwitch(top_bar, text="Log", command=self.render_selected_plot)
        self.sw_log_scale.pack(side="left", padx=6)

        btn_save_pdf = ctk.CTkButton(top_bar, text="📄 PDF Vector", width=95, command=lambda: self.save_figure("pdf"))
        btn_save_pdf.pack(side="right", padx=2)

        btn_save_svg = ctk.CTkButton(top_bar, text="📐 SVG", width=75, command=lambda: self.save_figure("svg"))
        btn_save_svg.pack(side="right", padx=2)

        btn_save_png = ctk.CTkButton(top_bar, text="🖼️ PNG HD", width=85, command=lambda: self.save_figure("png"))
        btn_save_png.pack(side="right", padx=2)

        self.lbl_plot_sug = ctk.CTkLabel(tab, text="", text_color=THEME_BASE["text_muted"], font=ctk.CTkFont(size=11, slant="italic"))
        self.lbl_plot_sug.grid(row=2, column=0, sticky="w", padx=12, pady=4)

        self.plot_canvas_frame = ctk.CTkFrame(tab, fg_color=THEME_BASE["surface"])
        self.plot_canvas_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 2))

        self.fig_analytics = Figure(figsize=(8.5, 5.2), dpi=110, facecolor=THEME_BASE["surface"])
        self.canvas_analytics = FigureCanvasTkAgg(self.fig_analytics, master=self.plot_canvas_frame)
        self.canvas_analytics.get_tk_widget().pack(fill="both", expand=True)

    # -------------------------------------------------------------------------
    # TAB 4: FUNDAMENTO MATEMÁTICO RENDERIZADO
    # -------------------------------------------------------------------------
    def _setup_tab_math(self):
        tab = self.tabview.tab("Fundamento Matemático")
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(1, weight=1)

        top_math = ctk.CTkFrame(tab, fg_color="transparent")
        top_math.grid(row=0, column=0, sticky="ew", padx=12, pady=8)

        ctk.CTkLabel(top_math, text="Ecuación y Metodología:", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=6)
        self.combo_math_metric = ctk.CTkComboBox(
            top_math,
            values=[
                "Media y Desviación Estándar (Paramétrico)",
                "Error Estándar (SEM) e Intervalo de Confianza 95%",
                "Mediana y Rango Intercuartílico (No Paramétrico)",
                "Prueba de Normalidad Shapiro-Wilk (W)",
                "Asimetría y Curtosis Muestral"
            ],
            width=380,
            command=lambda _: self._render_math_formula()
        )
        self.combo_math_metric.pack(side="left", padx=6)

        self.math_canvas_frame = ctk.CTkFrame(tab, fg_color=THEME_BASE["surface"])
        self.math_canvas_frame.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 10))

        self.fig_math = Figure(figsize=(9, 6), dpi=115, facecolor=THEME_BASE["surface"])
        self.canvas_math = FigureCanvasTkAgg(self.fig_math, master=self.math_canvas_frame)
        self.canvas_math.get_tk_widget().pack(fill="both", expand=True)
        self._render_math_formula()

    def _render_math_formula(self):
        choice = self.combo_math_metric.get()
        self.fig_math.clear()
        ax = self.fig_math.add_subplot(111)
        ax.set_facecolor(THEME_BASE["surface"])
        ax.axis("off")

        if "Media y Desviación" in choice:
            formula = (
                r"$\mathbf{1.\; Media\; Muestral\; (\bar{x}):}\quad \bar{x} = \frac{1}{n} \sum_{i=1}^{n} x_i$"
                "\n\n"
                r"$\mathbf{2.\; Desviaci\acute{o}n\; Est\acute{a}ndar\; (s):}\quad s = \sqrt{\frac{1}{n-1} \sum_{i=1}^{n} (x_i - \bar{x})^2}$"
                "\n\n"
                r"$\mathbf{3.\; Rango\; Referencia\; Param\acute{e}trico\; (95\%):}\quad \mathrm{Ref}_{95\%} = \left[\, \bar{x} - 1.96 \cdot s \,,\; \bar{x} + 1.96 \cdot s \,\right]$"
            )
            desc = (
                "• Grados de libertad (g.d.l.): n - 1 (Corrección de Bessel para remover sesgo de la varianza muestral).\n"
                "• Requisito editorial: Exclusivo para poblaciones con distribución normal confirmada (p >= 0.05)."
            )
        elif "Error Estándar" in choice:
            formula = (
                r"$\mathbf{1.\; Error\; Est\acute{a}ndar\; de\; la\; Media\; (SEM):}\quad \mathrm{SEM} = \frac{s}{\sqrt{n}}$"
                "\n\n"
                r"$\mathbf{2.\; Intervalo\; de\; Confianza\; del\; 95\%\; (t-Student):}\quad \mathrm{IC}_{95\%} = \bar{x} \pm t_{\alpha/2,\, n-1} \cdot \mathrm{SEM}$"
            )
            desc = (
                "• Cuantifica la precisión del estimador muestral respecto a la verdadera media poblacional μ.\n"
                "• Emplea la distribución t de Student para corregir la incertidumbre asociada a varianzas muestrales."
            )
        elif "Mediana y Rango" in choice:
            formula = (
                r"$\mathbf{1.\; Mediana\; (P_{50}):}\quad \tilde{x} = x_{\left(\frac{n+1}{2}\right)} \quad \text{o} \quad \frac{1}{2}\left(x_{(n/2)} + x_{(n/2+1)}\right)$"
                "\n\n"
                r"$\mathbf{2.\; Rango\; Intercuart\acute{\imath}lico\; (IQR):}\quad \mathrm{IQR} = Q_3 - Q_1 = P_{75} - P_{25}$"
                "\n\n"
                r"$\mathbf{3.\; Rango\; Emp\acute{\imath}rico\; Incondicional\; (95\%):}\quad \mathrm{Ref}_{95\%}^* = \left[\, P_{2.5} \,,\; P_{97.5} \,\right]$"
            )
            desc = (
                "• Estadística robusta no paramétrica: Invariante ante asimetrías severas y outliers de laboratorio.\n"
                "• Obligatorio al rechazar la hipótesis nula de normalidad (p < 0.05 en Shapiro-Wilk)."
            )
        elif "Shapiro-Wilk" in choice:
            formula = (
                r"$\mathbf{Estad\acute{\imath}stico\; W\; de\; Shapiro-Wilk:}\quad W = \frac{\left( \sum_{i=1}^{n} a_i \, x_{(i)} \right)^2}{\sum_{i=1}^{n} (x_i - \bar{x})^2}$"
                "\n\n"
                r"$\mathbf{Criterio\; de\; Decisi\acute{o}n\; Metodol\acute{o}gica:}\quad "
                r"\begin{cases} "
                r"p \ge 0.05 \implies \text{Ajuste Normal} \implies \text{Reportar } \bar{x} \pm s \\ "
                r"p < 0.05 \implies \text{No Normal} \implies \text{Reportar Mediana [IQR]} "
                r"\end{cases}$"
            )
            desc = (
                "• x_(i) representa los estadísticos de orden muestrales.\n"
                "• a_i se calcula a través de las matrices de covarianza de los cuantiles teóricos normales."
            )
        else:
            formula = (
                r"$\mathbf{Asimetr\acute{\imath}a\; Insesgada\; (g_1):}\quad g_1 = \frac{n}{(n-1)(n-2)} \sum_{i=1}^{n} \left(\frac{x_i - \bar{x}}{s}\right)^3$"
                "\n\n"
                r"$\mathbf{Curtosis\; Excesiva\; (g_2):}\quad g_2 = \frac{n(n+1)}{(n-1)(n-2)(n-3)} \sum_{i=1}^{n} \left(\frac{x_i - \bar{x}}{s}\right)^4 - \frac{3(n-1)^2}{(n-2)(n-3)}$"
            )
            desc = (
                "• g1 > 0: Cola extendida a la derecha; g1 < 0: Cola extendida a la izquierda.\n"
                "• g2 = 0 corresponde a la distribución mesocúrtica normal."
            )

        ax.text(0.04, 0.78, formula, fontsize=12, color=PALETTES[self.combo_palette.get()]["accent"], verticalalignment="top")
        ax.text(0.04, 0.20, desc, fontsize=10, color=THEME_BASE["text"], verticalalignment="top", style="italic")
        self.fig_math.tight_layout()
        self.canvas_math.draw()

    # -------------------------------------------------------------------------
    # GESTIÓN CONCURRENTE (THREADING)
    # -------------------------------------------------------------------------
    def load_file_threaded(self):
        path = filedialog.askopenfilename(
            filetypes=[("Archivos Tabulares", "*.csv *.tsv *.txt *.xlsx *.xls"), ("Todos los archivos", "*.*")]
        )
        if not path:
            return

        self.current_filepath = path
        self.progress_bar.set(0.1)
        self.lbl_progress.configure(text="Detectando delimitadores y codificación...")

        def _worker():
            try:
                df_loaded, meta = read_delimited_robust(path)
                self.after(0, self._on_file_loaded, df_loaded, meta, path)
            except Exception as e:
                self.after(0, self._on_worker_error, f"Error en lectura de datos: {e}")

        threading.Thread(target=_worker, daemon=True).start()

    def _on_file_loaded(self, df_loaded: pd.DataFrame, meta: Dict[str, Any], path: str):
        self.df = df_loaded
        self.current_meta = meta
        self.progress_bar.set(0.4)

        # Log de saneamiento profesional en UI
        log_str = f"{os.path.basename(path)} | Enc: {meta['encoding']} | Sep: '{meta['delimiter']}' | Comas corregidas: {meta['coerced_columns']}"
        self.lbl_progress.configure(text=log_str, text_color=THEME_BASE["success"])
        self.btn_copy.configure(state="normal")
        self.btn_save_tex.configure(state="normal")

        self._populate_variables()
        self._populate_preview()
        self.trigger_analysis_thread()

    def _on_worker_error(self, err_msg: str):
        self.progress_bar.set(0)
        self.lbl_progress.configure(text="Fallo en la operación", text_color=THEME_BASE["danger"])
        messagebox.showerror("Error", err_msg)

    def trigger_analysis_thread(self):
        if self.df is None:
            return
        self.progress_bar.set(0.5)
        threading.Thread(target=self._compute_analysis_worker, daemon=True).start()

    # -------------------------------------------------------------------------
    # MOTOR CIENTÍFICO Y GENERADOR LATEX
    # -------------------------------------------------------------------------
    def _compute_analysis_worker(self):
        try:
            selected_vars = [col for col, cb in self.var_checkboxes.items() if cb.get() == 1]
            if not selected_vars:
                self.after(0, self._update_ui_empty_vars)
                return

            active_metrics = [m for m, sw in self.stat_switches.items() if sw.get() == 1]
            use_comma = self.sw_comma.get() == 1
            group_col = self.combo_group.get()
            is_grouped = group_col != "(sin agrupar)" and group_col in self.df.columns
            split_headers = self.sw_multiline.get() == 1
            strict_norm = self.sw_strict_norm.get() == 1

            def fmt(n: float, dec: int = 2) -> str:
                if pd.isna(n) or np.isinf(n):
                    return "---"
                txt = f"{n:.{dec}f}"
                return txt.replace(".", ",") if use_comma else txt

            rows = []
            preview_table_data = []

            latex_headers = ["Grupo", "Variable"] if is_grouped else ["Variable"]
            clean_headers = ["Grupo", "Variable"] if is_grouped else ["Variable"]

            for m in active_metrics:
                latex_headers.append(m.latex_header)
                txt_h = m.display_name
                if split_headers and " " in txt_h:
                    txt_h = txt_h.replace(" ", "\n", 1)
                clean_headers.append(txt_h)

            total_computations = len(selected_vars) * (self.df[group_col].nunique() if is_grouped else 1)
            comp_done = 0

            # Cómputo estadístico con filtrado estricto de normalidad
            def process_series(s: pd.Series, safe_v: str, safe_g: Optional[str] = None):
                n_len = len(s)
                es_normal = True
                if n_len >= 3 and s.nunique() > 1:
                    _, p_val = stats.shapiro(s[:5000])
                    es_normal = p_val >= 0.05

                r_tex = [safe_g, safe_v] if safe_g else [safe_v]
                r_prev = [str(safe_g), safe_v] if safe_g else [safe_v]

                for m in active_metrics:
                    if strict_norm and m.is_parametric and not es_normal:
                        val = r"\text{---}"
                        val_prev = "---"
                    elif strict_norm and not m.is_parametric and es_normal and not isinstance(m, (MinMaxMetric, SampleSizeMetric)):
                        val = r"\text{---}"
                        val_prev = "---"
                    else:
                        val = m.compute(s, fmt)
                        val_prev = val.replace("$", "").replace(r"\pm", "±").replace(r"\'{\i}", "í").replace(r"\'ax", "á")

                    r_tex.append(val)
                    r_prev.append(val_prev)

                return r_tex, r_prev

            if is_grouped:
                for grp, sub in self.df.groupby(group_col):
                    safe_grp = sanitize_latex(str(grp))
                    for var in selected_vars:
                        s = sub[var].dropna()
                        safe_var = sanitize_latex(var)
                        r_t, r_p = process_series(s, safe_var, safe_grp)
                        rows.append(r_t)
                        preview_table_data.append(r_p)
                        comp_done += 1
                        self.progress_bar.set(0.5 + 0.4 * (comp_done / total_computations))
            else:
                for var in selected_vars:
                    s = self.df[var].dropna()
                    safe_var = sanitize_latex(var)
                    r_t, r_p = process_series(s, safe_var)
                    rows.append(r_t)
                    preview_table_data.append(r_p)
                    comp_done += 1
                    self.progress_bar.set(0.5 + 0.4 * (comp_done / total_computations))

            # Ensamblado LaTeX formal (booktabs)
            cols_def = "l" + "c" * (len(latex_headers) - 1)
            font_cmd = self.combo_font.get()
            use_resize = self.sw_resize.get() == 1
            use_linespace = self.sw_linespace.get() == 1
            tabcol_val = int(self.slider_tabcol.get())
            stretch_val = self.slider_stretch.get()

            tex = [
                r"% ===================================================================",
                r"% TABLA FORMATEADA CON BIOEVO | LABSTATS CORE (v1.0.0-rc.1)",
                r"% Paquetes requeridos: \usepackage{booktabs}, \usepackage{graphicx}",
                r"% ===================================================================",
                r"\begin{table}[htbp]",
                r"  \centering",
                f"  {font_cmd}",
                f"  \\setlength{{\\tabcolsep}}{{{tabcol_val}pt}}",
                f"  \\renewcommand{{\\arraystretch}}{{{stretch_val:.2f}}}",
                r"  \caption{Resumen estadístico de variables biométricas.}",
                r"  \label{tab:labstats_summary}"
            ]

            if use_resize:
                tex.append(r"  \resizebox{\textwidth}{!}{%")

            tex.extend([
                f"  \\begin{{tabular}}{{{cols_def}}}",
                r"    \toprule",
                f"    {' & '.join(latex_headers)} \\\\",
                r"    \midrule"
            ])

            for idx, r in enumerate(rows):
                tex.append(f"    {' & '.join(r)} \\\\")
                if use_linespace and (idx + 1) < len(rows):
                    tex.append(r"    \addlinespace[0.4ex]")

            tex.extend([
                r"    \bottomrule",
                r"  \end{tabular}"
            ])

            if use_resize:
                tex.append(r"  }")

            if self.sw_apa.get() == 1:
                tex.extend([
                    r"  \vspace{1ex}\\",
                    r"  \raggedright\footnotesize\textit{Nota.} Datos expresados según normalidad (Shapiro-Wilk): paramétricos como media $\pm$ DE y no paramétricos como mediana [IQR]."
                ])

            tex.append(r"\end{table}")
            full_latex = "\n".join(tex)

            # Validación de sintaxis LaTeX en tiempo real
            is_valid, reason = validate_latex_syntax(full_latex)
            norm_report = self._compute_normality_report(selected_vars, fmt)

            self.after(0, self._render_results_on_ui, full_latex, clean_headers, preview_table_data, norm_report, is_valid, reason)

        except Exception as e:
            self.after(0, self._on_worker_error, f"Error en cómputo analítico: {e}")

    def _compute_normality_report(self, selected_vars: List[str], fmt: Callable[[float, int], str]) -> str:
        report = [
            "=" * 80,
            " DIAGNÓSTICO DE AJUSTE A LA NORMALIDAD (SHAPIRO-WILK)",
            "=" * 80,
            f"{'Variable':<22} {'W':<8} {'Valor p':<10} {'Ajuste':<14} {'Rango Ref. (95%)':<24}",
            "-" * 80
        ]

        for var in selected_vars:
            s = self.df[var].dropna()
            n_len = len(s)
            if n_len >= 3 and s.nunique() > 1:
                w_stat, p_val = stats.shapiro(s[:5000])
                es_normal = p_val >= 0.05
                conclusion = "Normal" if es_normal else "No normal"
                p_str = f"{p_val:.4f}" if p_val >= 0.001 else "< 0.001"

                if es_normal:
                    m, sd = s.mean(), s.std(ddof=1) if n_len > 1 else 0.0
                    rango = f"[{fmt(m - 1.96 * sd)} -- {fmt(m + 1.96 * sd)}]"
                else:
                    q025, q975 = s.quantile(0.025), s.quantile(0.975)
                    rango = f"[{fmt(q025)} -- {fmt(q975)}]*"

                report.append(f"{var:<22} {w_stat:<8.4f} {p_str:<10} {conclusion:<14} {rango:<24}")
            elif s.nunique() <= 1:
                report.append(f"{var:<22} Serie constante (Varianza nula)")
            else:
                report.append(f"{var:<22} Muestra insuficiente (n < 3)")

        report.extend([
            "-" * 80,
            "Criterio metodológico: Normal si p >= 0.05 (H0: la muestra procede de una distribución normal).",
            "* Rangos con asterisco calculados vía cuantiles empíricos [P2.5 -- P97.5] por no normalidad."
        ])
        return "\n".join(report)

    # -------------------------------------------------------------------------
    # RENDERIZADO VISUAL
    # -------------------------------------------------------------------------
    def _render_results_on_ui(self, latex_code: str, headers: List[str], rows: List[List[str]], norm_text: str, is_valid: bool, val_reason: str):
        self.progress_bar.set(1.0)

        # Editor de texto
        self.tex_editor.delete("1.0", "end")
        self.tex_editor.insert("1.0", latex_code)

        # Validación sintáctica en interfaz
        if is_valid:
            self.lbl_latex_validation.configure(text="✓ Sintaxis LaTeX verificada", text_color=THEME_BASE["success"])
        else:
            self.lbl_latex_validation.configure(text=f"⚠ Error: {val_reason}", text_color=THEME_BASE["danger"])

        # Previsualización gráfica renderizada con Matplotlib
        self.ax_preview.clear()
        self.ax_preview.axis("off")

        if rows:
            tab_obj = self.ax_preview.table(
                cellText=rows,
                colLabels=headers,
                loc="center",
                cellLoc="center"
            )
            tab_obj.auto_set_font_size(False)
            tab_obj.set_fontsize(8.2)
            tab_obj.scale(1.0, 1.8)
            tab_obj.auto_set_column_width(col=list(range(len(headers))))

            palette = PALETTES[self.combo_palette.get()]
            for (r_idx, c_idx), cell in tab_obj.get_celld().items():
                cell.set_edgecolor(THEME_BASE["border"])
                cell.set_linewidth(0.6)
                if r_idx == 0:
                    cell.set_facecolor(THEME_BASE["card"])
                    cell.set_text_props(weight="bold", color=palette["accent"])
                else:
                    cell.set_facecolor(THEME_BASE["surface"])
                    cell.set_text_props(color=THEME_BASE["text"])

        self.canvas_preview.draw()
        self.txt_norm.delete("1.0", "end")
        self.txt_norm.insert("1.0", norm_text)

        # Actualizar combos gráficos
        numeric_cols = self.df.select_dtypes(include=[np.number]).columns.tolist()
        self.combo_plot_var.configure(values=numeric_cols)
        self.combo_plot_var_y.configure(values=["(ninguna)"] + numeric_cols)
        if numeric_cols and self.combo_plot_var.get() not in numeric_cols:
            self.combo_plot_var.set(numeric_cols[0])
            self.render_selected_plot()

    # -------------------------------------------------------------------------
    # SUITE DE GRÁFICAS ANALÍTICAS
    # -------------------------------------------------------------------------
    def render_selected_plot(self):
        if self.df is None:
            return

        var_x = self.combo_plot_var.get()
        if var_x not in self.df.columns:
            return

        s_x = self.df[var_x].dropna()
        if len(s_x) < 2:
            return

        var_y = self.combo_plot_var_y.get()
        mode = self.combo_plot_type.get()
        palette = PALETTES[self.combo_palette.get()]
        use_log = self.sw_log_scale.get() == 1

        # Detección de escala logarítmica automática si el rango abarca > 3 órdenes de magnitud
        if s_x.min() > 0 and (s_x.max() / s_x.min()) >= 1000 and not self.sw_log_scale.get():
            use_log = True
            self.lbl_plot_sug.configure(text="Sugerencia: Escala Log aplicada automáticamente (rango > 3 órdenes de magnitud).")

        es_normal = True
        if len(s_x) >= 3 and s_x.nunique() > 1:
            _, p_val = stats.shapiro(s_x[:5000])
            es_normal = p_val >= 0.05
        else:
            p_val = 1.0

        if "Auto" in mode:
            plot_to_run = "Histograma + KDE" if es_normal else "Boxplot + Jitter"
            self.lbl_plot_sug.configure(text=f"Sugerencia analítica: {'Normal' if es_normal else 'No normal'} (p={p_val:.4f})")
        else:
            plot_to_run = mode

        self.fig_analytics.clear()
        ax = self.fig_analytics.add_subplot(111)
        ax.set_facecolor(THEME_BASE["surface"])

        ax.tick_params(colors=THEME_BASE["text"], labelsize=9)
        for spine in ax.spines.values():
            spine.set_color(THEME_BASE["border"])

        # 1. Boxplot + Jitter
        if plot_to_run == "Boxplot + Jitter":
            bp = ax.boxplot(s_x, patch_artist=True, vert=True, widths=0.35, showfliers=False)
            for box in bp["boxes"]:
                box.set_facecolor(palette["primary"])
                box.set_alpha(0.7)
            for median in bp["medians"]:
                median.set_color(palette["highlight"])
                median.set_linewidth(2)

            jitter = np.random.normal(1, 0.04, size=len(s_x))
            ax.scatter(jitter, s_x, color=palette["accent"], alpha=0.6, s=25, edgecolors="none")
            ax.set_xticks([1])
            ax.set_xticklabels([var_x])
            ax.set_title(f"Boxplot con Jitter: {var_x}", color=THEME_BASE["text"], weight="bold")

        # 2. Violin Plot
        elif plot_to_run == "Violin Plot":
            v_parts = ax.violinplot(s_x, showmeans=False, showmedians=True)
            for pc in v_parts["bodies"]:
                pc.set_facecolor(palette["accent"])
                pc.set_edgecolor(palette["primary"])
                pc.set_alpha(0.65)
            v_parts["cmedians"].set_color(palette["highlight"])
            ax.set_xticks([1])
            ax.set_xticklabels([var_x])
            ax.set_title(f"Violin Plot: {var_x}", color=THEME_BASE["text"], weight="bold")

        # 3. Dot Plot + SEM
        elif plot_to_run == "Dot Plot + SEM":
            m_val = s_x.mean()
            sem_val = s_x.std(ddof=1) / np.sqrt(len(s_x)) if len(s_x) > 1 else 0.0
            jitter = np.random.normal(1, 0.05, size=len(s_x))
            ax.scatter(jitter, s_x, color=palette["accent"], alpha=0.45, s=20)
            ax.errorbar([1], [m_val], yerr=[sem_val], fmt="o", color=THEME_BASE["danger"], elinewidth=2.5, capsize=6, label=r"$\bar{x} \pm \mathrm{SEM}$")
            ax.set_xticks([1])
            ax.set_xticklabels([var_x])
            ax.set_title(f"Dot Plot con Error Estándar: {var_x}", color=THEME_BASE["text"], weight="bold")
            ax.legend(facecolor=THEME_BASE["card"], edgecolor=THEME_BASE["border"], fontsize=9)

        # 4. Histograma + KDE
        elif plot_to_run == "Histograma + KDE":
            n_bins = max(5, int(np.sqrt(len(s_x))))
            ax.hist(s_x, bins=n_bins, density=True, color=palette["primary"], alpha=0.5, edgecolor=palette["accent"])
            mu, sigma = s_x.mean(), s_x.std(ddof=1) if len(s_x) > 1 else 1.0
            x_line = np.linspace(s_x.min(), s_x.max(), 200)
            y_line = stats.norm.pdf(x_line, mu, sigma)
            ax.plot(x_line, y_line, color=palette["highlight"], linewidth=2, label="Ajuste Normal")
            ax.set_title(f"Histograma y Curva Normal: {var_x}", color=THEME_BASE["text"], weight="bold")
            ax.legend(facecolor=THEME_BASE["card"], edgecolor=THEME_BASE["border"], fontsize=9)

        # 5. Q-Q Plot
        elif plot_to_run == "Q-Q Plot Normal":
            (osm, osr), (slope, intercept, r) = stats.probplot(s_x, dist="norm")
            ax.scatter(osm, osr, color=palette["accent"], alpha=0.7, s=25)
            ax.plot(osm, slope * np.array(osm) + intercept, color=THEME_BASE["danger"], linewidth=1.8, label=f"R² = {r**2:.3f}")
            ax.set_title(f"Q-Q Plot Normal: {var_x}", color=THEME_BASE["text"], weight="bold")
            ax.set_xlabel("Cuantiles Teóricos")
            ax.set_ylabel("Cuantiles Muestrales")
            ax.legend(facecolor=THEME_BASE["card"], edgecolor=THEME_BASE["border"], fontsize=9)

        # 6. Forest Plot (IC 95%)
        elif plot_to_run == "Forest Plot (IC 95%)":
            selected_vars = [col for col, cb in self.var_checkboxes.items() if cb.get() == 1]
            y_coords = list(range(len(selected_vars)))
            means, ci_lows, ci_highs = [], [], []

            for col in selected_vars:
                s = self.df[col].dropna()
                n = len(s)
                m = s.mean()
                sem = s.std(ddof=1) / np.sqrt(n) if n > 1 else 0.0
                ci = stats.t.interval(0.95, df=max(1, n - 1), loc=m, scale=sem)
                means.append(m)
                ci_lows.append(m - ci[0])
                ci_highs.append(ci[1] - m)

            ax.errorbar(means, y_coords, xerr=[ci_lows, ci_highs], fmt="o", color=palette["accent"], ecolor=palette["highlight"], elinewidth=2, capsize=5)
            ax.set_yticks(y_coords)
            ax.set_yticklabels(selected_vars)
            ax.set_title("Forest Plot: Intervalos de Confianza 95%", color=THEME_BASE["text"], weight="bold")

        # 7. Dispersión + Regresión
        elif plot_to_run == "Dispersión + Regresión":
            if var_y not in self.df.columns or var_y == "(ninguna)":
                ax.text(0.5, 0.5, "Selecciona una Variable Y válida en la barra superior", ha="center", va="center", color=THEME_BASE["warning"])
            else:
                paired = self.df[[var_x, var_y]].dropna()
                ax.scatter(paired[var_x], paired[var_y], color=palette["accent"], alpha=0.7, s=30)
                if len(paired) > 2:
                    slope, intercept, r_val, _, _ = stats.linregress(paired[var_x], paired[var_y])
                    x_vals = np.linspace(paired[var_x].min(), paired[var_x].max(), 100)
                    ax.plot(x_vals, slope * x_vals + intercept, color=THEME_BASE["danger"], linewidth=2, label=f"R² = {r_val**2:.3f}")
                    ax.legend(facecolor=THEME_BASE["card"], edgecolor=THEME_BASE["border"], fontsize=9)
                ax.set_xlabel(var_x)
                ax.set_ylabel(var_y)
                ax.set_title(f"Dispersión y Regresión: {var_x} vs {var_y}", color=THEME_BASE["text"], weight="bold")

        # 8. Heatmap de Correlación
        elif plot_to_run == "Heatmap Correlación":
            numeric_df = self.df.select_dtypes(include=[np.number])
            if numeric_df.shape[1] < 2:
                ax.text(0.5, 0.5, "Se requieren al menos 2 variables numéricas", ha="center", va="center")
            else:
                corr = numeric_df.corr(method="pearson").values
                cax = ax.matshow(corr, cmap="coolwarm", vmin=-1, vmax=1)
                self.fig_analytics.colorbar(cax, ax=ax, fraction=0.046, pad=0.04)
                cols = numeric_df.columns
                ax.set_xticks(range(len(cols)))
                ax.set_yticks(range(len(cols)))
                ax.set_xticklabels(cols, rotation=45, ha="left")
                ax.set_yticklabels(cols)
                ax.set_title("Matriz de Correlación de Pearson", color=THEME_BASE["text"], pad=20, weight="bold")

        if use_log and plot_to_run not in ("Q-Q Plot Normal", "Heatmap Correlación", "Forest Plot (IC 95%)"):
            ax.set_yscale("log")

        ax.grid(True, linestyle="--", alpha=0.15, color=THEME_BASE["text_muted"])
        self.fig_analytics.tight_layout()
        self.canvas_analytics.draw()

    # -------------------------------------------------------------------------
    # EXPORTACIÓN Y SERIALIZACIÓN DE PROYECTOS (.BIOEVO)
    # -------------------------------------------------------------------------
    def save_figure(self, ext: str = "pdf"):
        path = filedialog.asksaveasfilename(
            defaultextension=f".{ext}",
            filetypes=[(f"Archivo {ext.upper()}", f"*.{ext}")]
        )
        if path:
            metadata = {
                "Creator": "BioEvo LabStats Formatter v1.0.0-rc.1",
                "CreationDate": datetime.now().isoformat(),
                "Title": f"Análisis bioestadístico - {self.combo_plot_var.get()}"
            }
            self.fig_analytics.savefig(
                path, dpi=300, facecolor=self.fig_analytics.get_facecolor(),
                edgecolor="none", metadata=metadata if ext == "pdf" else None
            )
            messagebox.showinfo("Guardado", f"Figura exportada exitosamente en:\n{path}")

    def save_tex_file(self):
        code = self.tex_editor.get("1.0", "end").strip()
        if not code:
            return

        base = os.path.splitext(os.path.basename(self.current_filepath))[0] if self.current_filepath else "labstats"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"{base}_{timestamp}.tex"

        path = filedialog.asksaveasfilename(
            initialfile=default_name,
            defaultextension=".tex",
            filetypes=[("Documento LaTeX", "*.tex")]
        )
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(code)
            messagebox.showinfo("Guardado", f"Archivo .tex guardado en:\n{path}")

    def save_project_json(self):
        """Serializa la configuración del dataset y sidebar a formato .bioevo."""
        if self.df is None:
            messagebox.showwarning("Atención", "No hay datos cargados para exportar un proyecto.")
            return

        project_state = {
            "version": "1.0.0-rc.1",
            "source_file": self.current_filepath,
            "created_at": datetime.now().isoformat(),
            "group_by": self.combo_group.get(),
            "font_size": self.combo_font.get(),
            "tabcolsep": self.slider_tabcol.get(),
            "arraystretch": self.slider_stretch.get(),
            "switches": {
                "strict_norm": self.sw_strict_norm.get(),
                "resizebox": self.sw_resize.get(),
                "linespace": self.sw_linespace.get(),
                "comma": self.sw_comma.get(),
                "apa": self.sw_apa.get(),
            },
            "active_metrics": [m.id_key for m, sw in self.stat_switches.items() if sw.get() == 1],
            "selected_vars": [col for col, cb in self.var_checkboxes.items() if cb.get() == 1]
        }

        path = filedialog.asksaveasfilename(
            defaultextension=".bioevo",
            filetypes=[("Proyecto BioEvo", "*.bioevo")]
        )
        if path:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(project_state, f, indent=2)
            messagebox.showinfo("Proyecto Guardado", f"Configuración guardada en:\n{path}")

    # -------------------------------------------------------------------------
    # GESTIÓN DE VARIABLES Y ESTADO
    # -------------------------------------------------------------------------
    def _populate_variables(self):
        for widget in self.var_container.winfo_children():
            widget.destroy()
        self.var_checkboxes.clear()

        numeric_cols = self.df.select_dtypes(include=[np.number]).columns.tolist()
        all_cols = self.df.columns.tolist()

        for col in numeric_cols:
            cb = ctk.CTkCheckBox(self.var_container, text=col, command=self.trigger_analysis_thread)
            cb.select()
            cb.pack(anchor="w", padx=8, pady=3)
            self.var_checkboxes[col] = cb

        group_candidates = ["(sin agrupar)"] + [c for c in all_cols if c not in numeric_cols or self.df[c].nunique() < 15]
        self.combo_group.configure(values=group_candidates)
        self.combo_group.set("(sin agrupar)")

    def _filter_variable_checkboxes(self):
        query = self.entry_filter_var.get().strip().lower()
        for col, cb in self.var_checkboxes.items():
            if query in col.lower():
                cb.pack(anchor="w", padx=8, pady=3)
            else:
                cb.pack_forget()

    def _populate_preview(self):
        self.tree.delete(*self.tree.get_children())
        self.tree["columns"] = list(self.df.columns)

        for col in self.df.columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=110, anchor="center")

        for _, row in self.df.head(60).iterrows():
            self.tree.insert("", "end", values=list(row))

    def _update_ui_empty_vars(self):
        self.progress_bar.set(0)
        self.tex_editor.delete("1.0", "end")
        self.tex_editor.insert("1.0", "% Selecciona al menos una variable en la barra lateral.")
        self.ax_preview.clear()
        self.ax_preview.axis("off")
        self.canvas_preview.draw()

    def select_all_vars(self):
        for cb in self.var_checkboxes.values():
            cb.select()
        self.trigger_analysis_thread()

    def deselect_all_vars(self):
        for cb in self.var_checkboxes.values():
            cb.deselect()
        self.trigger_analysis_thread()

    def copy_latex(self):
        code = self.tex_editor.get("1.0", "end").strip()
        if not code:
            return

        if HAS_PYPERCLIP:
            pyperclip.copy(code)
            messagebox.showinfo("Copiado", "¡Código LaTeX copiado al portapapeles!")
        else:
            self.clipboard_clear()
            self.clipboard_append(code)
            messagebox.showinfo("Copiado", "¡Código copiado al portapapeles!\n(Vía fallback nativo de Tkinter).")

    def clear_all(self):
        self.df = None
        self.current_filepath = ""
        self.current_meta = {}
        self.tree.delete(*self.tree.get_children())
        self.tex_editor.delete("1.0", "end")
        self.txt_norm.delete("1.0", "end")
        self.lbl_progress.configure(text="Sin archivo cargado", text_color=THEME_BASE["text_muted"])
        self.lbl_latex_validation.configure(text="Sintaxis: Pendiente", text_color=THEME_BASE["text_muted"])
        self.btn_copy.configure(state="disabled")
        self.btn_save_tex.configure(state="disabled")

        self.ax_preview.clear()
        self.ax_preview.axis("off")
        self.canvas_preview.draw()

        self.fig_analytics.clear()
        self.canvas_analytics.draw()

        for widget in self.var_container.winfo_children():
            widget.destroy()
        self.var_checkboxes.clear()
        self.combo_group.configure(values=["(sin agrupar)"])
        self.combo_group.set("(sin agrupar)")


if __name__ == "__main__":
    app = LabStatsApp()
    app.mainloop()