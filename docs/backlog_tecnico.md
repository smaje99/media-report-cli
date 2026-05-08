# Backlog Técnico Operativo de `media-report-cli`

## Propósito

Este documento convierte el estado real del repositorio en un backlog técnico listo para implementación. La referencia obligatoria es el baseline actual del código, y el roadmap externo de 90 días se trata como presión de negocio, no como fuente de verdad cuando entra en conflicto con el repositorio.

El backlog está organizado por épicas alineadas a `docs/context/roadmap.md` y descompuesto en sprints de dos semanas. Cada sprint define alcance cerrado, entregables verificables, riesgos y work items suficientemente específicos para arrancar implementación sin abrir decisiones de diseño.

## Supuestos Fijos

- Baseline oficial: versión `0.1.0` del repo actual.
- Arquitectura obligatoria: hexagonal con slicing moderado.
- Comando raíz estable: `media-report`.
- Comandos bootstrap que no se rompen:
  - `process`
  - `doctor`
  - `config init`
  - `config show`
  - `templates list`
- Nuevos comandos públicos planificados:
  - `transcribe`
  - `report`
  - `clean`
- Plataformas objetivo: Linux y macOS.
- Windows: experimental, documentando regresiones sin bloquear el roadmap salvo regresión introducida de forma explícita.
- Recursos empaquetados siempre por `importlib.resources`.
- Secretos siempre redactados.
- Proveedores remotos siempre generan warning visible.
- Los artefactos intermedios se preservan por defecto para trazabilidad.

## Estado Actual vs Estado Objetivo

| Área | Estado actual confirmado | Estado objetivo del backlog | Tratamiento |
| --- | --- | --- | --- |
| CLI pública | Existen `process`, `doctor`, `config`, `templates` | Mantener compatibilidad y añadir `transcribe`, `report`, `clean` | Incremental, sin renombres |
| `process` | Valida paths, descubre media, crea artefactos, escribe `metadata.json` y `pipeline.log` | Ejecutar pipeline completo hasta Markdown/PDF con reanudación por etapas | Evolución del comando existente |
| FFmpeg | Hay builder de comando en `infrastructure/ffmpeg/service.py`, sin ejecución ni port dedicado | Extraer y normalizar audio desde aplicación a través de port/adaptador | Scaffolded, no cableado |
| Transcripción | Existe `TranscriptionProvider`; `faster_whisper` solo levanta `NotImplementedError` | Transcribir audio, persistir texto crudo y segmentos, soportar `transcribe` | Scaffolded, no cableado |
| Reporting LLM | Existen `LLMProvider`, `OllamaProvider`, `OpenAICompatibleProvider`; sin integración real | Renderizar prompt, llamar proveedor, persistir prompt/respuesta y producir `report.md` | Scaffolded, no cableado |
| PDF | Existe builder de Pandoc; plantilla TeX empaquetada | Renderizar `report.pdf` desde `report.md` preservando Markdown ante fallos | Scaffolded, no cableado |
| Configuración | Archivo TOML, env overrides, redacción de secretos, selección básica de proveedor/modelo | Configuración validada por etapa, perfiles de provider y warnings coherentes | Extender sin romper |
| Metadata | `metadata.json` incluye source, artifacts, workflow y etapas `planned` | Metadata trazable con estados `planned/running/completed/failed/skipped`, timestamps y errores resumidos | Extensión de esquema |
| Recursos empaquetados | Templates Markdown y TeX se cargan por paquete | Mantener el contrato para instalación por wheel, sdist y tool install | Ya bien encaminado |
| Tests | Unitarias para scanner, planner, settings y resources; integración CLI bootstrap | Cobertura por etapa, smoke tests instalados y fixtures realistas | Expandir |
| Release | Docs de release y packaging presentes | CI/CD, trusted publishing, TestPyPI/PyPI, smoke tests de instalación | Parcial, no automatizado |
| Portfolio/docs | README y contexto técnico presentes | Demo, guía de extensibilidad, artículo técnico y ficha de portfolio | Pendiente |

## Política de Alcance por Fase

- Fases 0 a 2 consolidan el baseline y preparan reanudación, pero no introducen aún integraciones pesadas.
- Fase 3 introduce FFmpeg sin contaminar `cli` con lógica de subprocess.
- Fase 4 cierra el contrato de transcripción y expone `transcribe` como superficie pública estable.
- Fase 5 cierra prompting y reportes LLM, y expone `report`.
- Fase 6 conecta renderizado PDF y hace que `process` sea un flujo end-to-end.
- Fase 7 endurece distribución, CI/CD y validación de instalación.
- Fase 8 se reserva para extensiones tardías; `clean` entra aquí si compite por capacidad con transcripción y reporting.

## Mapa de Sprints

| Sprint | Fases | Horizonte | Objetivo principal |
| --- | --- | --- | --- |
| Sprint 01 | 0-1 | Días 0-14 | Congelar contrato público, baseline y esquema de metadata |
| Sprint 02 | 2 | Días 15-28 | Reanudación y modelo de artefactos listos para pipeline real |
| Sprint 03 | 3 | Días 29-42 | Extracción y normalización con FFmpeg |
| Sprint 04 | 4 | Días 43-56 | Pipeline de transcripción y comando `transcribe` |
| Sprint 05 | 5 | Días 57-70 | Prompting, LLM providers y comando `report` |
| Sprint 06 | 6 | Días 71-84 | PDF, cierre end-to-end de `process` y fallos parciales |
| Sprint 07 | 7 | Días 85-98 | Packaging hardening, CI/CD y publicación |
| Sprint 08 | 8 | Días 99-112 | `clean`, extensibilidad, demo y activos de portfolio |

Los primeros seis sprints cubren el núcleo del roadmap de 90 días. Los sprints 07 y 08 quedan en el mismo backlog operativo porque dependen directamente de las decisiones técnicas anteriores.

## Epic 01: Fases 0-1

### Sprint 01 - Baseline, CLI estable y esquema de metadata

- Objetivo del sprint: fijar el contrato público de `0.1.0`, cerrar vacíos de metadata y dejar una base segura para resumir etapas posteriores.
- Alcance:
  - documentar y validar el contrato actual de CLI;
  - endurecer `doctor`, `config show` y `process` como bootstrap estable;
  - versionar el esquema de metadata para estados futuros.
- Fuera de alcance:
  - ejecución real de FFmpeg;
  - transcripción real;
  - llamadas LLM o render PDF.
- Entregables:
  - contrato de CLI documentado en tests de integración;
  - esquema de metadata v2 definido y migración desde bootstrap v1;
  - fixtures mínimas para archivo único y carpeta recursiva.
