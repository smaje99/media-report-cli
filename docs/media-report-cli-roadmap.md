# Roadmap 4: Media Report CLI

Media Report CLI es el proyecto más cercano a convertirse en un **producto técnico publicable**. A diferencia de ITA o Jurídico, no necesita validación comercial compleja para empezar a generar valor; necesita estabilidad, pruebas reales, documentación, empaquetado y una versión instalable.

Su valor principal es claro:

> Una CLI en Python que toma videos o audios desde una carpeta, automatiza el flujo completo de extracción, transcripción, limpieza, resumen y generación de reportes, dejando los resultados organizados junto al archivo original.

Este proyecto debe avanzar como una herramienta open source seria, útil para tu perfil, tu portfolio y tus propios flujos de trabajo.

---

# Estado actual

Media Report CLI ya tiene:

* Documento de arquitectura definido.
* Scaffold construido.
* CLI básica funcionando.
* Flujo inicial en marcha.
* Está en proceso de empezar pruebas pesadas.
* Se proyecta como paquete instalable desde **PyPI**.
* Licencia sugerida: **MIT**.
* Integración futura con APIs de LLM.
* Automatización local sobre carpetas con video/audio.

Esto significa que ya superó la fase de idea. El foco ahora debe ser:

1. Robustecer el flujo.
2. Probarlo con archivos reales.
3. Estandarizar configuración.
4. Mejorar UX de CLI.
5. Prepararlo para publicación.
6. Documentarlo muy bien.

---

# Objetivo estratégico de Media Report CLI

Construir una herramienta CLI instalable y reutilizable para transformar archivos multimedia en transcripciones y reportes estructurados, con una arquitectura flexible para usar diferentes motores de transcripción y diferentes proveedores LLM.

En términos de posicionamiento profesional, este proyecto demuestra:

* Automatización con Python (Reforzando algo de RPA).
* Diseño de CLI.
* Procesamiento multimedia (vídeo, audio, texto, e imágenes avanzadas).
* Integración con IA.
* Empaquetado profesional.
* Arquitectura extensible.
* Producto open source publicable (El open-source es atractivo en el CV y LinkedIn).
* Capacidad de resolver una necesidad real con software reutilizable (al menos, las mías, pero esto es como tener una mini-secretaría).

---

# Decisión técnica base

Media Report CLI debería mantenerse como **paquete Python publicable en PyPI**, no como aplicación pesada ni como SaaS.

La guía oficial de empaquetado de Python se mantiene como referencia para distribuir e instalar paquetes modernos, incluyendo configuración con `pyproject.toml`. Para publicación, PyPI recomienda Trusted Publishing como alternativa más segura a tokens de larga duración, especialmente cuando se publica desde CI/CD como GitHub Actions. ([packaging.python.org][1])

Para la interfaz de comandos, **Click** es una opción sólida porque está diseñado para construir CLIs composables, con comandos anidados y defaults razonables. Esto encaja bien si Media Report CLI crecerá con comandos como `process`, `transcribe`, `report`, `clean`, `config` o `doctor`. ([click.palletsprojects.com][2])

---

# Enfoque semanal

Media Report CLI es de fin de semana.

| Bloque                 | Uso                                            |
| ---------------------- | ---------------------------------------------- |
| Domingo mañana         | Desarrollo, pruebas pesadas, empaquetado       |
| Domingo tarde / buffer | Documentación, refactor, fixes                 |
| Viernes cierre         | Elegir archivo de prueba y objetivo del sprint |

Regla operativa:

> Cada fin de semana debe cerrar con una mejora ejecutable: comando nuevo, prueba pesada, fix real, documentación, release interna o mejora de empaquetado.

---

# OKRs de Media Report CLI

## Objetivo 1: Estabilizar el flujo completo de procesamiento

**KR1.** Procesar correctamente al menos 5 archivos reales de distinto tipo.
**KR2.** Generar salida organizada por archivo procesado.
**KR3.** Separar claramente archivos temporales, transcripción, resumen y reporte final.
**KR4.** Manejar errores comunes sin romper toda la ejecución.

---

## Objetivo 2: Convertir la CLI en una herramienta instalable y usable

**KR1.** Tener `pyproject.toml` completo y limpio.
**KR2.** Definir entry point global, por ejemplo `media-report`.
**KR3.** Ejecutar instalación local con `pipx` o instalación editable.
**KR4.** Publicar una primera versión en TestPyPI o preparar release candidata.
**KR5.** Dejar lista la publicación segura en PyPI mediante flujo CI/CD.

