# LabStats Formatter

**LabStats Formatter** es una utilidad local diseñada para transformar conjuntos de datos experimentales, análisis de varianza (ANOVA), pruebas $t$ de Student y métricas bioestadísticas en tablas científicas maquetadas bajo el estándar de calidad tipográfica de **LaTeX (`booktabs`)**.

## 🎯 Problema que Resuelve

El traslado manual de resultados desde hojas de cálculo o entornos estadísticos a tablas compatibles con revistas científicas suele ser propenso a errores tipográficos, pérdida de decimales significativos y formatos no estandarizados. LabStats automatiza la limpieza, el cálculo descriptivo y la generación del código LaTeX listo para ser insertado mediante `\input{tabla.tex}`.

## ⚙️ Capacidades

* **Generación Tipográfica Estricta:** Salida nativa utilizando los entornos `table`, `threeparttable` y macros del paquete `booktabs` (`\toprule`, `\midrule`, `\bottomrule`).

* **Formateo de Precisión Científica:**

  * Notación estadística formal ($p$-valores formateados según estándares APA/Vancouver: ej. $p < 0.001$, $p = 0.042$).

  * Manejo estandarizado de medidas de tendencia central y dispersión ($\bar{x} \pm \text{DE}$, Mediana \[RIC\]).

* **Alineación Decimal Automática:** Compatibilidad con paquetes de alineación tabular como `siunitx`.

* **Procesamiento Offline:** Todo el cálculo numérico se efectúa de manera local mediante NumPy, SciPy y pandas.

## 📊 Ejemplo de Flujo de Trabajo

### 1. Entrada de Datos (CSV / DataFrame)

```
Tratamiento,Muestra_N,Media,Desv_Estandar,P_Valor
Control,30,12.45,1.20,-
Compuesto_A,30,18.92,1.85,0.0024
Compuesto_B,30,14.10,1.15,0.1180

```

### 2. Salida Generada por LabStats Formatter

```
\begin{table}[htbp]
  \centering
  \caption{Parámetros biométricos observados según grupo de tratamiento.}
  \label{tab:labstats_biometric}
  \begin{tabular}{lcccc}
    \toprule
    Tratamiento & $n$ & Media & $\pm$ DE & $p$-valor \\
    \midrule
    Control     & 30  & 12.45 & 1.20     & — \\
    Compuesto A & 30  & 18.92 & 1.85     & $0.002^{**}$ \\
    Compuesto B & 30  & 14.10 & 1.15     & $0.118$ \\
    \bottomrule
  \end{tabular}
\end{table}

```

## 💻 Requisitos e Instalación

Para entornos de prueba locales:

```
# Clonar el repositorio
git clone https://github.com/RVEsteban/BioEvo.git

# Ingresar al directorio del módulo
cd BioEvo/labstats

# Crear un entorno virtual
python -m venv venv
source venv/bin/activate  # En Windows: .\venv\Scripts\activate

# Instalar dependencias base
pip install pandas numpy scipy

```

## 📌 Próximas Funcionalidades

* \[ \] Soporte para pruebas post-hoc (Tukey HSD, Bonferroni) con letras de significancia compartida ($a, b, c$).

* \[ \] Exportación simultánea a Markdown compatible con Typst y Quarto.

* \[ \] Interfaz gráfica minimalista para arrastrar y soltar archivos `.csv` / `.xlsx`.