- Dependencias: ninguna externa; usa solamente baseline del repo.
- Riesgos:
  - congelar demasiado pronto opciones que luego choquen con `transcribe` y `report`;
  - introducir metadata incompatible con artefactos ya generados.
- Criterio de salida:
  - tests de integración cubren ayuda, `doctor`, `config`, `templates` y `process`;
  - metadata nueva puede ser escrita y leída sin romper el bootstrap existente.

#### WI-01-01 - Congelar contrato de CLI bootstrap

- Estado: hecho
- Cerrado en: `2026-05-07T00:00:00-05:00`

- Objetivo: formalizar la superficie pública actual como contrato compatible.
- Contexto técnico: hoy la CLI se arma en `media_report.cli.app` y `process` ya expone opciones futuras como `--only-transcribe` y `--only-report`, pero aún no ejecuta etapas reales.
- Alcance funcional:
  - fijar help text y códigos de salida esperados;
  - documentar qué opciones son activas hoy y cuáles son placeholders de roadmap;
  - asegurar que nuevas opciones sean aditivas.
- No se tocará:
  - semántica de FFmpeg;
  - estructura de prompts;
  - elección final de proveedor de transcripción.
- Cambios esperados de CLI/API/artefactos/config:
  - posibles mejoras de help text;
  - documentación explícita de opciones no cableadas;
  - ningún cambio de nombres de comandos.
- Gherkin mínimo:

```gherkin
Scenario: Mostrar ayuda del comando raíz
  Given una instalación limpia del CLI
  When ejecuto "media-report --help"
  Then veo el comando raíz "media-report"
  And veo "process", "doctor", "config" y "templates"
```

- Happy path:
  - ayuda coherente;
  - opciones visibles y estables;
  - códigos de salida 0 en comandos informativos.
- Bad paths:
  - opciones inconsistentes entre README y CLI;
  - cambios accidentales de nombre o help text crítico;
  - códigos de salida no deterministas.
- Observabilidad/logging:
  - registrar en `pipeline.log` solo cuando `process` genere artefactos;
  - no emitir stack traces para errores de uso esperados.
- Pruebas unitarias/integración:
  - integración CLI para `--help` y subcommands;
  - snapshot textual liviano de help output si aporta estabilidad.
- Criterio de aceptación:
  - la ayuda pública queda cubierta por pruebas y alineada con README.

#### WI-01-02 - Evolucionar `metadata.json` para reanudación futura

- Estado: hecho
- Cerrado en: `2026-05-08T00:11:06-05:00`

- Objetivo: mover el bootstrap actual hacia un esquema que soporte estados por etapa y errores resumidos.
- Contexto técnico: `ArtifactPlanner.bootstrap_metadata()` ya escribe `schema_version`, `workflow` y `stages`, pero todas las etapas quedan solo como `planned`.
- Alcance funcional:
  - definir estados `planned`, `running`, `completed`, `failed`, `skipped`;
  - agregar timestamps por etapa;
  - reservar campos para errores resumidos sin almacenar secretos.
- No se tocará:
  - formato final de `transcript_segments.json`;
  - política de colas o ejecución paralela.
- Cambios esperados de CLI/API/artefactos/config:
  - nuevo esquema de `metadata.json`;
  - posible helper de lectura/escritura de metadata en dominio/aplicación;
  - sin cambios de flags públicos.
- Gherkin mínimo:

```gherkin
Scenario: Bootstrap de metadata para archivo nuevo
  Given un archivo de media válido
  When ejecuto "media-report process archivo.mp4"
  Then se crea "metadata.json"
  And cada etapa tiene estado inicial y campos reservados para trazabilidad
```

- Happy path:
  - metadata legible y estable;
  - artefactos futuros ya direccionados;
  - esquema versionado.
- Bad paths:
  - incompatibilidad con artefactos existentes;
  - error de serialización al crear bootstrap;
  - fuga de secretos en errores persistidos.
- Observabilidad/logging:
  - loggear creación de metadata y versión de esquema;
  - no persistir variables de entorno sensibles.
- Pruebas unitarias/integración:
  - unitarias del planner y round-trip de metadata;
  - integración `process` verificando campos nuevos.
- Criterio de aceptación:
  - `metadata.json` soporta el ciclo completo del pipeline sin rediseño posterior.

#### WI-01-03 - Endurecer fixtures y casos de baseline

- Objetivo: disponer de fixtures mínimas y reproducibles para todo el backlog.
- Contexto técnico: hoy las pruebas fabrican archivos fake locales; falta una convención para casos de carpeta recursiva y colisión de artefactos.
- Alcance funcional:
  - crear fixtures repo-local para un archivo audio/video nominal;
  - crear fixture de carpeta con subdirectorios;
  - dejar helper de smoke test reutilizable.
- No se tocará:
  - archivos multimedia pesados;
  - fixtures que requieran internet o herramientas reales.
- Cambios esperados de CLI/API/artefactos/config:
  - nuevos fixtures bajo `tests/fixtures`;
  - sin cambios de CLI.
- Gherkin mínimo:

```gherkin
Scenario: Procesar carpeta con exploración recursiva
  Given una carpeta con media en raíz y subdirectorios
  When ejecuto "media-report process carpeta --recursive"
  Then se planifican artefactos para todos los medios soportados
```

- Happy path:
  - fixtures pequeñas y portables;
  - tests rápidos;
  - base común para sprints 02-08.
- Bad paths:
  - fixtures frágiles por paths absolutos;
  - archivos demasiado grandes para CI;
  - diferencias por plataforma.
- Observabilidad/logging:
  - no aplica más allá de mensajes de prueba.
- Pruebas unitarias/integración:
  - integración `process` con archivo único, carpeta recursiva y colisión.
- Criterio de aceptación:
  - la suite puede reutilizar fixtures sin depender de generación ad hoc.

## Epic 02: Fase 2

### Sprint 02 - Reanudación y modelo de artefactos

- Objetivo del sprint: dejar listo el modelo de artefactos para ejecución real por etapas sin perder trazabilidad ni compatibilidad.
- Alcance:
  - lectura/escritura consistente de metadata;
  - decisiones de reanudación por etapa;
  - política explícita de overwrite, reuse y fallo parcial.
- Fuera de alcance:
  - integración real con proveedores externos;
  - ejecución concurrente;
  - limpieza semántica de transcripción.
- Entregables:
  - servicio de estado de pipeline;
  - decisiones de resume/reuse desde aplicación;
  - cobertura de conflictos de artefactos y reentrada.
- Dependencias: Sprint 01 completado.
- Riesgos:
  - diseñar reanudación demasiado compleja antes de tener pipeline real;
  - duplicar reglas entre dominio y CLI.
- Criterio de salida:
  - la aplicación puede decidir qué etapas ejecutar o reutilizar en función de metadata existente.

