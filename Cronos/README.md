# Cronos Desktop

[![Submódulo: BioEvo](https://img.shields.io/badge/BioEvo-Core_Module-38bdf8)](../README.md)
[![Runtime: Local Ollama](https://img.shields.io/badge/Inference-Local_Ollama-black.svg)](#arquitectura-técnica)
[![Status: Development](https://img.shields.io/badge/Status-Active_Development-orange.svg)](#hoja-de-ruta)

**Cronos Desktop** es un asistente local para el procesamiento, consulta y síntesis de literatura científica (artículos peer-reviewed, tesis y preprints) diseñado para investigadores biológicos que requieren confidencialidad absoluta sobre sus manuscritos preliminares.

---

## ✨ Características Principales

* **Inferencia 100% Desconectada:** Funciona conectado a motores locales como **Ollama** (ej. Llama 3, Mistral, Qwen, DeepSeek). Ningún fragmento de texto se transmite a servicios como OpenAI o Anthropic.
* **Procesamiento de Fuentes Primarias:** Ingesta y parseo estructurado de documentos en formato PDF, extrayendo metodología, tablas resumidas y conclusiones.
* **RAG Especializado para Ciencia:** indexación de fragmentos con generación aumentada por recuperación (Retrieval-Augmented Generation) para responder consultas con atribución directa a páginas y párrafos de los artículos indexados.
* **Cero Telemetría:** El binario no envía métricas de uso ni huellas digitales del sistema.

---

## 🛠️ Arquitectura Técnica

```text
[PDFs / Manuscritos] 
         │
         ▼
[Parser PyMuPDF / pdfplumber] ──► [Embeddings Locales (Sentence-Transformers)]
                                                │
                                                ▼
                                    [Base Vectorial Local (Chroma / FAISS)]
                                                │
[Consulta del Investigador] ────────────────────┤
                                                ▼
                                    [LLM Local vía Ollama (API REST :11434)]
                                                │
                                                ▼
                                    [Síntesis con Citas Verificables]
```

### Requisitos Previos Recomendados
* **Sistema Operativo:** Windows 10/11 (64-bit), Linux (x86_64), o macOS (Apple Silicon).
* **Entorno de ejecución:** [Ollama](https://ollama.com/) instalado y en ejecución en `http://localhost:11434`.
* **Hardware:** Mínimo 16 GB de memoria RAM (32 GB recomendados para modelos de 8B o cuantizaciones Q5/Q8) o GPU con al menos 6–8 GB VRAM.

---

## 🚀 Hoja de Ruta (Roadmap)

- [x] Especificación de interfaz e integración en BioEvo Core.
- [ ] Módulo CLI para indexación por lotes de carpetas con literatura en PDF.
- [ ] Empaquetado de GUI nativa liviana (PyQt6 o Flet).
- [ ] Exportación de fichas bibliográficas y citas compatibles con BibTeX y Zotero.
- [ ] Distribución de ejecutable independiente para Windows (`.exe`).

---

## ⚠️ Advertencia Metodológica sobre Modelos de Lenguaje

Los modelos de inferencia estadística probabilística pueden producir imprecisiones u omisiones involuntarias. Toda síntesis generada por Cronos Desktop debe ser contrastada frente al texto original del autor antes de ser incorporada en manuscritos destinados a evaluación por pares o decisiones clínicas.
