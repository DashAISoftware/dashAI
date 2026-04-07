---
title: Replicabilidad y Exportación
sidebar_label: Replicabilidad y Exportación
sidebar_position: 5
---

# Replicabilidad y Exportación

## El Principio de Replicabilidad

DashAI está diseñado para que cualquier experimento pueda reproducirse. Esto es fundamental tanto para la enseñanza (un instructor puede repetir actividades entre cohortes) como para la investigación (los resultados deben ser verificables).

## Qué se Registra

Cada experimento en DashAI registra:

- **Configuración completa**: tarea, dataset, divisiones, columnas de características seleccionadas
- **Parámetros del modelo**: todos los hiperparámetros para cada ejecución
- **Métricas de evaluación**: por ejecución, por división y por nivel (paso/lote/prueba)
- **Transformaciones de datos**: la cadena de conversores aplicada al dataset

Estos datos se almacenan en SQLite (`~/.DashAI/db.sqlite`) con historial completo.

## Trazabilidad

Cada acción en DashAI deja un registro. Esto permite:

- Comparar ejecuciones con diferentes configuraciones ("¿qué cambié entre la ejecución 1 y la ejecución 2?")
- Auditar decisiones metodológicas
- Comunicar el proceso a terceros (revisores, colegas, supervisores)

El esquema de base de datos separa `ModelSession` (configuración del experimento) de `Run` (ejecución individual de entrenamiento), `Metric` (resultados de evaluación) y `Prediction` (salidas de inferencia).

## Exportación de Resultados

DashAI permite exportar resultados para su uso fuera de la plataforma:

- **Resultados de predicción** — descargables desde la vista de Predicciones
- **Gráficos de exploración** — generados por Exploradores dentro de un Notebook y disponibles para descargar como imágenes PNG directamente desde la interfaz
- **Configuración del experimento** — visible en la interfaz para referencia

:::warning
La exportación completa de la pipeline (una "receta" portátil que captura toda la cadena de preprocesamiento + modelo) está en desarrollo para versiones futuras. La versión actual admite la exportación de resultados y configuraciones básicas.
:::

:::info ¿Qué es un Notebook?
Un Notebook en DashAI es una sesión de trabajo con una copia mutable de un dataset. Agrupa Exploradores (visualizaciones) y Conversores (transformaciones) aplicados a esa copia. El dataset original nunca se modifica. Consulta [Diseño del Sistema → Notebook](./notebook) para más detalles.
:::

## Detalles del Almacenamiento de Datos

| Artefacto             | Ubicación de almacenamiento                                                                          |
| --------------------- | ---------------------------------------------------------------------------------------------------- |
| Conjuntos de datos    | Archivos Apache Arrow IPC en `~/.DashAI/`                                                            |
| Modelos entrenados    | Archivos pickle/joblib en `~/.DashAI/runs/{run_id}/`                                                 |
| Gráficos de optimización | Objetos Plotly serializados junto a la ejecución                                                  |
| Métricas              | Tabla `Metric` en `db.sqlite`                                                                        |
| Resultados de exploración | Imágenes PNG generadas por Exploradores dentro de un Notebook, referenciadas por la tabla `Explorer` |