#### WI-02-01 - Introducir modelo de estado de pipeline en dominio

- Objetivo: encapsular las reglas de transición de etapas fuera del CLI.
- Contexto técnico: hoy `_select_stages()` en `ProcessMediaService` solo decide una tupla plana a partir de flags.
- Alcance funcional:
  - representar estado de etapa y transiciones válidas;
  - modelar prerequisitos entre `extract_audio`, `normalize_audio`, `transcribe`, `report` y `pdf`;
  - exponer una decisión de plan ejecutable para `process`, `transcribe`, `report` y `clean`.
- No se tocará:
  - implementación concreta de subprocess;
  - política de retries automáticos.
- Cambios esperados de CLI/API/artefactos/config:
  - ningún nuevo flag aún;
  - metadata enriquecida con resultados de transición;
  - posible módulo nuevo en `domain.artifacts`.
- Gherkin mínimo:

```gherkin
Scenario: Reanudar desde transcripción ya completada
  Given un artifact directory con "transcribe" completado
  When solicito ejecutar reporting
  Then el plan omite extracción y normalización
  And conserva los artefactos previos
```

- Happy path:
  - el dominio decide etapas sin depender de Typer;
  - reuso correcto de artefactos;
  - base común para comandos dedicados.
- Bad paths:
  - etapa posterior solicitada sin prerequisitos;
  - metadata corrupta;
  - ambigüedad entre `overwrite` y resume.
- Observabilidad/logging:
  - cada decisión de skip/reuse debe quedar en `pipeline.log`;
  - registrar motivo resumido por etapa.
- Pruebas unitarias/integración:
  - unitarias de transiciones válidas e inválidas;
  - integración de `process --only-report` usando metadata existente.
- Criterio de aceptación:
  - el plan de ejecución se deriva de metadata y reglas de dominio, no de `if` dispersos en CLI.

#### WI-02-02 - Política cerrada de conflictos y reutilización de artefactos

- Objetivo: distinguir claramente entre crear, reusar, sobrescribir y abortar.
- Contexto técnico: hoy `ArtifactPlanner.prepare()` solo conoce `overwrite` y trata cualquier directorio existente como conflicto.
- Alcance funcional:
  - definir cuándo `--overwrite` borra, recicla o reescribe archivos puntuales;
  - introducir validación de artifact directory incompleto;
  - preparar la entrada futura de `report` sobre directorios existentes.
- No se tocará:
  - borrado masivo de artefactos;
  - garbage collection automática.
- Cambios esperados de CLI/API/artefactos/config:
  - posible flag aditivo como `--resume`;
  - metadata de conflicto/lock liviana si resulta necesaria;
  - mensajes de error más precisos.
- Gherkin mínimo:

```gherkin
Scenario: Conflicto de artefactos sin overwrite
  Given un artifact directory ya existente
  When ejecuto "media-report process archivo.mp4"
  Then el comando falla con código de uso controlado
  And el mensaje indica cómo reusar o sobrescribir
```

- Happy path:
  - usuario entiende cómo continuar;
  - no se pisan artefactos silenciosamente;
  - `report` y `transcribe` podrán operar sobre directorios existentes.
- Bad paths:
  - directorio parcial imposible de interpretar;
  - metadata ausente con archivos presentes;
  - reuso accidental de artefactos incompatibles.
- Observabilidad/logging:
  - registrar detección de conflicto y decisión;
  - dejar trazas sin stack trace para errores previstos.
- Pruebas unitarias/integración:
  - unitarias del planner con combinaciones create/reuse/overwrite;
  - integración CLI para conflicto, resume y directorio incompleto.
- Criterio de aceptación:
  - el usuario nunca duda si el comando va a reusar o a sobrescribir artefactos.

#### WI-02-03 - Contrato de entrada para artifact directory

- Objetivo: establecer que `report` y `clean` puedan tomar un artifact directory como input oficial.
- Contexto técnico: hoy `process` recibe path de media o directorio de media; no hay contrato aún para operar sobre artefactos existentes.
- Alcance funcional:
  - definir heurística o validador explícito de artifact root;
  - documentar archivos mínimos requeridos por comando;
  - preparar lectura de metadata desde comandos futuros.
- No se tocará:
  - migraciones complejas entre esquemas viejos;
  - soporte de bases de datos o estado externo.
- Cambios esperados de CLI/API/artefactos/config:
  - validadores reutilizables en aplicación;
  - sin comando nuevo en este sprint, pero sí contrato interno listo.
- Gherkin mínimo:

```gherkin
Scenario: Directorio de artefactos válido para etapas posteriores
  Given un directorio con metadata y transcriptos requeridos
  When una etapa posterior valida su entrada
  Then el directorio es aceptado como artifact root oficial
```

- Happy path:
  - los comandos futuros comparten el mismo contrato de entrada;
  - menos lógica duplicada.
- Bad paths:
  - directorio con nombre correcto pero sin metadata;
  - metadata con paths absolutos inválidos;
  - artefactos requeridos ausentes.
- Observabilidad/logging:
  - registrar validación y faltantes detectados.
- Pruebas unitarias/integración:
  - unitarias del validador;
  - integración indirecta vía `process --only-report` o helpers de aplicación.
- Criterio de aceptación:
  - existe una forma única y reusable de reconocer artifact directories.

## Epic 03: Fase 3

### Sprint 03 - Extracción y normalización con FFmpeg

- Objetivo del sprint: ejecutar extracción y normalización reales manteniendo FFmpeg encapsulado en infraestructura.
- Alcance:
  - port de media processing;
  - adaptador FFmpeg con construcción y ejecución de comandos;
  - actualización de metadata por etapa.
- Fuera de alcance:
  - transcripción;
  - LLM;
  - PDF.
- Entregables:
  - `MediaProcessingService` operativo;
  - `audio_extracted.wav` y `audio_normalized.wav` generados;
  - errores claros cuando falta `ffmpeg`.
- Dependencias: Sprints 01-02.
- Riesgos:
  - diferencias de comportamiento entre audio y video;
  - dependencia real de binario externo en pruebas.
- Criterio de salida:
  - `process` ejecuta extracción y normalización en Linux/macOS con pruebas unitarias y al menos una integración con binario mockeado.

#### WI-03-01 - Formalizar el port `MediaProcessingService`

- Objetivo: sacar el conocimiento de FFmpeg de la capa de aplicación.
- Contexto técnico: existe `FFmpegService.build_extract_command()` pero no un port estable ni una implementación completa para normalización.
- Alcance funcional:
  - definir port de dominio para extracción y normalización;
  - modelar resultados y errores;
  - agregar soporte tanto para input audio como video.
- No se tocará:
  - paralelización de FFmpeg;
  - soporte de formatos exóticos fuera de los ya clasificados por scanner.
