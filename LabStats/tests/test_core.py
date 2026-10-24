"""
Suite de Pruebas Unitarias para LabStats Core v1.0.0-rc.1
Ejecutar con: python -m pytest tests/test_core.py -v
"""

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import pytest
import pandas as pd
import numpy as np
from main import (
    sanitize_latex,
    validate_latex_syntax,
    read_delimited_robust,
    MeanStdMetric,
    SEMMetric,
    CI95Metric,
    MedianIQRMetric,
    SampleSizeMetric
)

def fmt_test(n: float, dec: int = 2) -> str:
    return f"{n:.{dec}f}".replace(".", ",")


def test_sanitize_latex_special_characters():
    raw_str = "peso_mg & concentracion% $calc# {test}"
    sanitized = sanitize_latex(raw_str)
    assert r"\_" in sanitized
    assert r"\&" in sanitized
    assert r"\%" in sanitized
    assert r"\$" in sanitized
    assert r"\#" in sanitized


def test_validate_latex_syntax_valid():
    valid_code = (
        r"\begin{table}"
        r"\begin{tabular}{cc}"
        r"  1 & 2 \\"
        r"\end{tabular}"
        r"\end{table}"
    )
    is_valid, _ = validate_latex_syntax(valid_code)
    assert is_valid is True


def test_validate_latex_syntax_mismatched_environments():
    invalid_code = r"\begin{table}\begin{tabular}{cc} 1 & 2 \\\end{tabular}"
    is_valid, reason = validate_latex_syntax(invalid_code)
    assert is_valid is False
    assert "Desbalance" in reason


def test_validate_latex_syntax_column_mismatch():
    invalid_code = (
        r"\begin{table}"
        r"\begin{tabular}{cc}"
        r"  1 & 2 & 3 \\"
        r"\end{tabular}"
        r"\end{table}"
    )
    is_valid, reason = validate_latex_syntax(invalid_code)
    assert is_valid is False
    assert "espera 2" in reason


def test_mean_std_metric():
    series = pd.Series([10.0, 20.0, 30.0])
    metric = MeanStdMetric()
    res = metric.compute(series, fmt_test)
    assert "20,00" in res
    assert "10,00" in res
    assert r"\pm" in res


def test_sem_and_ci95_precision():
    series = pd.Series([2.0, 4.0, 6.0, 8.0, 10.0])
    sem_metric = SEMMetric()
    ci_metric = CI95Metric()
    sem_res = sem_metric.compute(series, fmt_test)
    ci_res = ci_metric.compute(series, fmt_test)
    # SEM debe formatearse con 3 decimales
    assert len(sem_res.split(",")[1]) == 3
    assert "--" in ci_res


def test_edge_case_single_sample():
    series = pd.Series([42.0])
    mean_metric = MeanStdMetric()
    sem_metric = SEMMetric()
    res = mean_metric.compute(series, fmt_test)
    assert "42,00" in res
    assert "0,00" in res
    assert sem_metric.compute(series, fmt_test) == "---"


def test_read_delimited_sniffer_csv(tmp_path):
    csv_file = tmp_path / "test_data.csv"
    # Caracteres con tilde/ñ para forzar el byte Latin-1 incompatible con UTF-8 estricto
    content = "individuo;región;tamaño\nind1;Nariño;45,3\nind2;Pasto;48,9"
    csv_file.write_bytes(content.encode("latin-1"))
    
    df, meta = read_delimited_robust(str(csv_file))
    assert meta["delimiter"] == ";"
    assert meta["encoding"] in ("latin-1", "iso-8859-1", "cp1252")
    assert pd.api.types.is_float_dtype(df["tamaño"])
    assert len(df) == 2