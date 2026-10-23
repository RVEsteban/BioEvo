"""
LabStats Formatter - Main GUI
Parte del ecosistema BioEvo Core.

Genera tablas descriptivas en sintaxis LaTeX (booktabs, estilo APA 7) a partir de
archivos CSV / TSV / TXT / XLSX. Todo el procesamiento es local.
"""

from __future__ import annotations

import re
import sys
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from tkinter import font as tkfont

import numpy as np
import pandas as pd

# Portapapeles: pyperclip es opcional; si no está, se usa el de Tkinter.
try:
    import pyperclip
    HAS_PYPERCLIP = True
except ImportError:
    HAS_PYPERCLIP = False


APP_TITLE = "BioEvo | LabStats Formatter"
DEFAULT_CAPTION = "Resumen estadístico de variables analizadas"
DEFAULT_LABEL = "tab:labstats_summary"
MISSING = "--"           # valor ausente en la tabla (seguro en LaTeX)
MAX_GROUP_LEVELS = 12    # máximo de niveles para ofrecer una columna como grupo


# ==========================================
# LECTURA DE DATOS
# ==========================================

_NUMERIC_RE = re.compile(r"^[-+]?\d+(?:[.,]\d+)?$")


def _read_delimited(path: Path) -> pd.DataFrame:
    """Lee un archivo delimitado probando codificaciones y separadores habituales."""
    last_error: Exception | None = None
    for encoding in ("utf-8-sig", "latin-1"):          # Excel en español suele guardar en latin-1
        fallback: pd.DataFrame | None = None
        for sep in (None, ";", "\t", ","):            # None = detección automática
            try:
                df = pd.read_csv(path, sep=sep, engine="python", encoding=encoding)
            except UnicodeDecodeError as err:
                last_error = err
                break                                  # probar otra codificación
            except Exception as err:                   # separador incorrecto, filas irregulares...
                last_error = err
                continue
            if df.shape[1] > 1:
                return df
            fallback = df if fallback is None else fallback
        else:
            if fallback is not None:                   # archivo legítimo de una sola columna
                return fallback
    raise ValueError(f"No se pudo interpretar el archivo: {last_error}")