- Cambios esperados de CLI/API/artefactos/config:
  - sin cambios públicos obligatorios;
  - nuevas clases en `domain.media.ports` o módulo equivalente;
  - artefactos `audio_extracted.wav` y `audio_normalized.wav` como outputs reales.
- Gherkin mínimo:

```gherkin
Scenario: Extraer audio desde video
  Given un archivo de video soportado
  When la aplicación ejecuta la etapa de extracción
  Then se genera "audio_extracted.wav"
  And la metadata marca "extract_audio" como completada
```

- Happy path:
  - video produce audio mono a 16 kHz;
  - audio de entrada puede pasar directo a normalización si aplica;
  - resultados persistidos en artifact dir.
- Bad paths:
  - binario `ffmpeg` ausente;
  - comando retorna código no cero;
  - output parcial o corrupto.
- Observabilidad/logging:
  - log de comando ejecutado sin secretos;
  - duración, exit code y paths de salida;
  - resumen de stderr en metadata si falla.
- Pruebas unitarias/integración:
  - unitarias de builders de comando;
  - tests de mapping de errores;
  - integración con monkeypatch/subprocess fake.
- Criterio de aceptación:
  - aplicación depende del port, no de listas de strings FFmpeg.

#### WI-03-02 - Cablear `process` a etapas reales de audio

- Objetivo: pasar de planificación a ejecución real en las primeras dos etapas.
- Contexto técnico: `ProcessMediaService.process()` hoy solo crea artefactos y devuelve plan.
- Alcance funcional:
  - ejecutar etapas `extract_audio` y `normalize_audio`;
  - actualizar metadata y log en tiempo real;
  - dejar preparado el handoff a transcripción.
- No se tocará:
  - report generation;
  - reintentos inteligentes;
  - ejecución paralela de múltiples archivos.
- Cambios esperados de CLI/API/artefactos/config:
  - `process` pasa de planning-only a ejecución parcial real;
  - posible salida de consola con resumen de etapas ejecutadas;
  - sin cambio de nombre de flags.
- Gherkin mínimo:

```gherkin
Scenario: Procesar archivo y detenerse antes de transcribir
  Given un archivo soportado
  When ejecuto "media-report process archivo.mp4 --only-transcribe"
  Then se ejecutan extracción y normalización
  And quedan listos los WAV para transcripción
```

- Happy path:
  - audio normalizado persistido;
  - etapas previas marcadas como completadas;
  - pipeline listo para sprint 04.
- Bad paths:
  - normalización falla y deja solo extracción;
  - metadata no refleja fallo parcial;
  - directorio existente contiene WAV incompatibles.
- Observabilidad/logging:
  - inicio/fin por etapa;
  - resumen de skip/reuse por archivo;
  - logging consistente con `pipeline.log`.
- Pruebas unitarias/integración:
  - integración `process` con stub de media processor;
  - tests de fallo parcial preservando `audio_extracted.wav`.
- Criterio de aceptación:
  - `process` deja el pipeline realmente avanzado, no solo planificado.

## Epic 04: Fase 4

### Sprint 04 - Transcripción y comando `transcribe`

- Objetivo del sprint: cerrar el pipeline de transcripción y exponer un comando público dedicado.
- Alcance:
  - provider contract para texto crudo y segmentos;
  - adaptador `faster-whisper`;
  - comando `transcribe` y reutilización desde `process`.
- Fuera de alcance:
  - limpieza semántica de transcriptos;
  - report generation;
  - diarización.
- Entregables:
  - `transcript_raw.txt` y `transcript_segments.json`;
  - `media-report transcribe`;
  - warning/documentación clara sobre dependencia opcional `transcription`.
- Dependencias: Sprint 03.
- Riesgos:
  - coste de dependencia `faster-whisper`;
  - variación de formatos de salida;
  - necesidad de fixtures reales mínimas.
- Criterio de salida:
  - existe una ruta soportada para transcribir un artefacto normalizado o un archivo fuente desde CLI.

#### WI-04-01 - Expandir `TranscriptionProvider` para salida estructurada

- Objetivo: hacer que el port devuelva suficiente información para reporting y limpieza futura.
- Contexto técnico: hoy `TranscriptionProvider.transcribe()` devuelve solo `str`.
- Alcance funcional:
  - definir entidades de segmento y resultado de transcripción;
  - persistir texto plano y JSON estructurado;
  - incluir idioma detectado cuando esté disponible.
- No se tocará:
  - diarización;
  - alineación word-level;
  - storage externo.
- Cambios esperados de CLI/API/artefactos/config:
  - `transcript_segments.json` con contrato estable;
  - posible campo de idioma en metadata;
  - sin flags nuevos obligatorios salvo `transcribe`.
- Gherkin mínimo:

```gherkin
Scenario: Transcribir audio normalizado
  Given un "audio_normalized.wav" disponible
  When la etapa de transcripción se ejecuta
  Then se guarda "transcript_raw.txt"
  And se guarda "transcript_segments.json"
```

- Happy path:
  - resultado consistente entre texto y segmentos;
  - idioma persistido;
  - base utilizable por `clean` y `report`.
- Bad paths:
  - modelo no disponible;
  - provider devuelve segmentos vacíos;
  - JSON no serializable.
- Observabilidad/logging:
  - registrar modelo usado y duración;
  - no loggear contenido completo del transcript salvo referencia a artefacto.
- Pruebas unitarias/integración:
  - unitarias de serialización de segmentos;
  - tests de adapters con provider fake;
  - integración CLI con stub de transcripción.
- Criterio de aceptación:
  - el resultado de transcripción ya no obliga a reinterpretar texto libre aguas abajo.

#### WI-04-02 - Implementar `FasterWhisperProvider` y feature gating

- Objetivo: soportar la primera implementación real del port de transcripción.
- Contexto técnico: `faster_whisper_provider.py` hoy solo levanta `NotImplementedError`.
- Alcance funcional:
  - cargar modelo según config;
  - mapear salida del proveedor al contrato del dominio;
  - fallar con mensaje claro si la extra opcional no está instalada.
- No se tocará:
  - otros proveedores de transcripción;
  - descarga automática de modelos fuera del flujo explícito del proveedor.
- Cambios esperados de CLI/API/artefactos/config:
  - uso efectivo de `MEDIA_REPORT_WHISPER_MODEL`;
  - mensajes de `doctor` y `transcribe` sobre dependencia opcional.
- Gherkin mínimo:

```gherkin
Scenario: Ejecutar transcribe sin extra instalada
  Given una instalación sin la extra "transcription"
  When ejecuto "media-report transcribe archivo.mp3"
  Then el comando falla con mensaje accionable
  And no imprime stack trace innecesario
```

