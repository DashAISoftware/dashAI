---
title: Ejemplos de Flujo de Trabajo
sidebar_label: Ejemplos de Flujo de Trabajo
---

## Entrenar un Modelo

Este ejemplo recorre el proceso completo de entrenamiento de un modelo de clasificación de texto, desde la interacción del usuario hasta los resultados finales.

### Paso 1: Crear una Sesión de Modelo

El usuario selecciona un dataset, una tarea, columnas de entrada/salida, métricas y divisiones de datos en el frontend. El frontend envía:

```
POST /api/v1/model-session/
{
    "dataset_id": 1,
    "task_name": "TextClassification",
    "input_columns": ["text"],
    "output_columns": ["label"],
    "train_metrics": ["Accuracy", "F1"],
    "validation_metrics": ["Accuracy"],
    "test_metrics": ["Accuracy"],
    "splits": { "train": 0.7, "validation": 0.15, "test": 0.15 }
}
```

La API crea un registro `ModelSession` en la base de datos y devuelve su ID.

### Paso 2: Crear una Ejecución

El usuario selecciona un modelo, configura sus parámetros y opcionalmente selecciona un optimizador de hiperparámetros. El frontend envía:

```
POST /api/v1/run/
{
    "model_session_id": 1,
    "model_name": "DistilBertTransformer",
    "parameters": { "learning_rate": 1e-5, "num_epochs": 3 },
    "optimizer_name": null,
    "optimizer_parameters": {},
    "goal_metric": "F1",
    "name": "DistilBERT run"
}
```

La API crea un registro `Run` con estado `NOT_STARTED`.

### Paso 3: Encolar el Trabajo de Entrenamiento

El frontend solicita la ejecución del trabajo:

```
POST /api/v1/job/
{
    "job_type": "ModelJob",
    "kwargs": { "run_id": 1 }
}
```

La API instancia un `ModelJob` con el `run_id` dado, llama a `job_queue.put(job)` y devuelve el ID del trabajo Huey al frontend de inmediato.

### Paso 4: Ejecución en Segundo Plano

El consumidor Huey recoge el `ModelJob` y llama a `job.run()`. Dentro de `run()`:

1. Cargar los registros `Run`, `ModelSession` y `Dataset` desde la base de datos.
2. Cargar el dataset desde su archivo Arrow.
3. Instanciar la clase `Task` (p. ej., `TextClassification`) y llamar a `prepare_for_task()` para validar y formatear los datos.
4. Dividir los datos en subconjuntos de entrenamiento/validación/test según las proporciones de división de la sesión.
5. Instanciar la clase `Model` (p. ej., `DistilBertTransformer`) con los parámetros del usuario mediante `validate_and_transform()`.
6. Llamar a `model.train(x_train, y_train, x_val, y_val)`.
7. Para cada división (entrenamiento, validación, test), llamar a `model.calculate_metrics()`, que calcula todas las métricas seleccionadas y las almacena en la tabla `Metric`.
8. Guardar el modelo entrenado en disco en `~/.DashAI/runs/{run_id}/`.
9. Actualizar el estado de `Run` de `STARTED` a `FINISHED`.

Si se ha configurado un optimizador de hiperparámetros, el paso 6 se reemplaza por `optimizer.optimize()`, que ejecuta múltiples pruebas, registra métricas por prueba (`LevelEnum.TRIAL`) y genera gráficos de visualización Plotly (historial, slice, contorno, importancia) guardados junto a la ejecución.

### Paso 5: Recuperar Resultados

El frontend consulta el estado hasta la finalización y recupera los resultados:

```
GET /api/v1/job/status/{job_id}         # Consultar hasta finalizar
GET /api/v1/run/{run_id}                # Obtener detalles de la ejecución con métricas
GET /api/v1/run/plot/{run_id}/history   # Obtener gráficos de optimización (si aplica)
```

El frontend muestra las métricas y cualquier visualización de optimización al usuario.

---

## Crear un Gráfico para un Dataset

Este ejemplo muestra cómo un usuario crea una exploración de gráfico de dispersión para un dataset.

### Paso 1: Seleccionar un Explorador

El frontend obtiene los exploradores disponibles del registro:

```
GET /api/v1/component/?select_types=["Explorer"]
```

La respuesta incluye los esquemas de los componentes, por lo que el frontend puede renderizar formularios de configuración dinámicamente. El usuario selecciona `ScatterPlotExplorer`.

### Paso 2: Configurar y Lanzar la Exploración

El usuario selecciona columnas y establece parámetros (p. ej., mapeo de color). El frontend valida los parámetros del explorador:

```
POST /api/v1/explorer/validate
{
    "exploration_type": "ScatterPlotExplorer",
    "columns": ["sepal_length", "sepal_width"],
    "parameters": { "color": "species" }
}
```

Tras la validación, el frontend crea el explorador y encola el trabajo:

```
POST /api/v1/explorer/
{
    "notebook_id": 1,
    "exploration_type": "ScatterPlotExplorer",
    "columns": ["sepal_length", "sepal_width"],
    "parameters": { "color": "species" }
}
```

Esto crea un registro `Explorer` en la base de datos y encola un `ExplorerJob`.

### Paso 3: Ejecución en Segundo Plano

El consumidor Huey recoge el `ExplorerJob` y llama a `job.run()`:

1. Cargar el registro `Explorer` y el dataset asociado.
2. Instanciar el componente `ScatterPlotExplorer`.
3. Llamar a `explorer.launch_exploration(dataset, explorer_info)`, que genera la visualización.
4. Llamar a `explorer.save_notebook()` para persistir la exploración como un notebook.
5. Llamar a `explorer.get_results()` para extraer la salida renderizable.
6. Guardar los resultados en disco y actualizar el estado del `Explorer` a `FINISHED`.

### Paso 4: Mostrar Resultados

El frontend recupera los resultados de la exploración:

```
GET /api/v1/explorer/{explorer_id}/results
```

La respuesta contiene los datos del gráfico (típicamente una especificación JSON de Plotly), que el frontend renderiza como una visualización interactiva.