---

## Objetivo 3: Diseñar una arquitectura extensible

**KR1.** Separar procesamiento multimedia, transcripción, limpieza, generación de reporte y proveedores LLM.
**KR2.** Permitir configurar proveedor LLM sin tocar el código.
**KR3.** Permitir cambiar motor de transcripción.
**KR4.** Crear interfaces/ports para transcriptor, reporter y LLM client.
**KR5.** Documentar cómo agregar un nuevo proveedor.

---

## Objetivo 4: Publicar el proyecto como caso fuerte de portfolio

**KR1.** Crear README profesional.
**KR2.** Grabar o documentar una demo.
**KR3.** Publicar una ficha del proyecto en el portfolio.
**KR4.** Escribir un artículo técnico sobre el diseño de la CLI (en [Medium](medium.com)).
**KR5.** Tener una versión mínima etiquetada, por ejemplo `v0.1.0`.
**KR6.** Crear documentación técnica en una página web.

---

# Roadmap operativo de 90 días

## Fase 1 — Pruebas pesadas y estabilización del flujo

**Duración:** semanas 1 y 2
**Bloques:** 2 fines de semana

### Objetivo

Validar que la CLI funciona con archivos reales, no solo con ejemplos pequeños.

### Entregables

* Carpeta de pruebas locales.
* Dataset mínimo de audios/videos.
* Registro de resultados.
* Lista de errores encontrados.
* Manejo inicial de excepciones.
* Validación de formatos soportados.
* Primer reporte real generado.

### Archivos de prueba recomendados

| Tipo            |  Duración | Propósito                        |
| --------------- | --------: | -------------------------------- |
| Audio corto     |   1-3 min | Validar flujo básico             |
| Audio medio     | 10-20 min | Validar rendimiento              |
| Video corto     |   1-5 min | Validar extracción de audio      |
| Video largo     | 30-60 min | Validar proceso pesado           |
| Audio con ruido |  Variable | Validar calidad de transcripción |

### Resultado esperado

Al final de esta fase debes saber con honestidad:

* Qué funciona.
* Qué se rompe.
* Qué tarda demasiado.
* Qué formato causa problemas.
* Qué salida necesita rediseño.

---

## Fase 2 — Estructura de salidas y archivos temporales

**Duración:** semanas 3 y 4
**Bloques:** 2 fines de semana

### Objetivo

Organizar el resultado de cada procesamiento de forma predecible.

### Entregables

* Convención de carpetas.
* Convención de nombres.
* Limpieza controlada de temporales.
* Opción para conservar o borrar temporales.
* Archivo de metadatos del proceso.
* Log por ejecución.

### Estructura recomendada

```txt
archivo-original.mp4
archivo-original.media-report/
├── input/
│   └── metadata.json
├── temp/
│   └── extracted-audio.wav
├── transcript/
│   ├── raw.txt
│   └── clean.md
├── report/
│   ├── summary.md
│   ├── report.md
│   └── action-items.md
└── logs/
    └── run.log
```

### Decisión importante

Tu idea inicial era dejar los temporales “ahí mismo”. Eso está bien, pero conviene que no queden sueltos en la carpeta. Deben vivir dentro de una carpeta generada por archivo, para evitar desorden.

### Resultado esperado

La CLI debe dejar resultados claros y reutilizables, no una carpeta llena de archivos ambiguos.

---

## Fase 3 — Configuración y proveedores

**Duración:** semanas 5 y 6
**Bloques:** 2 fines de semana

### Objetivo

Permitir que la CLI use distintos proveedores de transcripción y LLM sin modificar código.

### Entregables

* Archivo de configuración.
* Variables de entorno.
* Configuración por proyecto/carpeta.
* Selector de proveedor LLM.
* Selector de motor de transcripción.
* Validación de configuración.
* Comando `doctor` o `check`.

### Configuración sugerida

```toml
[media_report]
output_mode = "folder"
keep_temp = true
language = "es"

[transcription]
provider = "local"
model = "whisper"

[llm]
provider = "openai-compatible"
model = "gpt-4.1-mini"
api_key_env = "MEDIA_REPORT_LLM_API_KEY"

[report]
template = "meeting-notes"
format = "markdown"
```

### Comandos sugeridos

```bash
media-report process ./reunion.mp4
media-report process ./carpeta --recursive
media-report transcribe ./audio.mp3
media-report report ./transcript/raw.txt
media-report config init
media-report doctor
```

### Resultado esperado

La herramienta empieza a sentirse configurable y no como un script rígido.