- Happy path:
  - provider inicializa modelo configurado;
  - output persistido;
  - integración clara con config.
- Bad paths:
  - paquete opcional ausente;
  - modelo inválido;
  - error interno del provider.
- Observabilidad/logging:
  - registrar provider, modelo y duración;
  - mensaje de warning si fallback local no está disponible.
- Pruebas unitarias/integración:
  - unitarias de import lazy/failure mapping;
  - integración con monkeypatch simulando proveedor instalado/no instalado.
- Criterio de aceptación:
  - `faster-whisper` queda enchufado sin meter lógica del modelo en CLI.

#### WI-04-03 - Exponer `media-report transcribe`

- Objetivo: ofrecer un comando público estable para etapa de transcripción.
- Contexto técnico: hoy `process --only-transcribe` es un placeholder; falta una unidad pública más precisa.
- Alcance funcional:
  - aceptar archivo de media o artifact directory;
  - reusar extracción/normalización si faltan;
  - permitir `--language`, `--model` y `--overwrite` de forma aditiva.
- No se tocará:
  - generación de reportes;
  - limpieza de texto;
  - ejecución batch en background.
- Cambios esperados de CLI/API/artefactos/config:
  - nuevo comando `transcribe`;
  - `process --only-transcribe` reutiliza el mismo caso de uso;
  - README y help text actualizados.
- Gherkin mínimo:

```gherkin
Scenario: Transcribir archivo fuente desde comando dedicado
  Given un archivo de media válido
  When ejecuto "media-report transcribe archivo.mp3 --language es"
  Then se crean o reutilizan los artefactos previos necesarios
  And la transcripción termina en el artifact directory del archivo
```

- Happy path:
  - el comando sirve tanto para primera ejecución como para resume;
  - salida clara por archivo.
- Bad paths:
  - artifact directory inválido;
  - prerequisitos ausentes;
  - `--only-transcribe` diverge semánticamente de `transcribe`.
- Observabilidad/logging:
  - registrar fuente de entrada y artifact root;
  - etapas ejecutadas vs reutilizadas.
- Pruebas unitarias/integración:
  - integración de CLI para archivo único y artifact directory;
  - tests de compatibilidad con `process --only-transcribe`.
- Criterio de aceptación:
  - `transcribe` es el contrato público recomendado para esta etapa y `process` queda como orquestador amplio.

## Epic 05: Fase 5

### Sprint 05 - Prompting, LLM y comando `report`

- Objetivo del sprint: producir `report.md` reproducible desde transcriptos y provider LLM configurado.
- Alcance:
  - renderizado de prompt desde recursos empaquetados;
  - integración Ollama y OpenAI-compatible;
  - comando `report`.
- Fuera de alcance:
  - PDF;
  - limpieza semántica avanzada si compite con el sprint;
  - múltiples providers LLM adicionales.
- Entregables:
  - `prompt_used.md`, `llm_response_raw.txt`, `report.md`;
  - warning de proveedor remoto;
  - `media-report report`.
- Dependencias: Sprint 04.
- Riesgos:
  - template context insuficiente;
  - respuestas LLM no estructuradas;
  - fuga accidental de secretos o headers.
- Criterio de salida:
  - un transcripto válido puede convertirse en `report.md` desde CLI y también desde `process`.

#### WI-05-01 - Servicio de render de prompt y contexto de reporte

- Objetivo: convertir artefactos de transcripción en prompts deterministas y auditables.
- Contexto técnico: los templates ya viven en `src/media_report/templates/prompts`, pero hoy solo se listan y validan por nombre.
- Alcance funcional:
  - definir contexto mínimo de prompt;
  - persistir `prompt_used.md`;
  - soportar plantillas `generic`, `meeting`, `interview`, `technical_report`, `class_notes`.
- No se tocará:
  - editor visual de prompts;
  - plantillas remotas;
  - parametrización arbitraria desde CLI más allá de opciones justificadas.
- Cambios esperados de CLI/API/artefactos/config:
  - `report` acepta `--template`;
  - `metadata.json` guarda template efectivo y quizá hash de prompt;
  - `prompt_used.md` se vuelve artefacto obligatorio de reporting.
- Gherkin mínimo:

```gherkin
Scenario: Generar prompt para template meeting
  Given un transcripto y metadata válidos
  When ejecuto la etapa de reporting con "--template meeting"
  Then se persiste "prompt_used.md"
  And el prompt incorpora el contenido del transcripto y el contexto del archivo
```

- Happy path:
  - prompt reproducible;
  - template cargada desde paquete instalado;
  - sin dependencia de paths del repo.
- Bad paths:
  - template inexistente;
  - transcripto vacío;
  - prompt excesivo sin control de tamaño.
- Observabilidad/logging:
  - registrar template seleccionada y tamaño del prompt;
  - no loggear el prompt completo en consola.
- Pruebas unitarias/integración:
  - unitarias de carga de templates y render;
  - integración `templates list` y `report` con template válida/inválida.
- Criterio de aceptación:
  - cualquier reporte puede auditar qué prompt exacto se usó.

#### WI-05-02 - Implementar providers LLM reales y redacción de secretos

- Objetivo: soportar generación Markdown con un proveedor local y uno remoto compatible OpenAI.
- Contexto técnico: existen `OllamaProvider` y `OpenAICompatibleProvider`, pero ambos están scaffolded.
- Alcance funcional:
  - implementar llamadas HTTP encapsuladas en infraestructura;
  - soportar selección explícita por configuración o flag;
  - mantener warning cuando `llm_provider != "ollama"`.
- No se tocará:
  - streaming complejo;
  - retries sofisticados;
  - múltiples backends remotos adicionales.
- Cambios esperados de CLI/API/artefactos/config:
  - `MEDIA_REPORT_OPENAI_API_KEY` y base URLs usados de forma real;
  - `doctor` puede detectar configuración incompleta;
  - errores con provider/model sin imprimir tokens.
- Gherkin mínimo:

```gherkin
Scenario: Generar reporte con proveedor remoto
  Given una configuración "openai-compatible" válida
  When ejecuto "media-report report artefactos --provider openai-compatible"
  Then veo un warning sobre procesamiento remoto
  And se genera "llm_response_raw.txt"
  And nunca se imprime la API key
```

- Happy path:
  - Ollama local funciona por defecto;
  - proveedor remoto funciona por opt-in explícito;
  - respuesta cruda persistida.
- Bad paths:
  - API key ausente;
  - timeout o HTTP error;
  - salida vacía o no Markdown.
- Observabilidad/logging:
  - registrar provider, modelo, latencia y código HTTP resumido;
  - redacción estricta de secretos.
