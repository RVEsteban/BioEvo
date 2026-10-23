"""
Suite de Pruebas Unitarias para LabStats Core
Ejecutar con: pytest tests/test_core.py -v
"""

import pytest
import pandas as pd
import numpy as np
from main import (
    sanitize_latex,
    validate_latex_syntax,
    coerce_numeric_columns,
    MeanStdMetric,
    MedianIQRMetric,
    SEMMetric,
    CI95Metric,
    SampleSizeMetric
)

def fmt_helper(n: float) -> str:
    return f"{n:.2f}".replace(".", ",")

def test_sanitize_latex():
    raw_str = "peso_mg & concentracion% $calc# {test}"
    sanitized = sanitize_latex(raw_str)
    assert r"\_" in sanitized
    assert r"\&" in sanitized
    assert r"\%" in sanitized
    assert r"\$" in sanitized
    assert r"\#" in sanitized

def test_validate_latex_syntax_ok():
    valid_code = r"\begin{table}\begin{tabular}{cc} 1 & 2 \\\end{tabular}\end{table}"
    is_valid, _ = validate_latex_syntax(valid_code)
    assert is_valid is True

def test_validate_latex_syntax_fail():
    invalid_code = r"\begin{table}\begin{tabular}{cc} 1 & 2 \\\end{tabular}"
    is_valid, reason = validate_latex_syntax(invalid_code)
    assert is_valid is False
    assert "Desbalance" in reason

def test_coerce_numeric_columns():
    df = pd.DataFrame({
        "texto": ["a", "b", "c"],
        "coma_nums": ["1,25", "3,40", "5,12"],
        "punto_nums": ["1.25", "3.40", "5.12"]
    })
    df_coerced = coerce_numeric_columns(df)
    assert np.issubdtype(df_coerced["coma_nums"].dtype, np.floating)
    assert np.issubdtype(df_coerced["punto_nums"].dtype, np.floating)
    assert df_coerced["texto"].dtype == object

def test_mean_std_metric():
    series = pd.Series([10.0, 20.0, 30.0])
    metric = MeanStdMetric()
    res = metric.compute(series, fmt_helper)
    assert "20,00" in res
    assert "10,00" in res
    assert r"\pm" in res

def test_sem_and_ci95_metric():
    series = pd.Series([2.0, 4.0, 6.0, 8.0, 10.0])
    sem = SEMMetric()
    ci = CI95Metric()
    assert sem.compute(series, fmt_helper) != "---"
    assert "--" in ci.compute(series, fmt_helper)

def test_edge_case_single_sample():
    series = pd.Series([42.0])
    mean_metric = MeanStdMetric()
    sem_metric = SEMMetric()
    assert r"\pm 0,00" in mean_metric.compute(series, fmt_helper)
    assert sem_metric.compute(series, fmt_helper) == "---"
