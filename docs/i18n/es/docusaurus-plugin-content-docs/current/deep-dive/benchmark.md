---
title: Benchmark comparativo
description: Comparación de DashAI con KNIME, Orange y WEKA en licencia, extensibilidad y cobertura de tareas.
sidebar_label: Benchmark comparativo
---

# Benchmark comparativo

Esta sección compara DashAI con KNIME Analytics Platform, Orange Data Mining y WEKA — las principales plataformas no-code ML open-source con arquitectura comparable.

---

## Metodología

El subconjunto de plataformas se delimitó a herramientas que cumplen simultáneamente tres condiciones: distribución open-source, operación sin código para el usuario final y arquitectura de catálogo extensible por terceros. KNIME Analytics Platform, Orange Data Mining y WEKA satisfacen ese criterio junto a DashAI.

La comparación se estructura en tres dimensiones medibles: condiciones de licencia, costo arquitectónico de extensión y cobertura paradigmática del catálogo nativo. Para la dimensión de extensibilidad, el boilerplate reportado corresponde a componentes de referencia implementados en cada plataforma a partir de sus repositorios oficiales; las fuentes están listadas al final de esta página.

---

## Licencia

DashAI se distribuye bajo licencia **MIT**, lo que permite su uso, modificación y distribución sin restricciones en proyectos comerciales o institucionales.

KNIME y Orange utilizan GPLv3; WEKA, GPL. Las tres licencias incluyen copyleft sobre obras derivadas distribuidas. KNIME presenta además funcionalidades adicionales — scheduling, despliegue gobernado, RBAC y la AI Extension — disponibles únicamente a través de KNIME Business Hub bajo licenciamiento comercial.

---

## Extensibilidad

DashAI expone doce clases base organizadas por rol funcional: `BaseModel`, `BaseMetric`, `BaseTask`, `BaseExplainer`, entre otras. Un nuevo componente se implementa subclasificando la abstracción correspondiente y declarando sus parámetros mediante un schema Pydantic. A partir del schema, la plataforma genera automáticamente el formulario de configuración en la interfaz, sin requerir código de frontend. El componente se distribuye vía PyPI e instala directamente desde la interfaz de DashAI.

El boilerplate resultante es de aproximadamente **20–40 líneas de código** para componentes simples (métricas, clasificadores básicos) y **70–110 líneas** para modelos con múltiples hiperparámetros, donde la mayor parte del código corresponde a la declaración del schema de parámetros.

Para referencia, los mecanismos de extensión de las otras plataformas evaluadas son los siguientes:

- **Orange** permite extensiones en Python, pero cada widget requiere acoplarse a Qt/PyQt e instanciar manualmente los controles de interfaz (≈50–70 líneas de código).
- **WEKA** se extiende en Java heredando de `AbstractClassifier` e implementando `buildClassifier(Instances)` y `distributionForInstance(Instance)` sobre la abstracción `Instances` (≈80–120 líneas de código).
- **KNIME**, en su vía oficial, requiere un plugin OSGi/Eclipse con cuatro clases Java — `NodeFactory`, `NodeModel`, `NodeDialog` y `NodeView` —, descriptores `plugin.xml` y `MANIFEST.MF`, y build con Maven/Tycho (≈150–250 líneas de código). Desde la versión 4.6 existe una vía experimental en Python (Labs) que genera UI desde declaraciones de parámetros, pero no reemplaza al camino Java como vía oficial y requiere herramientas de empaquetado propias (`pixi`, `knime.yml`).

### Arquitectura de interfaz

DashAI adopta una arquitectura cliente-servidor: un servidor FastAPI expone el catálogo de componentes, datasets, jobs de entrenamiento y resultados; un frontend React consume esa API vía HTTP. Cuando se registra un componente nuevo, el servidor expone su schema JSON y el frontend renderiza el formulario de configuración sin conocimiento previo del componente. El servidor puede ejecutarse en cualquier máquina y accederse desde un navegador, incluso desde otro dispositivo en la misma red local.

KNIME está construido sobre Eclipse RCP, Orange sobre PyQt y WEKA sobre Java Swing. En los tres casos la interfaz y la lógica de negocio corren en el mismo proceso; añadir un componente nuevo implica modificar también la capa de presentación.

---

## Cobertura de tareas

El catálogo nativo de DashAI cubre cuatro tareas predictivas — clasificación tabular, regresión, clasificación de texto y traducción — con aproximadamente quince modelos cada una, junto con cinco LLMs y once modelos de generación de imagen, todos ejecutables localmente. La optimización de hiperparámetros integra Optuna y HyperOpt.