- Pruebas unitarias/integración:
  - unitarias de adapters HTTP con `httpx` mockeado;
  - tests de redacción de errores;
  - integración CLI con proveedor fake local/remoto.
- Criterio de aceptación:
  - reporting real funciona sin violar la política de secretos.

#### WI-05-03 - Exponer `media-report report`

- Objetivo: dar una entrada pública para generar o regenerar reportes desde un artifact directory.
- Contexto técnico: el reporte depende de transcriptos, template y provider, y no debe forzar rehacer etapas previas.
- Alcance funcional:
  - aceptar artifact directory como input principal;
  - permitir override de provider, model, template y output format;
  - reutilizar desde `process --only-report`.
- No se tocará:
  - render PDF;
  - limpieza avanzada del transcripto;
  - almacenamiento remoto de resultados.
- Cambios esperados de CLI/API/artefactos/config:
  - nuevo comando `report`;
  - `process --only-report` pasa a ser compatibilidad sobre el mismo caso de uso;
  - README actualizado.
- Gherkin mínimo:

```gherkin
Scenario: Regenerar reporte desde artefactos existentes
  Given un artifact directory con transcripción completada
  When ejecuto "media-report report ruta_al_artifact_dir --template technical_report"
  Then se genera o actualiza "report.md"
  And no se reejecuta transcripción
```

- Happy path:
  - permite iterar templates y modelos;
  - no rehace etapas upstream.
- Bad paths:
  - artifact dir sin transcripto;
  - provider no configurado;
  - conflicto de overwrite sobre `report.md`.
- Observabilidad/logging:
  - registrar inputs del reporte y etapas omitidas;
  - log separado de prompt y respuesta cruda.
- Pruebas unitarias/integración:
  - integración CLI sobre artifact directory válido e inválido;
  - tests de compatibilidad con `process --only-report`.
- Criterio de aceptación:
  - el usuario puede regenerar reportes de forma aislada y trazable.

## Epic 06: Fase 6

### Sprint 06 - PDF y flujo end-to-end de `process`

- Objetivo del sprint: completar el pipeline hasta `report.pdf` y consolidar `process` como comando extremo a extremo.
- Alcance:
  - `DocumentRenderer` real con Pandoc y plantilla TeX empaquetada;
  - orquestación completa de `process`;
  - manejo de fallos parciales preservando Markdown.
- Fuera de alcance:
  - QA visual profunda de PDF;
  - múltiples engines PDF configurables más allá del mínimo razonable;
  - optimizaciones de rendimiento.
- Entregables:
  - `report.pdf`;
  - metadata con estados finales completos;
  - smoke tests end-to-end con doubles de infraestructura y un camino de integración controlado.
- Dependencias: Sprint 05.
- Riesgos:
  - presencia de `pandoc` y `xelatex/lualatex`;
  - diferencias tipográficas por plataforma;
  - pipeline largo y frágil si la orquestación no queda limpia.
- Criterio de salida:
  - `process` produce `report.md` y `report.pdf`, o deja trazabilidad clara si PDF falla.

#### WI-06-01 - Implementar `DocumentRenderer` y Pandoc adapter

- Objetivo: renderizar PDF desde Markdown usando recursos empaquetados.
- Contexto técnico: `PandocService.build_command()` ya existe, pero no ejecuta ni resuelve template desde recurso instalado.
- Alcance funcional:
  - cargar `default.tex` con `importlib.resources`;
  - ejecutar Pandoc con engine soportado;
  - persistir `report.pdf`.
- No se tocará:
  - edición avanzada de plantilla TeX;
  - múltiples themes PDF en este sprint;
  - importación PDF como input.
- Cambios esperados de CLI/API/artefactos/config:
  - uso real de `report.pdf`;
  - `doctor` potencialmente valida `pandoc` y motor TeX con mayor precisión.
- Gherkin mínimo:

```gherkin
Scenario: Renderizar PDF desde Markdown existente
  Given un "report.md" válido
  When ejecuto la etapa PDF
  Then se genera "report.pdf"
  And la metadata marca "pdf" como completada
```

- Happy path:
  - template empaquetada funciona desde instalación;
  - PDF generado en artifact dir.
- Bad paths:
  - `pandoc` ausente;
  - engine TeX ausente;
  - `report.md` inválido o vacío.
- Observabilidad/logging:
  - registrar comando, engine usado y tamaño del output;
  - stderr resumido en fallo.
- Pruebas unitarias/integración:
  - unitarias del adapter y resolución de recursos;
  - integración con subprocess fake;
  - smoke test instalado cuando el entorno tenga dependencias.
- Criterio de aceptación:
  - el render PDF funciona desde wheel instalada sin paths relativos al repo.

#### WI-06-02 - Cerrar la orquestación completa de `process`

- Objetivo: convertir `process` en la ruta principal end-to-end.
- Contexto técnico: `process` empezó como bootstrap planner y debe terminar siendo un comando de pipeline completo.
- Alcance funcional:
  - ejecutar descubrimiento, audio, transcripción, reporting y PDF;
  - reutilizar los mismos casos de uso de `transcribe` y `report`;
  - respetar `--only-transcribe` y `--only-report` como compatibilidad aditiva.
- No se tocará:
  - daemonización;
  - colas de trabajo;
  - TUI.
- Cambios esperados de CLI/API/artefactos/config:
  - output de consola más orientado a resumen de pipeline;
  - compatibilidad preservada con banderas existentes;
  - sin renombrar `process`.
- Gherkin mínimo:

```gherkin
Scenario: Ejecutar pipeline completo para archivo único
  Given un archivo de media válido y dependencias disponibles
  When ejecuto "media-report process archivo.mp4"
  Then se generan transcriptos, "report.md" y "report.pdf"
  And cada etapa queda trazada en metadata y pipeline.log
```

- Happy path:
  - `process` cubre el caso principal del producto;
  - los comandos dedicados comparten la misma lógica de aplicación.
- Bad paths:
  - falla PDF pero se conserva `report.md`;
  - falla LLM pero se conserva transcripción;
  - error en un archivo no corrompe artefactos de otro.
- Observabilidad/logging:
  - resumen por etapa y por archivo;
  - señal clara de fallo parcial versus total.
- Pruebas unitarias/integración:
  - integración CLI con doubles de todas las etapas;
  - casos de fallo parcial preservando artefactos previos.
- Criterio de aceptación:
  - `process` ya representa el workflow del producto y no solo un bootstrap.

## Epic 07: Fase 7

### Sprint 07 - Packaging hardening, CI/CD y publicación

- Objetivo del sprint: tratar distribución e instalación como artefactos de primera clase.
- Alcance:
  - build y validación automatizados;
  - smoke tests de instalación;
  - pipeline de release a TestPyPI/PyPI con trusted publishing.