---

## Fase 4 — Arquitectura por servicios internos

**Duración:** semanas 7 y 8
**Bloques:** 2 fines de semana

### Objetivo

Separar responsabilidades internas para que el proyecto no se convierta en un script gigante.

### Entregables

* Servicio de media extraction.
* Servicio de transcription.
* Servicio de transcript cleaning.
* Servicio de report generation.
* Servicio de file management.
* Ports/interfaces.
* Tests unitarios por servicio.
* Tests de integración del flujo completo.

### Módulos internos recomendados

```txt
media_report/
├── cli/
│   ├── app.py
│   └── commands/
├── core/
│   ├── pipeline.py
│   ├── config.py
│   └── errors.py
├── media/
│   └── extractor.py
├── transcription/
│   ├── ports.py
│   └── providers/
├── llm/
│   ├── ports.py
│   └── providers/
├── reports/
│   ├── generator.py
│   └── templates/
├── storage/
│   └── workspace.py
└── tests/
```

### Resultado esperado

Media Report CLI debe ser una herramienta mantenible, no un conjunto de scripts pegados.

---

## Fase 5 — Empaquetado y distribución

**Duración:** semanas 9 y 10
**Bloques:** 2 fines de semana

### Objetivo

Preparar el proyecto para instalación profesional.

### Entregables

* `pyproject.toml` completo.
* Entry point de CLI.
* README PyPI-friendly.
* Licencia MIT.
* Versionado semántico.
* Build local.
* Instalación local probada.
* Publicación en TestPyPI o release candidata.
* Workflow de GitHub Actions para test/build.

### Checklist de empaquetado

```txt
- Nombre del paquete definido.
- Nombre del comando definido.
- Versión inicial definida.
- Dependencias mínimas definidas.
- Dependencias opcionales separadas.
- README visible en PyPI.
- LICENSE incluido.
- pyproject.toml válido.
- Build local exitoso.
- Instalación local probada.
- Comando global funcionando.
```

### Dependencias opcionales sugeridas

Conviene no obligar a instalar todo desde el inicio.

```toml
[project.optional-dependencies]
local-transcription = ["openai-whisper"]
dev = ["pytest", "ruff", "ty"]
docs = ["mkdocs-material"]
```

### Resultado esperado

Media Report CLI debe poder instalarse y ejecutarse como herramienta real.

---

## Fase 6 — Release 0.1.0 y caso de estudio

**Duración:** semanas 11 y 12
**Bloques:** 2 fines de semana

### Objetivo

Cerrar una primera versión demostrable.

### Entregables

* Tag `v0.1.0`.
* Changelog.
* README final.
* Demo documentada.
* Caso de estudio para portfolio.
* Artículo técnico.
* Lista de mejoras para `v0.2.0`.

### Alcance recomendado de `v0.1.0`

La versión `0.1.0` debería hacer pocas cosas, pero bien:

1. Procesar un archivo de audio.
2. Procesar un archivo de video extrayendo audio.
3. Generar transcripción.
4. Generar reporte Markdown.
5. Guardar resultados organizados.
6. Permitir configuración básica.
7. Mostrar errores entendibles.

### Resultado esperado

Una primera versión instalable, documentada y suficientemente estable para mostrar.

---

# Roadmap macro de 12 meses

| Trimestre | Objetivo                 | Resultado esperado                                                       |
| --------- | ------------------------ | ------------------------------------------------------------------------ |
| T1        | CLI estable y publicable | Flujo completo, pruebas pesadas, release 0.1.0                           |
| T2        | Extensibilidad           | Proveedores múltiples, plantillas, batch processing                      |
| T3        | Calidad profesional      | CI/CD, documentación avanzada, plugins, reportes especializados          |
| T4        | Producto maduro          | PyPI estable, casos reales, comunidad inicial, integración con portfolio |

---

# Backlog inicial priorizado

## Alta prioridad

* Pruebas con archivos reales.
* Manejo robusto de errores.
* Estructura clara de salida.
* Configuración inicial.
* Comando `process`.
* Comando `doctor`.
* Entry point global.
* README.
* Tests del pipeline.
* Release `0.1.0`.

## Prioridad media

* Procesamiento por carpeta.
* Modo recursivo.
* Plantillas de reporte.
* Proveedores LLM múltiples.
* Proveedores de transcripción múltiples.
* Logs detallados.
* Changelog.
* Publicación en TestPyPI.
* GitHub Actions.

## Prioridad futura