La interfaz está disponible en español e inglés.

---

## Tabla comparativa

| Criterio                        |             KNIME              |       Orange        |         WEKA         |        **DashAI**         |
| ------------------------------- | :----------------------------: | :-----------------: | :------------------: | :-----------------------: |
| **Licenciamiento**              |                                |                     |                      |                           |
| Licencia                        |             GPLv3              |        GPLv3        |         GPL          |          **MIT**          |
| Sin paywall productivo          |               ✗                |          ✓          |          ✓           |           **✓**           |
| **Extensibilidad**              |                                |                     |                      |                           |
| Lenguaje de extensión           | Java (oficial) / Python (Labs) |  Python + Qt/PyQt   |         Java         |        **Python**         |
| Abstracciones por rol funcional |       1 (nodo genérico)        | 1 (widget genérico) |  6 jerarquías Java   |    **12 clases base**     |
| Tipo de interfaz                |       Desktop (Eclipse)        |   Desktop (PyQt)    | Desktop (Java Swing) | **Web (React + FastAPI)** |
| UI generada automáticamente     |               ⚠                |          ✗          |          ✗           |           **✓**           |
| Boilerplate por componente      |       150–250 LdC (Java)       |      50–70 LdC      |      80–120 LdC      |       **20–40 LdC**       |
| Soporte GPU                     |               ⚠                |          ⚠          |          ⚠           |           **⚠**           |
| Interfaz multiidioma (ES/EN)    |               ✗                |          ✗          |          ✗           |           **✓**           |
| **Catálogo nativo**             |                                |                     |                      |                           |
| Modelos clasificación tabular   |              ~11               |         ~12         |         ~39          |          **15**           |
| Modelos de regresión            |               ~9               |         ~12         |         ~32          |          **15**           |
| Modelos clasificación de texto  |               ⚠                |          ⚠          |      33 (BoW)†       |          **15**           |
| Modelos de traducción           |               ⚠                |          ✗          |          ✗           |           **9**           |
| LLMs ejecutados localmente      |               ✗                |          ✗          |          ✗           |           **5**           |
| Modelos de generación de imagen |               ⚠                |          ✗          |          ✗           |          **11**           |
| Frameworks de HPO integrados    |               1                |          0          |          1           |           **2**           |

**Convenciones:** ✓ soporte nativo completo · ⚠ parcial o requiere extensiones adicionales · ✗ no soportado · LdC = líneas de código.

:::note UI generada automáticamente
La vía oficial de KNIME (Java) requiere programar `NodeDialog` y `NodeView` manualmente. La vía experimental Python (Labs, desde v4.6) genera UI desde declaraciones de parámetros, pero no es el camino oficial. Orange y WEKA requieren código de interfaz manual en todos los casos.
:::

:::note Boilerplate por componente
Las 150–250 LdC de KNIME corresponden a la vía Java oficial. La vía Python (Labs) reduce ese número pero añade archivos de configuración propios (`knime.yml`, `pixi.toml`). En DashAI: ≈20–40 LdC para componentes simples; ≈70–110 LdC para modelos complejos con múltiples hiperparámetros, donde la mayor parte del código es la declaración del schema de parámetros.
:::

:::note Solapamiento entre tasks (DashAI)
9 de los 15 modelos de clasificación tabular tienen contraparte en regresión (Random Forest, Gradient Boosting, SVM, entre otros); cada task dispone de su propia implementación y configuración independiente. En WEKA, regresión y clasificación heredan de `AbstractClassifier` y se diferencian por capability flag.
:::

---

## Fuentes

- [knime-python-extension-template — `extension.py`](https://github.com/knime-oss/knime-python-extension-template/blob/releases/2025-12/src/extension.py)
- [Orange3 — `OWDataSamplerA.py`](https://github.com/biolab/orange3/blob/master/doc/development/source/orange-demo/orangedemo/OWDataSamplerA.py)
- [knime-examples — `UnitConverterNodeModel.java`](https://github.com/knime-oss/knime-examples/blob/master/org.knime.examples.unitconverter/src/org/knime/examples/unitconverter/UnitConverterNodeModel.java)
- [weka-3.8 — `NBTree.java`](https://github.com/Waikato/weka-3.8/blob/master/packages/internal/naiveBayesTree/src/main/java/weka/classifiers/trees/NBTree.java)
- [weka-3.8 — `SMOTE.java`](https://github.com/Waikato/weka-3.8/blob/master/packages/external/SMOTE/src/main/java/weka/filters/supervised/instance/SMOTE.java)