- Fuera de alcance:
  - nuevos features de pipeline de media;
  - soporte oficial de Windows;
  - marketplace de plugins o extensiones.
- Entregables:
  - workflow CI con `pytest`, `ruff`, `build`, `twine check`;
  - smoke tests `uv tool install .` y `pipx install .`;
  - guía de release cerrada para TestPyPI/PyPI.
- Dependencias: Sprint 06.
- Riesgos:
  - diferencias entre entorno dev y entorno instalado;
  - fallos de empaquetado de recursos;
  - credenciales mal configuradas para publicación.
- Criterio de salida:
  - cualquier release candidate puede instalarse y ejecutar `doctor`, `templates list` y un smoke test de `process`.

#### WI-07-01 - Automatizar CI de calidad y packaging

- Objetivo: ejecutar en cada cambio el mínimo de calidad requerido por distribución.
- Contexto técnico: hoy existen comandos documentados, pero no hay evidencia de automatización de CI/CD en el repo inspeccionado.
- Alcance funcional:
  - `uv sync --extra dev`;
  - `uv run pytest`;
  - `uv run ruff check .`;
  - `uv run ruff format --check .`;
  - `uv run python -m build`;
  - `uv run twine check dist/*`.
- No se tocará:
  - benchmarks;
  - tests contra servicios remotos reales.
- Cambios esperados de CLI/API/artefactos/config:
  - workflows CI;
  - documentación de gates obligatorios.
- Gherkin mínimo:

```gherkin
Scenario: Validar paquete en CI
  Given un commit listo para merge
  When corre la pipeline de CI
  Then el wheel y el sdist se construyen
  And "twine check" valida metadatos y artefactos
```

- Happy path:
  - CI falla temprano;
  - packaging se valida en cada PR.
- Bad paths:
  - recurso empaquetado faltante;
  - tests verdes en source checkout pero rojos al construir wheel.
- Observabilidad/logging:
  - publicar artefactos de build y logs de smoke tests.
- Pruebas unitarias/integración:
  - smoke de instalación como parte de CI;
  - prueba explícita de carga de templates desde wheel.
- Criterio de aceptación:
  - ningún release candidate avanza sin build y verificación de paquete.

#### WI-07-02 - Smoke tests de instalación real

- Objetivo: validar comportamiento desde entorno instalado, no solo desde checkout.
- Contexto técnico: `docs/release.md` ya exige `uv tool install .` y `pipx install .`.
- Alcance funcional:
  - instalar wheel localmente;
  - ejecutar `media-report doctor`;
  - ejecutar `media-report templates list`;
  - ejecutar `media-report process` sobre fixture realista.
- No se tocará:
  - publicación directa a producción desde ramas de feature;
  - matrices extensas de sistemas operativos fuera del alcance oficial.
- Cambios esperados de CLI/API/artefactos/config:
  - posibles ajustes en empaquetado y entrypoint;
  - fixtures compatibles con instalación.
- Gherkin mínimo:

```gherkin
Scenario: Smoke test desde herramienta instalada
  Given un wheel construido localmente
  When instalo el paquete con "uv tool install"
  Then "media-report doctor" y "media-report templates list" funcionan
  And "media-report process" crea artefactos sobre una fixture soportada
```

- Happy path:
  - entrypoint disponible;
  - recursos empaquetados resueltos;
  - smoke reproducible.
- Bad paths:
  - scripts no expuestos;
  - plantillas no incluidas en wheel;
  - dependencia opcional faltante sin mensaje claro.
- Observabilidad/logging:
  - conservar logs de instalación y ejecución.
- Pruebas unitarias/integración:
  - smoke scripts invocados por CI/release;
  - documentación de prerequisitos de entorno.
- Criterio de aceptación:
  - el paquete se comporta igual instalado que desde el repo.

#### WI-07-03 - Preparar publicación TestPyPI/PyPI y changelog de release

- Objetivo: cerrar el circuito de publicación repetible.
- Contexto técnico: el proyecto declara PyPI como target principal, pero falta automatizar publicación y endurecer la disciplina de release.
- Alcance funcional:
  - trusted publishing o credenciales seguras;
  - release checklist ejecutable;
  - proceso de versionado y changelog.
- No se tocará:
  - auto-versionado opaco;
  - generación de release notes desde IA sin revisión humana.
- Cambios esperados de CLI/API/artefactos/config:
  - docs de release actualizadas;
  - posible workflow manual de publish.
- Gherkin mínimo:

```gherkin
Scenario: Publicar un release candidate
  Given un tag de versión aprobado
  When ejecuto el flujo de publicación
  Then el paquete se publica en TestPyPI o PyPI
  And el changelog y la versión quedan consistentes
```

- Happy path:
  - publicación repetible y auditable;
  - reducción de pasos manuales frágiles.
- Bad paths:
  - versión de paquete y changelog desalineados;
  - fallo de autenticación;
  - release incompleto sin smoke tests.
- Observabilidad/logging:
  - evidencia de publicación y checks ejecutados.
- Pruebas unitarias/integración:
  - validación de metadatos de release;
  - dry run documentado cuando no haya credenciales.
- Criterio de aceptación:
  - publicar deja de depender de conocimiento tácito del mantenedor.

## Epic 08: Fase 8

### Sprint 08 - `clean`, extensibilidad y activos de portfolio

- Objetivo del sprint: completar la superficie pública planeada y convertir el proyecto en un artefacto demostrable y extensible.
- Alcance:
  - comando `clean` sobre transcriptos;
  - documentación de extensión para nuevos providers y templates;
  - README/demo/artículo/ficha de portfolio.
- Fuera de alcance:
  - diarización real;
  - WhisperX;
  - job queues, watchers o TUI.
- Entregables:
  - `media-report clean`;
  - guía para agregar `LLMProvider`, `TranscriptionProvider` y templates;
  - assets de portfolio y demo reproducible.
- Dependencias: Sprints 04-07. `clean` entra solo después de estabilizar el contrato de transcriptos.
- Riesgos:
  - derivar `clean` antes de tener claro el artefacto `transcript_clean.md`;
  - mezclar trabajo técnico y marketing sin criterio de prioridad.
- Criterio de salida:
  - el proyecto queda demostrable de punta a punta y un tercero puede extenderlo sin leer todo el repo.

#### WI-08-01 - Exponer `media-report clean`

- Objetivo: introducir una etapa pública para limpiar y segmentar transcriptos preservando raw data.
- Contexto técnico: el workflow objetivo ya contempla `transcript_clean.md`, pero el baseline actual aún no define ni comando ni algoritmo.
- Alcance funcional:
  - aceptar artifact directory con `transcript_raw.txt` y opcionalmente `transcript_segments.json`;
  - producir `transcript_clean.md`;
  - dejar `process` listo para insertar esta etapa entre `transcribe` y `report` cuando se active.