* Plugin system.
* Interfaz TUI.
* Reportes PDF.
* Exportación DOCX.
* Integración con Notion.
* Integración con Google Drive.
* Resumen por capítulos.
* Detección de hablantes.
* Segmentación por temas.
* Modo watch folder.
* Procesamiento paralelo.
* Interfaz GUI intuitiva para personas no técnicas, y que la misma GUI instale las dependencias externas.

---

# Flujo principal recomendado

```txt
Detectar archivo
↓
Validar formato
↓
Extraer audio si es video
↓
Normalizar audio
↓
Transcribir
↓
Limpiar transcripción
↓
Generar resumen
↓
Generar reporte
↓
Guardar resultados
↓
Registrar logs/metadatos
```

---

# Comandos mínimos del MVP

## `process`

Comando principal.

```bash
media-report process reunion.mp4
```

Debe ejecutar el pipeline completo.

---

## `transcribe`

Solo genera transcripción.

```bash
media-report transcribe audio.mp3
```

Útil para aislar errores.

---

## `report`

Genera reporte desde una transcripción existente.

```bash
media-report report transcript.txt
```

Útil cuando ya tienes texto.

---

## `config init`

Crea configuración base.

```bash
media-report config init
```

---

## `doctor`

Valida entorno.

```bash
media-report doctor
```

Debe revisar:

* FFmpeg disponible.
* Variables de entorno.
* Proveedor LLM configurado.
* Dependencias opcionales.
* Permisos de escritura.
* Versión de Python.

---

# Estructura de requerimientos MVP

| ID     | Requerimiento                                       | Prioridad |
| ------ | --------------------------------------------------- | --------: |
| MR-001 | La CLI debe procesar un archivo de audio            |      Alta |
| MR-002 | La CLI debe procesar un video extrayendo audio      |      Alta |
| MR-003 | La CLI debe generar transcripción en texto          |      Alta |
| MR-004 | La CLI debe generar reporte Markdown                |      Alta |
| MR-005 | La CLI debe crear una carpeta de salida por archivo |      Alta |
| MR-006 | La CLI debe conservar logs de ejecución             |      Alta |
| MR-007 | La CLI debe permitir configuración básica           |      Alta |
| MR-008 | La CLI debe validar dependencias del entorno        |      Alta |
| MR-009 | La CLI debe manejar errores comunes                 |      Alta |
| MR-010 | La CLI debe poder instalarse como comando global    |      Alta |

---

# Definition of Done por feature

Una feature no se considera terminada hasta que cumpla:

```txt
- Tiene comando o función accesible.
- Tiene prueba mínima.
- Tiene manejo de error esperado.
- Tiene documentación breve.
- No rompe el flujo principal.
- Funciona con al menos un archivo real.
- Registra salida o log verificable.
```

---

# Métricas de avance

| Métrica                      | Meta 90 días |
| ---------------------------- | -----------: |
| Archivos reales procesados   |           10 |
| Formatos probados            |            4 |
| Comandos principales         |            5 |
| Tests del pipeline           |           Sí |
| README profesional           |            1 |
| Release candidata            |            1 |
| Versión `v0.1.0`             |            1 |
| Caso de estudio en portfolio |            1 |
| Artículo técnico             |            1 |

---

# Riesgos principales

| Riesgo                            | Impacto | Mitigación                                     |
| --------------------------------- | ------- | ---------------------------------------------- |
| Archivos largos rompen el flujo   | Alto    | Pruebas pesadas desde el inicio                |
| Dependencias multimedia difíciles | Alto    | Comando `doctor` y documentación clara         |
| Salidas desordenadas              | Medio   | Carpeta por archivo procesado                  |
| Costos de LLM inesperados         | Medio   | Configuración explícita y modo local/parcial   |
| Transcripción de mala calidad     | Medio   | Permitir proveedores alternativos              |
| CLI demasiado compleja            | Alto    | Mantener `process` como comando principal      |
| Publicar antes de estabilizar     | Medio   | Pasar primero por TestPyPI o release candidata |

---

# Qué NO hacer todavía

No conviene hacer ahora:

* Interfaz gráfica.
* SaaS.
* Dashboard web.
* Integración con muchas APIs.
* PDF avanzado.
* Detección compleja de hablantes.
* Plugin system formal.
* Paralelización avanzada.
* Watch folder.
* Sincronización cloud.
* Automatización con Notion o Drive.

Primero necesitas una CLI fuerte y confiable.

---

# Sprint Media Report 01

## Objetivo

Ejecutar pruebas pesadas y detectar fallos reales del pipeline.

## Duración