def coerce_numeric_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Convierte a número las columnas de texto que sólo contienen valores numéricos ('12,4' -> 12.4)."""
    out = df.copy()
    for col in out.columns:
        series = out[col]
        if pd.api.types.is_numeric_dtype(series):      # incluye bool; ya es numérica
            continue
        text = series.astype("string").str.strip()
        valid = text.dropna()
        valid = valid[valid != ""]
        if len(valid) and valid.str.match(_NUMERIC_RE).all():
            out[col] = pd.to_numeric(text.str.replace(",", ".", regex=False), errors="coerce")
    return out


def load_table(filepath: str | Path) -> pd.DataFrame:
    """Carga CSV, TSV, TXT o Excel y normaliza nombres de columnas y tipos numéricos."""
    path = Path(filepath)
    if path.suffix.lower() in {".xlsx", ".xls"}:
        df = pd.read_excel(path)                       # requiere openpyxl (.xlsx)
    else:
        df = _read_delimited(path)
    df.columns = [str(c).strip() for c in df.columns]
    df = df.dropna(how="all").dropna(axis=1, how="all")
    if df.empty:
        raise ValueError("El archivo no contiene datos.")
    return coerce_numeric_columns(df)


def numeric_columns(df: pd.DataFrame) -> list[str]:
    return [c for c in df.columns
            if pd.api.types.is_numeric_dtype(df[c]) and not pd.api.types.is_bool_dtype(df[c])]


def group_candidates(df: pd.DataFrame) -> list[str]:
    """Columnas con pocos niveles distintos, aptas para agrupar (sexo, tratamiento, grupo...)."""
    def is_categorical(col: str) -> bool:
        series = df[col].dropna()
        if not 2 <= series.nunique() <= MAX_GROUP_LEVELS:
            return False
        if col in numeric_columns(df):                  # numéricas: sólo códigos enteros (0/1, 1/2/3...)
            return bool((series % 1 == 0).all())
        return True

    return [c for c in df.columns if is_categorical(c)]


# ==========================================
# ESTADÍSTICA Y MOTOR LATEX
# ==========================================

@dataclass
class StatsOptions:
    decimals: int = 2
    decimal_comma: bool = True
    mean_sd: bool = True
    median_iqr: bool = True
    min_max: bool = False
    n: bool = True
    missing: bool = False

    def any_stat(self) -> bool:
        return any((self.mean_sd, self.median_iqr, self.min_max, self.n, self.missing))


_LATEX_ESCAPES = {
    "\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#",
    "_": r"\_", "{": r"\{", "}": r"\}", "~": r"\textasciitilde{}", "^": r"\textasciicircum{}",
}


def escape_latex(text: object) -> str:
    """Escapa caracteres especiales de LaTeX en texto del usuario (nombres de variables, títulos)."""
    return "".join(_LATEX_ESCAPES.get(ch, ch) for ch in str(text))


def make_label(text: str) -> str:
    """Etiqueta LaTeX segura (letras, números, ':', '_' y '-')."""
    cleaned = re.sub(r"[^A-Za-z0-9:_-]+", "_", text.strip()).strip("_")
    return cleaned or DEFAULT_LABEL


def format_number(value: float, decimals: int, decimal_comma: bool) -> str:
    """Formatea un número; los negativos usan '$-$' para obtener un signo menos tipográfico."""
    if value is None or pd.isna(value):
        return MISSING
    text = f"{abs(value):.{decimals}f}"
    negative = value < 0 and float(text) != 0          # evita '-0,00'
    if decimal_comma:
        text = text.replace(".", ",")
    return f"$-${text}" if negative else text


def _describe(series: pd.Series, opt: StatsOptions, total_rows: int) -> dict[str, str]:
    """Calcula los estadísticos pedidos para una serie."""
    fmt = lambda v: format_number(v, opt.decimals, opt.decimal_comma)  # noqa: E731
    s = series.dropna()
    n = len(s)
    out: dict[str, str] = {}

    if opt.mean_sd:
        sd = s.std(ddof=1) if n > 1 else np.nan        # con n=1 la DE no está definida
        out[r"Media $\pm$ DE"] = f"{fmt(s.mean())} $\\pm$ {fmt(sd)}" if n else MISSING
    if opt.median_iqr:
        out["Mediana [IQR]"] = (
            f"{fmt(s.median())} [{fmt(s.quantile(.25))} -- {fmt(s.quantile(.75))}]" if n else MISSING
        )
    if opt.min_max:
        out[r"Mín -- Máx"] = f"{fmt(s.min())} -- {fmt(s.max())}" if n else MISSING
    if opt.n:
        out["$n$"] = str(n)
    if opt.missing:
        out["Faltantes"] = str(total_rows - n)
    return out


def _group_label(value: object) -> str:
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def compute_summary(
    df: pd.DataFrame,
    columns: list[str],
    options: StatsOptions,
    group_by: str | None = None,
) -> pd.DataFrame:
    """Resumen descriptivo por variable (y opcionalmente por grupo)."""
    if not columns:
        raise ValueError("Selecciona al menos una variable numérica.")
    if not options.any_stat():
        raise ValueError("Activa al menos un estadístico.")

    rows: list[dict[str, str]] = []
    for col in columns:
        if group_by:
            for level, sub in df.groupby(group_by, sort=True, dropna=True):
                row = {"Variable": escape_latex(col) if not rows or rows[-1].get("_var") != col else "",
                       "Grupo": escape_latex(_group_label(level)), "_var": col}
                row.update(_describe(sub[col], options, len(sub)))
                rows.append(row)
        else:
            row = {"Variable": escape_latex(col)}
            row.update(_describe(df[col], options, len(df)))
            rows.append(row)

    summary = pd.DataFrame(rows)
    return summary.drop(columns="_var", errors="ignore")


def build_note(options: StatsOptions) -> str:
    """Nota al pie al estilo APA ('Nota.') con las abreviaturas usadas."""
    parts = []
    if options.mean_sd:
        parts.append("DE = desviación estándar")
    if options.median_iqr:
        parts.append(r"IQR = rango intercuartílico (P25 -- P75)")
    if options.n:
        parts.append(r"$n$ = observaciones válidas")
    return "; ".join(parts) + "." if parts else ""


def summary_to_latex(
    summary: pd.DataFrame,
    caption: str = DEFAULT_CAPTION,
    label: str = DEFAULT_LABEL,
    note: str | None = None,
    spaced_groups: bool = False,
) -> str:
    """Construye la tabla LaTeX con booktabs, sin líneas verticales."""
    left_cols = 2 if "Grupo" in summary.columns else 1
    col_spec = "l" * left_cols + "c" * (len(summary.columns) - left_cols)

    lines = [
        r"% Código generado por LabStats Formatter (BioEvo Core)",
        r"% Requiere \usepackage{booktabs} en el preámbulo de tu documento LaTeX.",
        r"\begin{table}[htbp]",
        r"  \centering",
        r"  \small",
        f"  \\caption{{{escape_latex(caption)}}}",
        f"  \\label{{{make_label(label)}}}",
        f"  \\begin{{tabular}}{{{col_spec}}}",
        r"    \toprule",
        "    " + " & ".join(summary.columns) + r" \\",
        r"    \midrule",
    ]

    for i, (_, row) in enumerate(summary.iterrows()):
        if spaced_groups and i > 0 and row.iloc[0] != "":
            lines.append(r"    \addlinespace")        # separa visualmente cada variable
        lines.append("    " + " & ".join(str(v) for v in row.values) + r" \\")

    lines += [r"    \bottomrule", r"  \end{tabular}"]
    if note:
        lines.append(r"  \par\smallskip{\footnotesize\raggedright\textit{Nota.} " + note + "}")
    lines.append(r"\end{table}")
    return "\n".join(lines)


# ==========================================
# INTERFAZ GRÁFICA (TKINTER)
# ==========================================

class LabStatsApp(tk.Tk):
    REFRESH_DELAY_MS = 250
    NO_GROUP = "(sin agrupar)"

    def __init__(self) -> None:
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1000x720")
        self.minsize(860, 640)

        self.df: pd.DataFrame | None = None
        self._filename = ""
        self._refresh_job: str | None = None
        self._flash_job: str | None = None
        self._status = ("Listo para cargar archivo.", "dim")

        self._init_style()
        self._init_vars()
        self._build_ui()
        self._bind_events()
        self._set_actions(False)

    # ---------- Configuración ----------

    def _init_style(self) -> None:
        self.style = ttk.Style(self)
        self.style.theme_use("clam")
        self.style.configure("Dim.TLabel", foreground="#666666")
        self.style.configure("Ok.TLabel", foreground="#0d652d")
        self.style.configure("Err.TLabel", foreground="#b3261e")

    def _init_vars(self) -> None:
        self.var_decimals = tk.IntVar(value=2)
        self.var_comma = tk.BooleanVar(value=True)
        self.var_mean_sd = tk.BooleanVar(value=True)
        self.var_median = tk.BooleanVar(value=True)
        self.var_minmax = tk.BooleanVar(value=False)
        self.var_n = tk.BooleanVar(value=True)
        self.var_missing = tk.BooleanVar(value=False)
        self.var_note = tk.BooleanVar(value=True)
        self.var_group = tk.StringVar(value=self.NO_GROUP)
        self.var_caption = tk.StringVar(value=DEFAULT_CAPTION)
        self.var_label = tk.StringVar(value=DEFAULT_LABEL)

    def _build_ui(self) -> None:
        self.columnconfigure(1, weight=1)
        self.rowconfigure(1, weight=1)

        # Barra de acciones
        bar = ttk.Frame(self, padding=(12, 10, 12, 6))
        bar.grid(row=0, column=0, columnspan=2, sticky="ew")
        self.btn_load = ttk.Button(bar, text="📂 Cargar archivo", command=self.load_file)
        self.btn_copy = ttk.Button(bar, text="📋 Copiar LaTeX", command=self.copy_to_clipboard)
        self.btn_save = ttk.Button(bar, text="💾 Guardar .tex", command=self.save_tex)
        self.btn_clear = ttk.Button(bar, text="Limpiar", command=self.clear_output)
        for b in (self.btn_load, self.btn_copy, self.btn_save, self.btn_clear):
            b.pack(side="left", padx=(0, 6))

        # Panel de opciones
        side = ttk.Frame(self, padding=(12, 0, 6, 8))
        side.grid(row=1, column=0, sticky="ns")

        vars_box = ttk.LabelFrame(side, text="Variables a analizar", padding=8)
        vars_box.pack(fill="x")
        list_frame = ttk.Frame(vars_box)
        list_frame.pack(fill="x")
        self.lst_cols = tk.Listbox(list_frame, selectmode="extended", exportselection=False,
                                   height=7, width=28, activestyle="none")
        sb = ttk.Scrollbar(list_frame, orient="vertical", command=self.lst_cols.yview)
        self.lst_cols.configure(yscrollcommand=sb.set)
        self.lst_cols.pack(side="left", fill="x", expand=True)
        sb.pack(side="right", fill="y")
        quick = ttk.Frame(vars_box)
        quick.pack(fill="x", pady=(6, 0))
        ttk.Button(quick, text="Todas", command=lambda: self._select_all(True)).pack(side="left")
        ttk.Button(quick, text="Ninguna", command=lambda: self._select_all(False)).pack(side="left", padx=6)

        group_box = ttk.LabelFrame(side, text="Agrupar por", padding=8)
        group_box.pack(fill="x", pady=(8, 0))
        self.cmb_group = ttk.Combobox(group_box, textvariable=self.var_group, state="readonly",
                                      values=[self.NO_GROUP])
        self.cmb_group.pack(fill="x")

        stats_box = ttk.LabelFrame(side, text="Estadísticos", padding=8)
        stats_box.pack(fill="x", pady=(8, 0))
        checks = [("Media ± DE", self.var_mean_sd), ("Mediana [IQR]", self.var_median),
                  ("Mín – Máx", self.var_minmax), ("n", self.var_n), ("Faltantes", self.var_missing)]
        for i, (text, var) in enumerate(checks):
            ttk.Checkbutton(stats_box, text=text, variable=var).grid(row=i // 2, column=i % 2, sticky="w", padx=(0, 10))

        fmt_box = ttk.LabelFrame(side, text="Formato", padding=8)
        fmt_box.pack(fill="x", pady=(8, 0))
        row = ttk.Frame(fmt_box)
        row.pack(fill="x")
        ttk.Label(row, text="Decimales").pack(side="left")
        ttk.Spinbox(row, from_=0, to=6, width=4, textvariable=self.var_decimals).pack(side="left", padx=6)
        ttk.Checkbutton(fmt_box, text="Coma decimal (,)", variable=self.var_comma).pack(anchor="w", pady=(4, 0))
        ttk.Checkbutton(fmt_box, text="Incluir nota al pie (APA)", variable=self.var_note).pack(anchor="w")

        tex_box = ttk.LabelFrame(side, text="Tabla LaTeX", padding=8)
        tex_box.pack(fill="x", pady=(8, 0))
        ttk.Label(tex_box, text="Título").pack(anchor="w")
        ttk.Entry(tex_box, textvariable=self.var_caption).pack(fill="x")
        ttk.Label(tex_box, text="Etiqueta (\\label)").pack(anchor="w", pady=(4, 0))
        ttk.Entry(tex_box, textvariable=self.var_label).pack(fill="x")

        # Editor LaTeX
        editor = ttk.Frame(self, padding=(6, 0, 12, 8))
        editor.grid(row=1, column=1, sticky="nsew")
        mono = tkfont.nametofont("TkFixedFont").copy()
        mono.configure(size=10)
        scroll_y = ttk.Scrollbar(editor, orient="vertical")
        scroll_x = ttk.Scrollbar(editor, orient="horizontal")
        self.txt_latex = tk.Text(editor, wrap="none", font=mono, undo=True,
                                 yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)
        scroll_y.config(command=self.txt_latex.yview)
        scroll_x.config(command=self.txt_latex.xview)
        scroll_y.pack(side="right", fill="y")
        scroll_x.pack(side="bottom", fill="x")
        self.txt_latex.pack(side="left", fill="both", expand=True)

        # Barra de estado
        self.lbl_status = ttk.Label(self, text=self._status[0], style="Dim.TLabel", padding=(12, 0, 12, 8))
        self.lbl_status.grid(row=2, column=0, columnspan=2, sticky="w")

    def _bind_events(self) -> None:
        for var in (self.var_decimals, self.var_comma, self.var_mean_sd, self.var_median, self.var_minmax,
                    self.var_n, self.var_missing, self.var_note, self.var_caption, self.var_label):
            var.trace_add("write", lambda *_: self._schedule_refresh())
        self.lst_cols.bind("<<ListboxSelect>>", lambda _e: self._schedule_refresh())
        self.cmb_group.bind("<<ComboboxSelected>>", self._on_group_change)
        self.bind_all("<Control-o>", lambda _e: self.load_file())
        self.bind_all("<Control-s>", lambda _e: self.save_tex())

    # ---------- Estado visual ----------

    def _set_status(self, text: str, kind: str = "dim") -> None:
        self._status = (text, kind)
        self.lbl_status.config(text=text, style=f"{kind.capitalize()}.TLabel")

    def _flash(self, text: str) -> None:
        """Mensaje temporal que luego restaura el estado anterior."""
        previous = self._status
        if self._flash_job:
            self.after_cancel(self._flash_job)
        self.lbl_status.config(text=text, style="Ok.TLabel")
        self._flash_job = self.after(2500, lambda: self._set_status(*previous))

    def _set_actions(self, enabled: bool) -> None:
        state = "normal" if enabled else "disabled"
        self.btn_copy.config(state=state)
        self.btn_save.config(state=state)

    # ---------- Lectura de opciones ----------

    def _read_options(self) -> StatsOptions:
        try:
            decimals = min(max(int(self.var_decimals.get()), 0), 6)
        except (tk.TclError, ValueError):               # campo vacío o texto mientras se escribe
            decimals = 2
        return StatsOptions(
            decimals=decimals,
            decimal_comma=self.var_comma.get(),
            mean_sd=self.var_mean_sd.get(),
            median_iqr=self.var_median.get(),
            min_max=self.var_minmax.get(),
            n=self.var_n.get(),
            missing=self.var_missing.get(),
        )

    def _group_column(self) -> str | None:
        value = self.var_group.get()
        return None if value == self.NO_GROUP else value

    def _selected_columns(self) -> list[str]:
        group = self._group_column()
        cols = [self.lst_cols.get(i) for i in self.lst_cols.curselection()]
        return [c for c in cols if c != group]

    def _select_all(self, state: bool) -> None:
        if state:
            self.lst_cols.selection_set(0, tk.END)
        else:
            self.lst_cols.selection_clear(0, tk.END)
        self._schedule_refresh()

    def _on_group_change(self, _event=None) -> None:
        group = self._group_column()
        if group:
            names = self.lst_cols.get(0, tk.END)
            if group in names:
                self.lst_cols.selection_clear(names.index(group))
        self._schedule_refresh()

    # ---------- Acciones ----------

    def load_file(self) -> None:
        path = filedialog.askopenfilename(
            title="Seleccionar tabla de datos",
            filetypes=[("Tablas de datos", "*.csv *.tsv *.txt *.xlsx *.xls"), ("Todos los archivos", "*.*")],
        )
        if not path:
            return
        try:
            df = load_table(path)
            if not numeric_columns(df):
                raise ValueError("El archivo no contiene columnas numéricas válidas para analizar.")
        except Exception as err:
            messagebox.showerror("Error al procesar", f"No se pudo analizar el archivo:\n{err}")
            self._set_status("Error al procesar archivo.", "err")
            return

        self.df = df
        self._filename = Path(path).name
        cols = numeric_columns(df)
        self.lst_cols.delete(0, tk.END)
        for c in cols:
            self.lst_cols.insert(tk.END, c)
        self.lst_cols.selection_set(0, tk.END)
        self.cmb_group.config(values=[self.NO_GROUP, *group_candidates(df)])
        self.var_group.set(self.NO_GROUP)
        self._refresh()

    def _schedule_refresh(self) -> None:
        """Agrupa cambios rápidos (p. ej. al escribir el título) en un solo recálculo."""
        if self.df is None:
            return
        if self._refresh_job:
            self.after_cancel(self._refresh_job)
        self._refresh_job = self.after(self.REFRESH_DELAY_MS, self._refresh)

    def _refresh(self) -> None:
        self._refresh_job = None
        if self.df is None:
            return
        options = self._read_options()
        group = self._group_column()
        columns = self._selected_columns()
        try:
            summary = compute_summary(self.df, columns, options, group)
        except ValueError as err:
            self._write_output("")
            self._set_actions(False)
            self._set_status(str(err), "err")
            return

        latex = summary_to_latex(
            summary,
            caption=self.var_caption.get().strip() or DEFAULT_CAPTION,
            label=self.var_label.get(),
            note=build_note(options) if self.var_note.get() else None,
            spaced_groups=group is not None,
        )
        self._write_output(latex)
        self._set_actions(True)
        extra = f" · por {group}" if group else ""
        self._set_status(
            f"Cargado: {self._filename} ({len(self.df)} filas) · {len(columns)} variable(s){extra}", "ok"
        )

    def _write_output(self, text: str) -> None:
        self.txt_latex.delete("1.0", tk.END)
        self.txt_latex.insert(tk.END, text)

    def _current_code(self) -> str:
        return self.txt_latex.get("1.0", tk.END).strip()

    def copy_to_clipboard(self) -> None:
        code = self._current_code()
        if not code:
            return
        copied = False
        if HAS_PYPERCLIP:
            try:
                pyperclip.copy(code)
                copied = True
            except pyperclip.PyperclipException:
                pass
        if not copied:
            self.clipboard_clear()
            self.clipboard_append(code)
            self.update()                               # conserva el contenido tras cerrar la app
        self._flash("¡Código LaTeX copiado al portapapeles!")

    def save_tex(self) -> None:
        code = self._current_code()
        if not code:
            return
        stem = Path(self._filename).stem if self._filename else "tabla"
        path = filedialog.asksaveasfilename(
            title="Guardar tabla LaTeX",
            defaultextension=".tex",
            initialfile=f"{stem}_tabla.tex",
            filetypes=[("Archivo LaTeX", "*.tex"), ("Todos los archivos", "*.*")],
        )
        if not path:
            return
        try:
            Path(path).write_text(code + "\n", encoding="utf-8")
        except OSError as err:
            messagebox.showerror("Error al guardar", str(err))
            return
        self._flash(f"Guardado: {Path(path).name}")

    def clear_output(self) -> None:
        self.df = None
        self._filename = ""
        self.lst_cols.delete(0, tk.END)
        self.cmb_group.config(values=[self.NO_GROUP])
        self.var_group.set(self.NO_GROUP)
        self._write_output("")
        self._set_actions(False)
        self._set_status("Listo para cargar archivo.", "dim")


def _enable_hidpi() -> None:
    """Evita interfaz borrosa en pantallas de alta resolución en Windows."""
    if sys.platform == "win32":
        try:
            from ctypes import windll
            windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass


if __name__ == "__main__":
    _enable_hidpi()
    LabStatsApp().mainloop()
