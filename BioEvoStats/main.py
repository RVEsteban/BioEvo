"""
BioEvo | LabStats Formatter (v1.1.0-beta.2 - Stable Engine)
Copyright (c) 2026 Esteban Rosero / BioEvo Core. Todos los derechos reservados.
Estación de trabajo bioestadística, ecológica e ingeniería local-first para maquetación LaTeX,
diagnóstico distribucional, diversidad alfa/beta e inferencia estadística robusta.
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

# Soporte tipográfico y matemático para Matplotlib
matplotlib.rcParams["font.sans-serif"] = ["Segoe UI", "Inter", "Microsoft YaHei", "SimHei", "DejaVu Sans", "Arial"]
matplotlib.rcParams["axes.unicode_minus"] = False
matplotlib.rcParams["mathtext.fontset"] = "cm"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

try:
    import pyperclip
    HAS_PYPERCLIP = True
except ImportError:
    HAS_PYPERCLIP = False

# =============================================================================
# 0. CONFIGURACIÓN VISUAL, DUAL-THEMING (CLARO/OSCURO) E IDIOMAS (i18n)
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

# Paleta reactiva: Tuplas (Modo Claro, Modo Oscuro)
C_BG = ("#f6f8fa", "#0d1117")
C_SURFACE = ("#ffffff", "#161b22")
C_CARD = ("#eaeef2", "#21262d")
C_BORDER = ("#d0d7de", "#30363d")
C_TEXT = ("#1f2328", "#e6edf3")
C_TEXT_MUTED = ("#656d76", "#8b949e")
C_ACCENT = ("#0969da", "#38bdf8")
C_SUCCESS = ("#1a7f37", "#3fb950")
C_WARNING = ("#9a6700", "#f0883e")
C_DANGER = ("#d1242f", "#f85149")
C_PRIMARY = ("#0969da", "#1f6feb")

LOCALES: Dict[str, Dict[str, str]] = {
    "[ES] Español": {
        "tab_latex": "Tabla & LaTeX",
        "tab_norm": "Normalidad",
        "tab_biodiv": "Biodiversidad (α/β)",
        "tab_inf": "Inferencia",
        "tab_plots": "Gráficas Analíticas",
        "tab_math": "Fundamento Matemático",
        "btn_settings": "⚙ Ajustes",
        "load_data": "📂 Cargar Dataset (Ctrl+O)",
        "open_proj": "📥 Abrir .bioevo",
        "save_proj": "💾 Guardar .bioevo",
        "export_tex": "📄 Exportar .tex",
        "copy_latex": "📋 Copiar LaTeX",
        "waiting_data": "Esperando datos...",
        "ed_standard": "Estándar Editorial",
        "vars_to_analyze": "Variables a analizar",
        "filter_placeholder": "🔍 Filtrar nombre...",
        "btn_all": "Todas",
        "btn_none": "Ninguna",
        "group_by": "Agrupar por factor",
        "stat_catalog": "Catálogo Estadístico & Ecológico",
        "auto_norm": "Auto según normalidad",
        "margins_geom": "Márgenes y Geometría LaTeX",
        "landscape_tbl": "Tabla Horizontal (sidewaystable)",
        "doc_margins": "Márgenes de Documento:",
        "typo_settings": "Ajustes Tipográficos",
        "auto_resize": "Autoajuste (\\resizebox)",
        "add_linespace": "Separar con \\addlinespace",
        "decimal_comma": "Coma decimal (,)",
        "font_scale": "Tipografía / Escala:",
        "input_dataset": "Dataset de Entrada",
        "rendered_preview": "Renderizado Tipográfico (Arrastra: mover | Rueda: zoom)",
        "two_line_headers": "Encabezados 2 Líneas",
        "latex_source": "Código Fuente LaTeX",
        "norm_title": "Diagnóstico de Bondad de Ajuste (Shapiro-Wilk)",
        "alpha_level": "Nivel de significancia (α):",
        "biodiv_title": "Ecología de Comunidades: Diversidad Alfa (α) y Disimilitud Beta (β)",
        "beta_metric": "Índice Beta:",
        "btn_calc_biodiv": "🌿 Calcular Diversidad",
        "btn_send_latex": "📤 Enviar Alfa a LaTeX",
        "btn_beta_latex": "📤 Enviar Beta a LaTeX",
        "settings_title": "Preferencias de Interfaz e Idioma",
        "lbl_lang": "Idioma (Language):",
        "lbl_theme": "Tema Visual (Apariencia):",
        "lbl_uifont": "Tipografía de Interfaz (UI Font):",
        "palette_lbl": "Paleta:"
    },
    "[US] English": {
        "tab_latex": "Table & LaTeX",
        "tab_norm": "Normality",
        "tab_biodiv": "Biodiversity (α/β)",
        "tab_inf": "Inference",
        "tab_plots": "Analytical Plots",
        "tab_math": "Mathematical Basis",
        "btn_settings": "⚙ Settings",
        "load_data": "📂 Load Dataset (Ctrl+O)",
        "open_proj": "📥 Open .bioevo",
        "save_proj": "💾 Save .bioevo",
        "export_tex": "📄 Export .tex",
        "copy_latex": "📋 Copy LaTeX",
        "waiting_data": "Waiting for data...",
        "ed_standard": "Editorial Standard",
        "vars_to_analyze": "Variables to Analyze",
        "filter_placeholder": "🔍 Filter name...",
        "btn_all": "All",
        "btn_none": "None",
        "group_by": "Group by Factor",
        "stat_catalog": "Statistical & Ecological Catalog",
        "auto_norm": "Auto by Normality",
        "margins_geom": "LaTeX Margins & Geometry",
        "landscape_tbl": "Landscape Table (sidewaystable)",
        "doc_margins": "Document Margins:",
        "typo_settings": "Typographic Settings",
        "auto_resize": "Auto-fit (\\resizebox)",
        "add_linespace": "Separate with \\addlinespace",
        "decimal_comma": "Decimal Comma (,)",
        "font_scale": "Font / Scale:",
        "input_dataset": "Input Dataset",
        "rendered_preview": "Typographic Preview (Drag: pan | Wheel: zoom)",
        "two_line_headers": "2-Line Headers",
        "latex_source": "LaTeX Source Code",
        "norm_title": "Goodness-of-Fit Diagnostic (Shapiro-Wilk)",
        "alpha_level": "Significance Level (α):",
        "biodiv_title": "Community Ecology: Alpha Diversity (α) & Beta Dissimilarity (β)",
        "beta_metric": "Beta Index:",
        "btn_calc_biodiv": "🌿 Compute Diversity",
        "btn_send_latex": "📤 Send Alpha to LaTeX",
        "btn_beta_latex": "📤 Send Beta to LaTeX",
        "settings_title": "Interface & Language Preferences",
        "lbl_lang": "Language:",
        "lbl_theme": "Visual Theme (Appearance):",
        "lbl_uifont": "Interface Font Family:",
        "palette_lbl": "Color Palette:"
    },
    "[GB] English (UK)": {
        "tab_latex": "Table & LaTeX",
        "tab_norm": "Normality",
        "tab_biodiv": "Biodiversity (α/β)",
        "tab_inf": "Inference",
        "tab_plots": "Analytical Plots",
        "tab_math": "Mathematical Basis",
        "btn_settings": "⚙ Preferences",
        "load_data": "📂 Load Dataset (Ctrl+O)",
        "open_proj": "📥 Open .bioevo",
        "save_proj": "💾 Save .bioevo",
        "export_tex": "📄 Export .tex",
        "copy_latex": "📋 Copy LaTeX",
        "waiting_data": "Awaiting data...",
        "ed_standard": "Editorial Standard",
        "vars_to_analyze": "Variables to Analyse",
        "filter_placeholder": "🔍 Filter name...",
        "btn_all": "All",
        "btn_none": "None",
        "group_by": "Group by Factor",
        "stat_catalog": "Statistical & Ecological Catalogue",
        "auto_norm": "Auto by Normality",
        "margins_geom": "LaTeX Margins & Geometry",
        "landscape_tbl": "Landscape Table (sidewaystable)",
        "doc_margins": "Document Margins:",
        "typo_settings": "Typographic Adjustments",
        "auto_resize": "Auto-fit (\\resizebox)",
        "add_linespace": "Separate with \\addlinespace",
        "decimal_comma": "Decimal Comma (,)",
        "font_scale": "Typeface / Scale:",
        "input_dataset": "Input Dataset",
        "rendered_preview": "Typographic Preview (Drag: pan | Wheel: zoom)",
        "two_line_headers": "2-Line Headers",
        "latex_source": "LaTeX Source Code",
        "norm_title": "Goodness-of-Fit Diagnostic (Shapiro-Wilk)",
        "alpha_level": "Significance Level (α):",
        "biodiv_title": "Community Ecology: Alpha Diversity (α) & Beta Dissimilarity (β)",
        "beta_metric": "Beta Index:",
        "btn_calc_biodiv": "🌿 Analyse Diversity",
        "btn_send_latex": "📤 Send Alpha to LaTeX",
        "btn_beta_latex": "📤 Send Beta to LaTeX",
        "settings_title": "Interface & Language Preferences",
        "lbl_lang": "Language:",
        "lbl_theme": "Visual Colour Theme:",
        "lbl_uifont": "Interface Typeface:",
        "palette_lbl": "Colour Palette:"
    },
    "[BR] Português": {
        "tab_latex": "Tabela & LaTeX",
        "tab_norm": "Normalidade",
        "tab_biodiv": "Biodiversidade (α/β)",
        "tab_inf": "Inferência",
        "tab_plots": "Gráficos Analíticos",
        "tab_math": "Fundamento Matemático",
        "btn_settings": "⚙ Ajustes",
        "load_data": "📂 Carregar Dados (Ctrl+O)",
        "open_proj": "📥 Abrir .bioevo",
        "save_proj": "💾 Salvar .bioevo",
        "export_tex": "📄 Exportar .tex",
        "copy_latex": "📋 Copiar LaTeX",
        "waiting_data": "Aguardando dados...",
        "ed_standard": "Padrão Editorial",
        "vars_to_analyze": "Variáveis para analisar",
        "filter_placeholder": "🔍 Filtrar nome...",
        "btn_all": "Todas",
        "btn_none": "Nenhuma",
        "group_by": "Agrupar por fator",
        "stat_catalog": "Catálogo Estatístico e Ecológico",
        "auto_norm": "Auto conforme normalidade",
        "margins_geom": "Margens e Geometria LaTeX",
        "landscape_tbl": "Tabela Horizontal (sidewaystable)",
        "doc_margins": "Margens do Documento:",
        "typo_settings": "Ajustes Tipográficos",
        "auto_resize": "Autoajuste (\\resizebox)",
        "add_linespace": "Separar com \\addlinespace",
        "decimal_comma": "Vírgula decimal (,)",
        "font_scale": "Tipografia / Escala:",
        "input_dataset": "Conjunto de Dados",
        "rendered_preview": "Pré-visualização Tipográfica (Arraste / Roda: zoom)",
        "two_line_headers": "Cabeçalhos 2 Linhas",
        "latex_source": "Código-Fonte LaTeX",
        "norm_title": "Diagnóstico de Normalidade (Shapiro-Wilk)",
        "alpha_level": "Nível de significância (α):",
        "biodiv_title": "Ecologia de Comunidades: Diversidade Alfa (α) e Beta (β)",
        "beta_metric": "Índice Beta:",
        "btn_calc_biodiv": "🌿 Calcular Diversidade",
        "btn_send_latex": "📤 Enviar Alfa ao LaTeX",
        "btn_beta_latex": "📤 Enviar Beta ao LaTeX",
        "settings_title": "Preferências de Interface e Idioma",
        "lbl_lang": "Idioma:",
        "lbl_theme": "Tema Visual (Aparência):",
        "lbl_uifont": "Fonte da Interface:",
        "palette_lbl": "Paleta:"
    },
    "[FR] Français": {
        "tab_latex": "Tableau & LaTeX",
        "tab_norm": "Normalité",
        "tab_biodiv": "Biodiversité (α/β)",
        "tab_inf": "Inférence",
        "tab_plots": "Graphiques Analytiques",
        "tab_math": "Fondement Mathématique",
        "btn_settings": "⚙ Paramètres",
        "load_data": "📂 Charger Données (Ctrl+O)",
        "open_proj": "📥 Ouvrir .bioevo",
        "save_proj": "💾 Sauver .bioevo",
        "export_tex": "📄 Exporter .tex",
        "copy_latex": "📋 Copier LaTeX",
        "waiting_data": "En attente de données...",
        "ed_standard": "Norme Éditoriale",
        "vars_to_analyze": "Variables à analyser",
        "filter_placeholder": "🔍 Filtrer le nom...",
        "btn_all": "Toutes",
        "btn_none": "Aucune",
        "group_by": "Grouper par facteur",
        "stat_catalog": "Catalogue Statistique & Écologique",
        "auto_norm": "Auto selon normalité",
        "margins_geom": "Marges et Géométrie LaTeX",
        "landscape_tbl": "Tableau Paysage (sidewaystable)",
        "doc_margins": "Marges du Document :",
        "typo_settings": "Paramètres Typographiques",
        "auto_resize": "Ajustement auto (\\resizebox)",
        "add_linespace": "Séparer avec \\addlinespace",
        "decimal_comma": "Virgule décimale (,)",
        "font_scale": "Police / Échelle :",
        "input_dataset": "Jeu de Données",
        "rendered_preview": "Aperçu Typographique (Glisser / Molette : zoom)",
        "two_line_headers": "En-têtes 2 Lignes",
        "latex_source": "Code Source LaTeX",
        "norm_title": "Diagnostic de Normalité (Shapiro-Wilk)",
        "alpha_level": "Seuil de signification (α) :",
        "biodiv_title": "Écologie des Communautés : Diversité Alpha (α) et Bêta (β)",
        "beta_metric": "Indice Bêta :",
        "btn_calc_biodiv": "🌿 Calculer Diversité",
        "btn_send_latex": "📤 Envoyer Alpha vers LaTeX",
        "btn_beta_latex": "📤 Envoyer Bêta vers LaTeX",
        "settings_title": "Préférences d'Interface et de Langue",
        "lbl_lang": "Langue :",
        "lbl_theme": "Thème Visuel (Apparence) :",
        "lbl_uifont": "Police de l'Interface :",
        "palette_lbl": "Palette :"
    },
    "[CN] 简体中文": {
        "tab_latex": "表格与 LaTeX",
        "tab_norm": "正态性检验",
        "tab_biodiv": "生物多样性 (α/β)",
        "tab_inf": "统计推断",
        "tab_plots": "分析图表",
        "tab_math": "数学原理",
        "btn_settings": "⚙ 设置",
        "load_data": "📂 加载数据集 (Ctrl+O)",
        "open_proj": "📥 打开 .bioevo",
        "save_proj": "💾 保存 .bioevo",
        "export_tex": "📄 导出 .tex",
        "copy_latex": "📋 复制 LaTeX",
        "waiting_data": "等待加载数据...",
        "ed_standard": "排版学术标准",
        "vars_to_analyze": "待分析变量",
        "filter_placeholder": "🔍 搜索变量名称...",
        "btn_all": "全选",
        "btn_none": "全不选",
        "group_by": "分组因子",
        "stat_catalog": "统计与生态学指标库",
        "auto_norm": "按正态性自动匹配",
        "margins_geom": "LaTeX 页边距与版面",
        "landscape_tbl": "横向宽表 (sidewaystable)",
        "doc_margins": "文档页边距:",
        "typo_settings": "排版微调",
        "auto_resize": "自动缩放 (\\resizebox)",
        "add_linespace": "行距分隔 (\\addlinespace)",
        "decimal_comma": "十进制逗号 (,)",
        "font_scale": "字体大小 / 缩放:",
        "input_dataset": "输入数据集预览",
        "rendered_preview": "排版渲染预览 (拖动平移 | 滚轮缩放)",
        "two_line_headers": "双行表头",
        "latex_source": "LaTeX 源代码",
        "norm_title": "正态分布拟合优度诊断 (Shapiro-Wilk)",
        "alpha_level": "显著性水平 (α):",
        "biodiv_title": "群落生态学：α多样性指数与 β相异性矩阵",
        "beta_metric": "β多样性指数:",
        "btn_calc_biodiv": "🌿 计算生物多样性",
        "btn_send_latex": "📤 导出 α多样性至 LaTeX",
        "btn_beta_latex": "📤 导出 β矩阵至 LaTeX",
        "settings_title": "界面与语言偏好设置",
        "lbl_lang": "界面语言 (Language):",
        "lbl_theme": "外观主题 (Theme):",
        "lbl_uifont": "界面字体 (Font Family):",
        "palette_lbl": "配色方案:"
    }
}

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


# =============================================================================
# 1. BLINDAJE DE DATOS Y MOTOR DE CÁLCULO ECOLÓGICO (ALFA & BETA)
# =============================================================================

def sanitize_latex(text: str) -> str:
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
    begins = re.findall(r"\\begin\{([^}]+)\}", code)
    ends = re.findall(r"\\end\{([^}]+)\}", code)
    if sorted(begins) != sorted(ends):
        return False, f"Desbalance de entornos: \\begin={begins} vs \\end={ends}"

    tabular_match = re.search(r"\\begin\{tabular\}\{([^}]+)\}(.*?)\\end\{tabular\}", code, re.DOTALL)
    if tabular_match:
        cols_spec = tabular_match.group(1).strip()
        expected_cols = len([c for c in cols_spec if c in "lcrpmsS"])
        table_body = tabular_match.group(2)
        rows = [
            r.strip() for r in table_body.split(r"\\")
            if r.strip() and not r.strip().startswith(r"\toprule")
            and not r.strip().startswith(r"\midrule")
            and not r.strip().startswith(r"\bottomrule")
        ]
        for i, r in enumerate(rows):
            if r.startswith(r"\addlinespace"):
                continue
            amp_count = r.count("&")
            if amp_count != expected_cols - 1:
                return False, f"Fila {i+1} posee {amp_count+1} columnas; {{{cols_spec}}} espera {expected_cols}."

    return True, "Sintaxis verificada exitosamente"


def read_delimited_robust(path: str) -> Tuple[pd.DataFrame, Dict[str, Any]]:
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
                raw_bytes.decode(enc)
                detected_enc = enc
                break
            except UnicodeDecodeError:
                continue

        if not detected_enc:
            detected_enc = "latin-1"
        metadata["encoding"] = detected_enc

        sample_str = raw_bytes.decode(detected_enc, errors="ignore")
        try:
            sniffer = csv.Sniffer()
            dialect = sniffer.sniff(sample_str[:4096], delimiters=[",", ";", "\t", "|"])
            detected_sep = dialect.delimiter
        except Exception:
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

    for col in df.columns:
        if pd.api.types.is_string_dtype(df[col]) or df[col].dtype == object:
            series_clean = df[col].dropna().astype(str).str.strip()
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


def compute_alpha_diversity_vector(series: pd.Series) -> Dict[str, float]:
    clean = series.dropna()
    pos = clean[clean > 0].astype(float)
    S = len(pos)
    N = float(pos.sum())

    if S == 0 or N <= 0:
        return {
            "S": 0, "N": 0.0, "H": 0.0, "D": 0.0,
            "1_D": 0.0, "inv_D": 0.0, "J": 0.0, "D_mg": 0.0
        }

    p = pos / N
    shannon_h = float(-np.sum(p * np.log(p)))
    simpson_d = float(np.sum(p ** 2))
    simpson_div = 1.0 - simpson_d
    inv_simpson = (1.0 / simpson_d) if simpson_d > 0 else 0.0
    pielou_j = (shannon_h / np.log(S)) if S > 1 else 1.0
    margalef = ((S - 1.0) / np.log(N)) if N > 1.0 else 0.0

    return {
        "S": S,
        "N": N,
        "H": shannon_h,
        "D": simpson_d,
        "1_D": simpson_div,
        "inv_D": inv_simpson,
        "J": pielou_j,
        "D_mg": margalef
    }


def compute_beta_diversity_matrix(df_sub: pd.DataFrame, method: str = "Bray-Curtis") -> pd.DataFrame:
    cols = df_sub.columns.tolist()
    k = len(cols)
    clean_df = df_sub.fillna(0.0).clip(lower=0.0)
    mat = np.zeros((k, k), dtype=float)

    for i in range(k):
        for j in range(i, k):
            u = clean_df.iloc[:, i].values
            v = clean_df.iloc[:, j].values

            if i == j:
                mat[i, j] = 0.0 if "Bray-Curtis" in method else 1.0
                continue

            if "Bray-Curtis" in method:
                denom = np.sum(u + v)
                val = (np.sum(np.abs(u - v)) / denom) if denom > 0 else 0.0
            elif "Jaccard" in method:
                bu = u > 0
                bv = v > 0
                a = np.logical_and(bu, bv).sum()
                union = np.logical_or(bu, bv).sum()
                val = float(a / union) if union > 0 else 0.0
            else:
                bu = u > 0
                bv = v > 0
                a = np.logical_and(bu, bv).sum()
                denom = bu.sum() + bv.sum()
                val = float((2.0 * a) / denom) if denom > 0 else 0.0

            mat[i, j] = val
            mat[j, i] = val

    return pd.DataFrame(mat, index=cols, columns=cols)


# =============================================================================
# 2. PATRÓN STRATEGY DE MÉTRICAS ESTADÍSTICAS Y ECOLÓGICAS
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
        return fmt(series.std(ddof=1) / np.sqrt(n), 3)


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


class ShannonMetric(StatMetric):
    @property
    def id_key(self) -> str: return "shannon_h"
    @property
    def display_name(self) -> str: return "Shannon (H')"
    @property
    def latex_header(self) -> str: return r"Shannon ($H'$)"
    @property
    def is_parametric(self) -> bool: return False
    @property
    def default_active(self) -> bool: return False
    def compute(self, series: pd.Series, fmt: Callable[[float, int], str]) -> str:
        res = compute_alpha_diversity_vector(series)
        return fmt(res["H"], 3) if res["S"] > 0 else "---"


class SimpsonDivMetric(StatMetric):
    @property
    def id_key(self) -> str: return "simpson_div"
    @property
    def display_name(self) -> str: return "Simpson (1 - D)"
    @property
    def latex_header(self) -> str: return r"Simpson ($1-D$)"
    @property
    def is_parametric(self) -> bool: return False
    @property
    def default_active(self) -> bool: return False
    def compute(self, series: pd.Series, fmt: Callable[[float, int], str]) -> str:
        res = compute_alpha_diversity_vector(series)
        return fmt(res["1_D"], 3) if res["S"] > 0 else "---"


class PielouMetric(StatMetric):
    @property
    def id_key(self) -> str: return "pielou_j"
    @property
    def display_name(self) -> str: return "Equidad Pielou (J')"
    @property
    def latex_header(self) -> str: return r"Pielou ($J'$)"
    @property
    def is_parametric(self) -> bool: return False
    @property
    def default_active(self) -> bool: return False
    def compute(self, series: pd.Series, fmt: Callable[[float, int], str]) -> str:
        res = compute_alpha_diversity_vector(series)
        return fmt(res["J"], 3) if res["S"] > 0 else "---"


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
# 3. WORKSTATION PRINCIPAL
# =============================================================================

class LabStatsApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.current_lang: str = "[ES] Español"
        self.current_theme_mode: str = "Dark"
        self.current_ui_font: str = "Segoe UI"

        self.title("BioEvo | LabStats Formatter v1.1.0-beta.2")
        self.geometry("1520x950")
        self.minsize(1220, 760)
        self.configure(fg_color=C_BG)

        self.df: Optional[pd.DataFrame] = None
        self.current_filepath: str = ""
        self.current_meta: Dict[str, Any] = {}
        self.var_checkboxes: Dict[str, ctk.CTkCheckBox] = {}
        self.stat_switches: Dict[StatMetric, ctk.CTkSwitch] = {}

        self.metrics: List[StatMetric] = [
            MeanStdMetric(), SEMMetric(), CI95Metric(), VarianceMetric(),
            MedianIQRMetric(), P10P90Metric(), MinMaxMetric(),
            SkewKurtMetric(), ShannonMetric(), SimpsonDivMetric(),
            PielouMetric(), SampleSizeMetric()
        ]

        self._pan_start = None
        self.active_view_key = "tab_latex"

        self.bind("<Control-o>", lambda _: self.load_file_threaded())
        self.bind("<Control-s>", lambda _: self.save_tex_file())

        self._build_layout()

    def _tr(self, key: str) -> str:
        return LOCALES.get(self.current_lang, LOCALES["[ES] Español"]).get(key, key)

    def _build_layout(self):
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.sidebar = ctk.CTkFrame(
            self, width=345, corner_radius=0,
            fg_color=C_SURFACE,
            border_width=1, border_color=C_BORDER
        )
        self.sidebar.grid(row=0, column=0, sticky="nsew")

        self.content_area = ctk.CTkFrame(self, fg_color=C_BG, corner_radius=0)
        self.content_area.grid(row=0, column=1, sticky="nsew", padx=14, pady=12)
        self.content_area.grid_rowconfigure(1, weight=1)
        self.content_area.grid_columnconfigure(0, weight=1)

        self._setup_top_nav()

        self.views: Dict[str, ctk.CTkFrame] = {}
        self._setup_sidebar()
        self._setup_views()

        self.switch_view("tab_latex")

    # -------------------------------------------------------------------------
    # HEADER Y NAVEGACIÓN SUPERIOR
    # -------------------------------------------------------------------------
    def _setup_top_nav(self):
        self.top_nav = ctk.CTkFrame(self.content_area, height=44, fg_color="transparent")
        self.top_nav.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        self.nav_buttons: Dict[str, ctk.CTkButton] = {}
        self.tab_keys = ["tab_latex", "tab_norm", "tab_biodiv", "tab_inf", "tab_plots", "tab_math"]

        for key in self.tab_keys:
            btn = ctk.CTkButton(
                self.top_nav, text=self._tr(key),
                font=ctk.CTkFont(family=self.current_ui_font, size=13, weight="bold"),
                fg_color="transparent", text_color=C_TEXT_MUTED,
                hover_color=C_SURFACE, height=32, corner_radius=6,
                command=lambda k=key: self.switch_view(k)
            )
            btn.pack(side="left", padx=3)
            self.nav_buttons[key] = btn

        self.btn_settings = ctk.CTkButton(
            self.top_nav, text=self._tr("btn_settings"),
            font=ctk.CTkFont(family=self.current_ui_font, size=12, weight="bold"),
            fg_color=C_CARD, text_color=C_ACCENT,
            hover_color=C_BORDER, border_width=1, border_color=C_BORDER,
            height=32, width=115, corner_radius=6,
            command=self.open_settings_modal
        )
        self.btn_settings.pack(side="right", padx=4)

    def switch_view(self, key: str):
        self.active_view_key = key
        for t_key, btn in self.nav_buttons.items():
            if t_key == key:
                btn.configure(text_color=C_ACCENT, fg_color=C_SURFACE)
            else:
                btn.configure(text_color=C_TEXT_MUTED, fg_color="transparent")

        for v_key, frame in self.views.items():
            if v_key == key:
                frame.grid(row=1, column=0, sticky="nsew")
            else:
                frame.grid_forget()

    # -------------------------------------------------------------------------
    # MODAL DE AJUSTES Y PREFERENCIAS
    # -------------------------------------------------------------------------
    def open_settings_modal(self):
        modal = ctk.CTkToplevel(self)
        modal.title(self._tr("settings_title"))
        modal.geometry("460x360")
        modal.resizable(False, False)
        modal.configure(fg_color=C_SURFACE)
        modal.transient(self)
        modal.grab_set()

        ctk.CTkLabel(
            modal, text=self._tr("settings_title"),
            font=ctk.CTkFont(family=self.current_ui_font, size=16, weight="bold"),
            text_color=C_TEXT
        ).pack(anchor="w", padx=20, pady=(18, 12))

        ctk.CTkLabel(modal, text=self._tr("lbl_lang"), font=ctk.CTkFont(family=self.current_ui_font, size=12, weight="bold")).pack(anchor="w", padx=20, pady=(6, 2))
        combo_lang = ctk.CTkComboBox(
            modal, values=list(LOCALES.keys()), width=420,
            command=self.change_language
        )
        combo_lang.set(self.current_lang)
        combo_lang.pack(padx=20, pady=4)

        ctk.CTkLabel(modal, text=self._tr("lbl_theme"), font=ctk.CTkFont(family=self.current_ui_font, size=12, weight="bold")).pack(anchor="w", padx=20, pady=(10, 2))
        seg_theme = ctk.CTkSegmentedButton(
            modal, values=["Dark", "Light"], width=420,
            selected_color=C_ACCENT,
            command=self.change_appearance_mode
        )
        seg_theme.set(self.current_theme_mode)
        seg_theme.pack(padx=20, pady=4)

        ctk.CTkLabel(modal, text=self._tr("lbl_uifont"), font=ctk.CTkFont(family=self.current_ui_font, size=12, weight="bold")).pack(anchor="w", padx=20, pady=(10, 2))
        combo_uifont = ctk.CTkComboBox(
            modal, values=["Segoe UI", "Inter", "Consolas", "Georgia", "Times New Roman", "Arial"],
            width=420, command=self.change_ui_font
        )
        combo_uifont.set(self.current_ui_font)
        combo_uifont.pack(padx=20, pady=4)

        ctk.CTkButton(
            modal, text="OK", width=120, fg_color=C_PRIMARY,
            command=modal.destroy
        ).pack(pady=(22, 10))

    def change_language(self, new_lang: str):
        if new_lang not in LOCALES:
            return
        self.current_lang = new_lang

        for key, btn in self.nav_buttons.items():
            btn.configure(text=self._tr(key))
        self.btn_settings.configure(text=self._tr("btn_settings"))

        self.btn_load.configure(text=self._tr("load_data"))
        self.btn_load_proj.configure(text=self._tr("open_proj"))
        self.btn_save_proj.configure(text=self._tr("save_proj"))
        self.btn_save_tex.configure(text=self._tr("export_tex"))
        self.btn_copy.configure(text=self._tr("copy_latex"))

        self.lbl_ed_std.configure(text=self._tr("ed_standard"))
        self.lbl_vars_analyze.configure(text=self._tr("vars_to_analyze"))
        self.entry_filter_var.configure(placeholder_text=self._tr("filter_placeholder"))
        self.btn_sel_all.configure(text=self._tr("btn_all"))
        self.btn_sel_none.configure(text=self._tr("btn_none"))
        self.lbl_group_by.configure(text=self._tr("group_by"))
        self.lbl_stat_cat.configure(text=self._tr("stat_catalog"))
        self.sw_strict_norm.configure(text=self._tr("auto_norm"))
        self.lbl_margins_geom.configure(text=self._tr("margins_geom"))
        self.sw_landscape.configure(text=self._tr("landscape_tbl"))
        self.lbl_doc_margins.configure(text=self._tr("doc_margins"))
        self.lbl_typo_settings.configure(text=self._tr("typo_settings"))
        self.sw_resize.configure(text=self._tr("auto_resize"))
        self.sw_linespace.configure(text=self._tr("add_linespace"))
        self.sw_comma.configure(text=self._tr("decimal_comma"))
        self.lbl_font_scale.configure(text=self._tr("font_scale"))

        self.lbl_in_dataset.configure(text=self._tr("input_dataset"))
        self.lbl_render_prev.configure(text=self._tr("rendered_preview"))
        self.sw_multiline.configure(text=self._tr("two_line_headers"))
        self.lbl_latex_src.configure(text=self._tr("latex_source"))
        self.lbl_norm_title.configure(text=self._tr("norm_title"))
        self.lbl_alpha_lvl.configure(text=self._tr("alpha_level"))

        self.lbl_biodiv_title.configure(text=self._tr("biodiv_title"))
        self.lbl_beta_metric.configure(text=self._tr("beta_metric"))
        self.btn_calc_biodiv.configure(text=self._tr("btn_calc_biodiv"))
        self.btn_alpha_tex.configure(text=self._tr("btn_send_latex"))
        self.btn_beta_tex.configure(text=self._tr("btn_beta_latex"))

    def change_appearance_mode(self, mode: str):
        self.current_theme_mode = mode
        ctk.set_appearance_mode(mode.lower())

        is_dark = mode.lower() == "dark"
        mat_bg = "#161b22" if is_dark else "#ffffff"
        mat_text = "#e6edf3" if is_dark else "#1f2328"
        mat_muted = "#8b949e" if is_dark else "#656d76"

        matplotlib.rcParams["text.color"] = mat_text
        matplotlib.rcParams["axes.labelcolor"] = mat_text
        matplotlib.rcParams["xtick.color"] = mat_muted
        matplotlib.rcParams["ytick.color"] = mat_muted

        self.fig_preview.patch.set_facecolor(mat_bg)
        self.fig_analytics.patch.set_facecolor(mat_bg)
        self.fig_math.patch.set_facecolor(mat_bg)

        self.ax_preview.set_facecolor(mat_bg)
        self.canvas_preview.draw_idle()
        self.canvas_analytics.draw_idle()
        self._render_math_formula()

    def _apply_font_recursive(self, widget, font_family: str):
        try:
            if hasattr(widget, "cget") and "font" in widget.keys():
                cur = widget.cget("font")
                if isinstance(cur, ctk.CTkFont):
                    cur.configure(family=font_family)
                elif isinstance(cur, tuple) and len(cur) >= 2:
                    widget.configure(font=(font_family, cur[1]))
        except Exception:
            pass

        for child in widget.winfo_children():
            self._apply_font_recursive(child, font_family)

    def change_ui_font(self, new_font: str):
        self.current_ui_font = new_font
        self._apply_font_recursive(self, new_font)
        self.tex_editor.configure(font=("Consolas", 12))
        self.txt_inference.configure(font=("Consolas", 12))
        self.txt_biodiv.configure(font=("Consolas", 12))

    # -------------------------------------------------------------------------
    # SIDEBAR
    # -------------------------------------------------------------------------
    def _setup_sidebar(self):
        header_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        header_frame.pack(fill="x", padx=16, pady=(16, 6))

        ctk.CTkLabel(header_frame, text="LabStats Core", font=ctk.CTkFont(size=20, weight="bold"), text_color=C_TEXT).pack(side="left")
        badge = ctk.CTkLabel(
            header_frame, text="v1.1.0-beta.2", font=ctk.CTkFont(family="Consolas", size=10),
            fg_color=C_CARD, text_color=C_ACCENT, corner_radius=4
        )
        badge.pack(side="right", pady=4)

        btn_grid = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        btn_grid.pack(fill="x", padx=16, pady=4)

        self.btn_load = ctk.CTkButton(
            btn_grid, text=self._tr("load_data"),
            fg_color=C_CARD, hover_color=C_BORDER,
            text_color=C_TEXT, border_width=1, border_color=C_BORDER,
            command=self.load_file_threaded
        )
        self.btn_load.pack(fill="x", pady=2)

        proj_btns = ctk.CTkFrame(btn_grid, fg_color="transparent")
        proj_btns.pack(fill="x", pady=2)

        self.btn_load_proj = ctk.CTkButton(
            proj_btns, text=self._tr("open_proj"), width=148,
            fg_color=C_CARD, hover_color=C_BORDER,
            text_color=C_TEXT, border_width=1, border_color=C_BORDER,
            command=self.load_project_json
        )
        self.btn_load_proj.pack(side="left", padx=(0, 4))

        self.btn_save_proj = ctk.CTkButton(
            proj_btns, text=self._tr("save_proj"), width=148,
            fg_color=C_CARD, hover_color=C_BORDER,
            text_color=C_TEXT, border_width=1, border_color=C_BORDER,
            command=self.save_project_json
        )
        self.btn_save_proj.pack(side="left")

        self.btn_save_tex = ctk.CTkButton(
            btn_grid, text=self._tr("export_tex"), fg_color=C_PRIMARY, hover_color="#388bfd",
            state="disabled", command=self.save_tex_file
        )
        self.btn_save_tex.pack(fill="x", pady=2)

        self.btn_copy = ctk.CTkButton(
            btn_grid, text=self._tr("copy_latex"), fg_color="#238636", hover_color="#2ea043",
            state="disabled", command=self.copy_latex
        )
        self.btn_copy.pack(fill="x", pady=2)

        self.progress_bar = ctk.CTkProgressBar(self.sidebar, height=4, fg_color=C_CARD, progress_color=C_ACCENT)
        self.progress_bar.pack(fill="x", padx=16, pady=(8, 2))
        self.progress_bar.set(0)

        self.lbl_progress = ctk.CTkLabel(self.sidebar, text=self._tr("waiting_data"), font=ctk.CTkFont(size=11), text_color=C_TEXT_MUTED)
        self.lbl_progress.pack(pady=(0, 4))

        self.scroll_sidebar = ctk.CTkScrollableFrame(self.sidebar, fg_color="transparent")
        self.scroll_sidebar.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # Estándar Editorial
        self.lbl_ed_std = ctk.CTkLabel(self.scroll_sidebar, text=self._tr("ed_standard"), font=ctk.CTkFont(size=12, weight="bold"), text_color=C_ACCENT)
        self.lbl_ed_std.pack(anchor="w", padx=6, pady=(6, 2))
        self.seg_format = ctk.CTkSegmentedButton(
            self.scroll_sidebar, values=["APA 7", "IEEE"],
            selected_color=C_ACCENT,
            command=lambda _: self.trigger_analysis_thread()
        )
        self.seg_format.set("APA 7")
        self.seg_format.pack(fill="x", padx=6, pady=2)

        # Variables y buscador
        self.lbl_vars_analyze = ctk.CTkLabel(self.scroll_sidebar, text=self._tr("vars_to_analyze"), font=ctk.CTkFont(size=13, weight="bold"), text_color=C_TEXT)
        self.lbl_vars_analyze.pack(anchor="w", padx=6, pady=(10, 2))
        self.entry_filter_var = ctk.CTkEntry(
            self.scroll_sidebar, placeholder_text=self._tr("filter_placeholder"),
            fg_color=C_BG, border_color=C_BORDER, text_color=C_TEXT, height=28
        )
        self.entry_filter_var.pack(fill="x", padx=6, pady=2)
        self.entry_filter_var.bind("<KeyRelease>", lambda _: self._filter_variable_checkboxes())

        btn_row = ctk.CTkFrame(self.scroll_sidebar, fg_color="transparent")
        btn_row.pack(fill="x", padx=6, pady=2)
        self.btn_sel_all = ctk.CTkButton(btn_row, text=self._tr("btn_all"), width=75, height=22, fg_color=C_CARD, text_color=C_TEXT, command=self.select_all_vars)
        self.btn_sel_all.pack(side="left", padx=(0, 4))
        self.btn_sel_none = ctk.CTkButton(btn_row, text=self._tr("btn_none"), width=75, height=22, fg_color=C_CARD, text_color=C_TEXT, command=self.deselect_all_vars)
        self.btn_sel_none.pack(side="left")

        self.var_container = ctk.CTkFrame(self.scroll_sidebar, fg_color=C_BG, corner_radius=6, border_width=1, border_color=C_BORDER)
        self.var_container.pack(fill="x", padx=6, pady=4)

        # Agrupación por factores
        self.lbl_group_by = ctk.CTkLabel(self.scroll_sidebar, text=self._tr("group_by"), font=ctk.CTkFont(size=13, weight="bold"), text_color=C_TEXT)
        self.lbl_group_by.pack(anchor="w", padx=6, pady=(8, 2))
        self.combo_group = ctk.CTkComboBox(self.scroll_sidebar, values=["(sin agrupar)"], command=lambda _: self.trigger_analysis_thread())
        self.combo_group.pack(fill="x", padx=6, pady=2)

        # Catálogo Estadístico y Ecológico
        self.lbl_stat_cat = ctk.CTkLabel(self.scroll_sidebar, text=self._tr("stat_catalog"), font=ctk.CTkFont(size=13, weight="bold"), text_color=C_TEXT)
        self.lbl_stat_cat.pack(anchor="w", padx=6, pady=(10, 2))
        self.sw_strict_norm = ctk.CTkSwitch(
            self.scroll_sidebar, text=self._tr("auto_norm"),
            progress_color=C_ACCENT,
            command=self.trigger_analysis_thread
        )
        self.sw_strict_norm.pack(anchor="w", padx=6, pady=3)

        for metric in self.metrics:
            sw = ctk.CTkSwitch(
                self.scroll_sidebar, text=metric.display_name,
                progress_color=C_ACCENT,
                command=lambda m=metric: self._on_metric_switch_toggled(m)
            )
            if metric.default_active:
                sw.select()
            sw.pack(anchor="w", padx=6, pady=2)
            self.stat_switches[metric] = sw

        # Márgenes y Geometría
        self.lbl_margins_geom = ctk.CTkLabel(self.scroll_sidebar, text=self._tr("margins_geom"), font=ctk.CTkFont(size=13, weight="bold"), text_color=C_TEXT)
        self.lbl_margins_geom.pack(anchor="w", padx=6, pady=(12, 2))

        self.sw_landscape = ctk.CTkSwitch(
            self.scroll_sidebar, text=self._tr("landscape_tbl"),
            progress_color=C_ACCENT, command=self.trigger_analysis_thread
        )
        self.sw_landscape.pack(anchor="w", padx=6, pady=2)

        self.lbl_doc_margins = ctk.CTkLabel(self.scroll_sidebar, text=self._tr("doc_margins"), text_color=C_TEXT)
        self.lbl_doc_margins.pack(anchor="w", padx=6, pady=(4, 1))
        self.combo_margin = ctk.CTkComboBox(
            self.scroll_sidebar,
            values=[
                "Normal (margin=2.5cm)",
                "Estrecho (margin=1.5cm)",
                "APA Estricto (margin=1in)",
                "Sin geometry (default)"
            ],
            command=lambda _: self.trigger_analysis_thread()
        )
        self.combo_margin.set("Normal (margin=2.5cm)")
        self.combo_margin.pack(fill="x", padx=6, pady=2)

        # Ajustes Tipográficos
        self.lbl_typo_settings = ctk.CTkLabel(self.scroll_sidebar, text=self._tr("typo_settings"), font=ctk.CTkFont(size=13, weight="bold"), text_color=C_TEXT)
        self.lbl_typo_settings.pack(anchor="w", padx=6, pady=(10, 2))
        self.sw_resize = ctk.CTkSwitch(self.scroll_sidebar, text=self._tr("auto_resize"), progress_color=C_ACCENT, command=self.trigger_analysis_thread)
        self.sw_resize.select()
        self.sw_resize.pack(anchor="w", padx=6, pady=2)

        self.sw_linespace = ctk.CTkSwitch(self.scroll_sidebar, text=self._tr("add_linespace"), progress_color=C_ACCENT, command=self.trigger_analysis_thread)
        self.sw_linespace.pack(anchor="w", padx=6, pady=2)

        self.sw_comma = ctk.CTkSwitch(self.scroll_sidebar, text=self._tr("decimal_comma"), progress_color=C_ACCENT, command=self.trigger_analysis_thread)
        self.sw_comma.select()
        self.sw_comma.pack(anchor="w", padx=6, pady=2)

        self.lbl_font_scale = ctk.CTkLabel(self.scroll_sidebar, text=self._tr("font_scale"), text_color=C_TEXT)
        self.lbl_font_scale.pack(anchor="w", padx=6, pady=(4, 1))
        self.combo_font = ctk.CTkComboBox(
            self.scroll_sidebar, values=["\\small", "\\footnotesize", "\\scriptsize", "\\normalsize"],
            command=lambda _: self.trigger_analysis_thread()
        )
        self.combo_font.set("\\small")
        self.combo_font.pack(fill="x", padx=6, pady=2)

        self.lbl_tabcol = ctk.CTkLabel(self.scroll_sidebar, text="Espaciado (\\tabcolsep): 6 pt", font=ctk.CTkFont(size=11), text_color=C_TEXT_MUTED)
        self.lbl_tabcol.pack(anchor="w", padx=6, pady=(6, 1))
        self.slider_tabcol = ctk.CTkSlider(self.scroll_sidebar, from_=2, to=16, number_of_steps=14, progress_color=C_ACCENT, command=self._on_slider_tabcol)
        self.slider_tabcol.set(6)
        self.slider_tabcol.pack(fill="x", padx=6, pady=2)

        self.lbl_stretch = ctk.CTkLabel(self.scroll_sidebar, text="Interlineado (\\arraystretch): 1.15", font=ctk.CTkFont(size=11), text_color=C_TEXT_MUTED)
        self.lbl_stretch.pack(anchor="w", padx=6, pady=(6, 1))
        self.slider_stretch = ctk.CTkSlider(self.scroll_sidebar, from_=1.0, to=2.0, number_of_steps=10, progress_color=C_ACCENT, command=self._on_slider_stretch)
        self.slider_stretch.set(1.15)
        self.slider_stretch.pack(fill="x", padx=6, pady=2)

    def _on_slider_tabcol(self, val: float):
        self.lbl_tabcol.configure(text=f"Espaciado (\\tabcolsep): {int(val)} pt")
        self.trigger_analysis_thread()

    def _on_slider_stretch(self, val: float):
        self.lbl_stretch.configure(text=f"Interlineado (\\arraystretch): {val:.2f}")
        self.trigger_analysis_thread()

    def _on_metric_switch_toggled(self, metric: StatMetric):
        metric_to_math_map = {
            "mean_sd": "Media y Desviación Estándar (Paramétrico)",
            "sem": "Error Estándar (SEM) e Intervalo de Confianza 95%",
            "ci95": "Error Estándar (SEM) e Intervalo de Confianza 95%",
            "variance": "Media y Desviación Estándar (Paramétrico)",
            "median_iqr": "Mediana y Rango Intercuartílico (No Paramétrico)",
            "p10_p90": "Mediana y Rango Intercuartílico (No Paramétrico)",
            "skew_kurt": "Asimetría y Curtosis Muestral",
            "shannon_h": "Diversidad Alfa: Shannon (H') y Pielou (J')",
            "pielou_j": "Diversidad Alfa: Shannon (H') y Pielou (J')",
            "simpson_div": "Índices de Simpson (D, 1-D, 1/D) y Margalef"
        }
        if metric.id_key in metric_to_math_map:
            self.combo_math_metric.set(metric_to_math_map[metric.id_key])
            self._render_math_formula()
        self.trigger_analysis_thread()

    # -------------------------------------------------------------------------
    # CONSTRUCCIÓN DE VISTAS
    # -------------------------------------------------------------------------
    def _setup_views(self):
        # 1. TABLA & LATEX
        v1 = ctk.CTkFrame(self.content_area, fg_color="transparent")
        v1.grid_columnconfigure(0, weight=1)
        v1.grid_columnconfigure(1, weight=1)
        v1.grid_rowconfigure(1, weight=1)
        v1.grid_rowconfigure(3, weight=2)

        self.lbl_in_dataset = ctk.CTkLabel(v1, text=self._tr("input_dataset"), font=ctk.CTkFont(weight="bold"), text_color=C_TEXT)
        self.lbl_in_dataset.grid(row=0, column=0, sticky="w", padx=6, pady=(4, 2))
        tree_frame_in = ctk.CTkFrame(v1, fg_color=C_SURFACE, border_width=1, border_color=C_BORDER)
        tree_frame_in.grid(row=1, column=0, sticky="nsew", padx=6, pady=(0, 6))

        scroll_y_in = ttk.Scrollbar(tree_frame_in, orient="vertical")
        scroll_x_in = ttk.Scrollbar(tree_frame_in, orient="horizontal")
        self.tree = ttk.Treeview(tree_frame_in, show="headings", yscrollcommand=scroll_y_in.set, xscrollcommand=scroll_x_in.set)
        scroll_y_in.config(command=self.tree.yview)
        scroll_x_in.config(command=self.tree.xview)
        scroll_y_in.pack(side="right", fill="y")
        scroll_x_in.pack(side="bottom", fill="x")
        self.tree.pack(side="left", fill="both", expand=True)

        render_header = ctk.CTkFrame(v1, fg_color="transparent")
        render_header.grid(row=0, column=1, sticky="ew", padx=6, pady=(4, 2))
        self.lbl_render_prev = ctk.CTkLabel(render_header, text=self._tr("rendered_preview"), font=ctk.CTkFont(weight="bold"), text_color=C_TEXT)
        self.lbl_render_prev.pack(side="left")

        self.btn_reset_view = ctk.CTkButton(
            render_header, text="🔄 Reset Zoom", width=90, height=22,
            fg_color=C_CARD, hover_color=C_BORDER, text_color=C_TEXT,
            command=self._reset_preview_zoom
        )
        self.btn_reset_view.pack(side="right", padx=4)

        self.sw_multiline = ctk.CTkSwitch(render_header, text=self._tr("two_line_headers"), progress_color=C_ACCENT, command=self.trigger_analysis_thread)
        self.sw_multiline.select()
        self.sw_multiline.pack(side="right", padx=6)

        self.preview_frame = ctk.CTkFrame(v1, fg_color=C_SURFACE, corner_radius=6, border_width=1, border_color=C_BORDER)
        self.preview_frame.grid(row=1, column=1, sticky="nsew", padx=6, pady=(0, 6))

        self.fig_preview = Figure(figsize=(5.5, 3.2), dpi=105, facecolor="#161b22")
        self.ax_preview = self.fig_preview.add_subplot(111)
        self.ax_preview.set_facecolor("#161b22")
        self.ax_preview.axis("off")

        self.canvas_preview = FigureCanvasTkAgg(self.fig_preview, master=self.preview_frame)
        self.canvas_preview_widget = self.canvas_preview.get_tk_widget()
        self.canvas_preview_widget.pack(fill="both", expand=True)

        self.canvas_preview_widget.bind("<ButtonPress-1>", self._on_preview_pan_start)
        self.canvas_preview_widget.bind("<B1-Motion>", self._on_preview_pan_move)
        self.canvas_preview_widget.bind("<MouseWheel>", self._on_preview_zoom)

        editor_bar = ctk.CTkFrame(v1, fg_color="transparent")
        editor_bar.grid(row=2, column=0, columnspan=2, sticky="ew", padx=6, pady=(6, 2))
        self.lbl_latex_src = ctk.CTkLabel(editor_bar, text=self._tr("latex_source"), font=ctk.CTkFont(weight="bold"), text_color=C_TEXT)
        self.lbl_latex_src.pack(side="left")
        self.lbl_latex_validation = ctk.CTkLabel(editor_bar, text="Sintaxis: Pendiente", font=ctk.CTkFont(size=11), text_color=C_TEXT_MUTED)
        self.lbl_latex_validation.pack(side="right")

        self.tex_editor = ctk.CTkTextbox(
            v1, font=("Consolas", 12), fg_color=C_SURFACE, text_color=C_TEXT,
            border_width=1, border_color=C_BORDER, wrap="none"
        )
        self.tex_editor.grid(row=3, column=0, columnspan=2, sticky="nsew", padx=6, pady=(0, 6))
        self.views["tab_latex"] = v1

        # 2. NORMALIDAD
        v2 = ctk.CTkFrame(self.content_area, fg_color="transparent")
        v2.grid_columnconfigure(0, weight=1)
        v2.grid_rowconfigure(1, weight=1)

        norm_top = ctk.CTkFrame(v2, fg_color=C_SURFACE, corner_radius=6, border_width=1, border_color=C_BORDER)
        norm_top.grid(row=0, column=0, sticky="ew", padx=6, pady=(4, 8))

        self.lbl_norm_title = ctk.CTkLabel(norm_top, text=self._tr("norm_title"), font=ctk.CTkFont(size=14, weight="bold"), text_color=C_TEXT)
        self.lbl_norm_title.pack(side="left", padx=12, pady=10)

        self.combo_alpha = ctk.CTkComboBox(
            norm_top, values=["0.01", "0.05", "0.10", "0.20", "0.30"], width=90,
            command=lambda _: self.trigger_analysis_thread()
        )
        self.combo_alpha.set("0.05")
        self.combo_alpha.pack(side="right", padx=12, pady=6)
        self.lbl_alpha_lvl = ctk.CTkLabel(norm_top, text=self._tr("alpha_level"), font=ctk.CTkFont(size=12), text_color=C_ACCENT)
        self.lbl_alpha_lvl.pack(side="right", padx=4)

        self.norm_cards_container = ctk.CTkScrollableFrame(
            v2, fg_color=C_SURFACE, corner_radius=6,
            border_width=1, border_color=C_BORDER
        )
        self.norm_cards_container.grid(row=1, column=0, sticky="nsew", padx=6, pady=(0, 6))
        self.views["tab_norm"] = v2

        # 3. BIODIVERSIDAD (DIVERSIDAD ALFA & BETA)
        v_bio = ctk.CTkFrame(self.content_area, fg_color="transparent")
        v_bio.grid_columnconfigure(0, weight=1)
        v_bio.grid_rowconfigure(1, weight=1)

        bio_top = ctk.CTkFrame(v_bio, fg_color=C_SURFACE, corner_radius=6, border_width=1, border_color=C_BORDER)
        bio_top.grid(row=0, column=0, sticky="ew", padx=6, pady=(4, 8))

        self.lbl_biodiv_title = ctk.CTkLabel(bio_top, text=self._tr("biodiv_title"), font=ctk.CTkFont(size=13, weight="bold"), text_color=C_TEXT)
        self.lbl_biodiv_title.pack(side="left", padx=12, pady=8)

        self.btn_beta_tex = ctk.CTkButton(
            bio_top, text=self._tr("btn_beta_latex"), width=155, fg_color=C_CARD,
            hover_color=C_BORDER, text_color=C_TEXT, border_width=1, border_color=C_BORDER,
            command=lambda: self.export_biodiv_to_latex(mode="beta")
        )
        self.btn_beta_tex.pack(side="right", padx=6, pady=6)

        self.btn_alpha_tex = ctk.CTkButton(
            bio_top, text=self._tr("btn_send_latex"), width=155, fg_color="#238636", hover_color="#2ea043",
            command=lambda: self.export_biodiv_to_latex(mode="alpha")
        )
        self.btn_alpha_tex.pack(side="right", padx=4, pady=6)

        self.btn_calc_biodiv = ctk.CTkButton(
            bio_top, text=self._tr("btn_calc_biodiv"), width=150, fg_color=C_PRIMARY,
            command=self.compute_biodiversity_analysis
        )
        self.btn_calc_biodiv.pack(side="right", padx=4, pady=6)

        self.combo_beta_method = ctk.CTkComboBox(
            bio_top, values=["Bray-Curtis (Disimilitud)", "Jaccard (Similitud)", "Sørensen-Dice (Similitud)"],
            width=185, command=lambda _: self.compute_biodiversity_analysis()
        )
        self.combo_beta_method.set("Bray-Curtis (Disimilitud)")
        self.combo_beta_method.pack(side="right", padx=6)

        self.lbl_beta_metric = ctk.CTkLabel(bio_top, text=self._tr("beta_metric"), text_color=C_TEXT)
        self.lbl_beta_metric.pack(side="right", padx=4)

        self.txt_biodiv = ctk.CTkTextbox(
            v_bio, font=("Consolas", 12), fg_color=C_SURFACE, text_color=C_TEXT,
            border_width=1, border_color=C_BORDER, wrap="none"
        )
        self.txt_biodiv.grid(row=1, column=0, sticky="nsew", padx=6, pady=(0, 6))
        self.views["tab_biodiv"] = v_bio

        # 4. INFERENCIA ESTADÍSTICA
        v_inf = ctk.CTkFrame(self.content_area, fg_color="transparent")
        v_inf.grid_columnconfigure(0, weight=1)
        v_inf.grid_rowconfigure(1, weight=1)

        inf_top = ctk.CTkFrame(v_inf, fg_color=C_SURFACE, corner_radius=6, border_width=1, border_color=C_BORDER)
        inf_top.grid(row=0, column=0, sticky="ew", padx=6, pady=(4, 8))

        ctk.CTkLabel(inf_top, text="Prueba Inferencia:", font=ctk.CTkFont(weight="bold"), text_color=C_TEXT).pack(side="left", padx=(12, 4), pady=8)
        self.combo_inf_test = ctk.CTkComboBox(
            inf_top, values=["t-Student (2 Muestras Independientes)", "Chi-cuadrado (Independencia)"],
            width=290, command=lambda _: self._update_inf_selectors()
        )
        self.combo_inf_test.pack(side="left", padx=4)

        self.lbl_inf_v1 = ctk.CTkLabel(inf_top, text="Var Cuantitativa:", text_color=C_TEXT)
        self.lbl_inf_v1.pack(side="left", padx=(10, 4))
        self.combo_inf_var1 = ctk.CTkComboBox(inf_top, values=["(ninguna)"], width=130)
        self.combo_inf_var1.pack(side="left", padx=4)

        self.lbl_inf_v2 = ctk.CTkLabel(inf_top, text="Factor (2 niveles):", text_color=C_TEXT)
        self.lbl_inf_v2.pack(side="left", padx=(10, 4))
        self.combo_inf_var2 = ctk.CTkComboBox(inf_top, values=["(ninguna)"], width=130)
        self.combo_inf_var2.pack(side="left", padx=4)

        self.btn_run_inf = ctk.CTkButton(
            inf_top, text="⚡ Ejecutar Prueba", width=120, fg_color=C_PRIMARY,
            command=self.compute_inference_test
        )
        self.btn_run_inf.pack(side="right", padx=12)

        self.txt_inference = ctk.CTkTextbox(
            v_inf, font=("Consolas", 12), fg_color=C_SURFACE, text_color=C_TEXT,
            border_width=1, border_color=C_BORDER, wrap="none"
        )
        self.txt_inference.grid(row=1, column=0, sticky="nsew", padx=6, pady=(0, 6))
        self.views["tab_inf"] = v_inf

        # 5. GRÁFICAS ANALÍTICAS
        v3 = ctk.CTkFrame(self.content_area, fg_color="transparent")
        v3.grid_columnconfigure(0, weight=1)
        v3.grid_rowconfigure(1, weight=1)

        top_bar = ctk.CTkFrame(v3, fg_color=C_SURFACE, corner_radius=6, border_width=1, border_color=C_BORDER)
        top_bar.grid(row=0, column=0, sticky="ew", padx=6, pady=(4, 8))

        ctk.CTkLabel(top_bar, text="Var X:", text_color=C_TEXT).pack(side="left", padx=(10, 4), pady=6)
        self.combo_plot_var = ctk.CTkComboBox(top_bar, values=["(ninguna)"], width=125, command=lambda _: self.render_selected_plot())
        self.combo_plot_var.pack(side="left", padx=4)

        ctk.CTkLabel(top_bar, text="Var Y:", text_color=C_TEXT).pack(side="left", padx=(6, 4))
        self.combo_plot_var_y = ctk.CTkComboBox(top_bar, values=["(ninguna)"], width=125, command=lambda _: self.render_selected_plot())
        self.combo_plot_var_y.pack(side="left", padx=4)

        ctk.CTkLabel(top_bar, text="Tipo:", text_color=C_TEXT).pack(side="left", padx=(6, 4))
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
                "Heatmap Correlación",
                "Curva Rango-Abundancia (Whittaker)",
                "Perfil Diversidad Alfa (H', 1-D, J')",
                "Heatmap Diversidad Beta (Bray-Curtis)"
            ],
            width=225,
            command=lambda _: self.render_selected_plot()
        )
        self.combo_plot_type.pack(side="left", padx=4)

        ctk.CTkLabel(top_bar, text=self._tr("palette_lbl"), text_color=C_TEXT).pack(side="left", padx=(6, 4))
        self.combo_palette = ctk.CTkComboBox(
            top_bar,
            values=list(PALETTES.keys()),
            width=170,
            command=lambda _: self.render_selected_plot()
        )
        self.combo_palette.set("BioEvo Classic (Cyan/Blue)")
        self.combo_palette.pack(side="left", padx=4)

        self.sw_log_scale = ctk.CTkSwitch(top_bar, text="Log", progress_color=C_ACCENT, command=self.render_selected_plot)
        self.sw_log_scale.pack(side="left", padx=6)

        btn_save_pdf = ctk.CTkButton(top_bar, text="📄 PDF Vector", width=90, fg_color=C_CARD, hover_color=C_BORDER, text_color=C_TEXT, command=lambda: self.save_figure("pdf"))
        btn_save_pdf.pack(side="right", padx=3)

        btn_save_png = ctk.CTkButton(top_bar, text="🖼️ PNG HD", width=80, fg_color=C_CARD, hover_color=C_BORDER, text_color=C_TEXT, command=lambda: self.save_figure("png"))
        btn_save_png.pack(side="right", padx=3)

        self.lbl_plot_sug = ctk.CTkLabel(v3, text="", text_color=C_TEXT_MUTED, font=ctk.CTkFont(size=11, slant="italic"))
        self.lbl_plot_sug.grid(row=2, column=0, sticky="w", padx=12, pady=4)

        self.plot_canvas_frame = ctk.CTkFrame(v3, fg_color=C_SURFACE, corner_radius=6, border_width=1, border_color=C_BORDER)
        self.plot_canvas_frame.grid(row=1, column=0, sticky="nsew", padx=6, pady=(0, 2))

        self.fig_analytics = Figure(figsize=(8.5, 5.2), dpi=110, facecolor="#161b22")
        self.canvas_analytics = FigureCanvasTkAgg(self.fig_analytics, master=self.plot_canvas_frame)
        self.canvas_analytics.get_tk_widget().pack(fill="both", expand=True)
        self.views["tab_plots"] = v3

        # 6. FUNDAMENTO MATEMÁTICO
        v4 = ctk.CTkFrame(self.content_area, fg_color="transparent")
        v4.grid_columnconfigure(0, weight=1)
        v4.grid_rowconfigure(1, weight=1)

        top_math = ctk.CTkFrame(v4, fg_color=C_SURFACE, corner_radius=6, border_width=1, border_color=C_BORDER)
        top_math.grid(row=0, column=0, sticky="ew", padx=6, pady=(4, 8))

        ctk.CTkLabel(top_math, text="Ecuación:", font=ctk.CTkFont(weight="bold"), text_color=C_TEXT).pack(side="left", padx=(10, 4), pady=8)
        self.combo_math_metric = ctk.CTkComboBox(
            top_math,
            values=[
                "Media y Desviación Estándar (Paramétrico)",
                "Error Estándar (SEM) e Intervalo de Confianza 95%",
                "Mediana y Rango Intercuartílico (No Paramétrico)",
                "Prueba de Normalidad Shapiro-Wilk (W)",
                "Asimetría y Curtosis Muestral",
                "Diversidad Alfa: Shannon (H') y Pielou (J')",
                "Índices de Simpson (D, 1-D, 1/D) y Margalef",
                "Diversidad Beta: Bray-Curtis, Jaccard y Sørensen"
            ],
            width=360,
            command=lambda _: self._render_math_formula()
        )
        self.combo_math_metric.pack(side="left", padx=4)

        ctk.CTkLabel(top_math, text="Variable activa para cálculo empírico:", text_color=C_TEXT).pack(side="left", padx=(12, 4))
        self.combo_math_var = ctk.CTkComboBox(
            top_math, values=["(ninguna)"], width=160,
            command=lambda _: self._render_math_formula()
        )
        self.combo_math_var.pack(side="left", padx=4)

        self.math_canvas_frame = ctk.CTkFrame(v4, fg_color=C_SURFACE, corner_radius=6, border_width=1, border_color=C_BORDER)
        self.math_canvas_frame.grid(row=1, column=0, sticky="nsew", padx=6, pady=(0, 10))

        self.fig_math = Figure(figsize=(9, 6), dpi=115, facecolor="#161b22")
        self.canvas_math = FigureCanvasTkAgg(self.fig_math, master=self.math_canvas_frame)
        self.canvas_math.get_tk_widget().pack(fill="both", expand=True)
        self._render_math_formula()
        self.views["tab_math"] = v4

    # -------------------------------------------------------------------------
    # INTERACCIÓN CON EL RENDERIZADO MATPLOTLIB (PAN Y ZOOM)
    # -------------------------------------------------------------------------
    def _on_preview_pan_start(self, event):
        self._pan_start = (event.x, event.y)

    def _on_preview_pan_move(self, event):
        if self._pan_start is None:
            return
        dx = (event.x - self._pan_start[0]) * 0.003
        dy = (event.y - self._pan_start[1]) * 0.003
        self._pan_start = (event.x, event.y)

        xlim = self.ax_preview.get_xlim()
        ylim = self.ax_preview.get_ylim()
        self.ax_preview.set_xlim(xlim[0] - dx, xlim[1] - dx)
        self.ax_preview.set_ylim(ylim[0] + dy, ylim[1] + dy)
        self.canvas_preview.draw_idle()

    def _on_preview_zoom(self, event):
        base_scale = 1.15
        cur_xlim = self.ax_preview.get_xlim()
        cur_ylim = self.ax_preview.get_ylim()

        scale_factor = (1 / base_scale) if event.delta > 0 else base_scale

        xdata = (cur_xlim[0] + cur_xlim[1]) / 2
        ydata = (cur_ylim[0] + cur_ylim[1]) / 2

        new_width = (cur_xlim[1] - cur_xlim[0]) * scale_factor
        new_height = (cur_ylim[1] - cur_ylim[0]) * scale_factor

        self.ax_preview.set_xlim([xdata - new_width / 2, xdata + new_width / 2])
        self.ax_preview.set_ylim([ydata - new_height / 2, ydata + new_height / 2])
        self.canvas_preview.draw_idle()

    def _reset_preview_zoom(self):
        self.ax_preview.set_xlim(0, 1)
        self.ax_preview.set_ylim(0, 1)
        self.trigger_analysis_thread()

    # -------------------------------------------------------------------------
    # FUNDAMENTO MATEMÁTICO DINÁMICO
    # -------------------------------------------------------------------------
    def _render_math_formula(self):
        choice = self.combo_math_metric.get()
        active_var = self.combo_math_var.get()
        use_comma = getattr(self, "sw_comma", None) and self.sw_comma.get() == 1

        def fmt(n: float, dec: int = 2) -> str:
            txt = f"{n:.{dec}f}"
            return txt.replace(".", ",") if use_comma else txt

        s_val = None
        if self.df is not None and active_var in self.df.columns and pd.api.types.is_numeric_dtype(self.df[active_var]):
            s_val = self.df[active_var].dropna()

        is_dark = self.current_theme_mode.lower() == "dark"
        mat_bg = "#161b22" if is_dark else "#ffffff"
        mat_text = "#e6edf3" if is_dark else "#1f2328"

        self.fig_math.clear()
        ax = self.fig_math.add_subplot(111)
        ax.set_facecolor(mat_bg)
        ax.axis("off")

        empirical_txt = ""

        if "Media y Desviación" in choice:
            formula = (
                r"$\mathbf{1.\; Media\; Muestral\; (\bar{x}):}\quad \bar{x} = \frac{1}{n} \sum_{i=1}^{n} x_i$"
                "\n\n"
                r"$\mathbf{2.\; Desviaci\acute{o}n\; Est\acute{a}ndar\; (s):}\quad s = \sqrt{\frac{1}{n-1} \sum_{i=1}^{n} (x_i - \bar{x})^2}$"
                "\n\n"
                r"$\mathbf{3.\; Rango\; Referencia\; Param\acute{e}trico\; (95\%):}\quad \mathrm{Ref}_{95\%} = \left[\, \bar{x} - 1.96 \cdot s \,,\; \bar{x} + 1.96 \cdot s \,\right]$"
            )
            desc = (
                "• Grados de libertad (g.d.l.): n - 1 (Corrección de Bessel para remover el sesgo muestral).\n"
                "• Supuesto obligatorio: Datos con distribución normal verificada (p >= alfa)."
            )
            if s_val is not None and len(s_val) > 1:
                m, s = s_val.mean(), s_val.std(ddof=1)
                empirical_txt = (
                    f"EVALUACIÓN CON DATOS REALES ({active_var}):\n"
                    f"n = {len(s_val)}   |   Media (x̄) = {fmt(m)}   |   DE (s) = {fmt(s)}\n"
                    f"Intervalo de Referencia 95%: [{fmt(m - 1.96 * s)} -- {fmt(m + 1.96 * s)}]"
                )

        elif "Error Estándar" in choice:
            formula = (
                r"$\mathbf{1.\; Error\; Est\acute{a}ndar\; de\; la\; Media\; (SEM):}\quad \mathrm{SEM} = \frac{s}{\sqrt{n}}$"
                "\n\n"
                r"$\mathbf{2.\; Intervalo\; de\; Confianza\; del\; 95\%\; (t-Student):}\quad \mathrm{IC}_{95\%} = \bar{x} \pm t_{\alpha/2,\, n-1} \cdot \mathrm{SEM}$"
            )
            desc = (
                "• Cuantifica la precisión del estimador muestral respecto a la media poblacional μ.\n"
                "• Emplea la distribución t-Student para incorporar la incertidumbre del tamaño muestral."
            )
            if s_val is not None and len(s_val) > 1:
                n = len(s_val)
                m = s_val.mean()
                sem = s_val.std(ddof=1) / np.sqrt(n)
                ci = stats.t.interval(0.95, df=n - 1, loc=m, scale=sem)
                empirical_txt = (
                    f"EVALUACIÓN CON DATOS REALES ({active_var}):\n"
                    f"n = {n}   |   SEM = {fmt(sem, 3)}   |   IC 95%: [{fmt(ci[0])} -- {fmt(ci[1])}]"
                )

        elif "Mediana y Rango" in choice:
            formula = (
                r"$\mathbf{1.\; Mediana\; (P_{50}):}\quad \tilde{x} = x_{\left(\frac{n+1}{2}\right)} \quad \text{o} \quad \frac{1}{2}\left(x_{(n/2)} + x_{(n/2+1)}\right)$"
                "\n\n"
                r"$\mathbf{2.\; Rango\; Intercuart\acute{\imath}lico\; (IQR):}\quad \mathrm{IQR} = Q_3 - Q_1 = P_{75} - P_{25}$"
            )
            desc = (
                "• Estadísticos robustos no paramétricos: Invariantes ante asimetría y valores extremos.\n"
                "• Indicados al rechazar normalidad en Shapiro-Wilk (p < alfa)."
            )
            if s_val is not None and len(s_val) > 0:
                med, q1, q3 = s_val.median(), s_val.quantile(0.25), s_val.quantile(0.75)
                empirical_txt = (
                    f"EVALUACIÓN CON DATOS REALES ({active_var}):\n"
                    f"Mediana = {fmt(med)}   |   Q1 (P25) = {fmt(q1)}   |   Q3 (P75) = {fmt(q3)}   |   IQR = {fmt(q3 - q1)}"
                )

        elif "Shapiro-Wilk" in choice:
            formula = (
                r"$\mathbf{Estad\acute{\imath}stico\; W\; de\; Shapiro-Wilk:}\quad W = \frac{\left( \sum_{i=1}^{n} a_i \, x_{(i)} \right)^2}{\sum_{i=1}^{n} (x_i - \bar{x})^2}$"
                "\n\n"
                r"$\mathbf{Regla\; de\; Decisi\acute{o}n:}\quad "
                r"\begin{cases} "
                r"p \ge \alpha \implies \text{Ajuste Normal} \implies \text{Reportar } \bar{x} \pm s \\ "
                r"p < \alpha \implies \text{No Normal} \implies \text{Reportar Mediana [IQR]} "
                r"\end{cases}$"
            )
            desc = (
                "• x_(i) son los estadísticos de orden muestrales.\n"
                "• Los coeficientes a_i derivan de los cuantiles de una normal estándar."
            )
            if s_val is not None and len(s_val) >= 3 and s_val.nunique() > 1:
                w_stat, p_val = stats.shapiro(s_val[:5000])
                alpha_thr = float(self.combo_alpha.get())
                conclusion = "Distribución Normal" if p_val >= alpha_thr else "Distribución No Normal"
                empirical_txt = (
                    f"EVALUACIÓN CON DATOS REALES ({active_var}):\n"
                    f"W = {fmt(w_stat, 4)}   |   p-valor = {fmt(p_val, 4)}   |   Regla (alfa = {fmt(alpha_thr, 2)}): {conclusion}"
                )

        elif "Shannon" in choice:
            formula = (
                r"$\mathbf{1.\; \acute{I}ndice\; de\; Shannon-Wiener\; (H'):}\quad H' = -\sum_{i=1}^{S} p_i \ln(p_i) \quad \text{donde}\quad p_i = \frac{n_i}{N}$"
                "\n\n"
                r"$\mathbf{2.\; Equidad\; de\; Pielou\; (J'):}\quad J' = \frac{H'}{H'_{\max}} = \frac{H'}{\ln(S)}$"
            )
            desc = (
                "• Cuantifica la entropía de información de la comunidad biológica.\n"
                "• J' oscila en [0, 1]: valores cercanos a 1 reflejan comunidades equitativas sin dominancia extrema."
            )
            if s_val is not None:
                res = compute_alpha_diversity_vector(s_val)
                empirical_txt = (
                    f"EVALUACIÓN ECOLÓGICA EMPÍRICA ({active_var}):\n"
                    f"Riqueza (S) = {res['S']} taxones   |   Abundancia Total (N) = {fmt(res['N'], 1)}\n"
                    f"Shannon (H') = {fmt(res['H'], 4)} nats   |   Equidad de Pielou (J') = {fmt(res['J'], 4)}"
                )

        elif "Simpson" in choice:
            formula = (
                r"$\mathbf{1.\; Dominancia\; de\; Simpson\; (D):}\quad D = \sum_{i=1}^{S} p_i^2 \quad \text{y}\quad \mathbf{Diversidad\; (1-D):}\quad 1 - \sum_{i=1}^{S} p_i^2$"
                "\n\n"
                r"$\mathbf{2.\; Rec\acute{\imath}proco\; de\; Simpson:}\quad \frac{1}{D} \qquad \mathbf{3.\; Riqueza\; de\; Margalef:}\quad D_{\mathrm{Mg}} = \frac{S - 1}{\ln(N)}$"
            )
            desc = (
                "• D mide la probabilidad de que dos individuos pertenezcan a la misma especie.\n"
                "• (1 - D) representa la probabilidad de extracción interespecífica."
            )
            if s_val is not None:
                res = compute_alpha_diversity_vector(s_val)
                empirical_txt = (
                    f"EVALUACIÓN ECOLÓGICA EMPÍRICA ({active_var}):\n"
                    f"Dominancia (D) = {fmt(res['D'], 4)}   |   Diversidad (1 - D) = {fmt(res['1_D'], 4)}\n"
                    f"Inverso (1/D) = {fmt(res['inv_D'], 3)}   |   Margalef (D_Mg) = {fmt(res['D_mg'], 3)}"
                )

        elif "Diversidad Beta" in choice:
            formula = (
                r"$\mathbf{1.\; Disimilitud\; de\; Bray-Curtis\; (BC_{jk}):}\quad BC_{jk} = \frac{\sum_{i=1}^{S} |n_{ij} - n_{ik}|}{\sum_{i=1}^{S} (n_{ij} + n_{ik})}$"
                "\n\n"
                r"$\mathbf{2.\; Similitud\; de\; Jaccard\; (I_J):}\quad I_J = \frac{a}{a + b + c} \qquad \mathbf{3.\; S\phi rensen\; (I_S):}\quad I_S = \frac{2a}{2a + b + c}$"
            )
            desc = (
                "• Evalúa el recambio de especies (turnover) entre sitios o tratamientos experimentales.\n"
                "• Bray-Curtis pondera abundancias cuantitativas; Jaccard y Sørensen evalúan presencia/ausencia."
            )
            if self.df is not None:
                num_cols = self.df.select_dtypes(include=[np.number]).columns.tolist()
                if len(num_cols) >= 2:
                    b_mat = compute_beta_diversity_matrix(self.df[num_cols[:2]], "Bray-Curtis")
                    j_mat = compute_beta_diversity_matrix(self.df[num_cols[:2]], "Jaccard")
                    empirical_txt = (
                        f"COMPARACIÓN BETA ENTRE '{num_cols[0]}' Y '{num_cols[1]}':\n"
                        f"Disimilitud Bray-Curtis = {fmt(b_mat.iloc[0, 1], 4)}   |   Similitud de Jaccard = {fmt(j_mat.iloc[0, 1], 4)}"
                    )
        else:
            formula = (
                r"$\mathbf{Asimetr\acute{\imath}a\; Insesgada\; (g_1):}\quad g_1 = \frac{n}{(n-1)(n-2)} \sum_{i=1}^{n} \left(\frac{x_i - \bar{x}}{s}\right)^3$"
                "\n\n"
                r"$\mathbf{Curtosis\; Excesiva\; (g_2):}\quad g_2 = \frac{n(n+1)}{(n-1)(n-2)(n-3)} \sum_{i=1}^{n} \left(\frac{x_i - \bar{x}}{s}\right)^4 - \frac{3(n-1)^2}{(n-2)(n-3)}$"
            )
            desc = (
                "• g1 > 0: Cola extendida a la derecha; g1 < 0: Cola extendida a la izquierda.\n"
                "• g2 = 0 representa el comportamiento mesocúrtico de la normal estándar."
            )
            if s_val is not None and len(s_val) >= 3:
                empirical_txt = (
                    f"EVALUACIÓN CON DATOS REALES ({active_var}):\n"
                    f"Asimetría (g1) = {fmt(s_val.skew(), 3)}   |   Curtosis Excesiva (g2) = {fmt(s_val.kurtosis(), 3)}"
                )

        palette_key = self.combo_palette.get() if hasattr(self, "combo_palette") else "BioEvo Classic (Cyan/Blue)"
        accent_color = PALETTES[palette_key]["accent"]

        ax.text(0.04, 0.88, formula, fontsize=12, color=accent_color, verticalalignment="top")
        ax.text(0.04, 0.38, desc, fontsize=10, color=mat_text, verticalalignment="top", style="italic")

        if empirical_txt:
            card_bg = "#21262d" if is_dark else "#eaeef2"
            ax.text(
                0.04, 0.19, empirical_txt, fontsize=10.5, fontfamily="monospace",
                color="#3fb950" if is_dark else "#1a7f37", verticalalignment="top",
                bbox=dict(boxstyle="round,pad=0.5", facecolor=card_bg, edgecolor="#30363d" if is_dark else "#d0d7de")
            )

        self.fig_math.tight_layout()
        self.canvas_math.draw_idle()

    # -------------------------------------------------------------------------
    # CONCURRENCIA SEGURA (THREAD-SAFE PROGRESS BAR)
    # -------------------------------------------------------------------------
    def load_file_threaded(self):
        path = filedialog.askopenfilename(
            filetypes=[("Archivos Tabulares", "*.csv *.tsv *.txt *.xlsx *.xls"), ("Todos los archivos", "*.*")]
        )
        if not path:
            return

        self.current_filepath = path
        self.progress_bar.set(0.1)
        self.lbl_progress.configure(text="Saneando dataset y codificación...")

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

        log_str = f"{os.path.basename(path)} | Enc: {meta['encoding']} | Sep: '{meta['delimiter']}' | Comas: {meta['coerced_columns']}"
        self.lbl_progress.configure(text=log_str, text_color=C_SUCCESS)
        self.btn_copy.configure(state="normal")
        self.btn_save_tex.configure(state="normal")

        self._populate_variables()
        self._populate_preview()
        self.trigger_analysis_thread()
        self.compute_biodiversity_analysis()

    def _on_worker_error(self, err_msg: str):
        self.progress_bar.set(0)
        self.lbl_progress.configure(text="Fallo en la operación", text_color=C_DANGER)
        messagebox.showerror("Error", err_msg)

    def trigger_analysis_thread(self):
        if self.df is None:
            return
        self.progress_bar.set(0.5)
        threading.Thread(target=self._compute_analysis_worker, daemon=True).start()

    # -------------------------------------------------------------------------
    # MOTOR DE CÓMPUTO Y MAQUETACIÓN LATEX
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
            standard = self.seg_format.get()
            alpha_threshold = float(self.combo_alpha.get())

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
            norm_card_items = []

            def process_series(s: pd.Series, safe_v: str, safe_g: Optional[str] = None):
                n_len = len(s)
                es_normal = True
                w_stat, p_val = 1.0, 1.0
                if n_len >= 3 and s.nunique() > 1:
                    w_stat, p_val = stats.shapiro(s[:5000])
                    es_normal = p_val >= alpha_threshold

                r_tex = [safe_g, safe_v] if safe_g else [safe_v]
                r_prev = [str(safe_g), safe_v] if safe_g else [safe_v]

                for m in active_metrics:
                    if strict_norm and m.is_parametric and not es_normal:
                        val = r"\text{---}"
                        val_prev = "---"
                    elif strict_norm and not m.is_parametric and es_normal and not isinstance(m, (MinMaxMetric, SampleSizeMetric, ShannonMetric, SimpsonDivMetric, PielouMetric)):
                        val = r"\text{---}"
                        val_prev = "---"
                    else:
                        val = m.compute(s, fmt)
                        val_prev = val.replace("$", "").replace(r"\pm", "±").replace(r"\'{\i}", "í").replace(r"\'ax", "á")

                    r_tex.append(val)
                    r_prev.append(val_prev)

                return r_tex, r_prev, (w_stat, p_val, es_normal, n_len, s.nunique())

            if is_grouped:
                for grp, sub in self.df.groupby(group_col):
                    safe_grp = sanitize_latex(str(grp))
                    for var in selected_vars:
                        s = sub[var].dropna()
                        safe_var = sanitize_latex(var)
                        r_t, r_p, n_info = process_series(s, safe_var, safe_grp)
                        rows.append(r_t)
                        preview_table_data.append(r_p)
                        norm_card_items.append((f"{grp} · {var}", n_info))
                        comp_done += 1
                        prog_val = 0.5 + 0.4 * (comp_done / total_computations)
                        self.after(0, self.progress_bar.set, prog_val)
            else:
                for var in selected_vars:
                    s = self.df[var].dropna()
                    safe_var = sanitize_latex(var)
                    r_t, r_p, n_info = process_series(s, safe_var)
                    rows.append(r_t)
                    preview_table_data.append(r_p)
                    norm_card_items.append((var, n_info))
                    comp_done += 1
                    prog_val = 0.5 + 0.4 * (comp_done / total_computations)
                    self.after(0, self.progress_bar.set, prog_val)

            cols_def = "l" + "c" * (len(latex_headers) - 1)
            font_cmd = self.combo_font.get()
            use_resize = self.sw_resize.get() == 1
            use_linespace = self.sw_linespace.get() == 1
            use_landscape = self.sw_landscape.get() == 1
            tab_env = "sidewaystable" if use_landscape else "table"
            tabcol_val = int(self.slider_tabcol.get())
            stretch_val = self.slider_stretch.get()

            margin_choice = self.combo_margin.get()
            geometry_map = {
                "Normal (margin=2.5cm)": r"\usepackage[margin=2.5cm]{geometry}",
                "Estrecho (margin=1.5cm)": r"\usepackage[margin=1.5cm]{geometry}",
                "APA Estricto (margin=1in)": r"\usepackage[margin=1in]{geometry}",
                "Sin geometry (default)": r"% \usepackage{geometry} (por defecto de documento)"
            }
            geom_line = geometry_map.get(margin_choice, "")

            tex = [
                r"% ===================================================================",
                f"% TABLA FORMATEADA EN ESTÁNDAR {standard} | BIOEVO v1.1.0-beta.2",
                f"% {geom_line}",
                r"% Requiere \usepackage{booktabs}, \usepackage{graphicx}" + (r", \usepackage{rotating}" if use_landscape else ""),
                r"% ===================================================================",
                f"\\begin{{{tab_env}}}[htbp]",
                r"  \centering"
            ]

            if standard == "IEEE":
                tex.extend([
                    r"  \caption{\textsc{Statistical and Ecological Summary of Experimental Variables}}",
                    r"  \label{tab:ieee_summary}",
                    f"  {font_cmd}",
                    f"  \\setlength{{\\tabcolsep}}{{{tabcol_val}pt}}",
                    f"  \\renewcommand{{\\arraystretch}}{{{stretch_val:.2f}}}"
                ])
            else:
                tex.extend([
                    f"  {font_cmd}",
                    f"  \\setlength{{\\tabcolsep}}{{{tabcol_val}pt}}",
                    f"  \\renewcommand{{\\arraystretch}}{{{stretch_val:.2f}}}",
                    r"  \caption{Resumen bioestadístico y ecológico de variables analizadas.}",
                    r"  \label{tab:labstats_summary}"
                ])

            if use_resize:
                target_w = r"\columnwidth" if (standard == "IEEE" and not use_landscape) else r"\textwidth"
                tex.append(f"  \\resizebox{{{target_w}}}{{!}}{{%")

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

            if standard == "APA 7":
                alpha_str = f"{alpha_threshold}".replace(".", ",") if use_comma else f"{alpha_threshold}"
                tex.extend([
                    r"  \vspace{1ex}\\",
                    f"  \\raggedright\\footnotesize\\textit{{Nota.}} Criterio de ajuste normal: Shapiro-Wilk con nivel $\\alpha = {alpha_str}$. Métricas paramétricas como media $\\pm$ DE y no paramétricas como mediana [IQR]."
                ])

            tex.append(f"\\end{{{tab_env}}}")
            full_latex = "\n".join(tex)

            is_valid, reason = validate_latex_syntax(full_latex)
            self.after(0, self._render_results_on_ui, full_latex, clean_headers, preview_table_data, norm_card_items, is_valid, reason)

        except Exception as e:
            self.after(0, self._on_worker_error, f"Error en cómputo analítico: {e}")

    # -------------------------------------------------------------------------
    # MÓDULO DE BIODIVERSIDAD ALFA Y BETA (REPORTE Y EXPORTACIÓN LATEX)
    # -------------------------------------------------------------------------
    def compute_biodiversity_analysis(self):
        if self.df is None:
            return

        selected_vars = [col for col, cb in self.var_checkboxes.items() if cb.get() == 1]
        if not selected_vars:
            self.txt_biodiv.delete("1.0", "end")
            self.txt_biodiv.insert("1.0", "% Selecciona al menos una variable o sitio en el panel izquierdo.")
            return

        use_comma = self.sw_comma.get() == 1
        beta_method = self.combo_beta_method.get()

        def fmt(n: float, dec: int = 3) -> str:
            txt = f"{n:.{dec}f}"
            return txt.replace(".", ",") if use_comma else txt

        out = [
            "=" * 94,
            " ESTACIÓN DE ECOLOGÍA DE COMUNIDADES | DIVERSIDAD ALFA (α) Y BETA (β)",
            "=" * 94,
            "1. ÍNDICES DE DIVERSIDAD ALFA POR SITIO / VARIABLE MUESTREADA:",
            "-" * 94,
            f"{'Sitio / Variable':<22} {'S':>5} {'N':>9} {'Shannon (H\')':>14} {'Simpson (D)':>13} {'1 - D':>10} {'1 / D':>10} {'Pielou (J\')':>12}",
            "-" * 94
        ]

        for v in selected_vars:
            res = compute_alpha_diversity_vector(self.df[v])
            out.append(
                f"{v[:21]:<22} {res['S']:>5} {fmt(res['N'], 1):>9} "
                f"{fmt(res['H'], 4):>14} {fmt(res['D'], 4):>13} "
                f"{fmt(res['1_D'], 4):>10} {fmt(res['inv_D'], 3):>10} {fmt(res['J'], 4):>12}"
            )

        out.append("-" * 94)
        out.append("Leyenda Alfa: S = Riqueza específica | N = Abundancia acumulada | H' = Entropía de Shannon (nats)")
        out.append("              D = Dominancia de Simpson | (1-D) = Prob. interespecífica | J' = Equidad de Pielou")
        out.append("\n" + "=" * 94)
        out.append(f"2. MATRIZ PAREADA DE DIVERSIDAD BETA ({beta_method.upper()}):")
        out.append("-" * 94)

        if len(selected_vars) >= 2:
            beta_df = compute_beta_diversity_matrix(self.df[selected_vars], beta_method)
            formatted_beta = beta_df.map(lambda x: fmt(x, 3))
            out.append(formatted_beta.to_string())
        else:
            out.append("Selecciona al menos 2 columnas numéricas (sitios/ensamblajes) para calcular la matriz Beta.")

        self.txt_biodiv.delete("1.0", "end")
        self.txt_biodiv.insert("1.0", "\n".join(out))

    def export_biodiv_to_latex(self, mode: str = "alpha"):
        if self.df is None:
            messagebox.showwarning("Atención", "Carga primero un dataset.")
            return

        selected_vars = [col for col, cb in self.var_checkboxes.items() if cb.get() == 1]
        if not selected_vars:
            return

        use_comma = self.sw_comma.get() == 1
        standard = self.seg_format.get()

        def fmt(n: float, dec: int = 3) -> str:
            txt = f"{n:.{dec}f}"
            return txt.replace(".", ",") if use_comma else txt

        tex = [
            r"% ===================================================================",
            f"% TABLA DE BIODIVERSIDAD ({mode.upper()}) | ESTÁNDAR {standard}",
            r"% Requiere \usepackage{booktabs} y \usepackage{graphicx}",
            r"% ===================================================================",
            r"\begin{table}[htbp]",
            r"  \centering",
            f"  {self.combo_font.get()}"
        ]

        if mode == "alpha":
            caption = r"\textsc{Alpha Diversity Indices Across Sampled Assemblages}" if standard == "IEEE" else "Índices de diversidad alfa ($\\alpha$) por unidad de muestreo."
            tex.extend([
                f"  \\caption{{{caption}}}",
                r"  \label{tab:alpha_diversity}",
                r"  \resizebox{\textwidth}{!}{%",
                r"  \begin{tabular}{lccccccc}",
                r"    \toprule",
                r"    Sitio / Unidad & $S$ & $N$ & Shannon ($H'$) & Dominancia ($D$) & Simpson ($1-D$) & Recíproco ($1/D$) & Pielou ($J'$) \\",
                r"    \midrule"
            ])
            for v in selected_vars:
                res = compute_alpha_diversity_vector(self.df[v])
                safe_v = sanitize_latex(v)
                tex.append(
                    f"    {safe_v} & {res['S']} & {fmt(res['N'], 1)} & {fmt(res['H'], 3)} & "
                    f"{fmt(res['D'], 3)} & {fmt(res['1_D'], 3)} & {fmt(res['inv_D'], 2)} & {fmt(res['J'], 3)} \\\\"
                )
            tex.extend([
                r"    \bottomrule",
                r"  \end{tabular}",
                r"  }"
            ])
        else:
            if len(selected_vars) < 2:
                messagebox.showwarning("Atención", "Se requieren al menos 2 variables para la matriz Beta.")
                return
            beta_method = self.combo_beta_method.get()
            beta_df = compute_beta_diversity_matrix(self.df[selected_vars], beta_method)
            cols_spec = "l" + "c" * len(selected_vars)
            safe_cols = [sanitize_latex(c) for c in selected_vars]

            tex.extend([
                f"  \\caption{{Matriz de diversidad beta ({sanitize_latex(beta_method)}).}}",
                r"  \label{tab:beta_diversity}",
                r"  \resizebox{\textwidth}{!}{%",
                f"  \\begin{{tabular}}{{{cols_spec}}}",
                r"    \toprule",
                f"    Sitio & {' & '.join(safe_cols)} \\\\",
                r"    \midrule"
            ])
            for idx, row_name in enumerate(selected_vars):
                vals = [fmt(beta_df.iloc[idx, j], 3) for j in range(len(selected_vars))]
                tex.append(f"    {sanitize_latex(row_name)} & {' & '.join(vals)} \\\\")
            tex.extend([
                r"    \bottomrule",
                r"  \end{tabular}",
                r"  }"
            ])

        tex.append(r"\end{table}")
        latex_str = "\n".join(tex)

        self.tex_editor.delete("1.0", "end")
        self.tex_editor.insert("1.0", latex_str)
        self.switch_view("tab_latex")
        messagebox.showinfo("Exportado a LaTeX", "La tabla de biodiversidad se ha cargado en el editor LaTeX principal.")

    # -------------------------------------------------------------------------
    # RENDERIZADO VISUAL PRINCIPAL
    # -------------------------------------------------------------------------
    def _render_results_on_ui(self, latex_code: str, headers: List[str], rows: List[List[str]], norm_card_items: List[Tuple], is_valid: bool, val_reason: str):
        self.progress_bar.set(1.0)

        self.tex_editor.delete("1.0", "end")
        self.tex_editor.insert("1.0", latex_code)

        if is_valid:
            self.lbl_latex_validation.configure(text=f"✓ Sintaxis {self.seg_format.get()} verificada", text_color=C_SUCCESS)
        else:
            self.lbl_latex_validation.configure(text=f"⚠ Error: {val_reason}", text_color=C_DANGER)

        is_dark = self.current_theme_mode.lower() == "dark"
        mat_bg = "#161b22" if is_dark else "#ffffff"
        mat_text = "#e6edf3" if is_dark else "#1f2328"
        mat_border = "#30363d" if is_dark else "#d0d7de"
        mat_card = "#21262d" if is_dark else "#eaeef2"

        self.ax_preview.clear()
        self.ax_preview.set_facecolor(mat_bg)
        self.ax_preview.axis("off")

        if rows:
            tab_obj = self.ax_preview.table(
                cellText=rows,
                colLabels=headers,
                loc="center",
                cellLoc="center"
            )
            tab_obj.auto_set_font_size(False)
            tab_obj.set_fontsize(8.5)
            tab_obj.scale(1.05, 1.85)
            tab_obj.auto_set_column_width(col=list(range(len(headers))))

            palette = PALETTES[self.combo_palette.get()]
            for (r_idx, c_idx), cell in tab_obj.get_celld().items():
                cell.set_edgecolor(mat_border)
                cell.set_linewidth(0.6)
                if r_idx == 0:
                    cell.set_facecolor(mat_card)
                    cell.set_text_props(weight="bold", color=palette["accent"])
                else:
                    cell.set_facecolor(mat_bg)
                    cell.set_text_props(color=mat_text)

        self.canvas_preview.draw_idle()

        for w in self.norm_cards_container.winfo_children():
            w.destroy()

        for label_text, (w_stat, p_val, es_normal, n_len, nunique) in norm_card_items:
            row_frame = ctk.CTkFrame(self.norm_cards_container, fg_color="transparent", height=42)
            row_frame.pack(fill="x", padx=12, pady=4)

            ctk.CTkLabel(
                row_frame, text=f"{label_text} · Shapiro-Wilk",
                font=ctk.CTkFont(family=self.current_ui_font, size=13, weight="bold"), text_color=C_TEXT
            ).pack(side="left", padx=6)

            if nunique <= 1:
                badge_txt = "Constante"
                badge_col = C_WARNING
                stats_txt = "Varianza nula"
            elif n_len < 3:
                badge_txt = "n < 3"
                badge_col = C_WARNING
                stats_txt = "Muestra insuficiente"
            else:
                badge_txt = "Normal" if es_normal else "No normal"
                badge_col = C_SUCCESS if es_normal else C_WARNING
                p_disp = f"{p_val:.4f}" if p_val >= 0.001 else "< 0,001"
                stats_txt = f"W = {w_stat:.2f}   p = {p_disp}".replace(".", ",")

            badge = ctk.CTkLabel(
                row_frame, text=badge_txt, font=ctk.CTkFont(family=self.current_ui_font, size=12, weight="bold"),
                text_color=badge_col, fg_color=C_CARD, corner_radius=6, width=90, height=26
            )
            badge.pack(side="right", padx=6)

            ctk.CTkLabel(
                row_frame, text=stats_txt,
                font=ctk.CTkFont(family="Consolas", size=13), text_color=C_TEXT_MUTED
            ).pack(side="right", padx=24)

            sep = ctk.CTkFrame(self.norm_cards_container, height=1, fg_color=C_BORDER)
            sep.pack(fill="x", padx=12)

        numeric_cols = self.df.select_dtypes(include=[np.number]).columns.tolist()

        self.combo_plot_var.configure(values=numeric_cols)
        self.combo_plot_var_y.configure(values=["(ninguna)"] + numeric_cols)
        if numeric_cols and self.combo_plot_var.get() not in numeric_cols:
            self.combo_plot_var.set(numeric_cols[0])
            self.render_selected_plot()

        self.combo_math_var.configure(values=numeric_cols)
        if numeric_cols and self.combo_math_var.get() not in numeric_cols:
            self.combo_math_var.set(numeric_cols[0])
        self._render_math_formula()

        self._update_inf_selectors()
        self.compute_biodiversity_analysis()

    # -------------------------------------------------------------------------
    # SUITE DE INFERENCIA ESTADÍSTICA ROBUSTA
    # -------------------------------------------------------------------------
    def _update_inf_selectors(self):
        if self.df is None:
            return
        test_mode = self.combo_inf_test.get()
        all_cols = self.df.columns.tolist()
        numeric_cols = self.df.select_dtypes(include=[np.number]).columns.tolist()
        cat_cols = [c for c in all_cols if not pd.api.types.is_numeric_dtype(self.df[c]) or self.df[c].nunique() <= 12]

        if "t-Student" in test_mode:
            self.lbl_inf_v1.configure(text="Var Continua:")
            self.lbl_inf_v2.configure(text="Factor (2 niveles):")
            self.combo_inf_var1.configure(values=numeric_cols)
            self.combo_inf_var2.configure(values=cat_cols)
            if numeric_cols: self.combo_inf_var1.set(numeric_cols[0])
            if cat_cols: self.combo_inf_var2.set(cat_cols[0])
        else:
            self.lbl_inf_v1.configure(text="Factor 1 (Categoría):")
            self.lbl_inf_v2.configure(text="Factor 2 (Categoría):")
            self.combo_inf_var1.configure(values=cat_cols)
            self.combo_inf_var2.configure(values=cat_cols)
            if len(cat_cols) > 0: self.combo_inf_var1.set(cat_cols[0])
            if len(cat_cols) > 1: self.combo_inf_var2.set(cat_cols[1])

    def compute_inference_test(self):
        if self.df is None:
            messagebox.showwarning("Atención", "Carga primero un dataset para ejecutar pruebas inferenciales.")
            return

        test_mode = self.combo_inf_test.get()
        v1 = self.combo_inf_var1.get()
        v2 = self.combo_inf_var2.get()
        use_comma = self.sw_comma.get() == 1
        alpha_threshold = float(self.combo_alpha.get())

        def fmt(n: float, dec: int = 3) -> str:
            txt = f"{n:.{dec}f}"
            return txt.replace(".", ",") if use_comma else txt

        out = [
            "=" * 86,
            f" REPORTE DE INFERENCIA BIOESTADÍSTICA BIOEVO | {test_mode.upper()}",
            "=" * 86
        ]

        try:
            if "t-Student" in test_mode:
                if not pd.api.types.is_numeric_dtype(self.df[v1]):
                    self.txt_inference.delete("1.0", "end")
                    self.txt_inference.insert("1.0", f"Error metodológico: La variable dependiente '{v1}' debe ser cuantitativa continua.")
                    return

                groups = self.df[v2].dropna().unique()
                if len(groups) != 2:
                    self.txt_inference.delete("1.0", "end")
                    self.txt_inference.insert(
                        "1.0",
                        f"Error de factor: La variable '{v2}' posee {len(groups)} niveles.\n"
                        f"La prueba t de dos muestras independientes exige exactamente 2 tratamientos.\n"
                        f"Niveles hallados: {list(groups)}"
                    )
                    return

                g1_data = self.df[self.df[v2] == groups[0]][v1].dropna()
                g2_data = self.df[self.df[v2] == groups[1]][v1].dropna()

                t_stat_std, p_val_std = stats.ttest_ind(g1_data, g2_data, equal_var=True)
                t_stat_welch, p_val_welch = stats.ttest_ind(g1_data, g2_data, equal_var=False)

                df_std = len(g1_data) + len(g2_data) - 2
                conclusion = "Diferencia estadísticamente significativa" if p_val_std < alpha_threshold else "No se detectaron diferencias significativas"

                out.append(f"Variable de respuesta:  {v1}")
                out.append(f"Factor de agrupación:   {v2} ('{groups[0]}' vs '{groups[1]}')")
                out.append(f"Tamaño muestral:        n_A = {len(g1_data)}, n_B = {len(g2_data)}")
                out.append(f"Medias observadas:      Media_A = {fmt(g1_data.mean())}, Media_B = {fmt(g2_data.mean())}")
                out.append("-" * 86)
                out.append(f"1. Prueba t Clásica (Homocedasticidad / Varianzas iguales):")
                out.append(f"   t = {fmt(t_stat_std)} | Grados de libertad (df) = {df_std} | p-valor = {fmt(p_val_std, 4)}")
                out.append(f"2. Prueba t de Welch (Robusta ante heterocedasticidad):")
                out.append(f"   t = {fmt(t_stat_welch)} | p-valor = {fmt(p_val_welch, 4)}")
                out.append("-" * 86)
                out.append(f"Dictamen estadístico (alfa = {fmt(alpha_threshold, 2)}): {conclusion} (H0: Medias idénticas).")

            else:
                if v1 == v2:
                    self.txt_inference.delete("1.0", "end")
                    self.txt_inference.insert("1.0", "Error: Selecciona dos variables o factores distintos para la tabla de contingencia.")
                    return

                if self.df[v1].nunique() > 20 or self.df[v2].nunique() > 20:
                    self.txt_inference.delete("1.0", "end")
                    self.txt_inference.insert(
                        "1.0",
                        f"Error Metodológico de Chi-cuadrado (χ²):\n"
                        f"Las variables seleccionadas poseen cardinalidad continua excesiva ({v1}: {self.df[v1].nunique()} valores únicos, {v2}: {self.df[v2].nunique()}).\n\n"
                        f"Razón: Chi-cuadrado no es aplicable sobre variables numéricas continuas con decimales, "
                        f"ya que produce una matriz dispersa de ceros y unos sin potencia estadística (Regla de Cochran violada).\n"
                        f"Solución: Selecciona factores cualitativos, tratamientos o variables discretizadas."
                    )
                    return

                ct = pd.crosstab(self.df[v1], self.df[v2])
                chi2_stat, p_val, dof, expected = stats.chi2_contingency(ct)

                low_exp = (expected < 5).sum()
                pct_low_exp = (low_exp / expected.size) * 100
                cochran_ok = pct_low_exp <= 20.0 and (expected >= 1.0).all()

                conclusion = "Asociación estadísticamente significativa" if p_val < alpha_threshold else "Variables independientes / Sin asociación"

                out.append(f"Tabla de Contingencia Cruzada: '{v1}' × '{v2}'")
                out.append("-" * 86)
                out.append("FRECUENCIAS OBSERVADAS (O):")
                out.append(ct.to_string())
                out.append("-" * 86)
                out.append(f"Estadístico Chi-cuadrado (Chi2): {fmt(chi2_stat, 3)}")
                out.append(f"Grados de libertad (df):         {dof}")
                out.append(f"Valor p:                         {fmt(p_val, 4)}")
                out.append(f"Criterio de Cochran:             {'Válido (<20% celdas esperadas < 5)' if cochran_ok else f'Precaución ({fmt(pct_low_exp, 1)}% celdas esperadas < 5)'}")
                out.append("-" * 86)
                out.append(f"Dictamen estadístico (alfa = {fmt(alpha_threshold, 2)}): {conclusion} (H0: Independencia entre factores).")

            self.txt_inference.delete("1.0", "end")
            self.txt_inference.insert("1.0", "\n".join(out))

        except Exception as e:
            self.txt_inference.delete("1.0", "end")
            self.txt_inference.insert("1.0", f"Error en cómputo inferencial: {e}")

    # -------------------------------------------------------------------------
    # SUITE DE GRÁFICAS ANALÍTICAS (CON CORRECCIÓN VERT -> ORIENTATION)
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
        alpha_threshold = float(self.combo_alpha.get())

        es_normal = True
        if len(s_x) >= 3 and s_x.nunique() > 1:
            _, p_val = stats.shapiro(s_x[:5000])
            es_normal = p_val >= alpha_threshold
        else:
            p_val = 1.0

        if "Auto" in mode:
            plot_to_run = "Histograma + KDE" if es_normal else "Boxplot + Jitter"
            self.lbl_plot_sug.configure(text=f"Sugerencia analítica: {'Normal' if es_normal else 'No normal'} (p={p_val:.4f}, α={alpha_threshold})")
        else:
            plot_to_run = mode

        is_dark = self.current_theme_mode.lower() == "dark"
        mat_bg = "#161b22" if is_dark else "#ffffff"
        mat_text = "#e6edf3" if is_dark else "#1f2328"
        mat_border = "#30363d" if is_dark else "#d0d7de"
        mat_card = "#21262d" if is_dark else "#eaeef2"

        self.fig_analytics.clear()
        ax = self.fig_analytics.add_subplot(111)
        ax.set_facecolor(mat_bg)

        ax.tick_params(colors=mat_text, labelsize=9)
        for spine in ax.spines.values():
            spine.set_color(mat_border)

        # CORRECCIÓN DE DEPRECATION: orientación 'vertical' en lugar de vert=True
        if plot_to_run == "Boxplot + Jitter":
            bp = ax.boxplot(s_x, patch_artist=True, orientation="vertical", widths=0.35, showfliers=False)
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
            ax.set_title(f"Boxplot con Jitter: {var_x}", color=mat_text, weight="bold")

        elif plot_to_run == "Violin Plot":
            v_parts = ax.violinplot(s_x, showmeans=False, showmedians=True)
            for pc in v_parts["bodies"]:
                pc.set_facecolor(palette["accent"])
                pc.set_edgecolor(palette["primary"])
                pc.set_alpha(0.65)
            v_parts["cmedians"].set_color(palette["highlight"])
            ax.set_xticks([1])
            ax.set_xticklabels([var_x])
            ax.set_title(f"Violin Plot: {var_x}", color=mat_text, weight="bold")

        elif plot_to_run == "Dot Plot + SEM":
            m_val = s_x.mean()
            sem_val = s_x.std(ddof=1) / np.sqrt(len(s_x)) if len(s_x) > 1 else 0.0
            jitter = np.random.normal(1, 0.05, size=len(s_x))
            ax.scatter(jitter, s_x, color=palette["accent"], alpha=0.45, s=20)
            ax.errorbar([1], [m_val], yerr=[sem_val], fmt="o", color="#d1242f" if not is_dark else "#f85149", elinewidth=2.5, capsize=6, label=r"$\bar{x} \pm \mathrm{SEM}$")
            ax.set_xticks([1])
            ax.set_xticklabels([var_x])
            ax.set_title(f"Dot Plot con Error Estándar: {var_x}", color=mat_text, weight="bold")
            ax.legend(facecolor=mat_card, edgecolor=mat_border, fontsize=9)

        elif plot_to_run == "Histograma + KDE":
            n_bins = max(5, int(np.sqrt(len(s_x))))
            ax.hist(s_x, bins=n_bins, density=True, color=palette["primary"], alpha=0.5, edgecolor=palette["accent"])
            mu, sigma = s_x.mean(), s_x.std(ddof=1) if len(s_x) > 1 else 1.0
            x_line = np.linspace(s_x.min(), s_x.max(), 200)
            y_line = stats.norm.pdf(x_line, mu, sigma)
            ax.plot(x_line, y_line, color=palette["highlight"], linewidth=2, label="Ajuste Normal")
            ax.set_title(f"Histograma y Curva Normal: {var_x}", color=mat_text, weight="bold")
            ax.legend(facecolor=mat_card, edgecolor=mat_border, fontsize=9)

        elif plot_to_run == "Q-Q Plot Normal":
            (osm, osr), (slope, intercept, r) = stats.probplot(s_x, dist="norm")
            ax.scatter(osm, osr, color=palette["accent"], alpha=0.7, s=25)
            ax.plot(osm, slope * np.array(osm) + intercept, color="#d1242f" if not is_dark else "#f85149", linewidth=1.8, label=f"R² = {r**2:.3f}")
            ax.set_title(f"Q-Q Plot Normal: {var_x}", color=mat_text, weight="bold")
            ax.set_xlabel("Cuantiles Teóricos")
            ax.set_ylabel("Cuantiles Muestrales")
            ax.legend(facecolor=mat_card, edgecolor=mat_border, fontsize=9)

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
            ax.set_title("Forest Plot: Intervalos de Confianza 95%", color=mat_text, weight="bold")

        elif plot_to_run == "Dispersión + Regresión":
            if var_y not in self.df.columns or var_y == "(ninguna)":
                ax.text(0.5, 0.5, "Selecciona una Variable Y válida en la barra superior", ha="center", va="center", color=palette["highlight"])
            else:
                paired = self.df[[var_x, var_y]].dropna()
                ax.scatter(paired[var_x], paired[var_y], color=palette["accent"], alpha=0.7, s=30)
                if len(paired) > 2:
                    slope, intercept, r_val, _, _ = stats.linregress(paired[var_x], paired[var_y])
                    x_vals = np.linspace(paired[var_x].min(), paired[var_x].max(), 100)
                    ax.plot(x_vals, slope * x_vals + intercept, color="#d1242f" if not is_dark else "#f85149", linewidth=2, label=f"R² = {r_val**2:.3f}")
                    ax.legend(facecolor=mat_card, edgecolor=mat_border, fontsize=9)
                ax.set_xlabel(var_x)
                ax.set_ylabel(var_y)
                ax.set_title(f"Dispersión y Regresión: {var_x} vs {var_y}", color=mat_text, weight="bold")

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
                ax.set_title("Matriz de Correlación de Pearson", color=mat_text, pad=20, weight="bold")

        elif plot_to_run == "Curva Rango-Abundancia (Whittaker)":
            selected_vars = [col for col, cb in self.var_checkboxes.items() if cb.get() == 1]
            colors = [palette["accent"], palette["highlight"], palette["primary"], "#f0883e", "#a371f7"]
            for idx, col in enumerate(selected_vars[:5]):
                pos = self.df[col].dropna()
                pos = pos[pos > 0].sort_values(ascending=False)
                if len(pos) > 0:
                    rel_ab = pos / pos.sum()
                    ranks = np.arange(1, len(rel_ab) + 1)
                    ax.plot(ranks, np.log10(rel_ab), marker="o", linewidth=2, markersize=5, color=colors[idx % len(colors)], label=col)
            ax.set_title("Curvas de Rango-Abundancia (Diagrama de Whittaker)", color=mat_text, weight="bold")
            ax.set_xlabel("Rango de Especie / Unidad")
            ax.set_ylabel(r"Abundancia Relativa ($\log_{10} p_i$)")
            ax.legend(facecolor=mat_card, edgecolor=mat_border, fontsize=9)

        elif plot_to_run == "Perfil Diversidad Alfa (H', 1-D, J')":
            selected_vars = [col for col, cb in self.var_checkboxes.items() if cb.get() == 1]
            h_vals, d_vals, j_vals = [], [], []
            for col in selected_vars:
                res = compute_alpha_diversity_vector(self.df[col])
                h_vals.append(res["H"])
                d_vals.append(res["1_D"])
                j_vals.append(res["J"])

            x = np.arange(len(selected_vars))
            w = 0.26
            ax.bar(x - w, h_vals, width=w, color=palette["primary"], label="Shannon (H')")
            ax.bar(x, d_vals, width=w, color=palette["accent"], label="Simpson (1-D)")
            ax.bar(x + w, j_vals, width=w, color=palette["highlight"], label="Pielou (J')")
            ax.set_xticks(x)
            ax.set_xticklabels(selected_vars, rotation=20, ha="right")
            ax.set_title("Comparación de Índices de Diversidad Alfa (α)", color=mat_text, weight="bold")
            ax.legend(facecolor=mat_card, edgecolor=mat_border, fontsize=9)

        elif plot_to_run == "Heatmap Diversidad Beta (Bray-Curtis)":
            selected_vars = [col for col, cb in self.var_checkboxes.items() if cb.get() == 1]
            if len(selected_vars) < 2:
                ax.text(0.5, 0.5, "Selecciona al menos 2 variables en el panel lateral para la matriz Beta", ha="center", va="center")
            else:
                b_df = compute_beta_diversity_matrix(self.df[selected_vars], "Bray-Curtis")
                cax = ax.matshow(b_df.values, cmap="viridis", vmin=0, vmax=1)
                self.fig_analytics.colorbar(cax, ax=ax, fraction=0.046, pad=0.04)
                ax.set_xticks(range(len(selected_vars)))
                ax.set_yticks(range(len(selected_vars)))
                ax.set_xticklabels(selected_vars, rotation=45, ha="left")
                ax.set_yticklabels(selected_vars)
                for i in range(len(selected_vars)):
                    for j in range(len(selected_vars)):
                        ax.text(j, i, f"{b_df.iloc[i, j]:.2f}", ha="center", va="center", color="white", fontsize=8.5, weight="bold")
                ax.set_title("Matriz de Disimilitud Beta (Bray-Curtis)", color=mat_text, pad=20, weight="bold")

        if use_log and plot_to_run not in ("Q-Q Plot Normal", "Heatmap Correlación", "Forest Plot (IC 95%)", "Curva Rango-Abundancia (Whittaker)", "Heatmap Diversidad Beta (Bray-Curtis)"):
            ax.set_yscale("log")

        ax.grid(True, linestyle="--", alpha=0.15, color=mat_border)
        self.fig_analytics.tight_layout()
        self.canvas_analytics.draw_idle()

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
                "Creator": "BioEvo LabStats Formatter v1.1.0-beta.2",
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
        std_suffix = self.seg_format.get().lower().replace(" ", "")
        default_name = f"{base}_{std_suffix}_{timestamp}.tex"

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
        if self.df is None:
            messagebox.showwarning("Atención", "No hay datos cargados para exportar un proyecto.")
            return

        project_state = {
            "version": "1.1.0-beta.2",
            "source_file": self.current_filepath,
            "created_at": datetime.now().isoformat(),
            "language": self.current_lang,
            "theme": self.current_theme_mode,
            "ui_font": self.current_ui_font,
            "standard": self.seg_format.get(),
            "group_by": self.combo_group.get(),
            "alpha": self.combo_alpha.get(),
            "margin": self.combo_margin.get(),
            "landscape": self.sw_landscape.get(),
            "font_size": self.combo_font.get(),
            "tabcolsep": self.slider_tabcol.get(),
            "arraystretch": self.slider_stretch.get(),
            "switches": {
                "strict_norm": self.sw_strict_norm.get(),
                "resizebox": self.sw_resize.get(),
                "linespace": self.sw_linespace.get(),
                "comma": self.sw_comma.get()
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

    def load_project_json(self):
        path = filedialog.askopenfilename(
            filetypes=[("Proyecto BioEvo", "*.bioevo"), ("Todos los archivos", "*.*")]
        )
        if not path:
            return

        try:
            with open(path, "r", encoding="utf-8") as f:
                state = json.load(f)

            source_csv = state.get("source_file", "")
            if source_csv and os.path.exists(source_csv):
                df_loaded, meta = read_delimited_robust(source_csv)
                self.df = df_loaded
                self.current_filepath = source_csv
                self.current_meta = meta
                self._populate_variables()
                self._populate_preview()
            else:
                messagebox.showwarning("Aviso", f"El archivo original de datos no se encontró en la ruta:\n{source_csv}")

            if "language" in state:
                self.change_language(state["language"])
            if "theme" in state:
                self.change_appearance_mode(state["theme"])
            if "ui_font" in state:
                self.change_ui_font(state["ui_font"])
            if "standard" in state:
                self.seg_format.set(state["standard"])
            if "group_by" in state and state["group_by"] in self.combo_group.cget("values"):
                self.combo_group.set(state["group_by"])
            if "alpha" in state:
                self.combo_alpha.set(state["alpha"])
            if "margin" in state:
                self.combo_margin.set(state["margin"])
            if "landscape" in state:
                self.sw_landscape.select() if state["landscape"] else self.sw_landscape.deselect()
            if "font_size" in state:
                self.combo_font.set(state["font_size"])
            if "tabcolsep" in state:
                self.slider_tabcol.set(state["tabcolsep"])
                self.lbl_tabcol.configure(text=f"Espaciado (\\tabcolsep): {int(state['tabcolsep'])} pt")
            if "arraystretch" in state:
                self.slider_stretch.set(state["arraystretch"])
                self.lbl_stretch.configure(text=f"Interlineado (\\arraystretch): {state['arraystretch']:.2f}")

            switches = state.get("switches", {})
            self.sw_strict_norm.select() if switches.get("strict_norm", False) else self.sw_strict_norm.deselect()
            self.sw_resize.select() if switches.get("resizebox", True) else self.sw_resize.deselect()
            self.sw_linespace.select() if switches.get("linespace", False) else self.sw_linespace.deselect()
            self.sw_comma.select() if switches.get("comma", True) else self.sw_comma.deselect()

            active_keys = set(state.get("active_metrics", []))
            for m, sw in self.stat_switches.items():
                if m.id_key in active_keys:
                    sw.select()
                else:
                    sw.deselect()

            sel_vars = set(state.get("selected_vars", []))
            for v, cb in self.var_checkboxes.items():
                if v in sel_vars:
                    cb.select()
                else:
                    cb.deselect()

            self.btn_copy.configure(state="normal")
            self.btn_save_tex.configure(state="normal")
            self.trigger_analysis_thread()
            messagebox.showinfo("Proyecto Restaurado", f"Sesión cargada exitosamente desde:\n{os.path.basename(path)}")

        except Exception as e:
            messagebox.showerror("Error", f"Fallo al abrir el archivo de proyecto: {e}")

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
        self.canvas_preview.draw_idle()

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


if __name__ == "__main__":
    app = LabStatsApp()
    app.mainloop()