Un fin de semana.

## Tareas

1. Crear carpeta `samples/` ignorada por Git.
2. Seleccionar 5 archivos reales:

   * audio corto,
   * audio medio,
   * video corto,
   * video largo,
   * audio con ruido.
3. Ejecutar la CLI sobre cada archivo.
4. Registrar tiempo de ejecución.
5. Registrar errores.
6. Registrar tamaño de salida.
7. Evaluar calidad de transcripción.
8. Evaluar estructura de archivos generados.
9. Crear issues o tareas por cada fallo.
10. Definir mejoras prioritarias.

## Entregable mínimo

```txt
docs/testing/heavy-test-report.md
```

Con esta estructura:

```txt
# Heavy Test Report

## Archivo probado
## Tipo
## Duración
## Resultado
## Tiempo de procesamiento
## Errores encontrados
## Calidad de transcripción
## Calidad del reporte
## Acciones correctivas
```

---

# Sprint Media Report 02

## Objetivo

Ordenar la salida del procesamiento.

## Tareas

1. Diseñar carpeta de salida por archivo.
2. Separar temporales, transcripción, reportes y logs.
3. Implementar creación automática de estructura.
4. Agregar opción `--keep-temp`.
5. Agregar opción `--output-dir`.
6. Crear pruebas sobre estructura de salida.
7. Documentar convención.

## Entregable mínimo

```txt
Un archivo procesado genera una carpeta clara con transcripción, reporte, temporales y logs.
```

---

# Sprint Media Report 03

## Objetivo

Agregar configuración básica y comando `doctor`.

## Tareas

1. Crear `config init`.
2. Leer configuración desde archivo.
3. Leer variables de entorno.
4. Validar FFmpeg.
5. Validar proveedor LLM.
6. Validar permisos de escritura.
7. Mostrar diagnóstico entendible.
8. Documentar configuración.

## Entregable mínimo

```txt
media-report doctor
```

Debe decir claramente qué está listo y qué falta.

---

# Sprint Media Report 04

## Objetivo

Preparar empaquetado instalable.

## Tareas

1. Revisar `pyproject.toml`.
2. Definir entry point.
3. Validar build local.
4. Instalar localmente.
5. Ejecutar comando global.
6. Revisar README.
7. Agregar LICENSE.
8. Crear changelog.
9. Preparar release candidata.

## Entregable mínimo

```txt
pipx install .
media-report --help
media-report process archivo.mp4
```

---

# Criterio para cerrar los primeros 90 días

Media Report CLI habrá avanzado correctamente si tienes:

1. CLI instalable localmente.
2. Flujo completo funcionando.
3. Pruebas con archivos reales.
4. Estructura de salida clara.
5. Configuración básica.
6. Comando `doctor`.
7. README profesional.
8. Licencia MIT.
9. Release `v0.1.0`.
10. Caso de estudio listo para portfolio.

---

# Rol de Media Report CLI dentro de tu consultoría

Media Report CLI puede cumplir tres funciones:

## 1. Herramienta personal

Para convertir reuniones, clases, entrevistas y videos en reportes útiles.

## 2. Producto open source

Para mostrar capacidad técnica real en Python, CLI, IA y automatización.

## 3. Activo de consultoría

Puede convertirse en una herramienta interna para levantar requerimientos desde reuniones, generar actas, detectar tareas y alimentar proyectos como ITA, Jurídico o Cognark.

De hecho, hay una conexión estratégica muy fuerte:

> Media Report puede procesar reuniones; Cognark puede estructurar el conocimiento resultante; ITA y Jurídico pueden usar ambos para acelerar análisis, requerimientos y documentación.

---

# Resumen ejecutivo

Media Report CLI debe avanzar como tu proyecto más publicable y demostrable a corto plazo. Ya tiene arquitectura, scaffold y CLI básica, así que el foco de los próximos 90 días debe estar en pruebas pesadas, estructura de salida, configuración, empaquetado, documentación y release `v0.1.0`.

La meta no es hacerlo enorme. La meta es que una persona pueda instalarlo, ejecutar `media-report process archivo.mp4` y obtener una transcripción y un reporte ordenado. Cuando eso funcione bien, el proyecto ya será una pieza muy fuerte para tu portfolio y una herramienta útil para alimentar los demás proyectos.

[1]: https://packaging.python.org/?utm_source=chatgpt.com "Python Packaging User Guide"
[2]: https://click.palletsprojects.com/?utm_source=chatgpt.com "Welcome to Click — Click Documentation (8.3.x)"
