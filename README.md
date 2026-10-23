# BioEvo Core

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![GitHub Pages](https://img.shields.io/badge/Landing_Page-Live-38bdf8)](https://rvesteban.github.io/BioEvo/)
[![Zero Telemetry](https://img.shields.io/badge/Telemetry-Zero_Cloud-3fb950.svg)](#principios-fundacionales)

**BioEvo Core** es un ecosistema de herramientas de software de computación local orientadas a investigación biológica, bioestadística y síntesis de literatura científica. Todas las aplicaciones están concebidas bajo el paradigma **local-first**: ejecución directa en la máquina del usuario, código auditable y cero telemetría externa.

---

## 🧭 Principios Fundacionales

1. **Ejecución Local Nativa (Zero-Cloud):** Ningún dato, manuscrito, conjunto de mediciones o resumen analizado sale del equipo del investigador. No existen llamadas a servidores opacos de inferencia ni almacenamiento en la nube.
2. **Modelos y Algoritmos Transparentes:** Empleo de motores de inteligencia artificial abiertos (Ollama, Hugging Face local) y scripts deterministas sin dependencias comerciales cautivas.
3. **Licenciamiento Abierto (MIT):** El código es público, auditable y modular, facilitando su revisión metodológica y su adopción en laboratorios e instituciones académicas.

---

## 📦 Estructura del Proyecto

El repositorio está organizado en submódulos especializados:

```text
BioEvo/
├── index.html              # Landing page estática desplegada en GitHub Pages
├── README.md               # Este archivo (visión global del repositorio)
├── cronos/                 # Cronos Desktop: análisis de literatura con LLMs locales
└── labstats/               # LabStats Formatter: tablas bioestadísticas y exportación a LaTeX
```

### Resumen de Módulos

| Módulo | Enfoque | Tecnologías Clave | Estado |
| :--- | :--- | :--- | :--- |
| [**Cronos Desktop**](./cronos/) | Síntesis y extracción de literatura científica (PDFs, preprints) mediante LLMs locales | Python, Ollama, LangChain/LlamaIndex | En desarrollo |
| [**LabStats Formatter**](./labstats/) | Procesamiento automatizado de pruebas estadísticas y exportación directa a tablas LaTeX | Python, pandas, scipy, statsmodels | En desarrollo |

---

## 🌐 Sitio Web y Demostración

La documentación interactiva y el panel de acceso a utilidades está disponible en:
👉 **[https://rvesteban.github.io/BioEvo/](https://rvesteban.github.io/BioEvo/)**

---

## ☕ Apoyo al Creador y Sostenibilidad

BioEvo Core es y seguirá siendo libre, local y completamente funcional. Si este software aporta valor a tu flujo de investigación o docencia y deseas respaldar su mantenimiento continuo, puedes aportar de forma voluntaria:

* **Wompi (Tarjetas de crédito / débito y PSE Colombia):** Disponible a través del modal en la [landing page](https://rvesteban.github.io/BioEvo/).
* **Nequi / Transfiya:** Recaudo directo en Colombia.
* **Criptoactivos:** Transferencias en USDT sobre red Polygon (PoS).

---

## 📄 Licencia y Descargo

Este repositorio se distribuye bajo la licencia **MIT**. Para conocer detalles de garantías y limitaciones de responsabilidad frente al uso de modelos de lenguaje en publicaciones científicas, consulta la sección legal en el sitio web del proyecto.