- No se tocará:
  - reescritura creativa del contenido;
  - clasificación temática avanzada;
  - dependencias de modelos LLM para limpiar texto.
- Cambios esperados de CLI/API/artefactos/config:
  - nuevo comando `clean`;
  - etapa `clean` añadida al esquema de metadata si se adopta formalmente;
  - posible flag `--max-line-length` o `--speaker-markers` solo si es imprescindible.
- Gherkin mínimo:

```gherkin
Scenario: Limpiar transcripto desde artifact directory
  Given un artifact directory con "transcript_raw.txt"
  When ejecuto "media-report clean artefactos"
  Then se genera "transcript_clean.md"
  And el transcripto crudo permanece intacto
```

- Happy path:
  - texto limpio y segmentado;
  - contrato claro para `report`.
- Bad paths:
  - transcripto ausente;
  - segmentos corruptos;
  - limpieza destruye información estructural relevante.
- Observabilidad/logging:
  - registrar heurísticas aplicadas y tamaño de salida;
  - no sobrescribir transcriptos crudos.
- Pruebas unitarias/integración:
  - unitarias de normalización de texto;
  - integración CLI sobre artifact directory.
- Criterio de aceptación:
  - `clean` queda como comando público útil y no bloquea la trazabilidad.

#### WI-08-02 - Documentar extensibilidad para providers y templates

- Objetivo: reducir el costo de agregar nuevas integraciones.
- Contexto técnico: AGENTS.md ya fija reglas para añadir providers y templates, pero falta documentación operativa para un colaborador externo.
- Alcance funcional:
  - guía de `LLMProvider`;
  - guía de `TranscriptionProvider`;
  - guía para prompts y plantillas PDF.
- No se tocará:
  - sistema de plugins dinámicos;
  - compatibilidad ABI entre versiones.
- Cambios esperados de CLI/API/artefactos/config:
  - docs nuevas o ampliadas bajo `docs/`;
  - referencias desde README.
- Gherkin mínimo:

```gherkin
Scenario: Agregar un nuevo provider siguiendo la guía
  Given un desarrollador nuevo en el proyecto
  When sigue la documentación de extensibilidad
  Then sabe qué port implementar
  And sabe qué artefactos y pruebas debe añadir
```

- Happy path:
  - extensión predecible;
  - menos decisiones implícitas.
- Bad paths:
  - guía desalineada con la arquitectura real;
  - olvidar reglas de secretos o empaquetado.
- Observabilidad/logging:
  - no aplica de forma directa.
- Pruebas unitarias/integración:
  - no requiere tests de runtime, pero sí revisión cruzada con ejemplos reales del repo.
- Criterio de aceptación:
  - la guía cubre puertos, capas, artefactos y pruebas obligatorias.

#### WI-08-03 - Demo, README final y assets de portfolio

- Objetivo: convertir el proyecto en un entregable demostrable además de instalable.
- Contexto técnico: el README actual describe `0.1.0` como bootstrap; una vez completado el pipeline, la documentación pública debe reflejar el flujo real.
- Alcance funcional:
  - README con flujo completo;
  - demo grabable o script reproducible;
  - artículo técnico corto y ficha de portfolio.
- No se tocará:
  - sitio web completo del producto;
  - materiales comerciales extensos.
- Cambios esperados de CLI/API/artefactos/config:
  - documentación actualizada;
  - ejemplos de comandos `process`, `transcribe`, `clean`, `report`.
- Gherkin mínimo:

```gherkin
Scenario: Usuario nuevo evalúa el proyecto desde README
  Given el repositorio publicado
  When leo el README y sigo la demo
  Then puedo instalar el CLI y ejecutar un flujo representativo
```

- Happy path:
  - el valor del proyecto se entiende rápido;
  - demo alineada con el comportamiento real.
- Bad paths:
  - documentación desactualizada respecto al CLI;
  - demo depende de entorno no documentado.
- Observabilidad/logging:
  - no aplica más allá de scripts de demo.
- Pruebas unitarias/integración:
  - smoke script de demo, si se automatiza;
  - revisión manual de ejemplos de README como parte de release.
- Criterio de aceptación:
  - un tercero puede instalar, ejecutar y entender el proyecto sin asistencia del autor.

## Estrategia de Pruebas por Nivel

### Unitarias

- Dominio:
  - clasificación y estado de etapas;
  - política de resume/overwrite;
  - serialización de metadata;
  - reglas de `clean`.
- Adaptadores:
  - builders y mapeo de errores FFmpeg/Pandoc;
  - provider adapters de transcripción y LLM;
  - carga de recursos con `importlib.resources`;
  - redacción de secretos.

### Integración CLI

- `media-report --help`
- `media-report templates list`
- `media-report config init`
- `media-report config show`
- `media-report doctor`
- `media-report process` con archivo válido
- `media-report process` con carpeta recursiva
- `media-report transcribe`
- `media-report report`
- `media-report clean`
- conflictos de artefactos
- config ausente o inválida
- proveedor local vs remoto
- fallo parcial con preservación de artefactos
- reanudación desde metadata existente

### Smoke Tests de Instalación

- `uv run python -m build`
- `uv run twine check dist/*`
- `uv tool install .`
- `pipx install .`
- `media-report doctor`
- `media-report templates list`
- `media-report process tests/fixtures/example.mp3`

### Pruebas con archivos reales o semi-reales

- archivo único válido;
- carpeta recursiva;
- video que requiere extracción;
- artifact directory ya existente;
- binarios externos ausentes;
- dependencia opcional de transcripción ausente;
- provider remoto con credenciales inválidas;
- fallo de PDF con preservación de `report.md`.

## Orden de Implementación Recomendado

1. Cerrar contrato y metadata.
2. Introducir reanudación y artifact directory como concepto de entrada.
3. Cablear FFmpeg y ejecución parcial.
4. Implementar transcripción real y `transcribe`.
5. Implementar reporting LLM y `report`.
6. Completar PDF y end-to-end de `process`.
7. Endurecer packaging, CI/CD y release.
8. Añadir `clean` y documentación de extensibilidad/portfolio.

## Criterio Global de Done

- La implementación respeta capas `cli`, `application`, `domain` e `infrastructure`.
- Ningún secreto aparece en CLI, metadata ni logs.
- `media-report`, `process`, `doctor`, `config init`, `config show` y `templates list` siguen disponibles.
- `transcribe`, `report` y `clean` se añaden de forma aditiva.
- Recursos empaquetados siguen funcionando desde instalación.
- Hay tests unitarios e integración para cada cambio público.
- El paquete puede construirse, validarse e instalarse fuera del checkout.
- README y docs reflejan el estado real del flujo.
